# StoryForge R57 G2 — 在 Mac 私有环境定位 2 个未使用过的 Gold 故事来源

2026-10-26 Owner 已两次确认 55 对照题全部创建，但仍 **55/55 UNREVIEWED**，即未作任何语义别名判定；这不是失败，只是尚未完成的人工审核阶段。八份冻结输入验签 PASS，29 UUID / 27 历史 SFT UUID / 2 额外 Gold UUID 与 114 没有逐字目标重复、32 连 UUID 都未重复的回放统计一致。

**重要：** 这两个故事均属于 Gold87，分别 14 条与 18 条。这 32 条拥有 `metadata.source_file`、`metadata.source_json_pointer` 和 `metadata.selection_title_zh` 字段。最后一个是候选条目的**选择标签**，不是可靠的小说正式书名。来源 SHA 元数据并不代表源文件的字节内容已另外重新读取校验。

新增 `scripts/r57_g2_private_candidate_source_locator.py`：只读取八份冻结白名单文件并验证 SHA256/Git Blob，生成一份只在 Owner 本机私有目录保存的 **32 条来源定位表**。文件包含两个真实故事 UUID、各记录在 Gold87 的源行序号、原始来源路径引用、JSON pointer、选择标签、原始元数据 SHA。**不会沿着 source_file 路径打开或扫描任意小说文件，也不会输出故事内容。**

## 1. 拉取并核对分支

在既有 StoryForge 仓库根目录执行：

```zsh
git status --short
git fetch origin r57/v03b-data-design
git switch r57/v03b-data-design
git pull --ff-only origin r57/v03b-data-design

PRIVATE="$HOME/.local/share/storyforge/r57/private"
python3 scripts/r57_g2_mac_preflight.py --repo-root "$PWD" --private-root "$PRIVATE"
```

如果 Git 工作区有尚未保存的修改，先处理；不要用 `reset --hard` 或覆盖。八源必须 8/8 `BYTE_PIN_PASS`。

## 2. 零写入地核对两组 Gold 原始来源元数据

```zsh
python3 scripts/r57_g2_private_candidate_source_locator.py \
  --repo-root "$PWD" --private-root "$PRIVATE"
```

预期仅输出脱敏汇总：`candidate_unseen_exact_uuid_worlds=2`、`candidate_gold87_rows=32`、`per_world_gold_row_counts_sorted=[14,18]`、`selection_label_metadata_present_count=32`、`original_story_files_opened=false`、`v04_admitted=0`。

## 3. 生成本机私有的来源定位表

```zsh
umask 077
LOCATOR_NAME="R57_G2_CANDIDATE_SOURCE_LOCATOR_$(date +%Y%m%d_%H%M%S)_PRIVATE.json"
python3 scripts/r57_g2_private_candidate_source_locator.py \
  --repo-root "$PWD" --private-root "$PRIVATE" \
  --private-locator-name "$LOCATOR_NAME"
echo "定位表仅在 Mac 本地：$PRIVATE/$LOCATOR_NAME"
```

程序仅新建（`O_EXCL`），权限 0600；不会覆写既有文件。不要将定位表复制到 GitHub、聊天、PR、公开 Issue，也不要附带原始 UUID、故事正文或逐条 SHA。

## 4. 只在本机查看两个故事的来源定位线索

```zsh
python3 - "$PRIVATE/$LOCATOR_NAME" <<'PY'
import json
import sys
from pathlib import Path

packet = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert packet["schema"] == "storyforge-r57-g2-owner-private-candidate-origin-locator-v1"
for i, world in enumerate(packet["candidate_worlds_PRIVATE"], 1):
    rows = world["source_locations_PRIVATE"]
    print(f"\\n本机候选故事 #{i}：{len(rows)} 条 Gold")
    print("故事 UUID（仅在 Mac 私有终端查看）：", world["source_story_uuid_PRIVATE"])
    print("来源文件引用：", sorted({x["source_file_reference_PRIVATE"] for x in rows}))
    print("前 3 条候选选择标签（不等于小说书名）：")
    for x in rows[:3]:
        print(" -", x["case_selection_label_zh_PRIVATE"])
        print("   源 JSON pointer：", x["source_json_pointer_PRIVATE"])
PY
```

源 `source_file_reference_PRIVATE` 是**元数据中的来源引用，不一定是现存文件绝对路径**，不要用 `source_file` 当作自动下载/打开指令。根据它们在本机安全寻找**原始故事名称、人物表/角色卡、版本与来源审查记录**。在确认目标时点证据后，再处理另一个脚本生成的 55 条 `R57_G2_ALIAS_EDGE_REVIEW_*_PRIVATE.json`，允许 `LINKED_WITH_EVIDENCE`、`DISTINCT_WITH_EVIDENCE` 或 `HOLD_INSUFFICIENT_EVIDENCE`，没有证据就保留 HOLD。

**不要根据 UUID 不同、文件名不同、名称相同/不同自动判断是否同一世界。** 即使 55 个问题都有证据与判定，也仅说明 Owner 覆盖率，不是独立 Reviewer 签核；G2 世界别名图仍待认证、G3 质量/权利/安全仍待审、R55 四项 HOLD 不改变、Dataset v0.4 = 0、R50 不访问、不训练、不晋升。
