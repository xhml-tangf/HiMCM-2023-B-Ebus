# 其他资料（Materials）

本文件夹保存**证据、来源、研究笔记和整理性记录**。模型运行所需的代码和论文不放在这里。

- `sources/raw/`: 保留的公开原始资料、GTFS 压缩包和下载清单；大文件由 GitHub Release 附件提供。
- `research/claude_plan/`: 用户提供的 Claude 规划原文、参考程序、引用审计、时间表获取说明和 AI 披露清单。
- `research/evidence_audit_v2/`: 证据登记、数据缺口、历史版本回收和研究问题支持矩阵。
- `research/himcm_exemplars/`: 仅用于版式参考的公开获奖论文调研。
- `results_notes/`: 已有结果的中文整理说明。
- `archive/`, `artifacts/`: 历史预览和旧版构建材料。

## 大文件恢复

`materials/sources/raw/comparator_timetables/` 和部分 GTFS 原始文件不进入普通 Git 仓库。
在 GitHub Release 中下载 `himcm-complete-data-2026-10-25.tar.gz`，执行：

```powershell
python scripts/restore_github_assets.py --archive himcm-complete-data-2026-10-25.tar.gz
```

恢复脚本只写入本项目内的 `materials/sources/raw/`、`data/processed/` 和 `results/claude_plan/`。
下载地址和 SHA-256 会记录在 `release/github_assets.json`。

证据与模型结论的边界说明仍以 `paper/claude_plan/latex/main.pdf` 和 `materials/research/` 中的原始记录为准。
