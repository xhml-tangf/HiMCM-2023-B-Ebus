# 准外发文件（Release Candidates）

此目录只保存准备对外发送的副本；源文件仍在主目录和 `materials/`。

- `charging_ahead_claude_plan.pdf`: 当前 LaTeX 论文的发送副本。
- `charging_ahead_latex_source.zip`: 可独立上传到 Overleaf 的 LaTeX 源码包。
- `github_assets.json`: GitHub Release 大文件附件清单及 SHA-256。

当前状态是**候选稿**：团队控制号仍为空，完整 Claude 原始对话仍未补齐；这两项会在交付说明和 AI 附录中保留，不能把候选稿当作正式参赛提交。

2026-10-25 的整理与本地提交已经完成，但 GitHub 连接和自动审批服务当时均不可用，因此远端尚未收到这次结构调整和大数据附件。连接恢复后应推送 `main`，建立 `data-2026-10-25` Release，并把附件地址写回 `github_assets.json`。

重新生成 PDF 和源码包：

```powershell
$env:HIMCM_TEAM_NUMBER='实际编号'
python scripts/build_claude_latex.py
tectonic paper/claude_plan/latex/main.tex
python scripts/check_claude_latex.py
python scripts/sync_release.py
```

发送前只需使用本目录的 PDF 与源码包，以及同一 GitHub Release 中的完整数据附件。
