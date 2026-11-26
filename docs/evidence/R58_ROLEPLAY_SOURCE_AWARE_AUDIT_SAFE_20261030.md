# R58 — RolePlay 源码 + Supabase 133 个候选目标时点审计（SAFE）

- 2026-10-30；数据库仅 SELECT、无故事/消息内容返回；源码仅 GitHub 读取，**RolePlay fork 无任何修改**。
- 源码仓库：`sunxu/RolePlay`，固定 revision [e9fe29c42434](https://github.com/sunxu/RolePlay/commit/e9fe29c42434caeb0bac5acc91845ab4741ecb2b)（commit 日期 2026-10-29 UTC）。
- 数据库侧原先 24 故事 / 45 会话 / 135 检查点后回复中，133 条有此前故事版本记录。**这次不是训练数据冻结；动态线上数据重新执行选择可能变化。**

## 1. 实际服务端调用链（源码已核对）

1. [`src/app/api/chat/v2/route.ts`](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/app/api/chat/v2/route.ts#L1669-L1734)：作者访问故事走 `getStoryById`，其他读者走 `getPublicStoryById`。之后 `localizeStoryForReader` 可能返回翻译版本，并覆盖所选开场。
2. [`src/lib/db/story-v2-service.ts`](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/lib/db/story-v2-service.ts#L229-L294) 与 [`story-v2-helpers.ts`](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/lib/db/story-v2-helpers.ts#L140-L184)：读者用批准的 `public_v2_data` 投影（特殊 unlisted 路径可使用冻结读者快照），不能用 `user_stories.v2_data` 作者当前稿冒充；若批准投影不完整，阻断，不自动回退。
3. [`src/lib/story-v2/localize-story.ts`](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/lib/story-v2/localize-story.ts#L241-L338)：非简体环境可能使用 `story_content_translations` 的历史翻译缓存；stale-while-translate 路径可以暂时继续使用旧缓存，即便 `source_hash` 不一致，因此仅有当时公开故事卡仍不足以断定模型实际收到的翻译卡字节。
4. [`src/lib/story-v2/prompts/index.ts`](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/lib/story-v2/prompts/index.ts#L220-L233) + [`runtime-rollout.ts`](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/lib/story-v2/prompts/runtime-rollout.ts)：`base + components + tail`，Base 可为 native/legacy；其选择由 session ID、选中模型、部署环境的 rollout 百分比/allowlist 共同决定。当前源码 `STABLE_PROMPT_VERSION=21`，不是所有历史请求的版本证明。
5. [`route.ts`](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/app/api/chat/v2/route.ts#L2480-L2680)：再拼接语言锁、实时记忆、玩家身份、伴侣指令、Anti-repeat、时间跳跃/指令、重生成、事件及实时语音条件段。
6. [`src/lib/story-v2/context-builder.ts`](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/lib/story-v2/context-builder.ts#L225-L350)：注入阶段状态、剧情摘要、事实检索、实体卡、卷/卷组长期记忆、上轮 UI、状态/好感等，有超时/降级分支。**仅靠某个检查点快照不能复原当时检索/超时结果。**
7. [`route.ts`](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/app/api/chat/v2/route.ts#L2250-L2440) + [`v2-message-service.ts`](https://github.com/sunxu/RolePlay/blob/e9fe29c42434caeb0bac5acc91845ab4741ecb2b/src/lib/db/v2-message-service.ts#L589-L618)：普通文字聊天从数据库按 turn_index DESC 读取有限历史（当前默认 `effectivePruneMaxKeep=12`，预取至多 24 条），再依摘要、重生成/续写、异常历史格式清理、重复输出清理；对最后 user 添加语言等提示。不能直接使用“历史所有消息”作为准确模型输入。

## 2. 当前 133 条的来源路径统计

| 路径 | 位置数 | 目前卡片版本时间线 |
|---|---:|---|
| 作者自己游玩，当前作者稿 | **3** | 当前 `updated_at` 不晚于回复时间；仅时间兼容，不是请求字节证明 |
| 非作者读者，批准的公开投影 | **113** | 现存 `public_updated_at` 不晚于回复时间；需要证明当时投影相同且部署版本使用此路径 |
| 非作者读者，较旧公开版本 | **17** | 现存 `public_updated_at` 晚于回复时间；归档作者草稿时间区间存在证据，但**不能替代当时批准公开投影**，需旧公开快照 |
| **总计** | **133** | **精确 Prompt 重放 PASS=0** |

其他数据：133 条当前均有公开投影；106/133 的回复 metadata 含 `v2EventRuntimeBefore/After`；42 条来源 `web` 平台标识，91 条 `mobile`。这不意味着非简体请求数量已知。

## 3. 继承已证实的数据库触发器结论

- `mutation_revision` 递增不仅来自正文修改，也来自状态/元数据变更；129/133 非零。
- 133/133 有此前的 `snapshot_version=2` 检查点；其中最近检查点距目标 ≤5 逻辑轮 80 条，≤20 轮 128 条，超过 50 轮 3 条。
- 账本中 107 条存在 `update_before` 业务快照，已检查到的旧正文不同于现今正文的计数为 0。但账本全生命周期覆盖不充分，**不能证明生成时原文始终不变**。

## 4. 更新后的复原优先顺序

1. **先恢复 3 条作者路径及 113 条读者路径（时间线兼容组）的实际故事版本分支**：必须区分是否经过翻译、实际开场、当时 Prompt 发布版本与 Base rollout 模式；不自动标为 PASS。
2. 另将 **17 条旧公开投影**保留 `HOLD_OLD_PUBLIC_PROJECTION`，不能以 `story_content_versions.v2_data` 假装历史读者卡。
3. 对 133 条继续查目标时点检查点后的消息事件、历史完成状态、摘要/RAG/导演及重复检测；若缺历史部署配置或请求快照，则标为 `RUNTIME_INPUT_UNVERIFIABLE`，不能声称 bytes-level parity。
4. 经独立世界重叠检查后，选少量满足条件的案例私有重放并保留 `source_card_hash`、`assembled_prompt_hash`、`history_hash`、`model_route`、`code_commit`、`runtime_config_hash` 和失败原因。原始请求无持久哈希时只能做证据分级，不能伪造“重建哈希与实际请求哈希相等”。

## 5. HOLD 边界

**源码分析完成的是当前 fork 2026-10-29 版本的逻辑，不等于证明它就是 2026-08-31 至 2026-10-30 每一次候选生成所用的部署 commit。** 旧环境变量、翻译缓存、事件导演、内存/搜索超时、模型路由与 provider 串行化，缺少目标时点完整可复核记录。R50 不访问。没有导出聊天正文、没有 Hugging Face 任务、没有生成 Teacher、没有审核通过或准入 v0.4。

状态：`ROLEPLAY_SOURCE_PATH_CONFIRMED__133_PROVENANCE_PARTIAL__0_EXACT_PROMPT_REPLAY_PASS`。
