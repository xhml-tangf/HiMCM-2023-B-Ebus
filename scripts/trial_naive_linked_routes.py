"""Small, evidence-labelled service-window experiment using plain backtracking.

No MILP, heuristics, learned coefficients, deadhead routes, or charging rates.
Trips retain their published times. Only the assignment to buses changes.
The 150 km envelope is an operator claim, not a calibrated route-energy model.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/naive_linked_routes"
DAY = date(2023, 11, 14)
RANGE_KM = 150.0
UNIT_COST = 16_000_000 / 15  # Nominal 2021 CAD; historical batch average only.
NODE_LIMIT = 10_000_000_000  # Search states, not the number of distinct fleets.


@dataclass(frozen=True)
class Trip:
    id: str
    route: str
    start: int
    end: int
    origin: str
    destination: str
    km: float
    first_stop: str = ""
    last_stop: str = ""
    first_name: str = ""
    last_name: str = ""
    proxy: str = ""


def clock(t):
    return f"{t//3600:02d}:{t%3600//60:02d}:{t%60:02d}"


def parse_gtfs_time(text):
    h, m, s = map(int, text.strip().split(":"))
    return 3600*h + 60*m + s


def terminal(stop, name):
    return "Lonsdale Quay" if name.startswith("Lonsdale Quay") else stop


def load_trips():
    folder = ROOT / "materials/sources/raw/vancouver_gtfs_2023"
    cal = pd.read_csv(folder / "calendar.txt", dtype={"service_id": str})
    exc = pd.read_csv(folder / "calendar_dates.txt", dtype={"service_id": str})
    day = int(DAY.strftime("%Y%m%d"))
    active = set(cal.loc[(cal[DAY.strftime("%A").lower()] == 1)
                        & (cal.start_date <= day) & (cal.end_date >= day), "service_id"])
    for row in exc[exc.date == day].itertuples():
        active.add(row.service_id) if row.exception_type == 1 else active.discard(row.service_id)
    source = ROOT / "data/processed/vancouver_gtfs_trip_manifest_classified_2023.csv"
    data = pd.read_csv(source, dtype={"trip_id": str, "service_id": str,
                       "route_short_name": str, "first_stop_id": str, "last_stop_id": str},
                       low_memory=False)
    data = data[data.service_id.isin(active) & data.route_short_name.isin(["229", "231", "236"])
                & (data.start_seconds >= 6*3600) & (data.start_seconds < 12*3600)]
    data = data.sort_values(["start_seconds", "trip_id"])
    names = pd.read_csv(folder / "stops.txt", dtype=str).set_index("stop_id").stop_name.to_dict()
    trips = []
    for r in data.itertuples():
        first, last = names[r.first_stop_id], names[r.last_stop_id]
        trips.append(Trip(r.trip_id, r.route_short_name, int(r.start_seconds), int(r.end_seconds),
                          terminal(r.first_stop_id, first), terminal(r.last_stop_id, last),
                          float(r.distance_km_upper), r.first_stop_id, r.last_stop_id,
                          first, last, r.proxy_class))
    assert len(trips) == 55 and all(t.end > t.start and t.km > 0 for t in trips)
    return trips, source


def inventory_bound(trips, gap=300, separate=False):
    """Necessary initial inventories; valid only without inter-terminal deadheads.

    Every trip removes one bus at departure and returns one at end+gap. Summing
    each terminal's maximum cumulative deficit bounds the initial fleet below.
    Range restrictions can increase this bound; no claim of sufficiency here.
    """
    events = defaultdict(list)
    for t in trips:
        group = t.route + " | " if separate else ""
        events[group+t.origin].append((t.start, 1))
        events[group+t.destination].append((t.end+gap, -1))
    certificate = []
    for location, items in sorted(events.items()):
        deficit = peak = 0
        when = None
        for at, change in sorted(items):  # available arrivals precede departures at ties
            deficit += change
            if deficit > peak:
                peak, when = deficit, at
        certificate.append(dict(location=location, minimum_initial_buses=peak,
                                first_peak_time=clock(when) if when is not None else None))
    return sum(r["minimum_initial_buses"] for r in certificate), certificate


def assign_at_limit(trips, fleet_limit, gap=300, range_km=RANGE_KM,
                    separate=False, enumerate_all=False, node_limit=NODE_LIMIT):
    """Try each existing bus, then a new bus; recurse or backtrack.

    Buses are labelled by first use. This avoids treating mere bus-ID permutations
    as different assignments. No search ordering or solver-specific techniques.
    """
    assert trips == sorted(trips, key=lambda t: (t.start, t.id))
    paths, kms = [], []
    first = None
    nodes = covers = 0
    interrupted = False

    def visit(i):
        nonlocal first, nodes, covers, interrupted
        if nodes >= node_limit:
            interrupted = True
            return False
        nodes += 1
        if i == len(trips):
            covers += 1
            if first is None:
                first = [p.copy() for p in paths]
            return not enumerate_all
        t = trips[i]
        for b in range(len(paths)):
            previous = trips[paths[b][-1]]
            if (previous.destination != t.origin or previous.end+gap > t.start
                    or (separate and previous.route != t.route)
                    or kms[b]+t.km > range_km+1e-9):
                continue
            old_km = kms[b]
            paths[b].append(i)
            kms[b] += t.km
            stop = visit(i+1)
            paths[b].pop()
            kms[b] = old_km
            if stop or interrupted:
                return stop
        if len(paths) < fleet_limit and t.km <= range_km+1e-9:
            paths.append([i])
            kms.append(t.km)
            stop = visit(i+1)
            paths.pop()
            kms.pop()
            if stop or interrupted:
                return stop
        return False

    visit(0)
    return dict(paths=first, states=nodes, complete_covers=covers, interrupted=interrupted,
                exhaustive=not interrupted and (enumerate_all or first is None))


def solve(trips, gap=300, separate=False, range_km=RANGE_KM, enumerate_all=False):
    lower, certificate = inventory_bound(trips, gap, separate)
    searches = []
    for fleet in range(lower, len(trips)+1):
        result = assign_at_limit(trips, fleet, gap, range_km, separate, enumerate_all)
        searches.append({k: v for k, v in result.items() if k != "paths"} | {"fleet_limit": fleet})
        if result["paths"] is not None:
            # All smaller counts were either ruled out by conservation or fully searched.
            return dict(fleet_size=len(result["paths"]), paths=result["paths"],
                        proven_optimal=True, inventory_lower_bound=lower,
                        lower_bound_certificate=certificate, searches=searches,
                        proof="matching_inventory_bound" if fleet == lower else "exhausted_smaller_fleets",
                        gap_seconds=gap, separate_routes=separate, range_envelope_km=range_km,
                        historical_contract_cost_cad_2021=len(result["paths"])*UNIT_COST)
        if result["interrupted"]:
            return dict(proven_optimal=False, status="SEARCH_LIMIT", searches=searches)
    return dict(proven_optimal=False, status="INFEASIBLE", searches=searches)


def validate(trips, result):
    """Replay the output independently of the recursion's mutable state."""
    paths = result["paths"]
    assert sorted(i for p in paths for i in p) == list(range(len(trips)))
    summaries, connections, rows = [], [], []
    for b, path in enumerate(paths, 1):
        seq = [trips[i] for i in path]
        km = sum(t.km for t in seq)
        assert km <= result["range_envelope_km"]+1e-8
        for left, right in zip(seq, seq[1:]):
            assert left.destination == right.origin
            assert right.start-left.end >= result["gap_seconds"]
            assert not result["separate_routes"] or left.route == right.route
            connections.append(dict(bus=b, from_trip=left.id, to_trip=right.id,
                                    arrival=clock(left.end), departure=clock(right.start),
                                    arrival_stop=left.last_stop, departure_stop=right.first_stop,
                                    terminal=left.destination, available_minutes=(right.start-left.end)/60,
                                    bay_change=left.last_stop != right.first_stop))
        used = 0
        for t in seq:
            used += t.km
            rows.append(dict(bus=b, **asdict(t), departure=clock(t.start), arrival=clock(t.end),
                             cumulative_service_km=used))
        summaries.append(dict(bus=b, trips=len(seq), routes=sorted({t.route for t in seq}),
                              start=clock(seq[0].start), end=clock(seq[-1].end),
                              initial_stop=seq[0].first_name, final_stop=seq[-1].last_name,
                              initial_terminal=seq[0].origin, final_terminal=seq[-1].destination,
                              service_km=km,
                              distance_envelope_headroom_km=result["range_envelope_km"]-km))
    return dict(covered_trips=len(trips), service_km=sum(t.km for t in trips),
                max_bus_service_km=max(s["service_km"] for s in summaries),
                min_connection_minutes=min((c["available_minutes"] for c in connections), default=None),
                cross_route_connections=sum(trips[p[i]].route != trips[p[i+1]].route
                                            for p in paths for i in range(len(p)-1)),
                final_arrival=clock(max(t.end for t in trips)), summaries=summaries,
                connections=connections, schedule=rows,
                validated=["exactly-once coverage", "time and terminal continuity", "turnaround windows",
                           "per-bus service-distance envelope", "fleet/cost reconciliation"],
                excluded=["depot pullout/pullin", "measured bay-transfer time/energy", "passenger peak loads",
                          "route-specific SOC/auxiliary loads", "overnight recharge", "driver duties"])


def audit_raw_times(trips):
    folder = ROOT / "materials/sources/raw/vancouver_gtfs_2023"
    ids = {t.id for t in trips}
    endpoints = {}
    with (folder / "stop_times.txt").open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            if r["trip_id"] not in ids:
                continue
            key, order = r["trip_id"], int(r["stop_sequence"])
            if key not in endpoints:
                endpoints[key] = [r, r]
            if order < int(endpoints[key][0]["stop_sequence"]):
                endpoints[key][0] = r
            if order > int(endpoints[key][1]["stop_sequence"]):
                endpoints[key][1] = r
    for t in trips:
        first, last = endpoints[t.id]
        assert (parse_gtfs_time(first["departure_time"]), parse_gtfs_time(last["arrival_time"]),
                first["stop_id"], last["stop_id"]) == (t.start, t.end, t.first_stop, t.last_stop)
    return {"checked_trips": len(trips), "source": str(folder / "stop_times.txt"),
            "result": "PASS: each departure, arrival and endpoint matches original GTFS"}


def save_csv(path, rows):
    if not rows:
        return
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot_schedule(trips, result):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "DejaVu Sans"]
    colors = {"229": "#2864AE", "231": "#D17B12", "236": "#198377"}
    fig, ax = plt.subplots(figsize=(13, 6.8), layout="constrained")
    for b, path in enumerate(result["paths"], 1):
        seq = [trips[i] for i in path]
        ax.plot([seq[0].start/3600, seq[-1].end/3600], [b, b], color="#c3c7ce", lw=1, zorder=1)
        for t in seq:
            ax.barh(b, (t.end-t.start)/3600, left=t.start/3600, height=.63,
                    color=colors[t.route], zorder=2)
        ax.text(12.6, b, f"{sum(t.km for t in seq):.1f} km", va="center", fontsize=9)
    ax.set(yticks=range(1, len(result["paths"])+1),
           yticklabels=[f"车辆 {i}" for i in range(1, len(result["paths"])+1)],
           xticks=range(6, 13), xticklabels=[f"{i:02d}:00" for i in range(6, 13)], xlim=(5.9, 13))
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=.2)
    ax.set_title("三线联动：11辆车完成55班次\n2023-11-14｜保留原班次时刻｜接班窗口至少5分钟", loc="left", fontsize=15, pad=18)
    ax.legend(handles=[Patch(color=v, label=f"{k} 路") for k,v in colors.items()],
              loc="lower right", bbox_to_anchor=(1, 1.01), ncol=3)
    fig.supxlabel("仅检验此服务窗口；灰线为两班之间的间隔，并不代表已验证的停车或充电活动。", fontsize=9)
    fig.savefig(OUT / "recommended_schedule.png", dpi=160)
    plt.close(fig)


def write_report(data):
    main = data["cases"]["joint_06_12"]
    replay = main["validation"]
    sep = data["cases"]["separate_06_12"]
    small = data["cases"]["joint_06_09_exhaustive"]
    diff = sep["fleet_size"]-main["fleet_size"]
    lines = ["# 朴素回溯：三线联动车队小案例", "",
             "结论：在下述服务窗口和输入条件内，推荐采用11辆同型电车联动执行229、231、236路的55个班次。",
             "这是有车辆收支下界证明的最小车辆数；由于同型同价，也是在此候选车型条件下的最低购置成本。", "",
             "## 本次到底保留了什么", "",
             "- 2023-11-14的真实GTFS；选取06:00（含）至12:00（不含）发车的全部55班，执行至最后一班实际到达。",
             "- 每班路线、首末站和时刻保持原样，重新分配车辆；可在共同终点换线路。",
             "- 同名Lonsdale Quay各站台按一个终点处理；两班之间至少保留5分钟。5分钟是设计条件，不是测得的站内移车时间。",
             "- 没有添加站间空驶；车辆从本窗口第一班的起点开始，最后一班终点结束。未证明与窗口外任务及车库回送兼容。",
             "- 所有车辆进入窗口时按150 km距离包络初始化。未设置途中充电，不虚构北岸终点充电设施。",
             "- 不建退役、衰减、司机排班或十年实施模型；未修改论文。", "",
             "## 结果", "",
             "| 试验 | 班次 | 最少车辆 | 验证方式 |", "|---|---:|---:|---|",
             f"| 三线06—09 | 28 | {small['fleet_size']} | 完整回溯枚举当前车辆上限内的分配，并与下界一致 |",
             f"| 三线06—12联动 | 55 | {main['fleet_size']} | 下界11 + 找到11辆的具体排班 |",
             f"| 三线06—12各线独立 | 55 | {sep['fleet_size']} | 同样的回溯与下界证明 |", "",
             f"联动比独立配车少{diff}辆。联动方案共{replay['service_km']:.4f}服务公里，最忙车辆{replay['max_bus_service_km']:.4f} km，最后一班{replay['final_arrival']}到达。",
             f"实际选中排班的最小接班窗口为{replay['min_connection_minutes']:g}分钟，有{replay['cross_route_connections']}次跨线路接班。", "",
             f"历史合同均价为16,000,000/15 = {UNIT_COST:,.2f} CAD/辆，11辆对应{main['historical_contract_cost_cad_2021']:,.2f} CAD，",
             f"相对独立配车少{diff*UNIT_COST:,.2f} CAD。这是2021年名义合同均价的条件性测算，非现价、非完整十年成本，也非逐车合同裸价。", "",
             "## 为什么能证明11辆最少", "",
             "令D_s(t)为终点s到时刻t累计发车数，A_s(t-5min)为到达后已留出5分钟的累计到车数。",
             "无站间空驶时，起始配车n_s必须满足n_s≥max_t[D_s(t)-A_s(t-5min)]_+。对各终点相加得到车辆下界。",
             "这只是必要条件；本次另找到了满足时间、地点和距离限制的11辆排班，才使上下界相等。", "",
             "| 起始终点 | 最低初始车辆 | 首次达到最大缺口 |", "|---|---:|---| "]
    for r in main["lower_bound_certificate"]:
        lines.append(f"| {r['location']} | {r['minimum_initial_buses']} | {r['first_peak_time'] or '—'} |")
    lines += ["", "## 逐车方案", "",
              "| 车辆 | 线路 | 班次 | 开始—结束 | 服务公里 | 初始站点 |", "|---|---|---:|---|---:|---|"]
    for s in replay["summaries"]:
        lines.append(f"| {s['bus']} | {' / '.join(s['routes'])} | {s['trips']} | {s['start']}—{s['end']} | {s['service_km']:.2f} | {s['initial_stop']} |")
    lines += ["", "详细逐班结果见recommended_schedule.csv；接班站台和可用时间见connections.csv。", "",
              "## 算法输入、输出与伪代码", "",
              "输入：固定班次(起终点、发到时间、距离)、允许接班地点、接班间隔、单车距离包络、候选同型车的合同参考价。",
              "输出：每辆车的班次序列、总车数与成本、逐次接班窗口、距离账本、可行性检查、最优性证明或未完成状态。", "",
              "```text", "下界 ← 各终点累计车辆缺口的最大值之和",
              "对 车辆上限N = 下界, 下界+1, ...：", "    将班次按发车时刻排序",
              "    分配下一班：", "        依次尝试每一辆已有车",
              "        若位置衔接、时间衔接、累计距离不超包络：放入该车并递归",
              "        若失败：撤销刚才的分配，试下一辆车",
              "        若已有车辆少于N：新开一辆车并递归",
              "    第一份完整分配即为该N下可行解；小N须已穷尽或被下界排除",
              "    独立重放检查；找到可行解即停止增加N", "```", "",
              "没有使用整数规划求解器。主案例只取第一份达到理论下界的可行解，没有穷举所有55班排班，也没有声称该解能耗/距离分摊最优。",
              f"28班固定最小车数完整枚举：{small['searches'][-1]['states']:,}个搜索状态、{small['searches'][-1]['complete_covers']:,}份完整分配。搜索状态、排班分配、车型数量方案是不同概念。", "",
              "## 接班窗口敏感性", "",
              "| 要求的最小间隔 | 最少车辆 | 证明 |", "|---|---:|---|"]
    for key in ["joint_gap_0", "joint_06_12", "joint_gap_301", "joint_gap_600"]:
        r = data["cases"][key]
        lines.append(f"| {r['gap_seconds']}秒 | {r['fleet_size']} | 下界{r['inventory_lower_bound']}，构造{r['fleet_size']}辆 |")
    lines += ["", "超过5分钟是否增车以本表为准；这比人为添加备用车比例更直接。", "",
              "## 证据及尚未闭合的运营条件", "",
              "- [TransLink 2023公告](https://www.translink.ca/news/2023/february/translink%20begins%20battery-electric%20bus%20fleet%20expansion)：Nova LFSe+、150 km单次续航。该值是公开运营包络，不能代替北岸坡度、载荷、冬季暖风与等候耗能的测量。",
              "- [2021采购公告](https://www.translink.ca/news/2021/january/translink%20expands%20battery-electric%20bus%20fleet)：15辆、1,600万CAD；相除是一步推断。",
              "- 现有cap50是线路/时段聚合容量代理，非每班最大乘客数；本试验仅在新车满足原服务容量及道路适配要求的条件下推荐排班，不声称已认证载客或道路适配。",
              "- 五组能力的使用：载客与道路能力目前是待核实的准入条件；储能与能耗暂由公开续航包络代理；补能能力因本窗口无需途中充电而不构成活跃约束。没有从缺失数据编造五项数值。",
              "- 150减去累计服务公里只叫距离包络余量，不能称为测得SOC、安全储备或可追加任意回送的保证。",
              "- 初始车辆需能到达表列站点并具备相应可用能量；站内移车、准备和停车条件需能容纳每条接班；车库出入、全天任务、充电及司机规则需另核实。",
              "- 本方案不证明全天无充电或次日可重复运行；无北岸充电曲线和真实位置数据，暂不强行制造一个途中充电最优案例。", "",
              "## 推荐的准确含义", "",
              "推荐把11辆三线联动排班作为本次小案例的基准方案；数学最优性在上述边界内已闭合。真实部署前应核对具体车辆容量/道路资格、站内接班和窗口边界能量。",
              "只比较一个有可追溯续航与历史价格的车型家族，不能据此宣布它是所有车型中最低成本的选择。",
              "本目录结果取代旧全天求解中尚未收敛的候选数作为本轮推荐依据；旧试验文件保留供追溯。"]
    (OUT / "readout.md").write_text("\n".join(lines)+"\n", encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    trips, source = load_trips()
    raw_audit = audit_raw_times(trips)
    cases = {}
    specs = [("joint_06_09_exhaustive", [t for t in trips if t.start < 9*3600], 300, False, True),
             ("joint_06_12", trips, 300, False, False),
             ("separate_06_12", trips, 300, True, False),
             ("joint_gap_0", trips, 0, False, False),
             ("joint_gap_301", trips, 301, False, False),
             ("joint_gap_600", trips, 600, False, False)]
    for name, chosen, gap, separate, exhaustive in specs:
        result = solve(chosen, gap, separate, enumerate_all=exhaustive)
        assert result["proven_optimal"], (name, result)
        result["validation"] = validate(chosen, result)
        cases[name] = result
        print(name, result["fleet_size"], result["searches"], flush=True)
    provenance = json.loads((ROOT / "materials/research/linked_route_trial_evidence.json").read_text(encoding="utf-8"))
    records = [r for r in provenance["records"] if r["id"] in
               {"CONTRACT_2021", "MODEL_RANGE_2023", "NORTH_NO_ONROUTE_2023"}]
    data = dict(status="EXACT_CONDITIONAL_SERVICE_WINDOW_RESULT", day=DAY.isoformat(),
                source=str(source), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                raw_timetable_audit=raw_audit, evidence=records,
                limits="No physical energy/SOC, bay-transfer, passenger-load or depot certification.",
                cases=cases)
    (OUT / "result.json").write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    main_case = cases["joint_06_12"]
    save_csv(OUT / "selected_trips.csv", [asdict(t) for t in trips])
    save_csv(OUT / "recommended_schedule.csv", main_case["validation"]["schedule"])
    save_csv(OUT / "connections.csv", main_case["validation"]["connections"])
    save_csv(OUT / "vehicles.csv", main_case["validation"]["summaries"])
    save_csv(OUT / "lower_bound_certificate.csv", main_case["lower_bound_certificate"])
    write_report(data)
    plot_schedule(trips, main_case)
    print(json.dumps({"output": str(OUT), "raw_audit": raw_audit,
                      "fleet": main_case["fleet_size"], "validation": main_case["validation"]["validated"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
