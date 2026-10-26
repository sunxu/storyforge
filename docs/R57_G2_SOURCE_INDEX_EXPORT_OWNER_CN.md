# StoryForge R57 G2 — Owner 本机离线来源索引导出（无训练）

**状态：** `R57_G2_PINNED_EXPORTER_PREPARED__ACTUAL_EIGHT_SOURCE_REPLAY_PENDING__NO_R50`

本工具 `scripts/r57_source_index_export.py` 为 G2 历史来源审核准备**私有中间索引**。它不是数据自动准入、来源真实性独立认证或模型模板验收。运行不需要网络、HF、GPU、R50、Reviewer 私有判定或重新下载模型。

## 固定白名单（不扫描目录）

仓库根目录内原始 Git 文件（可用历史 Git Blob SHA-1 做额外原始字节检查）：

| source ID | 固定相对路径 | 期望行数 |
|---|---|---:|
| GOLD87 | `evaluations/v0.2/gold-quality-87/gold_quality_accepted_87.jsonl` | 87 |
| GOLD108 | `evaluations/v0.2/gold-quality-108/gold_quality_accepted_108.jsonl` | 108 |
| V01_TRAIN | `data/compiled/v0.3/train.jsonl` | 65 |
| V01_VALIDATION | `data/compiled/v0.3/validation.jsonl` | 15 |

Owner 受控私有目录内的历史**实际 Trainer JSONL**（不能使用编造或另版本同名替代）：

| source ID | 相对于 `PRIVATE` 的路径 | 期望行数 |
|---|---|---:|
| R46_TRAIN | `r46/train.jsonl` | 49 |
| R46_VALIDATION | `r46/validation.jsonl` | 15 |
| R54_TRAIN | `r54/train.jsonl` | 31 |
| R54_VALIDATION | `r54/validation.jsonl` | 9 |

**历史字节强制门禁：** R46/R54 四份私有 compiled Trainer 文件另有仓库冻结回执 SHA256，脚本会**同时**检查私有 plan 的 SHA 与下列历史常量；plan 无法覆盖这些已归档 pin：

| 文件 | 已归档原始字节 SHA256 |
|---|---|
| R46_TRAIN（compiled） | `a028bf9fb28b12b4a3fa352d6a60281bd9e1ef5773ebfdfecc7ac80eb2cba517` |
| R46_VALIDATION（compiled） | `cc8d647471423f4969149f8cabdea980aad15d8bd4424d9dd98da3313c639f3c` |
| R54_TRAIN（R53 formal compiled） | `d0425c54b534307047457d05e6890b50076ad2d23ce9ab3d52f94d1a3db585a7` |
| R54_VALIDATION（R53 formal compiled） | `b5ea4075419ce02a1340f6ece875068746918ce1d4c6d72ee2f799b3fe58754d` |

来源：`docs/evidence/V02_R46_GPU_TRAINING_ACCEPTANCE_20261014.json` 的 `compiled_*_sha256` 与 `docs/evidence/V03_R53_FORMAL_PRIVATE_31_9_RELEASE_OWNER_RECEIPT_ACCEPTED_20261021.md` 的 formal output hash。**不要把 R46 frozen source 49/15 哈希 `e744...`/`5ebb...` 当成 compiled Trainer 哈希。** R54 的历史归档来自 Owner 形式验收，并非新作业的远端独立验证；保持证据层级。

**输入准备规则：**只有经 Owner 来源认证的既存历史源文件才可放入 `PRIVATE`；若缺失某组，保持 `--mode draft`，绝不可造一个“看似正确”的 49/15 或 31/9 文件。不能从封存评估、模型输出、R55 审稿件或未知 HF 作业推断目标内容。真实故事世界内容与 SHA 列表仅留本机；不提交普通 Git、PR 或聊天。

## 私有 plan 与别名映射

两份小型 JSON 文件必须放在 `PRIVATE` 目录中，且源文件路径不允许符号链接。下面示例是**合成说明**，实际每个 SHA 都必须由 Owner 对**原始字节**独立计算：

`R57_G2_ALIAS_GRAPH_PRIVATE.json`:

```json
{
  "schema": "storyforge-r57-g2-world-alias-private-v1",
  "story_to_component": {
    "synthetic-story-id": "C_synthetic_component_0001"
  }
}
```

此图必须覆盖每个实际 source row 的世界 ID、已知跨故事角色与别名连通分量。值是私有不透明 token，不能只凭 UUID 不同就认定不同世界；工具检查**映射存在与 token 相等**，但不能代替人工验证语义连通图。

`R57_G2_SOURCE_PINS_PRIVATE.json`:

```json
{
  "schema": "storyforge-r57-g2-source-pin-plan-private-v1",
  "no_protected_evaluation_accessed": true,
  "training_authorized": false,
  "alias_map_sha256": "<真实别名映射文件 SHA256，64 个小写十六进制字符>",
  "source_pins": {
    "R46_TRAIN": {
      "sha256": "<R46 真实 train.jsonl 原始字节 SHA256>",
      "metadata_world_field": "source_story_id"
    }
  }
}
```

8 组源均使用相同的 `source_pins` 格式；仅声明实际能校验的组。`metadata_world_field` 除 Gold108 的 `gold108_strict_mixed` 外，只允许 `story_id` 或 `source_story_id`，必须按真实原始行结构与来源日志确认后显式选择，不得自动猜测。两个 SHA 均要用**文件级原始字节**计算，而不是 Git Blob SHA-1 或目标段哈希。

**Gold108 字段差异已由冻结 Git Blob 直接确认：** 105 行使用 `story_id` + `target_sha256`，3 行使用 `source_story_id` + `target_content_sha256`；3 行备用世界值均落在其余 105 行已知 UUID 集合中。对 `GOLD108` **必须**使用 `"metadata_world_field": "gold108_strict_mixed"`，而非统一 `story_id`。程序要求每一行恰好提供一种来源世界字段和一种目标摘要字段，冲突或丢失直接 HOLD；此混合选项不接受其他数据源。其他来源继续显式选择经确认的 `story_id` 或 `source_story_id`。见 `docs/evidence/R57_G2_FOUR_GIT_BLOBS_SOURCE_CROSSCHECK_SAFE_20261026.md`。


## 执行（Mac，标准库 CPU，不联网）

```bash
# 只读核对文件存在，不自动下载/复制历史资料
cd ~/workspace/storyforge-r55-tooling
git status -sb

PRIVATE="$HOME/.local/share/storyforge/r57/private"
# 应先由 Owner 在此私有目录独立准备 source pins / alias map / 已认证原始文件
shasum -a 256 "$PRIVATE/R57_G2_ALIAS_GRAPH_PRIVATE.json"

python3 -m unittest discover -s tests -p 'test_r57_*.py' -v
python3 scripts/r57_source_index_export.py \
  --repo-root "$PWD" \
  --private-root "$PRIVATE" \
  --index-name R57_G2_SOURCE_INDEX_PRIVATE_01.json

python3 scripts/r57_training_lineage_audit.py \
  --private-index "$PRIVATE/R57_G2_SOURCE_INDEX_PRIVATE_01.json" \
  --mode draft \
  --safe-out "$PRIVATE/R57_G2_SOURCE_COUNTS_DRAFT_01.json"
```

**输入必须是普通文件**：来源路径为代码白名单固定值；不遍历目录、不跟随符号链接；单文件超过 128 MiB 或行超 3 MiB 会 HOLD；plan/alias 映射上限 8 MiB。索引只能**新建**（权限 0600），不能覆盖既有文件。输出不含故事正文，但含逐条哈希与世界 token，因此仍为**严格私有文件**。唯一可归档 Git 的是后续审核器产生、已人工检查的安全汇总计数，不含私有路径、世界映射和逐条 SHA。

仅当八组来源全部准备完、每组 SHA/行数校验通过，才可在审核器中选择 `--mode full`。该 `full` 标志只表示**给定私有索引的精确集合重放**，并非“G2 全部通过”。

## 提取口径与尚未解决的问题

- `target_sha256`：最后一条 Assistant 回复的原始 UTF-8 正文 SHA256；若原始 metadata 已带相应 target hash，强制核对。
- `input_sha256`：为兼容已归档 G2 计数 Schema，指按 `role`+`content` 做固定 JSON 序列化后的**完整消息（包括末轮目标）指纹**；**不是纯推理 Prompt，也不是 ms-swift 原始 Trainer 字节 SHA**。
- `history_sha256`：以上规范化格式的前置历史（不含最后 Assistant 目标）。历史被截断、System/角色卡改变时应视为不同；`loss` 标签未纳入此投影。
- 对 R46/R54 的实际 ms-swift input 级完整相同与否，另需对精确 frozen Trainer JSONL 原始字节、loss mask 与模板参数作逐项比对；本工具只回答前述**角色/文本内容投影**的重合。
- 如果来源投影、历史字段、世界组件无法取到确定结论，返回 HOLD，不能用缺项 `null` 或合成值冒充。
- 旧 R55 全部 152 类别和 4 项 HOLD 一律保持不变；本工具不读取、不修改这些文件；R50 保持完全不可访问。

**后续证据清单：**需单独归档（安全摘要）八组原始 bytes 校验的成功/失败状态、Owner 声明的别名图版本、世界组件 split 冲突、具体 Trainer 模板和历史重复审查的边界；`V04_ADMISSION_PASS` 仍为未达到，不能自动生成训练集。
