import math,subprocess,sys
import numpy as np
import pytest
from src.claude_evsp import Instance, evaluate, select_stations, validate, diesel, pvr, exact_milp, link_blocks


def example():
    return Instance(30,20,[[0,15],[15,0]],[[0,10],[10,0]],
                    [(0,1,0,15,10),(1,0,20,35,10),(0,1,40,55,10),
                     (1,0,80,95,10),(0,1,100,115,10),(1,0,120,135,10)])


def test_specification_example_and_site_choice():
    inst=example()
    assert evaluate(inst,[0,1]).N==1
    assert evaluate(inst,[]).N==2
    assert evaluate(inst,[0]).N==2
    sol,_=select_stations(inst,1)
    assert sol.N==1 and sol.stations==(1,)
    for S in ([],[0],[1],[0,1]):
        exact=exact_milp(inst,S)
        assert exact['optimal']
        assert exact['objective']==evaluate(inst,S).N
    assert exact_milp(inst,K=1)['objective']==1
    assert exact_milp(inst,K=0)['objective']==2


def test_three_blocks_incoming_deadhead_counterexample():
    inst=Instance(10,5,[[0,3],[3,0]],[[0,3],[3,0]],
                  [(0,0,0,1,10),(1,1,20,21,7),(0,0,40,41,10)])
    bad=[[0,('C',0),1,('C',0),2]]
    with pytest.raises(ValueError,match='reach charger'):
        validate(inst,[0],bad)
    sol=link_blocks(inst,[0],[[0],[1],[2]])
    assert sol.repairs>0 and sol.N==2
    validate(inst,[0],sol.buses)
    assert exact_milp(inst,[0])['objective']==2


def test_detours_both_legs_time_range_and_energy():
    inst=Instance(20,10,[[0,5],[5,0]],[[0,5],[5,0]],
                  [(0,0,1400,1410,10),(0,0,1450,1460,10)])
    result=validate(inst,[1],[[0,('C',1),1]])
    assert result['deadhead_km']==10
    assert result['daytime_replenished_range_km']==15
    assert result['overnight_replenished_range_km']==15
    with pytest.raises(ValueError,match='duplicated'):
        validate(inst,[],[[0],[0],[1]])
    with pytest.raises(ValueError,match='trailing'):
        validate(inst,[1],[[0,('C',1)],[1]])


def test_half_open_intervals_and_diesel_limit():
    inst=Instance(math.inf,0,[[0]],[[0]],[(0,0,0,10,20),(0,0,10,20,20)])
    assert pvr(inst)==1
    assert diesel(inst).N==evaluate(inst,[]).N==1
    assert evaluate(Instance(10,0,[[0]],[[0]],[]),[]).N==0
    with pytest.raises(ValueError,match='single trip'):
        evaluate(Instance(10,0,[[0]],[[0]],[(0,0,0,1,11)]),[])


def test_overnight_is_not_added_as_full_battery_each_charge():
    inst=Instance(100,5,[[0]],[[0]],[(0,0,0,1,10),(0,0,10,11,10)])
    result=validate(inst,[0],[[0,('C',0),1]])
    assert result['daytime_replenished_range_km']+result['overnight_replenished_range_km']==20


def test_nonmetric_time_does_not_justify_diesel_lower_bound():
    # User inputs may be nonmetric; the model must not assert N_e >= N_d then.
    inst=Instance(100,0,[[0,100,1],[100,0,1],[1,1,0]],np.zeros((3,3)),
                  [(0,0,0,1,1),(1,1,3,4,1)])
    assert diesel(inst).N==2
    assert exact_milp(inst,[2])['objective']==1


def test_sparse_linking_matches_full_when_all_successors_retained():
    from src.claude_evsp import link_blocks_sparse,block_pool
    for ii in [example(),Instance(10,5,[[0,3],[3,0]],[[0,3],[3,0]],
               [(0,0,0,1,10),(1,1,20,21,7),(0,0,40,41,10)])]:
        for S in [[0],[0,1]]:
            for blocks in block_pool(ii):
                full=link_blocks(ii,S,blocks);sparse=link_blocks_sparse(ii,S,blocks,successor_limit=len(blocks))
                assert sparse.N==full.N
                validate(ii,S,sparse.buses)
                reduced=link_blocks_sparse(ii,S,blocks,successor_limit=1)
                validate(ii,S,reduced.buses)


def test_time_indexed_diesel_against_full_graph_on_unsorted_trips():
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import maximum_bipartite_matching
    rng=np.random.default_rng(613)
    for _ in range(40):
        xy=rng.random((5,2))*30
        tau=np.sqrt(((xy[:,None]-xy[None,:])**2).sum(axis=2))
        trips=[(int(rng.integers(5)),int(rng.integers(5)),float(s),float(s+rng.integers(1,30)),1.) for s in rng.integers(0,200,40)]
        ii=Instance(math.inf,0,tau,tau,trips)
        graph=ii.e[:,None]+ii.tau[ii.dst[:,None],ii.o[None,:]]<=ii.s[None,:]+1e-7
        expected=ii.n-np.count_nonzero(maximum_bipartite_matching(csr_matrix(graph),perm_type='column')>=0)
        actual=diesel(ii)
        assert actual.N==expected
        validate(ii,[],actual.buses)
        ii.sparse_links=True
        batched=diesel(ii)
        assert batched.N==expected
        validate(ii,[],batched.buses)


def test_batched_full_graph_connects_long_gaps_outside_seed_window():
    ii=Instance(math.inf,0,[[0]],[[0]],[(0,0,100*i,100*i+1,1) for i in range(500)],sparse_links=True)
    sol=diesel(ii)
    assert sol.N==pvr(ii)==1
    validate(ii,[],sol.buses)


def test_command_line_p1_p2_contract():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    tau='0 15\n15 0';w='0 10\n10 0'
    trips='1 2 0 15 10\n2 1 20 35 10\n1 2 40 55 10\n2 1 80 95 10\n1 2 100 115 10\n2 1 120 135 10'
    for mode,header,want in [('p1','6 2 30 20\n1 1','1'),('p2','6 2 30 20 1','2\n1')]:
        stdin=f'{header}\n{tau}\n{w}\n{trips}\n'
        proc=subprocess.run([sys.executable,str(root/'src/claude_evsp.py'),mode,'--restarts','0'],input=stdin,
                            text=True,capture_output=True,cwd=root,check=True)
        lines=proc.stdout.strip().splitlines()
        assert '\n'.join(lines[:mode.count('p2')+1])==want
