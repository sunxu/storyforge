# R58 G1 — GitHub 既有来源证据交叉核验决策（SAFE）

日期：2026-11-01。对象：`sunxu/storyforge` Draft PR #7 / `r58/roleplay-sft-skill-v01`。

## 结论

已经在 GitHub 逐项复核 **R52 七世界限域语义审核、R52/R53 31/9 阶段数据、R55 旧 DEV20、R56 Stage3–7、R57 八源 replay、R50 已知五保护世界**的已归档 SAFE 说明。证据引用及 Git blob SHA 详见 `docs/evidence/R58_G1_HISTORICAL_METADATA_SOURCE_AUTHORITY_CROSSCHECK_SAFE_20261101.json`。

这些报告能够约束各自历史批次的**事实与已检查范围**，不能作为 Mac PRIVATE 发现的 22 个文件的真实身份、原始 UUID-only schema、可读权限或覆盖全集的自动证明。本轮没有读取那 22 个 PRIVATE 路径、29 条逐项名称、文件字节或 R50 密封题；**没有资格独立确认 11 条“索引类”文件名线索中的任何一项。**

## 按来源的证据处理

| 来源 | 可以复用的 SAFE 证据 | 不允许升级为 |
|---|---|---|
| R52 / R53 | Owner 限域接受的七世界 21 对来源审核、七 UUID 及 31/9 暂存拆分 | 适用于 R58 的全局世界独立证书、PRIVATE 索引的身份或正式训练准入 |
| R55 | 旧 20 道开发题来自两历史曝光世界，最终 152 类别记录已做格式/引用校验 | R55 全部开发/仲裁世界全集，或独立语义裁决通过 |
| R56 | Stage7 五条均属于旧 Gold，03/05/11 存在旧开发暴露及原始来源回放记录 | 所有 R56/heldout 世界都已被列举、旧材料可当作 fresh test |
| R57 | Gold87/Gold108 + v0.1/R46/R54 六拆分的已冻结计数/目标锚定 UUID 回放 | 其他全部 Trainer Job、DEV/Reserved 或真实历史输入全集 |
| R50 | 已知五世界局部 UUID 保护检查 | 所有 R50/其他保护来源权威完整名册，或查看 R50 题目权限 |

## 实际下一步，不要求 Owner 猜文件名

保留现有 PRIVATE 29 条 `UNREVIEWED_FILENAME_ONLY` 和 Owner 正式五范围清单 5/5 `MISSING_SOURCE_REFERENCE`；它们只是两种不同阶段，不矛盾。**不要为了填表伪造索引内容、覆盖声明或证据签名。**

现在最有价值的是获得**已存在**的、具有 Owner 授权的 metadata-only 来源登记，并建立以下严格对应：

1. **同一文件身份：**被选的 PRIVATE 元数据文件与哪一份已经记录来源的版本、冻结对象或不可变来源工件具有直接绑定；仅凭同名或 report SHA 不够。
2. **专用 schema 和读取边界：**只包含 story UUID/world identity/来源版本/覆盖元数据，没有受保护题文、原始故事、模型回复或 reviewer 内容；R50 必须单独授权 metadata-only 访问。
3. **完整覆盖声明：**来源 batch、cutoff、排除对象、其他 DEV、reserved/heldout 与所有历史实际 Trainer/teacher 来源都在明确注册表内。没有这种证据时标记 `SOURCE_AUTHORITY_UNAVAILABLE__HOLD`，不得把局部 UUID 零交集写成全集通过。

在出现以上源证据之前，**不再让 Owner 手动挑文件名，不再重复扫目录、生成审阅表或运行自动发现**。八范围 UUID 合约 `r58_g1_scope_reconcile.py` 已存在，缺少合格的输入来源时不运行它，不增设新检查器。

## 操作与门禁

本次仅 GitHub SAFE 文档核对与归档，无新本地执行要求。Owner 在已有 R58 分支按需运行 `git pull --ff-only` 同步即可。无需提供路径、Job ID、私有 SHA、UUID、PRIVATE 审阅表、任何源码正文或 R50 内容。

`G1=HOLD`、`G2=HOLD`、`G3=NOT_STARTED`、Train/Validation/Teacher=0、`expansion_allowed=false`。旧一条 SFT UUID 已排除、余四候选 HOLD、60 个未知 HF Job 全部 PENDING；不启动 HF Job、不合并 PR、不改 Skill 或 Dataset。
