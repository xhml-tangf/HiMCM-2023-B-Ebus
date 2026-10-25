"""Evidence-labelled linked-route trials, isolated from manuscript/canonical data.

North: enumerate every time/terminal-compatible single-bus path and solve an
exact partition. South: a compact arc MILP jointly selects vehicle paths and
capacity-limited five-minute charging services. The latter uses an explicitly
conditional range-credit proxy, not an invented measured battery/charge curve.
Both are service-window, terminal-aggregated subproblems, not depot certificates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix, csc_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching

from trial_short_route_231 import DAY, active_ids

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/linked_route_trial"
CONTRACT_UNIT = 16_000_000 / 15
PATH_LIMIT = 10_000_000_000
# This HiGHS build accepts signed 32-bit integer options; the path ceiling and
# solver-node ceiling are different quantities and are reported separately.
SOLVER_NODE_LIMIT = 2_000_000_000
RANGE_KM = 150.0


def hhmm(seconds):
    return f"{int(seconds)//3600:02d}:{int(seconds)%3600//60:02d}"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def terminal(name, stop):
    for key in ("Lonsdale Quay", "22nd Street Station", "Marpole Loop", "Lougheed Station"):
        if name.startswith(key):
            return key
    return str(stop)


def load_day():
    source = ROOT / "data/processed/vancouver_gtfs_trip_manifest_classified_2023.csv"
    data = pd.read_csv(source, dtype={"service_id": str, "route_short_name": str,
                        "block_id": str, "first_stop_id": str, "last_stop_id": str}, low_memory=False)
    cal = pd.read_csv(ROOT / "materials/sources/raw/vancouver_gtfs_2023/calendar.txt", dtype={"service_id": str})
    exc = pd.read_csv(ROOT / "materials/sources/raw/vancouver_gtfs_2023/calendar_dates.txt", dtype={"service_id": str})
    data = data[data.service_id.isin(active_ids(DAY, cal, exc))].copy()
    stops = pd.read_csv(ROOT / "materials/sources/raw/vancouver_gtfs_2023/stops.txt", dtype=str).set_index("stop_id")
    for side in ("first", "last"):
        data[f"{side}_name"] = data[f"{side}_stop_id"].map(stops.stop_name)
        data[f"{side}_terminal"] = [terminal(n, s) for n, s in
                                     zip(data[f"{side}_name"], data[f"{side}_stop_id"])]
    raw = pd.read_csv(ROOT / "materials/sources/raw/vancouver_gtfs_2023/trips.txt", dtype=str).set_index("trip_id")
    return data, source, raw


def select(data, routes, start, end):
    trips = data[data.route_short_name.isin(routes) & (data.start_seconds >= start*3600)
                 & (data.start_seconds < end*3600)].sort_values(["start_seconds", "trip_id"]).reset_index(drop=True)
    assert len(trips) and trips.distance_km_upper.notna().all()
    assert (trips.end_seconds > trips.start_seconds).all()
    return trips


def successors(trips, independent=False):
    rows = list(trips.itertuples())
    return [[j for j in range(i+1, len(rows))
             if left.end_seconds <= rows[j].start_seconds
             and left.last_terminal == rows[j].first_terminal
             and (not independent or left.route_short_name == rows[j].route_short_name)]
            for i, left in enumerate(rows)]


def path_count(succ):
    counts = [0] * len(succ)
    for i in reversed(range(len(succ))):
        counts[i] = 1 + sum(counts[j] for j in succ[i])
    return sum(counts)


def enumerate_paths(trips, succ):
    theoretical = path_count(succ)
    if theoretical > PATH_LIMIT:
        raise ValueError(f"{theoretical} paths exceed user ceiling {PATH_LIMIT}; do not enumerate")
    if theoretical > 1_000_000:
        raise ValueError("Path count is within the user ceiling but exceeds this prototype's materialization budget; use compact arc MILP")
    distances = trips.distance_km_upper.to_numpy()
    paths, km = [], []
    def visit(path, distance):
        paths.append(tuple(path)); km.append(float(distance))
        for j in succ[path[-1]]:
            visit(path+[j], distance+distances[j])
    for i in range(len(trips)):
        visit([i], distances[i])
    assert len(paths) == theoretical
    return paths, np.array(km), theoretical


def matching_paths(trips, min_gap=0):
    """Independent exact lower bound: minimum DAG path cover without range."""
    succ=successors(trips); rr=[];cc=[]
    for i,js in enumerate(succ):
        for j in js:
            if trips.iloc[j].start_seconds-trips.iloc[i].end_seconds>=min_gap:
                rr.append(i);cc.append(j)
    graph=coo_matrix((np.ones(len(rr)),(rr,cc)),shape=(len(trips),len(trips))).tocsr()
    match=maximum_bipartite_matching(graph,perm_type="column")
    incoming={int(j) for j in match if j>=0}
    paths=[]
    for i in range(len(trips)):
        if i in incoming:continue
        p=[]
        while i>=0:
            p.append(i);i=int(match[i])
        paths.append(tuple(p))
    assert sorted(i for p in paths for i in p)==list(range(len(trips)))
    return paths


def maximum_connection_slack(trips,target_fleet):
    succ=successors(trips)
    gaps=sorted({0}|{int(trips.iloc[j].start_seconds-trips.iloc[i].end_seconds)
                     for i,js in enumerate(succ) for j in js})
    lo,hi=0,len(gaps)
    while lo+1<hi:
        mid=(lo+hi)//2
        if len(matching_paths(trips,gaps[mid]))<=target_fleet:lo=mid
        else:hi=mid
    paths=matching_paths(trips,gaps[lo])
    assert len(paths)==target_fleet
    return paths,gaps[lo]


def solve_partition(trips, paths, kms, range_km):
    ids = np.flatnonzero(kms <= range_km+1e-8)
    selected_paths = [paths[j] for j in ids]
    rr, cc = [], []
    for j, p in enumerate(selected_paths):
        rr.extend(p); cc.extend([j]*len(p))
    mat = csc_matrix(coo_matrix((np.ones(len(rr)), (rr, cc)), shape=(len(trips), len(ids))))
    start = time.perf_counter()
    result = milp(np.ones(len(ids)), integrality=np.ones(len(ids)), bounds=Bounds(0,1),
                  constraints=LinearConstraint(mat, np.ones(len(trips)), np.ones(len(trips))),
                  options={"mip_rel_gap": 0.0, "time_limit": 60.0, "node_limit": SOLVER_NODE_LIMIT})
    if result.x is None:
        raise RuntimeError(result.message)
    chosen = [selected_paths[j] for j,x in enumerate(result.x) if x > .5]
    return chosen, dict(status=int(result.status), message=result.message, fleet_size=len(chosen),
                        objective_lower_bound=float(result.mip_dual_bound), mip_gap=float(result.mip_gap),
                        branch_nodes=int(result.mip_node_count), seconds=time.perf_counter()-start,
                        eligible_paths=len(ids), reference_range_km=range_km,
                        contract_average_budget_cad_2021=len(chosen)*CONTRACT_UNIT if range_km==150 else None)


def replay_paths(trips, paths, range_km):
    covered, schedules, min_gap = [], [], math.inf
    for v,p in enumerate(paths,1):
        remaining = range_km
        previous = None
        for i in p:
            t = trips.iloc[i]
            covered.append(i)
            if previous is not None:
                assert previous.last_terminal == t.first_terminal
                gap = int(t.start_seconds-previous.end_seconds)
                assert gap >= 0
                min_gap = min(min_gap,gap)
            remaining -= float(t.distance_km_upper)
            assert remaining >= -1e-6
            schedules.append(dict(vehicle=v, activity="trip", trip_id=int(t.trip_id), route=t.route_short_name,
                                  start=hhmm(t.start_seconds), end=hhmm(t.end_seconds),
                                  start_seconds=int(t.start_seconds), end_seconds=int(t.end_seconds),
                                  origin=t.first_terminal, destination=t.last_terminal,
                                  origin_stop=t.first_stop_id, destination_stop=t.last_stop_id,
                                  km_upper=float(t.distance_km_upper), remaining_range_credit_km=remaining))
            previous=t
    assert sorted(covered)==list(range(len(trips)))
    return schedules, dict(exact_trip_coverage=True, chronological_and_terminal_continuity=True,
                           range_credit_valid=True, minimum_connection_window_min=None if math.isinf(min_gap) else min_gap/60,
                           physical_bay_transfers_checked=False, depot_and_periodic_closure_checked=False)


@dataclass
class Event:
    kind: str
    start: int
    end: int
    origin: str
    destination: str
    km: float = 0.0
    trip_index: int | None = None
    credit: float = 0.0


class Rows:
    def __init__(self):
        self.rr=[]; self.cc=[]; self.vv=[]; self.lo=[]; self.hi=[]
    def add(self, pairs, lo=-np.inf, hi=np.inf):
        r=len(self.lo)
        for c,v in pairs:
            if v:
                self.rr.append(r); self.cc.append(c); self.vv.append(v)
        self.lo.append(lo); self.hi.append(hi)
    def constraint(self, size):
        mat=coo_matrix((self.vv,(self.rr,self.cc)),shape=(len(self.lo),size)).tocsc()
        return LinearConstraint(mat,np.array(self.lo),np.array(self.hi))


def arc_milp(trips, charging, credit, time_limit=90):
    """Mandatory trip nodes and optional single-capacity charger-slot nodes.

    Range balance is exact in the stated proxy model. Flow through one charging
    node is binary, enforcing one bus per five-minute slot without per-bus IDs.
    All connections stay at a named terminal, never between distinct terminals.
    """
    events=[Event("trip",int(t.start_seconds),int(t.end_seconds),t.first_terminal,t.last_terminal,
                  float(t.distance_km_upper),i) for i,t in enumerate(trips.itertuples())]
    if charging:
        first=int(trips.start_seconds.min()); last=int(trips.end_seconds.max())
        for site in ("22nd Street Station","Marpole Loop"):
            for begin in range(math.ceil(first/300)*300,last-299,300):
                events.append(Event("charge",begin,begin+300,site,site,credit=credit))
    events.sort(key=lambda e:(e.start,e.end,e.kind))
    n=len(events)
    arcs=[(i,j) for i,a in enumerate(events) for j,b in enumerate(events)
          if i<j and a.end<=b.start and a.destination==b.origin]
    incoming=[[] for _ in events]; outgoing=[[] for _ in events]
    for a,(i,j) in enumerate(arcs):
        outgoing[i].append(a); incoming[j].append(a)
    m=len(arcs); start0=m; end0=m+n; use0=m+2*n; soc0=m+3*n; q0=m+4*n; size=m+5*n
    lower=np.zeros(size); upper=np.ones(size); integ=np.zeros(size)
    integ[:soc0]=1
    upper[soc0:q0]=RANGE_KM
    upper[q0:]=0
    for i,e in enumerate(events):
        if e.kind=="trip":
            lower[use0+i]=upper[use0+i]=1
            upper[soc0+i]=max(0,RANGE_KM-e.km)
        else:
            upper[start0+i]=upper[end0+i]=0
            upper[q0+i]=e.credit
    c=np.zeros(size); c[start0:end0]=1
    rows=Rows()
    time_terminal_bound=len(matching_paths(trips))
    energy_bound=math.ceil(float(trips.distance_km_upper.sum())/RANGE_KM-1e-10) if not charging else 0
    rows.add([(start0+i,1) for i in range(n)],lo=max(time_terminal_bound,energy_bound))
    M=2*RANGE_KM+max(e.km for e in events)
    for i,e in enumerate(events):
        rows.add([(a,1) for a in incoming[i]]+[(start0+i,1),(use0+i,-1)],0,0)
        rows.add([(a,1) for a in outgoing[i]]+[(end0+i,1),(use0+i,-1)],0,0)
        rows.add([(soc0+i,1),(use0+i,-RANGE_KM)],hi=0)
        if e.kind=="charge":
            rows.add([(q0+i,1),(use0+i,-e.credit)],hi=0)
        else:
            # A newly deployed vehicle starts this service window with full credit.
            rows.add([(soc0+i,1),(start0+i,-M)],lo=RANGE_KM-e.km-M)
            rows.add([(soc0+i,1),(start0+i,M)],hi=RANGE_KM-e.km+M)
    for a,(i,j) in enumerate(arcs):
        # x=1 => r_after(j) = r_after(i) + recharge(j) - distance(j).
        base=[(soc0+j,1),(soc0+i,-1),(q0+j,-1)]
        rows.add(base+[(a,M)],hi=M-events[j].km)
        rows.add(base+[(a,-M)],lo=-M-events[j].km)
    constraints=rows.constraint(size)
    begin=time.perf_counter()
    result=milp(c,integrality=integ,bounds=Bounds(lower,upper),constraints=constraints,
                options={"mip_rel_gap":0.0,"time_limit":time_limit,"node_limit":SOLVER_NODE_LIMIT})
    primary_seconds=time.perf_counter()-begin
    if result.x is None:
        return None, dict(status=int(result.status),message=result.message,seconds=primary_seconds,
                          events=n,arcs=m,variables=size,constraints=len(rows.lo))
    fleet=int(round(sum(result.x[start0:end0])))
    primary=dict(status=int(result.status),message=result.message,fleet_size=fleet,
                 objective_lower_bound=float(result.mip_dual_bound),mip_gap=float(result.mip_gap),
                 branch_nodes=int(result.mip_node_count),seconds=primary_seconds,
                 events=n,arcs=m,variables=size,constraints=len(rows.lo),
                 independent_time_terminal_bound=time_terminal_bound,
                 aggregate_range_bound_without_charge=energy_bound if not charging else None,
                 contract_average_budget_cad_2021=fleet*CONTRACT_UNIT,
                 charging_enabled=charging,credit_per_five_minutes_km=credit if charging else 0)
    # Lexicographic tie-break only after the minimum fleet is certified. It keeps
    # procurement optimal and avoids gratuitous charging in the displayed plan.
    if result.status==0 and charging:
        rows.add([(start0+i,1) for i in range(n)],fleet,fleet)
        tie=np.zeros(size)
        for i,e in enumerate(events):
            if e.kind=="charge": tie[use0+i]=1
        tie_result=milp(tie,integrality=integ,bounds=Bounds(lower,upper),constraints=rows.constraint(size),
                        options={"mip_rel_gap":0.0,"time_limit":30.0})
        if tie_result.x is not None:
            result=tie_result
        primary["charge_count_tiebreak_status"]=int(tie_result.status)
    x=result.x
    succ={i:j for a,(i,j) in enumerate(arcs) if x[a]>.5}
    starts=[i for i in range(n) if x[start0+i]>.5]
    schedules=[]; covered=[]; occupied=[]; min_gap=math.inf
    for v,i in enumerate(starts,1):
        remaining=RANGE_KM; seen=set(); previous=None
        while True:
            assert i not in seen
            seen.add(i); e=events[i]
            if previous is not None:
                assert previous.destination==e.origin and previous.end<=e.start
                min_gap=min(min_gap,e.start-previous.end)
            gain=float(x[q0+i])
            if e.kind=="trip":
                covered.append(e.trip_index); remaining-=e.km
                t=trips.iloc[e.trip_index]
                tid=int(t.trip_id); route=t.route_short_name
                stop_a=t.first_stop_id; stop_b=t.last_stop_id
            else:
                assert -1e-5<=gain<=credit+1e-5
                occupied.append((e.origin,e.start,e.end,v))
                remaining+=gain; tid=None;route=None;stop_a=None;stop_b=None
            assert -1e-4<=remaining<=RANGE_KM+1e-4,(v,i,remaining)
            assert abs(remaining-x[soc0+i])<1e-3,(v,i,remaining,x[soc0+i])
            schedules.append(dict(vehicle=v,activity=e.kind,trip_id=tid,route=route,
                                  start=hhmm(e.start),end=hhmm(e.end),start_seconds=e.start,end_seconds=e.end,
                                  origin=e.origin,destination=e.destination,origin_stop=stop_a,destination_stop=stop_b,
                                  km_upper=e.km,charge_credit_km=gain,
                                  remaining_range_credit_km=max(0,remaining)))
            previous=e
            if i not in succ:
                assert x[end0+i]>.5
                break
            i=succ[i]
    assert sorted(covered)==list(range(len(trips)))
    assert len(starts)==fleet
    for site in {r[0] for r in occupied}:
        intervals=sorted((a,b,v) for s,a,b,v in occupied if s==site)
        for (_,left_end,_),(right_start,_,_) in zip(intervals,intervals[1:]):
            assert left_end<=right_start
    primary["charging_sessions"]=len(occupied)
    primary["total_charge_credit_km"]=sum(r["charge_credit_km"] for r in schedules)
    primary["checks"]=dict(exact_trip_coverage=True,chronological_and_terminal_continuity=True,
                             range_credit_replay=True,single_position_charger_capacity=True,
                             minimum_connection_window_min=None if math.isinf(min_gap) else min_gap/60,
                             battery_SOC_curve_verified=False,physical_bay_transfers_checked=False,
                             depot_and_periodic_closure_checked=False)
    return schedules,primary


def save_schedule(name,schedules,trips):
    pd.DataFrame(schedules).to_csv(OUT/f"{name}_schedule.csv",index=False,encoding="utf-8-sig")
    trips.to_csv(OUT/f"{name}_trips.csv",index=False,encoding="utf-8-sig")


def summary(trips):
    events=[]
    for t in trips.itertuples(): events.extend([(t.start_seconds,1),(t.end_seconds,-1)])
    active=peak=0
    for _,delta in sorted(events): active+=delta;peak=max(peak,active)
    return dict(trips=len(trips),route_counts={str(k):int(v) for k,v in trips.route_short_name.value_counts().items()},
                start=hhmm(trips.start_seconds.min()),last_arrival=hhmm(trips.end_seconds.max()),
                loaded_km_lower=float(trips.distance_km_lower.sum()),loaded_km_upper=float(trips.distance_km_upper.sum()),
                concurrency_lower_bound=peak,capacity_proxy_classes=sorted(trips.proxy_class.unique()))


def write_report(result):
    lines=["# 多线路联合排班算法试验", "", "## 结论口径", "",
           "本试验保留所选窗口内全部公布班次，允许重新指派车辆及跨线路接班；不固定原 block。不调整发车时刻，因为尚无经确认的允许偏移窗口。",
           "结果为终点站层级、服务窗口内的优化；站内移车耗时/耗能被放松，车辆可在所选终点开始和结束。不能直接解释为完整日、车库或十年连续运营可行车队。",
           "型号、价格与充电的直接资料及一步推断见 ../research/linked_route_trial_evidence.json。", "",
           "## 价格与参数", "",
           "2021 官方采购公告给出15辆Nova电动车、1600万加元合同；2023公告确认该批车型LFSe+。历史合同均价为1,066,666.67加元/辆，未调整年份，未宣称是当前裸车报价。",
           "150 km使用运营方对LFSe+的公开续航说明。40 km仅用作旧Nova续航参照，不套用新车单价。最大564 kWh是产品选项，不据车型名推断这批实车必装该电池。",
           "现有载客基准为cap50历史服务容量代理；不把它当逐班实测峰值或完整载荷认证。", "",
           "## 北岸：229、231、236", ""]
    north=result.get("north")
    if north:
        lines += [f"日期2023-11-14，选取06:00—12:00发车的{north['data']['trips']}班，并执行至最后到达。",
                  f"累计载客距离上界 {north['data']['loaded_km_upper']:.3f} km；峰值同时载客车辆下界 {north['data']['concurrency_lower_bound']}。",
                  f"完整生成 {north['all_time_terminal_paths']:,} 条单车路径；这是候选单车排班数，不是整支车队组合数。", "",
                  "|模式|续航额度 km|最小车辆数|求解下界|gap|", "|---|---:|---:|---:|---:|"]
        for key,r in north["cases"].items():
            lines.append(f"|{key}|{r['reference_range_km']:g}|{r['fleet_size']}|{r['objective_lower_bound']:g}|{r['mip_gap']:.6f}|")
        lines += ["", "229/231/236没有凭空设置途中充电。该组用于验证多线路联合接班与单线分开优化的差别，以及续航限制的影响。", ""]
    south=result.get("south")
    if south:
        lines += ["## 已有充电站附近：100、101", "",
                  f"同日选取06:00—{south['end_hour']:02d}:00发车的{south['data']['trips']}班；在22nd Street和Marpole使用每站一个充电服务位置的推断。",
                  f"每个5分钟服务块最多恢复 {south['topup_credit_km']:.4f} km 的运营里程额度，来自当日100路最短里程下界与‘约5分钟补下一趟’的转移代理；不是满充150 km，也不是实测SOC曲线。",
                  "只比较同一任务集合、同一站点聚合边界下有/无充电的两种优化。", "",
                  "|模式|车辆数|下界|gap|充电次数|", "|---|---:|---:|---:|---:|"]
        for key,r in south["cases"].items():
            lines.append(f"|{key}|{r.get('fleet_size','未取得解')}|{r.get('objective_lower_bound','')}|{r.get('mip_gap','')}|{r.get('charging_sessions','')}|")
        lines += ["", "本站资源只为所选服务保留；其他线路/未选班次占用未知。因此属于资源可用条件下的联动测试，不能称为现网实施证书。", ""]
    lines += ["## 100亿上限与验证", "",
              "用户上限为10,000,000,000。对完整枚举部分，先动态计数再展开，不超过该上限；不会把整支车队组合数冒充已枚举数。较大问题采用弧MILP并设搜索节点上限，节点数也不等于方案数。",
              "每份排班均独立重放覆盖、时间、终点与里程额度；有充电时检查单站同时占用。数据足够才认证SOC、站内移车及周期恢复，这些当前明确为未验证。",
              "只有全列枚举+整数最优，或紧凑MILP零gap，才报告本子模型最优。时间上限终止时报告可行解及下界，不称最优。", "",
              "## 输出", "", "- result.json：数据边界、全部计算统计、下界及验证结果。",
              "- *_trips.csv：各组原始班次快照。", "- *_schedule.csv：逐车班次与充电活动、剩余里程额度。",
              "- trial.png：联动排班时序图。", ""]
    (OUT/"readout.md").write_text("\n".join(lines),encoding="utf-8")


def plot_results(result):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.sans-serif"]=["Microsoft YaHei","DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"]=False
    names=[]
    if "north" in result: names.append(("north_joint_150","229 / 231 / 236：联合接班（无途中充电）"))
    if names and (OUT/"north_joint_150_slack_schedule.csv").exists():
        names[0]=("north_joint_150_slack",names[0][1])
    if "south" in result and result["south"]["cases"]["charging"].get("fleet_size"):
        names.append(("south_charging","100 / 101：联合接班与充电（里程额度代理）"))
    if not names:return
    fig,axs=plt.subplots(len(names),1,figsize=(15,5*len(names)),squeeze=False)
    colors={"229":"#2878b5","231":"#f1a340","236":"#59a14f","100":"#2878b5","101":"#f1a340"}
    for ax,(name,title) in zip(axs[:,0],names):
        df=pd.read_csv(OUT/f"{name}_schedule.csv",dtype={"route":str})
        for r in df.itertuples():
            color="#b24c63" if r.activity=="charge" else colors.get(r.route,"gray")
            ax.barh(r.vehicle,(r.end_seconds-r.start_seconds)/3600,left=r.start_seconds/3600,height=.65,color=color)
            if r.activity=="trip" and r.end_seconds-r.start_seconds>=600:
                ax.text((r.start_seconds+r.end_seconds)/7200,r.vehicle,r.route,ha="center",va="center",fontsize=6,color="white")
        ax.set_title(title,loc="left",fontweight="bold");ax.set_xlabel("时刻 / 小时");ax.set_ylabel("模型车辆编号")
        ax.set_yticks(range(1,int(df.vehicle.max())+1));ax.grid(axis="x",alpha=.2);ax.invert_yaxis()
    fig.suptitle("多线路算法测试：终点站聚合、局部服务窗口；不代表完整日调度认证",fontsize=13)
    fig.tight_layout(rect=(0,0,1,.96));fig.savefig(OUT/"trial.png",dpi=160);plt.close(fig)


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--part",choices=["north","south","all"],default="all")
    parser.add_argument("--south-end",type=int,default=24);parser.add_argument("--time-limit",type=float,default=90)
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    data,source,raw=load_day()
    result=json.loads((OUT/"result.json").read_text()) if (OUT/"result.json").exists() else {}
    result.update(date=str(DAY),status="EVIDENCE_LABELLED_TERMINAL_LEVEL_WINDOW_TRIAL",
                  source_sha256=digest(source),source_path=str(source.relative_to(ROOT)),
                  maximum_generated_paths=PATH_LIMIT,maximum_solver_nodes=SOLVER_NODE_LIMIT,
                  historical_contract_average_cad_2021=CONTRACT_UNIT)
    def check_raw(trips):
        for t in trips.itertuples():
            orig=raw.loc[str(t.trip_id)]
            assert orig.block_id==str(t.block_id) and orig.service_id==str(t.service_id)
    if args.part in ("north","all"):
        trips=select(data,["229","231","236"],6,12);check_raw(trips)
        succ=successors(trips); paths,kms,count=enumerate_paths(trips,succ)
        north=dict(data=summary(trips),all_time_terminal_paths=count,cases={})
        for R in [150.,40.]:
            chosen,meta=solve_partition(trips,paths,kms,R)
            schedules,checks=replay_paths(trips,chosen,R);meta["checks"]=checks
            name=f"north_joint_{int(R)}";save_schedule(name,schedules,trips);north["cases"][f"joint_{int(R)}"]=meta
            print(json.dumps(dict(case=name,**meta),ensure_ascii=False),flush=True)
        solo_paths,solo_kms,solo_count=enumerate_paths(trips,successors(trips,True))
        chosen,meta=solve_partition(trips,solo_paths,solo_kms,150.)
        schedules,checks=replay_paths(trips,chosen,150.);meta["checks"]=checks
        save_schedule("north_separate_150",schedules,trips);north["cases"]["separate_150"]=meta
        north["separate_paths"]=solo_count
        # No path in this window exceeds 150 km, so matching is an independent
        # optimality certificate and can maximize minimum connection slack.
        assert float(kms.max())<=150
        plain=matching_paths(trips)
        assert len(plain)==north["cases"]["joint_150"]["fleet_size"]
        slack_paths,slack=maximum_connection_slack(trips,len(plain))
        schedules,checks=replay_paths(trips,slack_paths,150.)
        save_schedule("north_joint_150_slack",schedules,trips)
        north["cost_optimal_maximum_minimum_connection_window_min"]=slack/60
        north["independent_matching_certificate"]=len(plain)
        north["slack_schedule_checks"]=checks
        full=select(data,["229","231","236"],0,28)
        north["full_day_time_terminal_paths_not_enumerated"]=path_count(successors(full))
        result["north"]=north
        (OUT/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    if args.part in ("south","all"):
        trips=select(data,["100","101"],6,args.south_end);check_raw(trips)
        credit=float(data.loc[data.route_short_name=="100","distance_km_lower"].min())
        south=dict(data=summary(trips),topup_credit_km=credit,end_hour=args.south_end,cases={})
        for charging in [False,True]:
            schedules,meta=arc_milp(trips,charging,credit,args.time_limit)
            key="charging" if charging else "no_charging";south["cases"][key]=meta
            if schedules is not None:
                save_schedule(f"south_{key}",schedules,trips)
                save_schedule(f"south_{args.south_end}_{key}",schedules,trips)
            print(json.dumps(dict(case=key,**meta),ensure_ascii=False),flush=True)
            result["south"]=south
            result.setdefault("south_windows",{})[str(args.south_end)]=south
            (OUT/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    write_report(result);plot_results(result)
    print(str(OUT/"readout.md"),flush=True)


if __name__=="__main__":main()
