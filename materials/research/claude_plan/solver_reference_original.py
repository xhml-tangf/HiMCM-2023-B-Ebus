"""
Reference implementation: electric bus scheduling with range R and full-charge time T.

Model (see spec_for_agent.md):
  - every timetable trip must be served exactly once, on time;
  - an e-bus is only two constants: max range R (km) and full-charge time T (min);
  - a bus starts the day fully charged at the origin of its first trip;
  - charging is only possible at stations in S; a charge takes T and resets range to R;
  - the deadhead to the charging station and from it to the next trip also consumes range.

Algorithm: two layers
  Layer 1 (build_blocks): greedy best-fit packing of trips into "range blocks" (<= R km).
  Layer 2 (link_blocks) : link blocks through a charge; minimum path cover = |B| - max matching.
Outer layer (select_stations): greedy add + swap improvement over candidate stations.

Usage:
  python solver_reference.py p1 < input   # stations given as 0/1 flags in the input
  python solver_reference.py p2 < input   # choose at most K stations
"""
import random
import sys

sys.setrecursionlimit(100000)


class Instance:
    def __init__(self, R, T, tau, w, trips):
        self.R, self.T, self.tau, self.w = R, T, tau, w
        # trips[i] = (origin, destination, start, end, distance); nodes are 0-based
        self.trips = trips
        self.n = len(trips)
        self.m = len(tau)


def charge_station(inst, S, loc, t_free, u, o_next, s_next, d_next):
    """Best station c in S through which a bus at `loc`, free at `t_free`, having run `u` km
    since its last full charge, can reach and charge, then start a task at `o_next` at time
    `s_next` that needs `d_next` km after leaving the station. Returns c or None."""
    R, T, tau, w = inst.R, inst.T, inst.tau, inst.w
    best, best_c = None, None
    for c in S:
        if u + w[loc][c] > R:
            continue
        if t_free + tau[loc][c] + T + tau[c][o_next] > s_next:
            continue
        if w[c][o_next] + d_next > R:
            continue
        cost = w[loc][c] + w[c][o_next]
        if best is None or cost < best:
            best, best_c = cost, c
    return best_c


def validate(inst, S, buses):
    """Independent checker. buses: list of lists with trip ids and ('C', station) tokens."""
    R, T, tau, w = inst.R, inst.T, inst.tau, inst.w
    seen = []
    for bus in buses:
        loc = t = None
        u = 0.0
        pending = None
        for tok in bus:
            if isinstance(tok, tuple):
                if loc is None or pending is not None:
                    return False
                pending = tok[1]
                continue
            o, dst, s, e, d = inst.trips[tok]
            if loc is None:
                if pending is not None or d > R:
                    return False
                u = d
            elif pending is not None:
                c = pending
                if c not in S:
                    return False
                if u + w[loc][c] > R:
                    return False
                if t + tau[loc][c] + T + tau[c][o] > s:
                    return False
                if w[c][o] + d > R:
                    return False
                u = w[c][o] + d
            else:
                if t + tau[loc][o] > s:
                    return False
                if u + w[loc][o] + d > R:
                    return False
                u += w[loc][o] + d
            pending = None
            loc, t = dst, e
            seen.append(tok)
        if pending is not None:
            return False
    return sorted(seen) == list(range(inst.n))


def build_blocks(inst, rng=None, noise=0.0, alpha=0.0):
    """Layer 1: greedy best-fit packing of trips into range blocks.

    Candidate block key (smaller is better), both parts normalised to [0, 1]:
      (1 - alpha) * residual_range / R  +  alpha * idle_time / horizon
    alpha = 0: tightest range fit; alpha = 1: shortest idle gap (optimal for plain interval
    partitioning); in between trades the two. `noise` adds random perturbation (for restarts).
    """
    R, tau, w = inst.R, inst.tau, inst.w
    order = sorted(range(inst.n), key=lambda i: (inst.trips[i][2], inst.trips[i][3]))
    horizon = max(1.0, max(t[3] for t in inst.trips) - min(t[2] for t in inst.trips))
    blocks = []  # each block: {'tr': [trip ids], 'dist': km used}
    for j in order:
        o, dst, s, e, d = inst.trips[j]
        if d > R:
            raise ValueError("trip %d is longer than the range R" % j)
        best = None
        best_key = None
        for b in blocks:
            last = inst.trips[b['tr'][-1]]
            if last[3] + tau[last[1]][o] > s:
                continue
            nd = b['dist'] + w[last[1]][o] + d
            if nd > R:
                continue
            idle = s - (last[3] + tau[last[1]][o])
            key = (1 - alpha) * (R - nd) / R + alpha * idle / horizon
            if rng is not None:
                key += rng.random() * noise
            if best is None or key < best_key:
                best, best_key = (b, nd), key
        if best is not None:
            b, nd = best
            b['tr'].append(j)
            b['dist'] = nd
        else:
            blocks.append({'tr': [j], 'dist': d})
    return blocks


def link_blocks(inst, S, blocks):
    """Layer 2: link blocks through a charge; max bipartite matching gives the fewest buses."""
    trips = inst.trips
    nb = len(blocks)
    info = []
    for b in blocks:
        f, l = trips[b['tr'][0]], trips[b['tr'][-1]]
        info.append({'o': f[0], 's': f[2], 'dst': l[1], 'e': l[3], 'dist': b['dist']})
    adj = [[] for _ in range(nb)]
    link = {}
    for a in range(nb):
        A = info[a]
        for b in range(nb):
            if a == b:
                continue
            B = info[b]
            if A['e'] >= B['s']:
                continue
            c = charge_station(inst, S, A['dst'], A['e'], A['dist'], B['o'], B['s'], B['dist'])
            if c is not None:
                adj[a].append(b)
                link[(a, b)] = c
    match_r = [-1] * nb  # match_r[b] = a means block a is followed by block b

    def augment(a, seen):
        for b in adj[a]:
            if b in seen:
                continue
            seen.add(b)
            if match_r[b] == -1 or augment(match_r[b], seen):
                match_r[b] = a
                return True
        return False

    for a in range(nb):
        augment(a, set())
    nxt = {}
    for b in range(nb):
        if match_r[b] != -1:
            nxt[match_r[b]] = b
    buses = []
    for b in range(nb):
        if match_r[b] == -1:  # chain head
            bus, cur = [], b
            while True:
                bus.extend(blocks[cur]['tr'])
                if cur in nxt:
                    nx = nxt[cur]
                    bus.append(('C', link[(cur, nx)]))
                    cur = nx
                else:
                    break
            buses.append(bus)
    num_edges = sum(len(x) for x in adj)
    return buses, num_edges


def evaluate(inst, S, restarts=30, seed=0):
    """Inner layer: fewest buses found for station set S (deterministic run + random restarts)."""
    rng = random.Random(seed)
    best = None
    fixed = [0.0, 1.0, 0.5]  # deterministic runs: range-first, time-first, balanced
    for r in range(restarts + len(fixed)):
        if r < len(fixed):
            blocks = build_blocks(inst, alpha=fixed[r])
        else:
            blocks = build_blocks(inst, rng, rng.choice([0.0, 0.05, 0.15]), rng.random())
        buses, ne = link_blocks(inst, S, blocks)
        key = (len(buses), -ne)
        if best is None or key < best[0]:
            best = (key, buses, ne)
    return best[1], best[2]


def station_scores(inst, horizon=200):
    """score[v] = number of consecutive-trip pairs whose time gap allows a charge at v."""
    trips, tau, T = inst.trips, inst.tau, inst.T
    order = sorted(range(inst.n), key=lambda i: trips[i][2])
    score = [0] * inst.m
    for a, i in enumerate(order):
        _, di, _, ei, _ = trips[i]
        for j in order[a + 1:a + 1 + horizon]:
            oj, _, sj, _, _ = trips[j]
            for v in range(inst.m):
                if ei + tau[di][v] + T + tau[v][oj] <= sj:
                    score[v] += 1
    return score


def select_stations(inst, K, cand_limit=15, restarts=10, seed=0):
    """Outer layer: choose at most K stations. Greedy add, then swap improvement."""
    sc = station_scores(inst)
    cand = sorted(range(inst.m), key=lambda v: -sc[v])[:cand_limit]

    def key(S):
        buses, ne = evaluate(inst, S, restarts, seed)
        return (len(buses), -ne)

    S = []
    cur = key(S)
    for _ in range(K):
        best = None
        for v in cand:
            if v in S:
                continue
            k = key(S + [v])
            if best is None or k < best[0]:
                best = (k, v)
        if best is not None and best[0] < cur:
            S.append(best[1])
            cur = best[0]
        else:
            break
    improved = True
    while improved and S:
        improved = False
        for v in list(S):
            for u in cand:
                if u in S:
                    continue
                S2 = [x for x in S if x != v] + [u]
                k = key(S2)
                if k < cur:
                    S, cur = S2, k
                    improved = True
                    break
            if improved:
                break
    return sorted(S)


def exact_min_buses(inst, S):
    """Exhaustive search, only for tiny instances (n <= ~9); used to benchmark the heuristic."""
    R, T, tau, w = inst.R, inst.T, inst.tau, inst.w
    order = sorted(range(inst.n), key=lambda i: (inst.trips[i][2], inst.trips[i][3]))
    best = [inst.n + 1]

    def dfs(k, buses):
        if len(buses) >= best[0]:
            return
        if k == inst.n:
            best[0] = len(buses)
            return
        o, dst, s, e, d = inst.trips[order[k]]
        for bi, (loc, t, u) in enumerate(buses):
            if t + tau[loc][o] <= s and u + w[loc][o] + d <= R:
                nb = buses[:]
                nb[bi] = (dst, e, u + w[loc][o] + d)
                dfs(k + 1, nb)
            for c in S:
                if u + w[loc][c] <= R and t + tau[loc][c] + T + tau[c][o] <= s and w[c][o] + d <= R:
                    nb = buses[:]
                    nb[bi] = (dst, e, w[c][o] + d)
                    dfs(k + 1, nb)
        dfs(k + 1, buses + [(dst, e, d)])

    dfs(0, [])
    return best[0]


def _num(x):
    return str(int(x)) if float(x).is_integer() else str(x)


def parse(tokens, mode):
    it = iter(tokens)
    n, m = int(next(it)), int(next(it))
    R, T = float(next(it)), float(next(it))
    extra = None
    if mode == 'p2':
        extra = int(next(it))
    else:
        extra = [int(next(it)) for _ in range(m)]
    tau = [[float(next(it)) for _ in range(m)] for _ in range(m)]
    w = [[float(next(it)) for _ in range(m)] for _ in range(m)]
    trips = []
    for _ in range(n):
        o, dst = int(next(it)) - 1, int(next(it)) - 1
        s, e, d = float(next(it)), float(next(it)), float(next(it))
        trips.append((o, dst, s, e, d))
    return Instance(R, T, tau, w, trips), extra


def fmt_bus(bus):
    return ' '.join('C(%d)' % (t[1] + 1) if isinstance(t, tuple) else str(t + 1) for t in bus)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'p2'
    inst, extra = parse(sys.stdin.read().split(), mode)
    if mode == 'p2':
        S = select_stations(inst, extra)
    else:
        S = [v for v, f in enumerate(extra) if f]
    buses, _ = evaluate(inst, S)
    assert validate(inst, S, buses)
    if mode == 'p2':
        print(' '.join(str(v + 1) for v in S))
    print(len(buses))
    for bus in buses:
        print(fmt_bus(bus))


if __name__ == '__main__':
    main()
