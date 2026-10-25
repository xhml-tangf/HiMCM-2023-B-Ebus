"""Reproducible tests of this implementation, NOT a claim to reproduce Claude's seed stream."""
from pathlib import Path
import sys, json, importlib.util, time
import numpy as np
from scipy.sparse.csgraph import shortest_path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.claude_evsp import Instance,evaluate,select_stations,exact_milp,diesel,validate
ROOT=Path(__file__).resolve().parents[1]


def random_instance(seed,n=8,m=3):
    rng=np.random.default_rng(seed)
    a=rng.integers(5,21,(m,m));a=np.triu(a,1);a=a+a.T
    # Triangle closure is required for the diesel bound, unlike arbitrary random matrices.
    tau=shortest_path(a,directed=False)
    w=tau*.7
    trips=[]
    for _ in range(n):
        o,d=rng.choice(m,2,replace=False);s=int(rng.integers(0,161))
        trips.append((int(o),int(d),s,s+tau[o,d]+int(rng.integers(0,6)),w[o,d]+int(rng.integers(0,4))))
    return Instance(30,20,tau,w,trips),tuple(map(int,rng.choice(m,int(rng.integers(0,m)),replace=False)))


def main():
    start=time.perf_counter()
    ref_path=ROOT/'materials/research/claude_plan/solver_reference_original.py'
    spec=importlib.util.spec_from_file_location('claude_original',ref_path)
    ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
    rows=[]
    for seed in range(300):
        inst,S=random_instance(seed)
        exact=exact_milp(inst,S)
        assert exact['optimal']
        old=ref.Instance(inst.R,inst.T,inst.tau.tolist(),inst.w.tolist(),inst.trips)
        exhaustive=ref.exact_min_buses(old,S)
        assert exhaustive==exact['objective']
        baseline=evaluate(inst,S,aware=False)
        improved=evaluate(inst,S,restarts=10,local_steps=40)
        assert improved.N>=exact['objective']
        validate(inst,S,improved.buses)
        old_buses,_=ref.evaluate(old,S,restarts=0)
        rows.append(dict(seed=seed,N_exact=exhaustive,N_baseline=baseline.N,N_improved=improved.N,
                         lp_bound=exact['lp_lower_bound'],N_d=diesel(inst).N,
                         reference_valid=ref.validate(old,S,old_buses)))
        if seed%50==0: print('P1',seed,flush=True)
    p2=[]
    for seed in range(60):
        inst,_=random_instance(10000+seed,m=4)
        sol,_=select_stations(inst,2,cand_limit=4,restarts=3)
        exact=exact_milp(inst,K=2)
        assert exact['optimal'] and sol.N>=exact['objective']
        p2.append(dict(seed=10000+seed,N_heuristic=sol.N,N_exact=exact['objective']))
    limits=[]
    for seed in range(200):
        inst,_=random_instance(20000+seed)
        big=Instance(float('inf'),0,inst.tau,inst.w,inst.trips)
        old=ref.Instance(1e9,0,inst.tau.tolist(),inst.w.tolist(),inst.trips)
        actual=evaluate(big,[]).N;expected=ref.exact_min_buses(old,[])
        assert actual==expected
        limits.append(dict(seed=20000+seed,N=actual))
    result=dict(generator='NumPy default_rng; symmetric integer times; shortest-path metric closure; w=.7*tau; distinct trip endpoints',
                seed_note='Independent test population; NOT the unspecified reference RNG stream.',
                p1=rows,p2=p2,diesel_limit=limits,
                summary=dict(p1_cases=len(rows),p1_optimal_baseline=sum(r['N_baseline']==r['N_exact'] for r in rows),
                             p1_optimal_improved=sum(r['N_improved']==r['N_exact'] for r in rows),
                             p1_max_gap=max(r['N_improved']-r['N_exact'] for r in rows),
                             p2_optimal=sum(r['N_heuristic']==r['N_exact'] for r in p2),
                             reference_invalid=sum(not r['reference_valid'] for r in rows),
                             diesel_limit_passed=len(limits)),elapsed_seconds=time.perf_counter()-start)
    (ROOT/'results/claude_plan/benchmark.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['summary']),flush=True)


if __name__=='__main__':main()
