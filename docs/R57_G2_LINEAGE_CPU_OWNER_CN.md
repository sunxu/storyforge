# R57 G2 — Gold195 与三次训练来源交叉审计（安全 CPU 草案）

**状态：** `G2_OFFLINE_TOOL_PREPARED__REAL_SOURCE_REPLAY_PENDING__NO_R50__NO_TRAINING`。

此工具是**私有元数据索引的只读聚合器**，不是训练器或真实源完整性证明。仅检查调用者提供的 SHA256、世界连通分量 token 及源文件哈希**声明的格式与集合关系**，不会读取源小说、Trainer JSONL、模型权重、GitHub/HF 或任何受保护测试。元数据中被声明的 SHA256 **不会自动同原始字节重算**。G2 全量 PASS 仍需独立来源回放、别名图证据和 Owner 签核。

## 1. 仅允许 8 组历史与 Gold 来源

| source.id | 原合同条数 | 身份 |
|---|---:|---|
| `GOLD87` | 87 | Gold 第一批，仅候选 |
| `GOLD108` | 108 | Gold 第二批，仅候选 |
| `V01_TRAIN` | 65 | v0.1 实际 Trainer Train |
| `V01_VALIDATION` | 15 | v0.1 实际 Trainer Val |
| `R46_TRAIN` | 49 | R46 v0.2 实际 Train |
| `R46_VALIDATION` | 15 | R46 v0.2 实际 Val |
| `R54_TRAIN` | 31 | R54 v0.3-A 实际 Train |
| `R54_VALIDATION` | 9 | R54 v0.3-A 实际 Val |

`--mode full` 要求八组齐全、每组行数符合历史回执、Gold195 target SHA256 去重、R54 Train 对 R46 Train/Val 14/9/8 数量一致。这只是**给定索引的重放检查**，不代表源数据自行验证为真。部分资料缺失时使用 `--mode draft`，它永不返回完整 G2 PASS。

## 2. 私有索引格式（仅供演示，所有哈希都是假数据）

下面的示例仅演示结构，不含可用数据，不能作为真实 full 审计：

```json
{
  "schema": "storyforge-r57-training-lineage-private-index-v1",
  "no_protected_evaluation_accessed": true,
  "training_authorized": false,
  "sources": [
    {
      "id": "GOLD87",
      "source_file_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "rows": [{
        "target_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "input_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
        "history_sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
        "world_component_token": "synthetic-component"
      }]
    }
  ]
}
```

- `source_file_sha256`：使用本地 Owner 授权的源文件原始字节计算。Git SHA-1 **不是** SHA256。
- `target_sha256`：最后一条受监督 Assistant 目标回复的原始 UTF-8 精确字节哈希。未经一致规范化的不同版本可能不相等，必须记录哈希算法和字段提取合同。
- `input_sha256`：送到模型的角色/消息完整序列的固定序列化后 SHA256；若与原导出不等价应 HOLD，不得凭空补造。
- `history_sha256`：目标前有效历史的固定序列化后 SHA256。
- `world_component_token`：Owner 私有别名/语义连通分量图关联的**不透明** token；同源不同 UUID 也应连为一个组件。工具只检测 token 是否相等，不能验证 graph 自身的正确性。

真实私有索引必须置于普通 Git 仓库**之外**，不要把完整索引、目标 Hash 列表、故事 ID、世界 token 或原始消息提交至 GitHub。不能从 R50 或受保护评估寻找重复/来源证据；如需证明保护集隔离，交由独立保管人仅提供不含题文的准入证明。未知即 HOLD。

## 3. CPU-only 使用方式

```bash
cd ~/workspace/storyforge-r55-tooling
python3 -m unittest discover -s tests -p 'test_r57_*.py' -v

PRIVATE="$HOME/.local/share/storyforge/r57/private"
python3 scripts/r57_training_lineage_audit.py \
  --private-index "$PRIVATE/R57_G2_SOURCE_INDEX_PRIVATE.json" \
  --mode draft \
  --safe-out "$PRIVATE/R57_G2_SOURCE_COUNTS_DRAFT_01.json"
```

只有 Owner 已独立生成完整八组来源索引时，才可改用 `--mode full`。报告输出为**只计数**，且 `--safe-out` 仅创建新文件，不覆盖旧文件或符号链接目标；再次执行须换新的版本化报告名。

## 4. 已知事实与仍缺的事实

历史回执说明 R54 Train31 的 target exact 重复：对 R46 Train14、对 R46 Val9、未匹配8；与早期 v0.1 target 比对结果见既有归档。**145 个 Train 放置 + 39 个 Val 放置不代表 184 个独立数据项**。Gold87+108=195 个候选，迄今 v0.4 **实际选入 0、准入 0**。不能把 195 个 SHA256 不同目标当成 195 个独立故事输入；更不能把已经曝光的旧题声明为新独立 Held-out。

即使 `--mode full` 的索引计数 PASS，以下全部仍为 PENDING：真实源 SHA 字节回放、精确训练输入版本/时点、近似/语义重复、世界别名图真实性、人工审校/授权证据与最终 Train/Val 新拆分。此工具**不签核**任何 Gold 或 R55 原判，四项 HOLD 继续隔离。
