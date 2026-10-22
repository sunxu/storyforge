# StoryForge R56 Stage 6 — 从非 R50 原始素材自动发现故事世界

状态：SOURCE_METADATA_ONLY__ALL_WORLDS_HOLD__NO_TEST_ADMISSION。

四份私有审核密文已在 GitHub main 归档。接下来优先清点新故事，不重复 Gold195 机械筛选、不使用 R50、不运行 GPU。现有 03/05 源自 Gold87，故事 11 (KSG) 在旧 R01/R04 已用于开发策展，故事 07 与 04 有共享设定隔离 HOLD。它们都不能因为 UUID 不同就成为新鲜、独立、未曝光的 Held-out 世界。

## 1. 在 Mac 上扫描原始 JSON/JSONL 故事

首先明确指定一个单独整理的非 R50 原始文件目录（包括不得含有 16–20 故事、R50 密封素材或以别名保存的 R50 文件），例如自行导出的新故事目录。不要对整个 home 目录递归扫描。

运行命令：

    cd ~/workspace/storyforge
    git pull --ff-only
    python3 -m unittest discover -s tools/r56/tests -p 'test_*.py' -v
    python3 tools/r56/scripts/r56_inventory_originals.py \
      --root '/PATH/TO/OWNER-NON-R50-ORIGINAL-JSONL-DIR' \
      --out-dir "$HOME/.local/share/storyforge/r56/stage6-original-inventory-v1"

脚本只读。跳过不完整故事 JSON、符号链接、大于150MB的文件、常见 R50/16–20 路径以及导出 rank 16–20。默认扫描深度4层，最多5000个 JSON/JSONL；不直接读取 ZIP，压缩包必须由 Owner 在确保不包含 R50 之后解压至独立私有目录。名称过滤不能代替用户正确隔离目录，也不能证明文件未被历史曝光。

输出：
- private/R56_AUTO_ORIGINAL_WORLD_INVENTORY_PRIVATE.jsonl：世界 UUID、原稿全文件 SHA256、原稿路径、消息数、来源版本冲突。只留本机或加密归档，不明文进 Git。
- safe/R56_AUTO_ORIGINAL_WORLD_COUNTS_ONLY.json：无原文、候选ID及来源路径，可用于安全计数归档。

## 2. 与冻结 Gold195 / R46 / R54 做 UUID 预筛

    OWNER="$HOME/.local/share/storyforge/r56/owner-full-replay-20261022-v1"
    INV="$HOME/.local/share/storyforge/r56/stage6-original-inventory-v1"
    python3 tools/r56/scripts/r56_discover_new_worlds.py \
      --repo "$PWD" \
      --historical "$OWNER/toolkit/private/R56_HISTORICAL_EXPOSURE_WORLD_IDS_PRIVATE.json" \
      --inventory "$INV/private/R56_AUTO_ORIGINAL_WORLD_INVENTORY_PRIVATE.jsonl" \
      --out-dir "$HOME/.local/share/storyforge/r56/stage6-world-uuid-triage-v1"

上传以上两份 count-only JSON，以及私有筛查 CSV（不得明文提交 Git）。由项目助手继续核查候选与历史完整评估材料、源时点角色卡、共享人物世界与旧提示的语义曝光。

## 3. 已验证事实与未满足门禁

本轮工具10项合成测试 PASS，既有 R56 工具44项测试此前 PASS。直接用用户已经提供的故事 03/05 完整原稿做单独试跑，均识别成功，2个独立 UUID、0个同 UUID 多版本冲突。**这两个均为旧 Gold 世界，不是新增世界**。本地试跑未读取 R50。

后续任何候选 UUID 不重叠都只获得 POTENTIAL_NON_GOLD_WORLD__SEMANTIC_EXPOSURE_HOLD。重新组建4世界正式题目时必须遵守6题/世界和真正的独立来源准入；旧 Gold 目标或已曝光候选不得包装成 Fresh Held-out。正式测试准入0、R50密封、没有新训练/GPU、R54 NOT_PROMOTED。
