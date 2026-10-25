"""Synthetic counterexamples verify algorithm invariants, not empirical inputs."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from trial_linked_routes import arc_milp, matching_paths, enumerate_paths, successors, solve_partition


def trips(rows):
    return pd.DataFrame([dict(trip_id=i+1,route_short_name="test",start_seconds=a,end_seconds=b,
                              first_terminal=o,last_terminal=d,first_stop_id=o,last_stop_id=d,
                              distance_km_upper=km) for i,(a,b,o,d,km) in enumerate(rows)])


def test_shared_charger_cannot_replenish_two_buses_simultaneously():
    # Two buses each arrive empty. One 5-minute position can replenish only one
    # before the next two simultaneous services. 3 buses with charge, 4 without.
    t=trips([(0,300,"A","Marpole Loop",150),(0,300,"B","Marpole Loop",150),
             (600,900,"Marpole Loop","C",150),(600,900,"Marpole Loop","D",150)])
    schedule,charged=arc_milp(t,True,150,time_limit=10)
    _,plain=arc_milp(t,False,150,time_limit=10)
    assert charged["fleet_size"]==3 and plain["fleet_size"]==4
    assert charged["charging_sessions"]==1
    assert schedule is not None


def test_distinct_terminal_locations_cannot_teleport():
    t=trips([(0,300,"A","B",10),(600,900,"C","D",10)])
    _,r=arc_milp(t,False,0,time_limit=10)
    assert r["fleet_size"]==2


def test_one_trip_longer_than_range_is_infeasible():
    t=trips([(0,300,"A","B",151)])
    schedule,r=arc_milp(t,False,0,time_limit=10)
    assert schedule is None and r["status"]==2


def test_path_partition_matches_independent_dag_cover():
    t=trips([(0,300,"A","B",10),(0,300,"A","B",10),
             (360,600,"B","A",10),(660,900,"A","B",10)])
    paths,km,count=enumerate_paths(t,successors(t))
    assert len(paths)==count
    _,r=solve_partition(t,paths,km,150)
    assert r["fleet_size"]==len(matching_paths(t))==2
