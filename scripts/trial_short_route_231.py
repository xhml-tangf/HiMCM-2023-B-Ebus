"""Counterfactual reblocking experiment, NOT the original route231 baseline.

For the replacement study use audit_route231_original_blocks.py instead.

Solve exact covers of all chronological trip subsets on route 231. Unknown
deadhead travel time, usable battery and charging efficiency remain requirements
or symbols. No retirement, degradation, depot coordinates or spare ratio.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/short_route_231_trial"
DAY = date(2023, 11, 14)
A, B = "12693", "9110"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hhmm(seconds):
    return f"{int(seconds)//3600:02d}:{int(seconds)%3600//60:02d}"


def active_ids(day, calendar, exceptions):
    key = int(day.strftime("%Y%m%d"))
    weekday = day.strftime("%A").lower()
    ids = set(calendar.loc[(calendar[weekday] == 1)
                          & (calendar.start_date <= key)
                          & (calendar.end_date >= key), "service_id"])
    for row in exceptions[exceptions.date == key].itertuples():
        if row.exception_type == 1:
            ids.add(row.service_id)
        else:
            ids.discard(row.service_id)
    return ids


def load():
    manifest_path = ROOT / "data/processed/vancouver_gtfs_trip_manifest_classified_2023.csv"
    mf = pd.read_csv(manifest_path, dtype={"service_id": str, "route_short_name": str,
                     "first_stop_id": str, "last_stop_id": str}, low_memory=False)
    mf = mf[mf.route_short_name == "231"].copy()
    cal = pd.read_csv(ROOT / "materials/sources/raw/vancouver_gtfs_2023/calendar.txt",
                      dtype={"service_id": str})
    exc = pd.read_csv(ROOT / "materials/sources/raw/vancouver_gtfs_2023/calendar_dates.txt",
                      dtype={"service_id": str})
    trips = mf[mf.service_id.isin(active_ids(DAY, cal, exc))].sort_values("start_seconds")
    trips = trips.reset_index(drop=True)
    assert len(trips) == 10
    assert set(trips.first_stop_id) == set(trips.last_stop_id) == {A, B}
    # Geometry bounds for an empty reposition use a published passenger alignment
    # with the same directed endpoints. No road factor or speed is invented.
    distances = {}
    for (origin, destination), g in trips.groupby(["first_stop_id", "last_stop_id"]):
        assert g.distance_km_lower.nunique() == g.distance_km_upper.nunique() == 1
        distances[(origin, destination)] = (float(g.distance_km_lower.iloc[0]),
                                            float(g.distance_km_upper.iloc[0]))
    return trips, mf, cal, exc, distances, manifest_path


def make_columns(trips, distances):
    rows = list(trips.itertuples())
    columns = []
    for mask in range(1, 1 << len(rows)):
        ids = [i for i in range(len(rows)) if mask & (1 << i)]
        chain = [rows[i] for i in ids]
        legs = []
        feasible = True
        if chain[0].first_stop_id != A:
            legs.append(dict(origin=A, destination=B,
                             window_min=float(chain[0].start_seconds / 60), kind="pullout"))
        for left, right in zip(chain, chain[1:]):
            gap = (right.start_seconds - left.end_seconds) / 60
            if gap < 0:
                feasible = False
                break
            if left.last_stop_id != right.first_stop_id:
                if gap <= 0:
                    feasible = False
                    break
                legs.append(dict(origin=left.last_stop_id, destination=right.first_stop_id,
                                 window_min=float(gap), kind="between_trips",
                                 after_trip=int(left.trip_id), before_trip=int(right.trip_id)))
        if not feasible:
            continue
        if chain[-1].last_stop_id != A:
            legs.append(dict(origin=B, destination=A,
                             window_min=float((86400 - chain[-1].end_seconds) / 60), kind="pullin"))
        lower = sum(distances[(leg["origin"], leg["destination"])][0] for leg in legs)
        upper = sum(distances[(leg["origin"], leg["destination"])][1] for leg in legs)
        columns.append(dict(mask=mask, indices=ids, trip_ids=[int(r.trip_id) for r in chain],
                            deadhead_legs=legs, deadhead_km_lower=lower, deadhead_km_upper=upper,
                            loaded_km_lower=sum(float(r.distance_km_lower) for r in chain),
                            loaded_km_upper=sum(float(r.distance_km_upper) for r in chain),
                            delta_limit_min=min((leg["window_min"] for leg in legs), default=math.inf),
                            first_departure_min=float(chain[0].start_seconds / 60),
                            last_arrival_min=float(chain[-1].end_seconds / 60),
                            initial_reposition=chain[0].first_stop_id != A,
                            final_reposition=chain[-1].last_stop_id != A))
    return columns


def solve(columns, trips, n, delta=0., no_deadhead=False):
    eligible = [p for p in columns if p["delta_limit_min"] + 1e-8 >= delta
                and (not no_deadhead or not p["deadhead_legs"])]
    if not eligible:
        return None
    mat = np.zeros((len(trips) + 1, len(eligible)))
    for j, p in enumerate(eligible):
        mat[p["indices"], j] = 1
        mat[-1, j] = 1
    rhs = np.r_[np.ones(len(trips)), n]
    result = milp(np.array([p["deadhead_km_upper"] for p in eligible]),
                  integrality=np.ones(len(eligible)), bounds=Bounds(0, 1),
                  constraints=LinearConstraint(mat, rhs, rhs),
                  options={"mip_rel_gap": 0.})
    if result.status == 2:
        return None
    if not result.success:
        raise RuntimeError(result.message)
    selected = [p for p, value in zip(eligible, result.x) if value > .5]
    assert len(selected) == n
    return selected, float(result.fun), float(result.mip_gap), int(result.mip_node_count)


def validate(selected, trips, delta, distances):
    # Independently replay locations, trip times, travel deadlines and a repeated
    # day. Battery/charger results below are required inputs, not certified supply.
    coverage = [i for p in selected for i in p["indices"]]
    assert sorted(coverage) == list(range(len(trips)))
    for p in selected:
        for repeat in (0, 1):
            now = repeat * 1440.
            location = A
            for i in p["indices"]:
                trip = trips.iloc[i]
                start = repeat * 1440 + trip.start_seconds / 60
                end = repeat * 1440 + trip.end_seconds / 60
                if location != trip.first_stop_id:
                    assert (location, trip.first_stop_id) in distances
                    now += delta
                assert now <= start + 1e-7
                now, location = end, trip.last_stop_id
            if location != A:
                now += delta
                location = A
            assert location == A and now <= (repeat + 1) * 1440 + 1e-7
    return dict(exact_trip_coverage=True, no_time_overlap=True,
                every_reposition_has_a_published_alignment=True,
                repeated_day_location_and_time_checked=True,
                battery_and_charging_status="REQUIREMENTS_ONLY_NOT_MEASURED_FEASIBILITY")


def write_readable_outputs(result):
    solutions = result["solutions"]
    masks = sorted({p["mask"] for p in result["vehicle_plans"]})
    labels = {mask: f"p{i+1}" for i, mask in enumerate(masks)}
    matrix = []
    for s in solutions:
        counts = {mask: 0 for mask in masks}
        for p in result["vehicle_plans"]:
            if p["fleet_size"] == s["vehicles"]:
                counts[p["mask"]] += 1
        matrix.append(dict(option=s["vehicles"], vehicle_type="LFSe+ six-battery",
                           **{labels[mask]: counts[mask] for mask in masks}))
    pd.DataFrame(matrix).to_csv(OUT / "fleet_matrices.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([dict(pattern=labels[m], mask=m,
                      trip_indices=";".join(str(i+1) for i in range(10) if m & (1 << i)))
                  for m in masks]).to_csv(OUT / "pattern_dictionary.csv", index=False, encoding="utf-8-sig")
    lines = ["# 231 路反事实重排试验（不作为原安排替换基准）", "",
             "> 已更正：此处 1—4 辆、7 分钟回送来自人为抽离 231 后的重新排车，不是原计划要求。原始安排包含跨线路任务链。保持原安排的结果见 ../short_route_231_original_blocks/readout.md。", "",
             "本实验不修改论文或规范结果；不考虑退役、寿命、衰减、替换。", "",
             "## 计算对象与边界", "",
             "- 2023-11-14 的 231 路，10 个班次。A 为 Lonsdale Quay @ Bay 9（12693），B 为 Harbourside Place（9110）。",
             "- 单日载客行驶距离为 20.4370—24.5285 km。缺少首站精确 shape 距离，故保留区间。",
             "- 一种候选车：Nova LFSe+ 六电池配置，厂商 2025 规格给出最多 59 人、最高 564 kWh、最高 150 kW 插充；不是完整本地认证。",
             "- 仅使用 A、B 两端点及已公布的正反向线路形状；空驶时间不设定，反向载客距离也不被当作空驶实测。",
             "- 各车日初和日末在 A；需要的停车及充电条件是设计要求，不声称该公交站已经具备这些设施。",
             "- 距离优化枚举全部非空班次子集任务链，用整数规划选择恰好覆盖，并用穷举分区交叉核对。",
             "- 不使用旧代码中的道路倍率、速度、备用比例、SOC 打折或暖风常数。", "",
             "## 运载映射", "",
             "F 为一个车型行、若干任务链列的整数矩阵。矩阵及任务链字典见 fleet_matrices.csv 和 pattern_dictionary.csv。",
             "每个班次恰好出现一次。名义容量代理比 T=59/50=1.18，不能随车辆数量相加。",
             "50 是路线历史实用容量代理，59 是厂商最大容量；口径未完成本地统一，因此 1.18 只作名义筛查，不能证明真实峰值或轮椅/载荷要求。", "",
             "## 结果", "",
             "|车辆数|空驶回送次数|最紧回送窗口 min|空驶 km 上界|总 km 上界|规划日耗电 kWh 上界|泛型硬件预算 CAD|",
             "|---:|---:|---:|---:|---:|---:|---:|"]
    for s in solutions:
        window = "无需空驶" if s["common_deadhead_time_bound_min"] is None else f'{s["common_deadhead_time_bound_min"]:.0f}'
        lines.append(f'|{s["vehicles"]}|{s["reposition_legs"]}|{window}|{s["min_empty_distance_upper_km"]:.4f}|{s["daily_km_upper"]:.4f}|{s["central_daily_battery_kwh"]:.4f}|{s["hardware_screening_budget_2023_cad"]:,.0f}|')
    lines += ["", "能耗表采用原始 2020 官方规划的 1.60 kWh/km 全车队年均值（含行驶与暖通），只作工程转移情景；未再次加暖风。",
              "原文 1.37—2.00 是不同路线的全年平均投影范围；1.79 是全车队冬季均值，均不能当成本线路实测或冬季安全上界。",
              "停车期间辅助用电没有可靠数据，未计入本次行驶能耗指标。",
              "预算来自 2023 年公布的泛型 BEB 约 CAD 1.2m/辆，不是对应 Nova 合同价，亦不是十年总成本。", "",
              "1 辆方案在 08:28 到达 B 后，必须于 08:35 前回到 A；7 分钟包含空驶及相关准备，尚未实测确认。",
              "4 辆方案不需要任何空驶；早晨在首个反向班次前连续四次 A→B，证明在禁用空驶的子问题中至少需 4 辆，所构造方案达到该界。",
              "1、2、3 辆的窗口是各自最短空驶距离方案的条件，不是对真实空驶时间的估计。", "",
              "## 电池与连续补能要求", "",
              "用原文另一情景 2.00 kWh/km 核算，各方案单车最大日可用电量需求分别为：",
              ", ".join(f'{s["vehicles"]} 辆方案 {s["required_battery_usable_kwh_transfer_2"]:.4f} kWh' for s in solutions)+"。",
              "这些值是条件性需求；额定 564 kWh 不代替 SOC 可用范围和实测能耗认证。",
              "所选方案均可利用 17:56 至次日 07:20 的 13.4 小时公共回充窗口。若一口充电设备能持续提供净电池侧功率，则顺序充电的充分要求为：",
              ", ".join(f'{s["vehicles"]} 辆方案 {s["one_port_required_received_kw_transfer_2"]:.4f} kW' for s in solutions)+"。",
              "这不是电网侧额定功率，且没有计入插拔时间。实际设备曲线、效率、位置及可用性仍需核验。",
              "整数规划方案已独立重放连续两日的任务与位置；电池补能只证明所需条件，未冒充现实已通过的充电证书。", "",
              "## 十年基准与三个评分", "",
              f'为检验核算，原 119 日秋季日历（{result["source_calendar_operating_days"]} 个运营日、{result["source_calendar_trip_occurrences"]} 次班次）固定重复至既有 2024—2033 评价窗，得到 {result["ten_year_reference"]["operating_days"]} 个运营日。这只是稳态重放实验，不是未来服务、节假日、季节或价格预测。',
              "记 eta 为尚未确认的电网至电池效率；在各方案使用相同效率的简化中，运行排放 E=-g/eta，购置与电量费的局部经济评分 C=-(预算+c/eta)。",
              "g 使用保留证据 E066 的 2023 年平均因子 0.0113 kgCO2e/kWh；本轮未将其更新为未来因子。",
              "c 仅使用 2023 RS1600 能量费 0.0614 CAD/kWh 分项，须在符合该费率的共用充电电表下解释；不含需量、基本费、税、维护、设施及资产剩余价值。", "",
              "|车辆数|g：十年 kgCO2e 系数|c：十年 CAD 电量费系数|购置预算 CAD|",
              "|---:|---:|---:|---:|"]
    for s in solutions:
        lines.append(f'|{s["vehicles"]}|{s["ten_year_grid_ghg_kg_coefficient_divided_by_eta"]:.4f}|{s["ten_year_energy_charge_cad_coefficient_divided_by_eta"]:.4f}|{s["hardware_screening_budget_2023_cad"]:,.0f}|')
    lines += ["", "不能给 eta 代入旧模型的 0.9。当前可画出行驶电量—泛型购车预算的候选筛查前沿；不能声称得到完整环境—十年总成本的现实 Pareto 前沿。", "",
              "## 可复现与验收", "",
              "运行 `python scripts/trial_short_route_231.py`。全部 4 个整数解 gap=0；最小空驶距离与穷举分区一致；每班一次、时序、端点回送、连续日位置与原始日历一致性检查通过。",
              "原始数据及 PDF 哈希、完整假设边界、每次回送时限、每车班次和方案矩阵均保存在同目录。", "",
              "## 来源", "",
              "- 时刻与距离：data/processed/vancouver_gtfs_trip_manifest_classified_2023.csv；原始 calendar.txt/calendar_dates.txt/stops.txt。",
              "- 负荷口径：data/processed/vancouver_load_capacity_proxy_2023.csv，231 路秋季 MF 的两个正值单元都对应 50 人实用容量签名。",
              "- 能耗：materials/sources/raw/translink_2020_fleet_plan.pdf，PDF p73（印刷 C-2）。",
              "- 泛型硬件预算：materials/sources/raw/translink_2023_june_technology_update.pdf，p29。",
              "- 车辆规格：[Nova LFSe+ 2025 规格](https://novabus.com/wp-content/uploads/2017/09/LFSe_Letter-Size_April-2025_EN.pdf)，p2；通过网页阅读核对，本机网络下载受限，因此没有声称本地保留或哈希。",
              "- 电价：data/processed/bchydro_2023_charging_tariffs.json；不把历史费率当作未来承诺。",
              "- 电网因子：materials/research/evidence_audit_v2/data_asset_inventory.csv，E066，保留的历史核验记录。", ""]
    (OUT / "readout.md").write_text("\n".join(lines), encoding="utf-8")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    assignments = pd.read_csv(OUT / "trip_assignments.csv")
    fig, axes = plt.subplots(2, 1, figsize=(11.5, 5.8), constrained_layout=True)
    colors = {A:"#1768ac", B:"#df8f23"}
    for ax, n in zip(axes, (1,4)):
        group = assignments[assignments.fleet_size == n]
        for row in group.itertuples():
            start = int(row.departure[:2]) + int(row.departure[3:]) / 60
            end = int(row.arrival[:2]) + int(row.arrival[3:]) / 60
            ax.barh(row.vehicle, end-start, left=start, height=.42,
                    color=colors[str(row.origin)], edgecolor="white", linewidth=.6)
        ax.set_xlim(7,18.5)
        ax.set_xticks(range(7,19), [f"{v:02}:00" for v in range(7,19)])
        ax.set_yticks(range(1,n+1), [f"Bus {v}" for v in range(1,n+1)])
        ax.set_ylim(.4,n+.7)
        ax.grid(axis="x", alpha=.18)
        ax.set_axisbelow(True)
        s = solutions[n-1]
        ax.set_title(f'{n} bus(es): {s["reposition_legs"]} empty moves required; moving-energy proxy {s["central_daily_battery_kwh"]:.2f} kWh/day', loc="left", fontsize=10)
        if n == 1:
            ax.annotate("07 min return window\n08:28 B -> 08:35 A", xy=(8.525,1), xytext=(9.25,1.32),
                        arrowprops={"arrowstyle":"->", "color":"#b54240"}, fontsize=9, color="#a13332")
    axes[1].set_xlabel("Published clock time (2023-11-14)")
    fig.suptitle("Counterfactual Route 231 reblocking (NOT original vehicle duties)", fontsize=13)
    fig.legend(handles=[Patch(color=colors[A], label="Passenger trip A -> B"),
                        Patch(color=colors[B], label="Passenger trip B -> A")],
               loc="outside lower center", ncol=2, frameon=False)
    fig.savefig(OUT / "duty_comparison.png", dpi=160)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    trips, mf, cal, exc, distances, manifest_path = load()
    columns = make_columns(trips, distances)
    first, last = date(2023, 9, 4), date(2023, 12, 31)
    day_rows = []
    signature = lambda g: sorted(tuple(r) for r in g[["first_stop_id", "last_stop_id",
                    "start_seconds", "end_seconds", "distance_km_lower", "distance_km_upper"]].itertuples(index=False, name=None))
    for d in (first + timedelta(days=i) for i in range((last - first).days + 1)):
        g = mf[mf.service_id.isin(active_ids(d, cal, exc))]
        same = not len(g) or signature(g) == signature(trips)
        if not same:
            raise RuntimeError(f"Different active route timetable on {d}; cannot repeat this prototype silently")
        day_rows.append(dict(date=d.isoformat(), operating=bool(len(g)), trips=len(g)))
    days10 = (date(2034, 1, 1) - date(2024, 1, 1)).days
    active10 = sum(day_rows[i % len(day_rows)]["operating"] for i in range(days10))
    active_source = sum(d["operating"] for d in day_rows)
    tariff = json.loads((ROOT / "data/processed/bchydro_2023_charging_tariffs.json").read_text())
    energy_price = tariff["rates"]["1600"]["energy_cad_per_kwh"]
    # Dated published screening budget, not a Nova contract price.
    hardware_price = 1_200_000.
    gamma = .0113
    energy_cases = {"annual_route_low_planning_transfer": 1.37,
                    "annual_fleet_mean_planning_transfer": 1.60,
                    "winter_fleet_mean_not_worst_case": 1.79,
                    "annual_route_high_planning_transfer": 2.00}
    breakpoints = sorted(set(p["delta_limit_min"] for p in columns if math.isfinite(p["delta_limit_min"])))
    solutions, assignments, plan_rows = [], [], []
    for n in range(1, 5):
        best = solve(columns, trips, n)
        assert best is not None
        optimum = best[1]
        # Find largest common reposition-time bound retaining minimum empty km.
        lo, hi = -1, len(breakpoints)
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            candidate = solve(columns, trips, n, delta=breakpoints[mid])
            if candidate is not None and candidate[1] <= optimum + 1e-7:
                lo = mid
            else:
                hi = mid
        no_empty = solve(columns, trips, n, no_deadhead=True)
        if no_empty is not None:
            chosen, delta = no_empty, 0.
            requirement = None
        else:
            assert lo >= 0
            requirement = breakpoints[lo]
            chosen, delta = solve(columns, trips, n, delta=requirement), requirement
        selected, _, gap, nodes = chosen
        checks = validate(selected, trips, delta, distances)
        km_low = sum(p["loaded_km_lower"] + p["deadhead_km_lower"] for p in selected)
        km_high = sum(p["loaded_km_upper"] + p["deadhead_km_upper"] for p in selected)
        last_return = max(p["last_arrival_min"] + delta * p["final_reposition"] for p in selected)
        next_pullout = min(p["first_departure_min"] - delta * p["initial_reposition"] for p in selected) + 1440
        common_charge_hours = (next_pullout - last_return) / 60
        assert common_charge_hours > 0
        max_bus_km = max(p["loaded_km_upper"] + p["deadhead_km_upper"] for p in selected)
        ten_km_low, ten_km_high = active10 * km_low, active10 * km_high
        central_energy = 1.60 * km_high
        ten_battery = active10 * central_energy
        rec = dict(vehicles=n, min_empty_distance_upper_km=optimum,
                   reposition_legs=sum(len(p["deadhead_legs"]) for p in selected),
                   common_deadhead_time_bound_min=requirement,
                   daily_km_lower=km_low, daily_km_upper=km_high,
                   T_capacity_proxy=59 / 50,
                   capacity_status="NOMINAL_MANUFACTURER_MAX_DIVIDED_BY_HISTORICAL_PRACTICAL_PROXY_NOT_CERTIFIED",
                   required_battery_usable_kwh_central=max_bus_km * 1.60,
                   required_battery_usable_kwh_transfer_2=max_bus_km * 2.00,
                   central_daily_battery_kwh=central_energy,
                   common_overnight_charging_window_hours=common_charge_hours,
                   one_port_required_received_kw_central=central_energy / common_charge_hours,
                   one_port_required_received_kw_transfer_2=2.00 * km_high / common_charge_hours,
                   ten_year_km_lower=ten_km_low, ten_year_km_upper=ten_km_high,
                   ten_year_battery_kwh_central_upper=ten_battery,
                   ten_year_grid_ghg_kg_coefficient_divided_by_eta=gamma * ten_battery,
                   ten_year_energy_charge_cad_coefficient_divided_by_eta=energy_price * ten_battery,
                   hardware_screening_budget_2023_cad=hardware_price * n,
                   score_status="E=-GHG_COEFFICIENT/eta; C=-(HARDWARE+ENERGY_COMPONENT/eta); PARTIAL_ONLY",
                   solver_gap=gap, solver_nodes=nodes, validation=checks)
        for case, e in energy_cases.items():
            rec[case] = dict(battery_kwh_lower=e * km_low, battery_kwh_upper=e * km_high)
        for bus, p in enumerate(selected, 1):
            plan_rows.append(dict(fleet_size=n, vehicle=bus, mask=p["mask"], trip_ids=p["trip_ids"],
                                  deadhead_legs=p["deadhead_legs"],
                                  loaded_km_upper=p["loaded_km_upper"], empty_km_upper=p["deadhead_km_upper"],
                                  received_energy_kwh_central=1.60 * (p["loaded_km_upper"] + p["deadhead_km_upper"])))
            for i in p["indices"]:
                r = trips.iloc[i]
                assignments.append(dict(fleet_size=n, vehicle=bus, trip_id=int(r.trip_id),
                                        origin=r.first_stop_id, destination=r.last_stop_id,
                                        departure=hhmm(r.start_seconds), arrival=hhmm(r.end_seconds),
                                        distance_km_lower=r.distance_km_lower,
                                        distance_km_upper=r.distance_km_upper))
        solutions.append(rec)
    assert next(s for s in solutions if s["vehicles"] == 4)["reposition_legs"] == 0
    assert solve(columns, trips, 3, no_deadhead=True) is None
    # Exhaustive partition enumeration independently verifies minimum-distance
    # results; no MILP logic or constraints are reused for enumeration itself.
    brute = {n: math.inf for n in range(1, 5)}
    def enumerate_partitions(remaining, groups, cost):
        if not remaining:
            if groups in brute:
                brute[groups] = min(brute[groups], cost)
            return
        if groups >= 4:
            return
        first_bit = remaining & -remaining
        for p in columns:
            mask = p["mask"]
            if mask & first_bit and (mask & remaining) == mask:
                enumerate_partitions(remaining ^ mask, groups + 1, cost + p["deadhead_km_upper"])
    enumerate_partitions((1 << len(trips)) - 1, 0, 0.)
    for s in solutions:
        assert abs(brute[s["vehicles"]] - s["min_empty_distance_upper_km"]) < 1e-7
    result = dict(status="COUNTERFACTUAL_REBLOCKING_WITHDRAWN_AS_ORIGINAL_BASELINE",
                  corrected_baseline="../short_route_231_original_blocks/readout.md",
                  route="231 Harbourside/Lonsdale Quay", representative_date=DAY.isoformat(),
                  loaded_trips=len(trips), loaded_km_lower=float(trips.distance_km_lower.sum()),
                  loaded_km_upper=float(trips.distance_km_upper.sum()),
                  concurrent_trip_lower_bound=1,
                  no_reposition_minimum_fleet=4,
                  no_reposition_proof="Four A->B departures before the first B->A departure; all four end at B.",
                  source_calendar_days=len(day_rows), source_calendar_operating_days=active_source,
                  source_calendar_trip_occurrences=sum(r["trips"] for r in day_rows),
                  ten_year_reference=dict(start="2024-01-01", end_exclusive="2034-01-01", days=days10,
                                          repeated_source_cycle_days=len(day_rows), operating_days=active10,
                                          status="STATIONARY_REPLAY_EXPERIMENT_NOT_FORECAST"),
                  candidate=dict(name="Nova LFSe+ 6-battery 2025 published specification",
                                 total_passengers=59, nominal_battery_kwh=564, max_plug_grid_kw=150,
                                 source_url="https://novabus.com/wp-content/uploads/2017/09/LFSe_Letter-Size_April-2025_EN.pdf",
                                 availability="2025 technical reference; not asserted known in 2023"),
                  external_inputs=dict(energy_kwh_per_km=energy_cases, grid_kgco2e_per_kwh=gamma,
                                       energy_component_2023_cad_per_kwh=energy_price,
                                       generic_hardware_screen_2023_cad=hardware_price),
                  evidence=dict(energy="2020 fleet plan, PDF p73: all-in propulsion+HVAC projections, NOT route231 measurements",
                                hardware="2023 June technology package PDF p29: generic BEB screening price, NOT Nova quote",
                                demand="cap50 route/time proxy, NOT per-trip passenger maximum",
                                alignment="Loaded passenger alignment reused for empty reposition; actual time remains unknown"),
                  unknowns=["actual directed deadhead times", "local road/stop approval for selected configuration",
                            "usable battery/SOC policy", "charging efficiency/curve and real charging facility at A",
                            "stationary HVAC energy", "garage travel/parking and interlining",
                            "actual future demand/weather/calendar/prices", "awarded vehicle price, maintenance and facility costs"],
                  hashes={str(p.relative_to(ROOT)): sha(p) for p in [manifest_path,
                          ROOT/'materials/sources/raw/vancouver_gtfs_2023/calendar.txt',
                          ROOT/'materials/sources/raw/vancouver_gtfs_2023/calendar_dates.txt',
                          ROOT/'materials/sources/raw/translink_2020_fleet_plan.pdf',
                          ROOT/'materials/sources/raw/translink_2023_june_technology_update.pdf']},
                  exhaustive_partition_min_empty_km=brute, solutions=solutions, vehicle_plans=plan_rows)
    (OUT / "trial.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    pd.DataFrame(assignments).to_csv(OUT / "trip_assignments.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(day_rows).to_csv(OUT / "source_calendar.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{k:v for k,v in s.items() if not isinstance(v,dict)} for s in solutions]).to_csv(
        OUT / "fleet_comparison.csv", index=False, encoding="utf-8-sig")
    trips.to_csv(OUT / "source_trips.csv", index=False, encoding="utf-8-sig")
    write_readable_outputs(result)
    print(json.dumps(dict(route=result["route"], trips=len(trips),
                          source_operating_days=active_source,
                          counts=[dict(vehicles=s["vehicles"], empty_km=s["min_empty_distance_upper_km"],
                                       tightest_return_minutes=s["common_deadhead_time_bound_min"],
                                       daily_battery_kwh=s["central_daily_battery_kwh"])
                                  for s in solutions],
                          verification="MILP gaps zero; exhaustive partitions and repeated-day replay passed",
                          report=str((OUT / 'readout.md').resolve())), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
