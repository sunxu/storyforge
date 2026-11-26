# R57 G2 — 两个 Gold 候选故事与 27 个历史 SFT 故事名称线索（Owner Mac）

2026-10-26 Owner 已确认两个来源：Gold87 的 `05-战争与血-…jsonl`（18 条）与 `03-我会在雪停之前等待和你重逢。-…jsonl`（14 条）。55 对人工关系审核仍 **UNREVIEWED=55**。这些名称是 Owner 提供的故事来源参考，**不是已经确认的语义世界不相交**。

代码 `scripts/r57_g2_alias_name_hints.py` 建立一个更易读的**本地私有索引**：对八份固定源严格核对 Git Blob SHA1 / R46/R54 Trainer SHA256，并重放 29 世界、27 历史 SFT 世界、两候选世界及 55 个需要人工确认的跨世界比较。只提取源元数据中的 `story_title`、`source_file`、`source_jsonl_member` 三种线索，不读取它们指向的原始文件、不解析故事全文、不访问 R50。对每个世界保留字段来源，不对同名故事做合并，对同一世界出现多个来源名称保持证据提示而不自动赋予标准名称。

来自冻结四份 Git Blob 的初步计数：29 个故事 UUID 中，24 个至少携带一项显式 `story_title`；12 个至少携带 `source_file` 或其他来源提示，且 1 个既没有显式名称也没有这两种文件提示。实际扫描的字段覆盖率仍需 Owner 本机运行结果确认。标签不是独立权威目录，也不自动证明不同/相同故事世界。

## 1. 在 Mac 建立可读私有索引

在 **已经切换到** `r57/v03b-data-design` 的 StoryForge 仓库根目录执行：

```zsh
git status --short
git fetch origin r57/v03b-data-design
git switch r57/v03b-data-design
git pull --ff-only origin r57/v03b-data-design

PRIVATE="$HOME/.local/share/storyforge/r57/private"
umask 077

python3 scripts/r57_g2_mac_preflight.py --repo-root "$PWD" --private-root "$PRIVATE"

NAME_INDEX="R57_G2_WORLD_NAME_HINTS_$(date +%Y%m%d_%H%M%S)_PRIVATE.json"
python3 scripts/r57_g2_alias_name_hints.py \
  --repo-root "$PWD" --private-root "$PRIVATE" \
  --create-private-name "$NAME_INDEX"
```

输出安全计数 JSON；**包含真实 UUID、故事标题/文件名的 JSON 只写到 `$PRIVATE/$NAME_INDEX`，权限 0600，拒绝覆盖/符号链接**。不可上传 GitHub、Issue、PR、公开文件库或直接粘贴聊天。

## 2. 仅在本机打印两候选与 55 对照的名称提示

```zsh
python3 - "$PRIVATE/$NAME_INDEX" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert data["schema"] == "storyforge-r57-g2-private-29-world-title-hints-and-55-pairs-v1"
worlds = data["worlds_PRIVATE"]
for idx, world in enumerate(
    [w for w in worlds if w["candidate_unseen_exact_uuid_gold_rows"]], 1
):
    print(f"候选 {idx}，Gold {world['candidate_unseen_exact_uuid_gold_rows']} 条")
    print("  故事源文件线索:", world["source_file_references_PRIVATE"])
    print("  显式故事标题线索:", world["suggested_story_titles_PRIVATE"])
print("总对照:", len(data["pair_name_hints_PRIVATE"]))
for i, entry in enumerate(data["pair_name_hints_PRIVATE"], 1):
    if i > 55:
        break
    left = entry["candidate_world_PRIVATE"]
    right = entry["comparison_world_PRIVATE"]
    def label(x):
        return (x["story_title_hints_PRIVATE"] or
                x["source_file_hints_PRIVATE"] or
                x["source_jsonl_member_hints_PRIVATE"] or
                ["<无可用名称证据>"])[0]
    print(f"{i:02d}. {label(left)}  <->  {label(right)}")
PY
```

这份打印包含可能属于 PRIVATE 的名字/来源文件信息，**只在 Mac 本机查看**，可与原本的 `R57_G2_ALIAS_EDGE_REVIEW_…_PRIVATE.json` 逐对对应。审查项目由私有的 pair UUID 唯一定位，不要仅凭名称去修改 UUID。若元数据不存在显式书名，名称索引将显示来源文件提示或 `<无可用名称证据>`，须 Owner 继续回溯来源。

## 3. 按证据对 55 项逐对审查

优先核对两个候选故事各自的目标时点人物表/别名、所属世界、连续剧情线索、共同机构/组织、跨故事角色出场、人物称呼复用。**相同人名并不自动是同一人物；故事名不同也不自动世界独立。**

每个决定只能写入原私有 55-pair 审查文件（不是名称提示索引），使用 `LINKED_WITH_EVIDENCE`、`DISTINCT_WITH_EVIDENCE` 或 `HOLD_INSUFFICIENT_EVIDENCE`，并附本机证据引用；不能根据没有查到资料自动写独立。已有 R55 4 条 HOLD 不改变。《战争与血》另需年龄、同意和安全边界逐案证明；另一部故事也须正常质量和角色自主权审查。

**即使 55 项全部完成，仍需 Owner 签核和独立 Reviewer 复核世界/别名图。** 这一步并不准入任何 Dataset v0.4 记录，不创建新 Held-out，不进行 GPU/HF 训练，不访问 R50。
