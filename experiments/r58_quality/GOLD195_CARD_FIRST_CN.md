# R58 Gold195 — B 路线：可信世界卡优先

Owner 已明确选择：**可信世界卡优先**。不要求任何历史 Provider 请求精确回放；但必须证明作为离线派生输入使用的故事卡**来源、内容版本与哈希**，不能把导出时快照冒充历史生效卡片。本工具只做结构绑定，**不能独立证明卡片事实正确、原著世界完整、安全准入或审核独立性**。

## 先运行无私有卡的 CI / Mac 只读自检

```bash
python3 -m unittest discover -s experiments/r58_quality -p 'test_gold195_card_first.py' -v
python3 experiments/r58_quality/gold195_card_first.py --repo-root "$PWD"
```

全部 195 条保持 `TRUSTED_CARD_NOT_PROVIDED` 或其他 HOLD，不生成训练文件。

## PRIVATE 卡片合同

在仓库外的权限 0700 目录创建权限 0600 的 `cards.json`，结构：

```json
{
  "schema": "r58_gold195_card_binding_private_v1",
  "cards": [
    {
      "story_uuid": "真实来源故事 UUID",
      "card_version": "冻结的离线卡版本/修订标识",
      "card_text": "完整且已核对的世界与人物约束，不要填虚构示例",
      "card_sha256": "card_text 的 UTF-8 SHA256 小写十六进制",
      "source_ref": "可回溯的授权原始卡片来源及版本"
    }
  ]
}
```

来源必须由 Owner/Reviewers 核实，不能使用不明来源或编造的文本。可以选定明确版本作为**新的离线训练设定**，不要求它等于原线上请求，但要检查与当轮 Gold / 历史上下文的事实冲突。已知 06–15 导出卡仅为导出时快照，其中部分晚于目标，不能自动通过。

```bash
python3 experiments/r58_quality/gold195_card_first.py \
  --repo-root "$PWD" \
  --private-card-manifest "$HOME/storyforge-review-private/cards.json" \
  --private-draft-output "$HOME/storyforge-review-private/gold195-card-first-v1.jsonl"
```

所有草稿保留 frozen Gold 的原文与目标哈希，System 使用所选卡片正文。起始为 Assistant 的 132 条保持 HOLD，不自动删去首条；3 条缺少可靠 UUID 的记录保持 HOLD。仅对输入结构安全的行建立私人审核草稿。草稿 **不是训练集**，所有 `training_admitted=false`，`split=null`；还需语义世界隔离、双人六维内容审核、Qwen 16K/last_round CPU 校验及明确 GPU 授权。

不得上传 PRIVATE 卡、草稿、故事正文或逐案 ID 到公开 CI、GitHub、聊天。R50 保持封存。
