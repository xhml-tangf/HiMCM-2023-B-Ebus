"""Preserve original source blocks; do not design route231-only vehicle duties."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from trial_short_route_231 import DAY, active_ids, hhmm, load

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/short_route_231_original_blocks"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    target, _, calendar, exceptions, _, _ = load()
    path = ROOT / "data/processed/vancouver_gtfs_trip_manifest_classified_2023.csv"
    all_trips = pd.read_csv(path, dtype={"service_id": str, "route_short_name": str,
                            "block_id": str, "first_stop_id": str, "last_stop_id": str}, low_memory=False)
    day = all_trips[all_trips.service_id.isin(active_ids(DAY, calendar, exceptions))]
    blocks = sorted(target.block_id.astype(str).unique())
    preserved = day[day.block_id.isin(blocks)].copy()
    preserved = preserved.sort_values(["block_id", "start_seconds", "trip_id"])
    raw = pd.read_csv(ROOT / "materials/sources/raw/vancouver_gtfs_2023/trips.txt", dtype=str).set_index("trip_id")
    for r in preserved.itertuples():
        original = raw.loc[str(r.trip_id)]
        assert original.block_id == r.block_id
        assert original.service_id == r.service_id
        assert original.route_id == str(r.route_id)
    summaries, context, transitions = [], [], []
    for block, g in preserved.groupby("block_id", sort=True):
        g = g.sort_values("start_seconds").reset_index(drop=True)
        summaries.append(dict(block_id=block, published_trips=len(g), route231_trips=int((g.route_short_name == "231").sum()),
                              routes=",".join(sorted(g.route_short_name.unique())),
                              first_departure=hhmm(g.start_seconds.min()), last_arrival=hhmm(g.end_seconds.max()),
                              published_km_lower=float(g.distance_km_lower.sum()),
                              published_km_upper=float(g.distance_km_upper.sum()),
                              scope="PUBLISHED_PASSENGER_TRIPS_ONLY; original nonrevenue movements unobserved"))
        for i in range(1, len(g)):
            left, right = g.iloc[i-1], g.iloc[i]
            gap = float((right.start_seconds - left.end_seconds) / 60)
            assert gap >= 0, (block, int(left.trip_id), int(right.trip_id))
            transitions.append(dict(block_id=block, before_trip=int(left.trip_id), after_trip=int(right.trip_id),
                                    before_route=left.route_short_name, after_route=right.route_short_name,
                                    arrival=hhmm(left.end_seconds), next_departure=hhmm(right.start_seconds),
                                    arrival_stop=left.last_stop_id, next_departure_stop=right.first_stop_id,
                                    gap_min=gap, endpoints_differ=left.last_stop_id != right.first_stop_id,
                                    status="KEEP_ORIGINAL_GAP; travel path/time/energy and usable charging window not inferred"))
        for i in g.index[g.route_short_name == "231"]:
            r = g.iloc[i]
            before = None if i == 0 else g.iloc[i-1]
            after = None if i + 1 == len(g) else g.iloc[i+1]
            context.append(dict(trip_id=int(r.trip_id), block_id=block, departure=hhmm(r.start_seconds),
                                arrival=hhmm(r.end_seconds), origin=r.first_stop_id, destination=r.last_stop_id,
                                previous_route=None if before is None else before.route_short_name,
                                previous_arrival=None if before is None else hhmm(before.end_seconds),
                                next_route=None if after is None else after.route_short_name,
                                next_departure=None if after is None else hhmm(after.start_seconds)))
    context.sort(key=lambda r: r["departure"])
    assert len(context) == 10 and len(blocks) == 8 and len(preserved) == 68
    assert len({r["block_id"] for r in context[:4]}) == 4
    original_return = next(r for r in transitions if r["before_trip"] == 13556760 and r["after_trip"] == 13556759)
    assert original_return["block_id"] == "2065363" and original_return["gap_min"] == 25
    assert raw.loc["13556763"].block_id != raw.loc["13556762"].block_id
    sample = preserved[preserved.block_id == "2065347"].copy()
    result = dict(status="ORIGINAL_PUBLISHED_BLOCKS_PRESERVED_NOT_VEHICLE_ROSTER",
                  date=DAY.isoformat(), route231_trips=len(context), original_source_blocks=len(blocks),
                  all_published_trips_in_these_blocks=len(preserved), other_route_trips=len(preserved)-len(context),
                  original_block_summary=summaries, route231_context=context, original_connections=transitions,
                  original_return_example=original_return,
                  original_7minute_return_required=False,
                  source_hash=hashlib.sha256(path.read_bytes()).hexdigest(),
                  checks=dict(raw_block_and_service_ids_unchanged=True, no_removed_other_route_trips=True,
                              no_departure_or_arrival_changes=True, no_new_repositioning_or_speed=True,
                              no_within_block_time_overlaps=True, morning_four_blocks_distinct=True),
                  fixed_short_sample=dict(block_id="2065347", trips=2,
                                          original_routes=["229", "231"],
                                          published_km_lower=float(sample.distance_km_lower.sum()),
                                          published_km_upper=float(sample.distance_km_upper.sum()),
                                          original_connection_gap_minutes=10,
                                          energy_expression="e * published_km + unknown original connection/pullout/auxiliary energy",
                                          charging_opportunities="Only original dwell at a confirmed compatible charger; gap is not automatically charging time"),
                  modelling_rule="Fix published tasks, times, source blocks and connections; compare compatible propulsion replacements by energy balance and original charging windows.")
    (OUT / "audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    preserved.to_csv(OUT / "original_block_trips.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(summaries).to_csv(OUT / "block_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(context).to_csv(OUT / "route231_context.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(transitions).to_csv(OUT / "original_connections.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(dict(trip_id=int(r.trip_id), **{b:int(r.block_id==b) for b in blocks})
                 for r in preserved.itertuples()).to_csv(OUT / "fixed_assignment_matrix.csv", index=False, encoding="utf-8-sig")
    lines = ["# 231 路：保留原始安排的更正", "",
             "此前 1—4 辆试算是把 231 的十班抽离后，另行构造的专线方案，不是原计划的电动替换基准；7 分钟回送要求随该重排撤回。", "",
             "本次原样保留 2023-11-14 的发车、到达、班次顺序、source block、跨线路衔接和原始间隔，不增加回送、不假设速度、不延长停站。", "",
             "## 原始计划证据", "",
             "GTFS block 表示同一服务日由同一车辆连续执行的一组计划班次。它可以跨线路；不同 block 的实车复用及车库记录仍未给出，不能由 8 个 block 直接推成 8 辆实车。",
             "[GTFS 官方定义](https://gtfs.org/documentation/schedule/reference/#tripstxt)。", "",
             "231 的 10 班属于 8 个 source block。这些 block 合计包含 68 个公布班次，其中另外 58 班属于其他线路。", "",
             "|231 发车|原 block|上一班线路|下一班线路|",
             "|---|---|---|---|"]
    for r in context:
        lines.append(f'|{r["departure"]}|{r["block_id"]}|{r["previous_route"] or "无公布前序"}|{r["next_route"] or "无公布后序"}|')
    lines += ["", "07:20、07:48、08:19、08:35 四班分别属于不同 block。08:19 这班于 08:28 到达后的 7 分钟回送，不是原安排要求。",
              "原安排仍可能需要非载客移车：block 2065363 的 17:13—17:23 与 17:48—17:56 两班均从 Harbourside 到 Lonsdale Quay，25 分钟间隔内必须衔接回另一端。GTFS 没有给出这段的具体路径、运行时间、停车或能耗，不把它设为零。", "",
              "## 固定 block 的替换边界", "",
              "载客能力、道路适配、发车到达时刻和任务链作为已给定基准；承认原计划正常运行这一研究前提。电动替换首先只检查：",
              "1. 原任务链的行驶、接续及必要辅助耗能是否落在可用储能范围内。",
              "2. 原计划停车窗口内，在已确认兼容且可用的补能设施处能否补回所需电量。",
              "原有接续间隔同时可能包含移车和准备，不能整段当作充电时间；缺少记录的接续能量保留未知项。", "",
              "## 最短的完整原任务链样本", "",
              "选择 block 2065347，保留其两个班次：", "",
              "|线路|发车|到达|原端点|",
              "|---|---|---|---|",
              "|229|07:44|08:09|Lynn Valley → Lonsdale Quay|",
              "|231|08:19|08:28|Lonsdale Quay → Harbourside|", "",
              "两班之间原有 10 分钟接续，保持不变。其公布载客距离为 8.0102—8.9631 km。",
              "若 e 是已核验的车型任务能耗率，则任务能量为 (8.0102—8.9631)e，加上原有接续、出入库和未包含的辅助耗能。尚未记录的量不赋值，也不宣称已得完整排放或经济评分。",
              "此样本代表一个公布任务链，不能当作某辆实车的完整日运行；后续实车衔接缺口单独保留。", "",
              "## 校验与输出", "",
              "68 班与原始 trips.txt 的 block、service、route 字段交叉核对通过；原定时刻、顺序和跨线路班次均保留，未发现链内时刻重叠。",
              "original_block_trips.csv 保留全部班次；route231_context.csv 列出每班前后衔接；fixed_assignment_matrix.csv 为固定班次到原 block 的指派矩阵；audit.json 保存可复现检查。", ""]
    (OUT / "readout.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(dict(blocks=len(blocks), published_trips=len(preserved), route231_trips=len(context),
                          checks=result["checks"], sample=result["fixed_short_sample"],
                          report=str((OUT / 'readout.md').resolve())), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
