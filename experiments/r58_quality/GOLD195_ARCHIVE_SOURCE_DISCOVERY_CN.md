# R58 Gold195 — GitHub source-archives 原始世界卡来源确认

Owner 指定 `evaluations/v0.2/source-archives` 是真实世界卡与原始故事导出来源。

## 已定位的两个 Git LFS 归档

- `06-15/StoryForge_v02_06-15_Full_Evidence_20261013.zip`：65,332,700 字节；SHA256 `b874cd07547092e9c3c967f69fab6b75262ff4f44ba2d368fd575f84e8886afb`，包含十故事的原始导出/审核档案。
- `StoryForge_v02_Pending_Raw_and_Artifact_Backup_20261012.zip`：41,511,118 字节；SHA256 `9c24cc762f91e2ced0766ac50ab178b6992958465f7c71f44eeb75c144bfe2a2`，待检查是否覆盖 Gold87 五个故事。

普通 Git checkout 只会得到 Git LFS 指针（约 133 字节），不是 ZIP。此前仓库记录的远端 LFS 完整性是 Owner 报告，尚不能宣称本轮已实际解包。

## Owner 本地执行（只读、不导出正文）

```bash
git lfs pull --include="evaluations/v0.2/source-archives/*.zip,evaluations/v0.2/source-archives/06-15/*.zip" --exclude=""
python3 experiments/r58_quality/gold195_archive_source_discovery.py --repo-root "$PWD"
```

Python 不会解压到磁盘；只在内存检查嵌套 ZIP，核对两份外层归档的大小与 SHA256，统计内部 JSON/JSONL/ZIP 和按**文件名**识别的卡片候选数量。SAFE 计数不含任何故事正文、文件成员路径和逐案标识。不会访问 R50、执行推理或训练。

请将 SAFE JSON 终端输出反馈到会话。识别完具体原始故事卡结构后，才从指定来源版本提取新的离线训练卡片，并对人物/世界事实、禁令和原 Gold 进行内容冲突审查。导出时快照不是历史当轮卡，但可以作为明确标记的离线设计候选，不要求历史 Provider 字节回放。未核实的来源、版本、质量与世界隔离继续 HOLD。

本工具不会写卡片内容、Quality-v1 通过结果或训练 JSONL。
