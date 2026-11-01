# StoryForge Quality-v1 — 高质量中文互动剧情 SFT 候选审核

日期：2026-11-01。适用于 R58 质量优先主线。**不再以原始生产请求精确回放作为训练研发前提。**

## 目标与来源

优先使用既有冻结 Gold195（87+108），不重选、重写原始来源。优先复用已完成且能逐案绑定的真实质量审查。其次审核 R58 原五世界中尚未排除的四个世界，整个 Pilot 回复目标总量不超过 20。当前新工具只接受 original_gold，禁止把 Teacher 输出标成原始 Gold。

主要训练目标：自然中文叙事、人物与规则一致、NPC 主动推进但不代写玩家行动、长期约束遵守和跨轮连续性。训练效果须通过独立世界盲审检验，而非仅凭训练 loss。

## 工具的权限和结果

实现：experiments/r58_quality/quality_v1.py。19 个纯合成测试：experiments/r58_quality/test_quality_v1.py。

本地读取经过 Owner 实际审核的 PRIVATE JSONL；校验 System/历史 User-Assistant 交替（允许 User-first 或 Assistant-first）/当前 User、独立目标 Assistant 文本、消息和目标 SHA256、来源及保护隔离声明、两份盲审评分、严重越权和硬规则问题、批次重复与世界跨 Train/Validation。stdout 仅有 SAFE 汇总计数和固定错误类别。

**PASS 仅表示结构和审查声明自洽，不代表脚本本身懂中文文学质量或独立证明保护集全覆盖。** 工具不访问 R50 测试正文、线上数据库、VPS、HF 或 Provider；不导出正文、不创建训练 JSONL、不启动推理或训练，永远输出 quality_dataset_admitted=0、training_authorized=false。

## 每条 PRIVATE 记录字段合同

- schema 固定为 storyforge-quality-v1-private-candidate-v1；case_id 私有、corpus=gold195 或 r58_round1、source_kind=original_gold、world_component_id、split=train/validation。
- source_version_sha256、world_graph_sha256、input_messages_sha256、assistant_target_sha256 均为小写 64 位十六进制。前两个是来源身份声明，不会被本工具自动回读证实。
- messages：首条 role=system；此后 User/Assistant 严格交替，允许首条历史为 User 或 Assistant（Assistant-first 已由 R58 真正 ms-swift 132/132 验证）；末条 role=user；每条只有 role/content 两键。target_text 是独立的下一条 Assistant 监督目标，不重复追加到 messages。
- evidence 中必须为 true：rights_attested、source_version_verified、context_is_coherent、context_no_future_leakage_reviewed、privacy_checked、world_component_reviewed、known_protected_metadata_checked、other_known_reserved_metadata_checked、final_heldout_metadata_checked、reviewers_blinded_and_independent_attested、owner_quality_approved。
- evidence 中必须为 false：known_protected_overlap、final_heldout_overlap、protected_test_body_accessed。未知时不能填 false：应留空并保持 HOLD。不得打开 R50 密封题目正文。
- reviews 恰好两个，含不同 reviewer_key、private_evidence_ref、decision、severe_flags、scores。三项严重标记为 serious_player_agency、hard_fact_or_ban、safety_exclusion；明确严重问题或 REJECT → REJECT，意见冲突 → HOLD。
- scores 六维 1–5 整数门槛：chinese_prose≥4、character_consistency≥4、npc_initiative≥3、player_agency≥4、rule_fidelity≥4、narrative_continuity≥4。两位 Reviewer 均须达到；不得靠总分抵消硬约束。

**禁止为通过脚本而编造证据布尔值、Reviewer 身份、质量分数或证据引用。** R55 的模型比较分数不自动等于本合同的逐案 Gold 质量结论；若复用历史审查，需先验证对应的是同一输入与目标文本。

## 立即可运行的纯合成验证

在 R58 工作区执行以下两条命令：

    git pull --ff-only
    python3 -m unittest discover -s experiments/r58_quality -p 'test_quality_v1.py' -v

当前还没有 Owner 的这 19 项真实执行回执；不得将它们标记为已通过。

真实 PRIVATE 候选审核文件准备完成、并由 Owner 同意本地读取后，才执行：

    python3 experiments/r58_quality/quality_v1.py --private-reviewed-jsonl /ABSOLUTE/OWNER-PRIVATE/reviewed_candidates.jsonl

PRIVATE 文件必须是 0600 普通文件、无符号链接；本机内存将解析其中的故事和回复内容，但不把内容、逐案 ID、原始哈希或 PRIVATE 路径输出。**现在不要求生成或运行私有输入，也不要造一份全 PASS 的示例冒充真实审核。**

## 从候选转为训练仍需的工作

Gold195/四世界逐条真实性和可用性核验；语义世界组件隔离与已知 Protected/Heldout 保护；实际两份质量审核证据；Qwen tokenizer 实际长度；ms-swift Collator 的 last_round 监督掩码；冻结数据集；Owner 对一次具体 GPU 训练和预算单独授权。全部通过才考虑训练。历史 G1/G2 HOLD 原样留档，但历史生产字节精确回放不再阻塞新质量研发。
