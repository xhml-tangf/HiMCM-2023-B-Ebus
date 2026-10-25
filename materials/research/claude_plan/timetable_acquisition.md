# 新增两城时刻表：来源与范围

取得时间：2026-10-22。原始公开压缩包保存在 `materials/sources/raw/comparator_timetables/`，最终分析使用其中的 **2023 年**版本。2026 年当前版本仅作下载回退备份，未替代历史运营输入。

## 芝加哥

- 发布机构：Chicago Transit Authority（CTA）。[官方 GTFS 说明](https://www.transitchicago.com/developers/gtfs/)说明其下载包包含公交及轨道的完整服务时刻，但只保留当前版本。
- 历史快照：2023-05-03，公开 OpenMobilityData 镜像。该日期亦见 Devunuri 等《ChatGPT for GTFS》论文的来源说明。下载地址为 `https://openmobilitydata-data.s3.us-west-1.amazonaws.com/public/feeds/chicago-transit-authority/165/20230503/gtfs.zip`。
- 服务日历：2023-05-03 至 2023-07-31；本次比较周为 2023-06-12 至 2023-06-18。
- 原包 65,120,098 字节；SHA-256：`a930f769f005468b72db71b2eb3a4ae4d749f19e5169539cdb498b98f03bf85a`。ZIP 全部成员 CRC 检查通过。
- 仅纳入公交类型，轨道剔除；所选周没有需要排除的公交频率模板，也没有非正时长记录。逐班时间、站点序列和线路身份来自原包。

## 伦敦

- 发布链：英国交通部 Bus Open Data Service → University of Glasgow Urban Big Data Centre → [Zenodo 公开档案](https://zenodo.org/records/14779119)，DOI `10.20394/dqmgka2s`。
- 内部 `feed_info.txt` 标注转换发布者 ITO World、版本 `20230609_112819`、服务覆盖 2023-04-10 至 2024-02-23。成员 SHA-256：`e542e686a5f6982ad643ba5049fcf191486bcc18c37adf0a4330e44c75f254da`；内层GTFS压缩包的所有成员CRC也已通过。
- 档案 `obds_archive_jun2023.zip` 的公开大小 19,549,809,163 字节；目录通过 HTTP Range 读取，仅提取 `OBDS_archive_Jun2023/OBDS_archive/bod_2023-06-10_21.00.02_gtfs.zip`。不声称核对了整个 19.5GB 包的 MD5；提取成员由 ZIP CRC 检查，独立 SHA-256 在 `london_2023_provenance.json` 中。
- 该快照是全英国文件。用公交类型及**至少一个站点前缀为 490**筛选触及大伦敦的班次。交通部 [NaPTAN 编码表](https://beta-naptan.dft.gov.uk/article/atco-codes-in-use)确认 490 属于 Greater London。
- 这是地理服务范围，可能包括跨界公交，不能等同于 TfL 合同车队名单。TfL 2023 年车队审计继续作为独立的车龄更新模型输入。
- TfL 官网演示压缩包明确不更新，本次没有将其当作当前或 2023 年的运营事实。

## 共同处理与限制

- 使用服务日历及日期例外确定实际运营日，保留大于 24:00 的时刻，不做取模。班次内各停站时刻以压缩 CSV 留存。
- `frequencies.txt` 中 `exact_times=1` 的9个伦敦模板是压缩存储的固定时刻表，按给定的起止时间、间隔及停站偏移恢复了63个班次。只有非精确间隔模板才单独排除、不伪造发车时刻；日程范围及异常数以各城市 `manifest.json` 为准。
- 新增两城的运营里程采用相邻停站大圆距离之和 × 1.35，是明确的路线距离代理，**不是实测道路距离或经证明的上界**。转场矩阵仍为端点大圆距离 × 1.35、30 km/h。
- 固定时刻表覆盖证明的是纳入班次在给定假设下可被服务；不证明原始发布数据没有缺漏，也不证明司机、客流、车场、跨日循环或充电点建设可行。
- 下载脚本只读取公开数据。原始文件不执行；失效链接及回退下载记录保留在原始目录，核心来源另列在清单中。
