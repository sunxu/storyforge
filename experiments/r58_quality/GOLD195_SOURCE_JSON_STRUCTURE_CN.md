# R58 原始归档 JSON 结构定位（仅 SAFE 汇总）

Owner 已确认 Gold195 世界卡来源位于 GitHub `evaluations/v0.2/source-archives`。两份已验证的 LFS ZIP 分别覆盖 06–15 和早期备份。此前按**文件名**扫描没有发现单独的卡片 JSON，不能因此认定卡片不存在：原始故事 JSON 可能将设定嵌在 `story.v2_data` 等字段。

```bash
python3 -m unittest discover -s experiments/r58_quality -p 'test_gold195_source_json_structure.py' -v
python3 experiments/r58_quality/gold195_source_json_structure.py --repo-root "$PWD"
```

脚本在检查两份固定 LFS ZIP 大小和 SHA256 后，有限深度读取 JSON 文件或每个 JSONL 的首条记录，仅输出固定的技术键名称计数和数据类型，禁止输出故事正文、名字、UUID、文件名、路径及来源文本。内层 ZIP 只在内存处理，不会提取到磁盘。报告只能决定后续的卡片提取适配器，不批准故事卡的语义正确性。

导出时卡片只能作为明确版本化的离线训练设定候选；须独立核对内容与 Gold 当轮的角色关系、禁令、时间线和安全边界。无需原始 Provider 请求精确回放；不修改冻结 Gold，不接触 R50，不启动 HF/GPU。
