# R55 Gold5 审核工具源码归档与恢复（2026-10-26）

## 归档范围

- 备份中包含原始**30 个**源码文件：8 个 scripts + 8 个 tests + 11 个 docs，以及 3 个 subtype 工具源码／测试／说明。
- 其中原版 `scripts/v03_r55_gold5_build.py`、配套测试和初版指南已在 `main`，Git 补丁只添加其余 **27 个缺失文件**和本说明、来源清单。
- 从此前在对话中交付的原始 ZIP **按原始字节恢复**，原始 ZIP 的脚本/测试/文档无修改；子类型工具保留单独目录，避免改变原有导入路径。
- 代码、合成测试和使用说明可以归档；**私有故事、原始回复、Reviewer 裁决、身份映射、HF 密钥、训练权重和 R50 均不在此包**。

## 测试

完整源树的合成测试（Python 3.13）：

`python3 -m unittest discover -s tests -p 'test_v03_r55_gold5*.py' -v` → **176/176 PASS**

`(cd tools/r55-gold5-subtypes && python3 -m unittest discover -s . -p 'test_*.py' -v)` → **15/15 PASS**

共 **191/191 PASS**。这只是合成回归，不是重新运行真实私有裁决，也不证明 AI 语义裁决正确。

## Git 补丁：恢复缺失源码

1. 保存 `StoryForge_R55_GOLD5_TOOLING_GIT_ARCHIVE_20261026.patch` 到 `~/Downloads/`。
2. 在 **已安装的** `~/workspace/storyforge`（应含已归档的初版 build.py、test、docs）中运行：

```bash
cd ~/workspace/storyforge
git status --short
git apply --check ~/Downloads/StoryForge_R55_GOLD5_TOOLING_GIT_ARCHIVE_20261026.patch
git apply --index ~/Downloads/StoryForge_R55_GOLD5_TOOLING_GIT_ARCHIVE_20261026.patch
python3 -m unittest discover -s tests -p 'test_v03_r55_gold5*.py' -q
(cd tools/r55-gold5-subtypes && python3 -m unittest discover -s . -p 'test_*.py' -q)
git diff --cached --name-only  # 只应看到补丁定义的 29 个路径
git diff --cached --stat
git commit -m 'audit(r55): archive blinded review, arbitration and evidence-resolution tooling'
git push origin main
```

审查 `git diff --cached --stat` 的路径，确认只有源码、合成测试、协议与安全清单。若分支受保护，则创建新分支并通过 PR 合并；不要 `git add -A`。如补丁 `--check` 失败，**停止**，先核对本地文件与已修改内容，不要强制覆盖。

## 完整备份与校验

完整备份 ZIP 中包含这 30 个原始源码／测试／说明文件、此指南、manifest、独立 Git 补丁以及原先来源 ZIP 的 SHA256 清单。使用 `shasum -a 256` 验证整个 ZIP，解压后用 Python 或 `shasum -a 256` 检查每个源文件的记录值。

机器可读的 `docs/evidence/R55_GOLD5_ARCHIVED_SOURCE_MANIFEST_20261026.json` 内每条 `files` 记录均包含逐文件 SHA256、字节数和原始来源 ZIP 名称。

## 审计边界

GitHub 远端是否已实际合并本补丁须以 Git commit 和树路径为准；只有本地生成 ZIP/补丁并不等于远端源码已归档。本次归档**没有**重新计算源数据 SHA，也不修改首审/二审/三审/终裁。152 格式验证完成，但语义签核仍待人工确认、4 项 HOLD 仍然未解决，R54 v0.3-A NO-GO，R50 封存。
