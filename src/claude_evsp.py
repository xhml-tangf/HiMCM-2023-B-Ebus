"""Two-constant EVSP, with resource-correct block linking.

Derived from the user-supplied Claude specification, archived in materials/research/claude_plan.
Heuristic counts are upper bounds. Units: km and unwrapped service-day minutes.
"""
from __future__ import annotations
import argparse
from dataclasses import dataclass, field
import math
import sys
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import csr_matrix, coo_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching

EPS = 1e-7


@dataclass
class Instance:
    R: float
    T: float
    tau: np.ndarray
    w: np.ndarray
    trips: list
    labels: list = field(default_factory=list)
    nodes: list = field(default_factory=list)
    sparse_links: bool = False

    def __post_init__(self):
        self.tau, self.w = np.asarray(self.tau, float), np.asarray(self.w, float)
        self.trips = [tuple(t) for t in self.trips]
        self.n, self.m = len(self.trips), len(self.tau)
        if not self.R > 0 or not math.isfinite(self.T) or self.T < 0:
            raise ValueError('R must be positive; T finite and nonnegative')
        for a in (self.tau, self.w):
            if a.shape != (self.m, self.m) or not np.isfinite(a).all() or (a < 0).any() or np.any(np.diag(a) != 0):
                raise ValueError('travel matrices must be finite, nonnegative, square, with zero diagonals')
        if self.n:
            a = np.asarray(self.trips, float)
            if a.shape != (self.n, 5) or not np.isfinite(a).all():
                raise ValueError('invalid trip tuple')
            if (a[:, :2] < 0).any() or (a[:, :2] >= self.m).any() or (a[:, :2] != np.floor(a[:, :2])).any():
                raise ValueError('invalid trip node')
            if (a[:, 3] <= a[:, 2]).any() or (a[:, 4] < 0).any():
                raise ValueError('trip duration must be positive; distance nonnegative')
        else:
            a = np.empty((0, 5))
        self.o, self.dst = a[:, 0].astype(int), a[:, 1].astype(int)
        self.s, self.e, self.d = a[:, 2], a[:, 3], a[:, 4]
        self.order = np.lexsort((np.arange(self.n), self.e, self.s))


@dataclass
class Solution:
    buses: list
    stations: tuple
    edges: int = 0
    repairs: int = 0
    method: str = 'block heuristic'

    @property
    def N(self):
        return len(self.buses)

    @property
    def key(self):
        return (self.N, -self.edges)


def check_stations(inst, stations):
    stations = tuple(sorted(set(map(int, stations))))
    if any(c < 0 or c >= inst.m for c in stations):
        raise ValueError('station outside node set')
    return stations


def validate(inst, stations, buses):
    """Independent token simulation: never trusts solver block distances."""
    S = set(check_stations(inst, stations))
    seen, sessions, duties = [], [], []
    total_dh = total_service = charged_range = overnight_range = 0.0
    for vehicle, bus in enumerate(buses):
        if not bus:
            raise ValueError('empty vehicle duty')
        loc = t = None
        u = 0.0
        pending = None
        dh = service = 0.0
        for token in bus:
            if isinstance(token, (tuple, list)):
                if len(token) != 2 or token[0] != 'C' or loc is None or pending is not None or token[1] not in S:
                    raise ValueError('malformed or unselected charge')
                pending = int(token[1])
                continue
            if not isinstance(token, (int, np.integer)) or token < 0 or token >= inst.n:
                raise ValueError('invalid trip index')
            o, dst, s, e, d = inst.trips[token]
            o, dst = int(o), int(dst)
            if loc is None:
                u = d
            elif pending is None:
                if t + inst.tau[loc, o] > s + EPS:
                    raise ValueError('late direct connection')
                dh += inst.w[loc, o]
                u += inst.w[loc, o] + d
            else:
                c = pending
                before = u + inst.w[loc, c]
                start = t + inst.tau[loc, c]
                finish = start + inst.T
                if before > inst.R + EPS:
                    raise ValueError('cannot reach charger with remaining range')
                if finish + inst.tau[c, o] > s + EPS:
                    raise ValueError('late charge connection')
                sessions.append(dict(vehicle=vehicle, station=c, start=start, end=finish,
                                     replenished_range_km=float(before)))
                charged_range += before
                dh += inst.w[loc, c] + inst.w[c, o]
                u = inst.w[c, o] + d
            if u > inst.R + EPS:
                raise ValueError('range exceeded')
            seen.append(int(token))
            service += d
            loc, t, pending = dst, e, None
        if pending is not None:
            raise ValueError('trailing charge token')
        overnight_range += u
        total_dh += dh
        total_service += service
        duties.append(dict(vehicle=vehicle, service_km=float(service), deadhead_km=float(dh),
                           end_used_range_km=float(u)))
    if sorted(seen) != list(range(inst.n)):
        raise ValueError('trips omitted or duplicated')
    if abs(charged_range + overnight_range - total_dh - total_service) > max(1e-5, 1e-9*(total_dh+total_service)):
        raise ValueError('daily recharge does not close energy ledger')
    peaks = {}
    for c in S:
        events = [(s['start'], 1) for s in sessions if s['station'] == c and s['end'] > s['start']]
        events += [(s['end'], -1) for s in sessions if s['station'] == c and s['end'] > s['start']]
        current = peak = 0
        for _, change in sorted(events):
            current += change
            peak = max(peak, current)
        peaks[str(c)] = peak
    return dict(valid=True, trips=len(seen), vehicles=len(buses), service_km=float(total_service),
                deadhead_km=float(total_dh), daytime_charge_count=len(sessions),
                daytime_replenished_range_km=float(charged_range),
                overnight_replenished_range_km=float(overnight_range),
                charger_peak_by_node=peaks, sessions=sessions, duties=duties)


def pvr(inst):
    events = [(float(s), 1) for s in inst.s] + [(float(e), -1) for e in inst.e]
    current = peak = 0
    for _, delta in sorted(events):
        current += delta
        peak = max(peak, current)
    return peak


def _paths(match):
    incoming = set(int(j) for j in match if j >= 0)
    paths = []
    for i in range(len(match)):
        if i in incoming:
            continue
        path = []
        while i >= 0:
            path.append(int(i))
            if len(path) > len(match):
                raise ValueError('cycle in purported DAG')
            i = int(match[i])
        paths.append(path)
    if sum(map(len, paths)) != len(match):
        raise ValueError('non-DAG matching')
    return paths


def diesel(inst):
    """Exact matching: short-connection seed followed by FULL-graph augmentation.

    The 10-minute seed saves memory. Termination is certified by absence of
    augmenting paths in the complete graph, never by a waiting-time cutoff.
    """
    chunks, ptr = [], [0]
    order=inst.order;starts=inst.s[order]
    for i in range(inst.n):
        # Nonnegative travel times make this time slice exact. It avoids
        # scanning 100,000 trips to find a few minutes of possible departures.
        lo=np.searchsorted(starts,inst.e[i]-EPS)
        hi=np.searchsorted(starts,inst.e[i]+10,side='right')
        possible=order[lo:hi]
        js=np.sort(possible[inst.e[i]+inst.tau[inst.dst[i],inst.o[possible]]<=inst.s[possible]+EPS]).astype(np.int32)
        chunks.append(js)
        ptr.append(ptr[-1] + len(js))
    indices = np.concatenate(chunks) if chunks else np.array([], np.int32)
    del chunks
    graph = csr_matrix((np.ones(len(indices), np.int8), indices, np.asarray(ptr, np.int64)), shape=(inst.n, inst.n))
    if inst.sparse_links and inst.n>30000:print('diesel seed edges',graph.nnz,flush=True)
    if inst.sparse_links:
        # A cheap seed is sufficient: full-graph augmentation below certifies
        # the optimum. Dense-in-time London chains make seed HK expensive.
        match=np.full(inst.n,-1,np.int32);taken=np.zeros(inst.n,bool)
        for i in np.argsort(inst.e,kind='stable'):
            js=graph.indices[graph.indptr[i]:graph.indptr[i+1]]
            free=js[~taken[js]]
            if len(free):match[i]=free[0];taken[free[0]]=True
    else:
        match = maximum_bipartite_matching(graph, perm_type='column')
    if inst.sparse_links and inst.n>30000:print('diesel seed fleet',inst.n-int(np.count_nonzero(match>=0)),flush=True)
    seed_edges=int(graph.nnz)
    del graph,indices
    reverse=np.full(inst.n,-1,int)
    for i,j in enumerate(match):
        if j>=0:reverse[j]=i
    if inst.sparse_links:
        _complete_augmentation_batched(inst,match,reverse,order,starts)
        return Solution(_paths(match),(),seed_edges,method='greedy short-connection seed; complete-DAG disjoint-tree augmentation certificate')
    from collections import deque
    while True:
        parent=np.full(inst.n,-1,int)
        queue=deque(map(int,np.flatnonzero(match<0)))
        seen_l=np.zeros(inst.n,bool);seen_l[list(queue)]=True
        unseen=np.ones(inst.n,bool)
        found=-1
        while queue and found<0:
            i=queue.popleft()
            lo=np.searchsorted(starts,inst.e[i]-EPS)
            possible=order[lo:]
            possible=possible[unseen[possible]]
            js=np.sort(possible[inst.e[i]+inst.tau[inst.dst[i],inst.o[possible]]<=inst.s[possible]+EPS])
            unseen[js]=False;parent[js]=i
            free=js[reverse[js]<0]
            if len(free):
                found=int(free[0]);break
            for j in js:
                left=int(reverse[j])
                if not seen_l[left]:
                    seen_l[left]=True;queue.append(left)
        if found<0:break
        j=found
        while j>=0:
            i=int(parent[j]);old=int(match[i])
            match[i]=j;reverse[j]=i;j=old
    return Solution(_paths(match), (), seed_edges, method='Hopcroft-Karp seed; complete-DAG augmenting-path certificate')


def _complete_augmentation_batched(inst,match,reverse,order,starts):
    """Augment once per disjoint BFS tree, then rebuild the forest.

    Every right vertex is claimed once in a pass. Its matched left vertex
    belongs to that same tree. Paths in distinct trees are vertex-disjoint,
    so completing one tree cannot invalidate another. A zero-change full
    pass is an exact no-augmenting-path certificate (no time cutoff).
    """
    from collections import deque
    while True:
        roots=np.flatnonzero(match<0)
        queue=deque(map(int,roots));root=np.full(inst.n,-1,int);root[roots]=roots
        parent=np.full(inst.n,-1,int);unseen=np.ones(inst.n,bool);done=np.zeros(inst.n,bool)
        changed=0
        while queue:
            i=queue.popleft();r=root[i]
            if done[r]:continue
            lo=np.searchsorted(starts,inst.e[i]-EPS)
            possible=order[lo:];possible=possible[unseen[possible]]
            js=np.sort(possible[inst.e[i]+inst.tau[inst.dst[i],inst.o[possible]]<=inst.s[possible]+EPS])
            unseen[js]=False;parent[js]=i
            free=js[reverse[js]<0]
            if len(free):
                done[r]=True;changed+=1;j=int(free[0])
                # This tree finishes immediately. Its newly discovered
                # alternatives are unclaimed and remain available to other
                # roots; only the chosen right vertex enters the path.
                unseen[js]=True;unseen[j]=False
                while j>=0:
                    left=int(parent[j]);old=int(match[left]);match[left]=j;reverse[j]=left;j=old
                continue
            for j in js:
                left=int(reverse[j])
                if root[left]<0:root[left]=r;queue.append(left)
        if inst.n>30000:print('diesel full-graph augmentations',changed,'fleet',int(np.count_nonzero(match<0)),flush=True)
        if not changed:return


def build_blocks(inst, alpha=0.0, seed=0, noise=0.0, stations=(), aware=False):
    if np.any(inst.d > inst.R + EPS):
        raise ValueError('a single trip exceeds usable range')
    if not inst.n:
        return []
    rng = np.random.default_rng(seed)
    horizon = max(1.0, max(inst.e) - min(inst.s))
    end = np.empty(inst.n)
    loc = np.empty(inst.n, int)
    dist = np.empty(inst.n)
    inbound = np.zeros(inst.n)
    blocks = []
    S = check_stations(inst, stations)
    nearest = np.min(inst.w[:, S], axis=1) if aware and S else np.zeros(inst.m)
    from_station = np.min(inst.w[list(S), :], axis=0) if aware and S else np.zeros(inst.m)
    for j in inst.order:
        n = len(blocks)
        ready = end[:n] + inst.tau[loc[:n], inst.o[j]]
        nd = dist[:n] + inst.w[loc[:n], inst.o[j]] + inst.d[j]
        okay = (ready <= inst.s[j] + EPS) & (nd <= inst.R + EPS)
        if aware and S:
            okay &= nd + inbound[:n] + nearest[inst.dst[j]] <= inst.R + EPS
        possible = np.flatnonzero(okay)
        if len(possible):
            residual = (inst.R - nd[possible])/inst.R if math.isfinite(inst.R) else np.zeros(len(possible))
            key = (1-alpha)*residual + alpha*(inst.s[j]-ready[possible])/horizon
            if noise:
                key += rng.random(len(possible))*noise
            b = int(possible[np.argmin(key)])
            blocks[b].append(int(j))
            dist[b] = nd[b]
        else:
            b = n
            blocks.append([int(j)])
            dist[b] = inst.d[j]
            inbound[b] = from_station[inst.o[j]]
        end[b], loc[b] = inst.e[j], inst.dst[j]
    return blocks


def block_info(inst, blocks):
    first = np.array([b[0] for b in blocks], int)
    last = np.array([b[-1] for b in blocks], int)
    distance = []
    for b in blocks:
        d = float(inst.d[b].sum())
        if len(b) > 1:
            if np.any(inst.e[b[:-1]] + inst.tau[inst.dst[b[:-1]], inst.o[b[1:]]] > inst.s[b[1:]] + EPS):
                raise ValueError('invalid internal block time')
            d += float(inst.w[inst.dst[b[:-1]], inst.o[b[1:]]].sum())
        if d > inst.R + EPS:
            raise ValueError('invalid internal block range')
        distance.append(d)
    return first, last, np.array(distance)


def link_blocks(inst, stations, blocks):
    """Match, propagate true incoming mileage, cut offending edges and rematch.

    Reference pairwise compatibility omits preceding station-to-block distance
    at the next charge. Matching is a relaxation; repaired results are upper bounds.
    """
    S = check_stations(inst, stations)
    nb = len(blocks)
    if inst.sparse_links and nb>3000 and S:
        return link_blocks_sparse(inst,S,blocks)
    if not S or not nb:
        return Solution([b[:] for b in blocks], S)
    first, last, dist = block_info(inst, blocks)
    origins, destinations = inst.o[first], inst.dst[last]
    starts, ends = inst.s[first], inst.e[last]
    graph = np.zeros((nb, nb), bool)
    for c in S:
        time_ok = ends[:, None] + inst.tau[destinations, c, None] + inst.T + inst.tau[c, origins][None, :] <= starts[None, :] + EPS
        graph |= time_ok & ((dist + inst.w[destinations, c])[:, None] <= inst.R + EPS) & ((dist + inst.w[c, origins])[None, :] <= inst.R + EPS)
    initial_edges = int(graph.sum())
    repairs = 0
    while True:
        match = maximum_bipartite_matching(csr_matrix(graph), perm_type='column')
        buses, conflicts = [], []
        for path in _paths(match):
            bus = blocks[path[0]][:]
            used = dist[path[0]]
            for a, b in zip(path, path[1:]):
                feasible = [c for c in S if used + inst.w[destinations[a], c] <= inst.R + EPS
                            and ends[a] + inst.tau[destinations[a], c] + inst.T + inst.tau[c, origins[b]] <= starts[b] + EPS
                            and inst.w[c, origins[b]] + dist[b] <= inst.R + EPS]
                if not feasible:
                    conflicts.append((a, b, used))
                    break
                # Least incoming consumption dominates for future feasibility.
                c = min(feasible, key=lambda c: (inst.w[c, origins[b]], inst.w[destinations[a], c] + inst.w[c, origins[b]], c))
                bus.append(('C', c))
                bus.extend(blocks[b])
                used = inst.w[c, origins[b]] + dist[b]
            buses.append(bus)
        if not conflicts:
            return Solution(buses, S, initial_edges-repairs, repairs)
        for a, b, used in conflicts:
            # Prune the entire incompatible outgoing row for this encountered
            # resource state. This is deliberately conservative if a later
            # matching changes the predecessor; optimality is not claimed.
            allowed=np.zeros(nb,bool)
            for c in S:
                if used+inst.w[destinations[a],c] <= inst.R+EPS:
                    allowed |= ((ends[a]+inst.tau[destinations[a],c]+inst.T+inst.tau[c,origins] <= starts+EPS)
                                & (inst.w[c,origins]+dist <= inst.R+EPS))
            removed=int(np.count_nonzero(graph[a] & ~allowed))
            graph[a] &= allowed
            if not removed:raise RuntimeError('resource repair made no progress')
            repairs += removed


def link_blocks_sparse(inst,stations,blocks,successor_limit=256):
    """Large-instance feasible upper bound using a bounded successor graph.

    For each source block and reachable station, keep the first 256 blocks
    after the earliest feasible charged arrival, then check their range.
    This is NOT a full-graph matching certificate or an optimal EVSP claim.
    The exact diesel baseline does not use this restriction.
    """
    S=check_stations(inst,stations);nb=len(blocks)
    first,last,dist=block_info(inst,blocks)
    origins,destinations=inst.o[first],inst.dst[last]
    starts,ends=inst.s[first],inst.e[last]
    # Station-dependent ready time contains destination-to-origin time. Sort
    # by the latest station departure able to reach each block on time.
    adjacency=[set() for _ in blocks]
    for c in S:
        deadline=starts-inst.tau[c,origins]
        order=np.argsort(deadline,kind='stable');ordered=deadline[order]
        for a in range(nb):
            if dist[a]+inst.w[destinations[a],c]>inst.R+EPS:continue
            ready=ends[a]+inst.tau[destinations[a],c]+inst.T
            k=int(np.searchsorted(ordered,ready-EPS))
            js=order[k:k+successor_limit]
            js=js[inst.w[c,origins[js]]+dist[js]<=inst.R+EPS]
            adjacency[a].update(map(int,js))
    repairs=0
    while True:
        ptr=np.zeros(nb+1,np.int64);ptr[1:]=np.cumsum([len(x) for x in adjacency])
        idx=np.fromiter((b for row in adjacency for b in sorted(row)),dtype=np.int32,count=int(ptr[-1]))
        graph=csr_matrix((np.ones(len(idx),np.int8),idx,ptr),shape=(nb,nb))
        match=maximum_bipartite_matching(graph,perm_type='column')
        buses=[];conflicts=[]
        for path in _paths(match):
            bus=blocks[path[0]][:];used=dist[path[0]]
            for a,b in zip(path,path[1:]):
                feasible=[c for c in S if used+inst.w[destinations[a],c]<=inst.R+EPS
                    and ends[a]+inst.tau[destinations[a],c]+inst.T+inst.tau[c,origins[b]]<=starts[b]+EPS
                    and inst.w[c,origins[b]]+dist[b]<=inst.R+EPS]
                if not feasible:conflicts.append((a,used));break
                c=min(feasible,key=lambda c:(inst.w[c,origins[b]],inst.w[destinations[a],c]+inst.w[c,origins[b]],c))
                bus.append(('C',c));bus.extend(blocks[b]);used=inst.w[c,origins[b]]+dist[b]
            buses.append(bus)
        if not conflicts:
            return Solution(buses,S,len(idx),repairs,'bounded 256-successor block graph; resource-correct feasible upper bound')
        for a,used in conflicts:
            keep=set()
            for b in adjacency[a]:
                if any(used+inst.w[destinations[a],c]<=inst.R+EPS
                       and ends[a]+inst.tau[destinations[a],c]+inst.T+inst.tau[c,origins[b]]<=starts[b]+EPS
                       and inst.w[c,origins[b]]+dist[b]<=inst.R+EPS for c in S):keep.add(b)
            removed=len(adjacency[a])-len(keep)
            if not removed:raise RuntimeError('sparse repair made no progress')
            repairs+=removed;adjacency[a]=keep


def block_pool(inst, restarts=0, seed=0):
    rng = np.random.default_rng(seed)
    specs = [(0., 0.), (1., 0.), (.5, 0.)]
    specs += [(float(rng.random()), float(rng.choice([0., .05, .15]))) for _ in range(restarts)]
    pool=[build_blocks(inst, alpha, seed+i, noise) for i, (alpha, noise) in enumerate(specs)]
    # Shorter blocks create intermediate charging opportunities. They are valid
    # under the actual R; no new vehicle parameter is introduced.
    for fraction in (.55,.75):
        if inst.n and np.max(inst.d)<=fraction*inst.R:
            smaller=Instance(inst.R*fraction,inst.T,inst.tau,inst.w,inst.trips)
            pool.append(build_blocks(smaller,alpha=.5,seed=seed))
    return pool


def evaluate(inst, stations, restarts=0, seed=0, pool=None, local_steps=0, aware=True, incumbent=None):
    S = check_stations(inst, stations)
    if math.isinf(inst.R):
        sol = diesel(inst)
        sol.stations = S
        return sol
    candidates = block_pool(inst, restarts, seed) if pool is None else list(pool)
    if aware and S:
        candidates.append(build_blocks(inst, .5, seed, stations=S, aware=True))
    best = None
    best_blocks = None
    for blocks in candidates:
        sol = link_blocks(inst, S, blocks)
        if best is None or sol.key < best.key:
            best, best_blocks = sol, blocks
    rng = np.random.default_rng(seed)
    for step in range(local_steps):
        if len(best_blocks) < 2:
            break
        a, b = map(int, rng.choice(len(best_blocks), 2, replace=False))
        trial = [x[:] for x in best_blocks]
        ia = int(rng.integers(len(trial[a])))
        if step % 2 and trial[b]:
            ib = int(rng.integers(len(trial[b])))
            trial[a][ia], trial[b][ib] = trial[b][ib], trial[a][ia]
        else:
            trial[b].append(trial[a].pop(ia))
        trial = [sorted(x, key=lambda j: (inst.s[j], inst.e[j], j)) for x in trial if x]
        try:
            block_info(inst, trial)
        except ValueError:
            continue
        sol = link_blocks(inst, S, trial)
        if sol.key < best.key:
            best, best_blocks = sol, trial
    if incumbent is not None and set(incumbent.stations) <= set(S) and incumbent.N < best.N:
        best = Solution(incumbent.buses, S, best.edges, best.repairs, 'retained feasible incumbent')
    validate(inst, S, best.buses)
    return best


def station_scores(inst, pair_limit=200):
    """Bounded pair sample ranks sites ONLY; never cuts diesel matching edges."""
    score = np.zeros(inst.m, np.int64)
    order = inst.order
    starts = inst.s[order]
    for i in order:
        lo = int(np.searchsorted(starts, inst.e[i] + inst.T - EPS))
        js = order[lo:lo+pair_limit]
        if len(js):
            valid = inst.e[i] + inst.tau[inst.dst[i], :, None] + inst.T + inst.tau[:, inst.o[js]] <= inst.s[js][None, :] + EPS
            score += valid.sum(axis=1)
    return score


def select_stations(inst, K, cand_limit=12, restarts=0, seed=0, pool=None, candidates=None, initial=(), swaps=True):
    if K < 0:
        raise ValueError('K must be nonnegative')
    S = check_stations(inst, initial)
    if len(S) > K:
        raise ValueError('initial stations exceed K')
    pool = block_pool(inst, restarts, seed) if pool is None else pool
    if candidates is None:
        score = station_scores(inst)
        candidates = sorted(range(inst.m), key=lambda c: (-score[c], c))[:cand_limit]
    candidates = sorted(set(candidates) | set(S))
    cache = {}
    def calc(s):
        key = tuple(sorted(s))
        if key not in cache:
            cache[key] = evaluate(inst, key, seed=seed, pool=pool, aware=False)
        return cache[key]
    cur = calc(S)
    trace = [dict(K=len(S), N=cur.N, stations=list(S), edges=cur.edges)]
    while len(S) < K:
        choices = [(calc((*S, c)), c) for c in candidates if c not in S]
        if not choices:
            break
        best, c = min(choices, key=lambda x: (x[0].key, x[1]))
        if best.key >= cur.key:
            break
        S, cur = tuple(sorted((*S, c))), best
        trace.append(dict(K=len(S), N=cur.N, stations=list(S), edges=cur.edges))
    if swaps:
        while S:
            options = [(calc(tuple(c for c in S if c != v)+(u,)), v, u)
                       for v in S if v not in initial for u in candidates if u not in S]
            if not options:
                break
            best, v, u = min(options, key=lambda x: (x[0].key, x[1], x[2]))
            if best.key >= cur.key:
                break
            S, cur = tuple(sorted(tuple(c for c in S if c != v)+(u,))), best
    final = evaluate(inst, S, seed=seed, pool=pool, aware=True, incumbent=cur)
    return final, trace


def exact_milp(inst, stations=None, K=None, time_limit=60):
    """Small-instance arc MILP for P1/P2, plus separately solved LP bound."""
    if inst.n > 100 or not math.isfinite(inst.R):
        raise ValueError('finite-range exact benchmark limited to 100 trips')
    if np.any(inst.d > inst.R + EPS):
        raise ValueError('single-trip infeasibility')
    if K is not None and K < 0:
        raise ValueError('K must be nonnegative')
    S = tuple(range(inst.m)) if K is not None else check_stations(inst, stations or ())
    n = inst.n
    if not n:
        return dict(optimal=True, objective=0, lp_lower_bound=0., dual_bound=0., gap=0., solution=Solution([], ()))
    arcs = [(-1, j, -1) for j in range(n)] + [(i, -1, -1) for i in range(n)]
    for i in range(n):
        for j in range(n):
            if inst.e[i]+inst.tau[inst.dst[i], inst.o[j]] <= inst.s[j]+EPS:
                arcs.append((i,j,-1))
            for c in S:
                if inst.e[i]+inst.tau[inst.dst[i],c]+inst.T+inst.tau[c,inst.o[j]] <= inst.s[j]+EPS:
                    arcs.append((i,j,c))
    na = len(arcs)
    ny = inst.m if K is not None else 0
    nv = na+n+ny
    rr, cc, vv, lows, highs = [], [], [], [], []
    def row(items, lo=-np.inf, hi=np.inf):
        r = len(lows)
        for c, val in items:
            rr.append(r); cc.append(c); vv.append(val)
        lows.append(lo); highs.append(hi)
    for j in range(n):
        row([(a,1.) for a,(_,dst,_) in enumerate(arcs) if dst==j],1,1)
        row([(a,1.) for a,(src,_,_) in enumerate(arcs) if src==j],1,1)
    for a,(i,j,c) in enumerate(arcs):
        if j < 0:
            continue
        if i < 0:
            row([(na+j,1.),(a,-inst.d[j])],0)
        elif c < 0:
            delta=inst.w[inst.dst[i],inst.o[j]]+inst.d[j]
            M=inst.R+delta
            row([(na+j,1.),(na+i,-1.),(a,-M)],delta-M)
        else:
            delta=inst.w[c,inst.o[j]]+inst.d[j]
            row([(na+j,1.),(a,-delta)],0)
            reach=inst.w[inst.dst[i],c]
            row([(na+i,1.),(a,reach)],hi=inst.R)
            if K is not None:
                row([(a,1.),(na+n+c,-1.)],hi=0)
    if K is not None:
        row([(na+n+c,1.) for c in range(inst.m)],hi=K)
    matrix=coo_matrix((vv,(rr,cc)),shape=(len(lows),nv)).tocsc()
    constraint=LinearConstraint(matrix,np.array(lows),np.array(highs))
    ub=np.ones(nv); ub[na:na+n]=inst.R
    bounds=Bounds(np.zeros(nv),ub)
    cost=np.zeros(nv);cost[:n]=1.
    integrality=np.ones(nv,int);integrality[na:na+n]=0
    lp=milp(cost,integrality=np.zeros(nv),bounds=bounds,constraints=constraint,options={'time_limit':time_limit})
    result=milp(cost,integrality=integrality,bounds=bounds,constraints=constraint,options={'time_limit':time_limit,'mip_rel_gap':0.})
    output=dict(optimal=result.status==0,status=int(result.status),message=result.message,
                objective=None,lp_lower_bound=float(lp.fun) if lp.status==0 else None,
                dual_bound=float(result.mip_dual_bound) if getattr(result,'mip_dual_bound',None) is not None else None,
                gap=float(result.mip_gap) if getattr(result,'mip_gap',None) is not None else None)
    if result.x is not None:
        selected=[arc for a,arc in enumerate(arcs) if result.x[a]>.5]
        starts=[j for i,j,c in selected if i<0]
        nxt={i:(j,c) for i,j,c in selected if i>=0 and j>=0}
        buses=[]
        for j in starts:
            bus=[j]
            while j in nxt:
                k,c=nxt[j]
                if c>=0: bus.append(('C',c))
                bus.append(k);j=k
            buses.append(bus)
        used=tuple(sorted({c for _,_,c in selected if c>=0}))
        validate(inst,used,buses)
        output.update(objective=len(buses),solution=Solution(buses,used,method='arc MILP'))
    return output


def parse(text, mode):
    it=iter(text.split())
    n,m=int(next(it)),int(next(it)); R,T=float(next(it)),float(next(it))
    extra=int(next(it)) if mode=='p2' else [int(next(it)) for _ in range(m)]
    tau=[[float(next(it)) for _ in range(m)] for _ in range(m)]
    w=[[float(next(it)) for _ in range(m)] for _ in range(m)]
    trips=[(int(next(it))-1,int(next(it))-1,float(next(it)),float(next(it)),float(next(it))) for _ in range(n)]
    if next(it,None) is not None:
        raise ValueError('unexpected trailing input')
    return Instance(R,T,tau,w,trips),extra


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['p1','p2']);p.add_argument('--restarts',type=int,default=10)
    args=p.parse_args();inst,extra=parse(sys.stdin.read(),args.mode)
    if args.mode=='p2':
        sol,_=select_stations(inst,extra,restarts=args.restarts)
        print(' '.join(str(c+1) for c in sol.stations))
    else:
        sol=evaluate(inst,[c for c,f in enumerate(extra) if f],restarts=args.restarts,local_steps=100 if inst.n<100 else 0)
    print(sol.N)
    for bus in sol.buses:
        print(' '.join(f'C({t[1]+1})' if isinstance(t,tuple) else str(t+1) for t in bus))


if __name__=='__main__':
    main()
