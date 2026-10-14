# StoryForge v0.2 — 新会话交接文档（R48 完成）

> **交接时间：2026-10-14｜项目：`sunxu/storyforge`｜主分支：`main`（私有仓库）。**
> **任务定位：R46 GPU 训练 + R47 三模型回归盲审 + R48 四回复原始 Gold 对照已经完成；v0.2 模型未晋升。**
> **验证基准：main 在本交接准备前的 commit `1ff4e509aacdafc0092c66a2eae96d7112fd0d73`。**

## 0. 给新会话的最短指令

阅读本交接文档及 `docs/evidence/V02_R48_ARCHIVE_MANIFEST_20261014.json`，从已完成的 R48 结果继续 StoryForge v0.2。不要重复 R46 GPU 训练、R47/R48 旧题推理或已经完成的独立盲审；不修改原始 Gold、R47/R48 CSV、私有答案映射和历史结果。优先检查 R48 归档、制定全新独立 Held-out 接收与封存规范，之后做 Base/v0.1/v0.2 的可复现三路测试和盲审晋升门槛。GitHub 审计只提交小型报告与脚本，尽量不用 LFS，不上传权重、私有密钥或未授权公开的故事全文。**GPU/收费任务必须单独征得授权。**

## 1. 已完成里程碑

| 阶段 | 数据与操作 | 结果 / 限制 |
|---|---|---|
| 原始 Gold 筛选 | v0.2 两批独立筛选得到 **195** 条 Gold（87+108）；记录在 `evaluations/v0.2/gold-quality-87/` 和 `gold-quality-108/` | 原始 Gold 不改写；它们不是全部正式训练准入 |
| R27–R45 | 通用**无角色卡** System Prompt 实验方案，历史与玩家自主权保守质量审查；R45 冻结 49 Train / 15 Val | 原 82 候选中 18 HOLD；**正式 Train/Val/Test 批准仍为 0**，只批准有限 GPU 实验 |
| R43 CPU | HF ms-swift 实际 Collator/最后助手监督检查（R45 64 条继承通过的逐条证据） | 技术标注检查 PASS；不得扩展成全剧情授权 |
| R46 GPU 训练 | Qwen/Qwen3.8-27B、A100 80GB、4-bit NF4 BF16、QLoRA rank64，1 epoch，49/15 | **工程 PASS**，Checkpoint-7、Adapter 重载 PASS；**NOT_PROMOTED** |
| R47 回归盲审 | 旧 v0.1 Test **20 题**，Base/v0.1/v0.2 三路、共 60 回复，三份独立评分表 | 多数胜出 **v0.2 11/20、Base 5/20、v0.1 4/20**，仅旧题回归 |
| R48 原始 Gold 对照 | 同 20 题，增加原始 Assistant Gold，一共 80 回复（Gold+Base+v0.1+v0.2），3 位评审，1440 评分格 | 多数胜出 **Gold 8/20、v0.2 7/20、v0.1 3/20、Base 2/20**；旧题四方比较，不晋升 |
| R48 归档 | 评分 CSV、源数据匹配、冻结、四方结果、Markdown/JSON、SHA256 manifest | **R48 专用 CI SUCCESS**，见下文；通用 CI Ruff 仍 FAIL（35 项待分流） |

## 2. 核心数字与解释

### R46：一次已完成的收费 GPU 训练，不要再启动

- Hugging Face：`adradar`，私有 Bucket `hf://buckets/adradar/storyforge-training`。
- Job `6acf29e4c66288145223871b`，RUN_KEY `r46-20261014T070529Z-248172`。
- 基础模型 `Qwen/Qwen3.8-27B`；基座 revision `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`。
- 7 个 optimizer steps；最终 Train loss `1.9259772300720215`，Validation loss `1.7483125925064087`；Runner 耗时 `1260.88` 秒（不是账单总时长）。
- Adapter 目录：`hf://buckets/adradar/storyforge-training/experiments/v02-r46/r46-20261014T070529Z-248172/output/v0-20261014-070817/checkpoint-7/`。
- `adapter_model.safetensors` SHA256 **按 HF Runner 报告**：`bec4ba74d858db3ff117d581478ef9cac41b1ecc7ea2a67523f6db1096addf2b`。Checkpoint 已保存并重载推理 PASS；本交接未重新下载大权重计算哈希。
- R45 原始 Train49 SHA256：`e7442993088617c4eaefd3a0c9efc7651932f7048f34586046bf6d5b5981a742`；Val15：`5ebbb3c6986a5ac4d294175bab1980ee61df08536f9b8438c8a67010630f1963`。
- R46 编译后 Train SHA256：`a028bf9fb28b12b4a3fa352d6a60281bd9e1ef5773ebfdfecc7ac80eb2cba517`；Val：`cc8d647471423f4969149f8cabdea980aad15d8bd4424d9dd98da3313c639f3c`。
- 完整 HF 报告本地 `R46_TRAINING_REPORT_PRIVATE.json` SHA256 `4ad35faedc97724f588914f59d3a00293e681e2245d2d74c27d528e3179a8e83`。

### R47：Base/v0.1/v0.2 三回复对照

- R47 原 Base Job `6acf3b8fc66288145223b41e` 在 Base 20/20 推理完成后因 `messages` 输出元字段校验失败；已通过安全恢复重用这 20 条输出，**不是模型生成失败**。
- Base 保存文件 SHA256 `becd890268edb1002c3f7195a1906f73045a86643fdac45eaf7090ee82d4dcfe`。
- R47 恢复 Job `6acf48935ccb47ba0f79853d`，RUN_KEY `r47-20261014T091647Z-637890`，三模型 60 回复 SHA/上下文对齐检查通过。
- 三独立评分表源提交：`04fbf45e73ec824c25d2692c8e6a6ebf4ca14a7d`；R47 私有解盲 JSON SHA256 `086861daa047cf2426344d1b9da47574e7363592968579bc7eb724d19896710c`。
- 多数偏好 20 题：v0.2 11、Base 5、v0.1 4；60 张偏好票：v0.2 31、Base 16、v0.1 13。
- 硬问题：`eval-014` v0.2 仍使用明确禁句“你只能是我的。”；`eval-019` 还出现代写玩家自主行动。不能靠总体得票抵销。

### R48：原始 Gold+三模型四回复同题对照

- 原始 Gold 来自已经存在于私有 Git 的 `data/compiled/v0.3/test.jsonl`，20 条原始 Assistant 最终回复；正式文件 SHA256 `d8eee6db5882d85dce7ffc01256e7c5b9b46e133bdb2cf8591259112b92e980d`。20/20 角色/前文/输入与 v0.1 冻结 Test Prompt 匹配。
- R48 三份完成版评分 CSV 冻结于 commit `c4688f709352642cedec4e273c6c4be75279e786`，目录 `evaluations/v0.2/r48/reviews/round1/`。CI 检查 20×4 原文对齐、60 条完整评审记录、1,440 格评分有效。
- 私有原始解盲文件 `R48_PRIVATE_UNBLIND_DIAGNOSTIC.json` SHA256 `e1593437c51a7b880a6e7495031ad8c06cbaa84f510e7be74326e1bc336575e8`；**私有答案映射本身未上传或提交**。

| R48 指标 | 原始 Gold | Base | v0.1 | v0.2 |
|---|---:|---:|---:|---:|
| 20 题多数胜出 | **8** | 2 | 3 | 7 |
| 60 张评审者偏好票 | **23** | 8 | 8 | 21 |
| 六维综合平均 /5 | **3.4611** | 3.1639 | 2.9111 | 3.3750 |
| 剧情连续性 | **3.7500** | 3.4000 | 3.4667 | 3.6167 |
| 角色一致性 | **3.9500** | 3.4833 | 3.3500 | 3.6667 |
| 指令遵循 | 2.4333 | 2.4333 | 2.2500 | **2.6500** |
| 文学表现力 | **4.0167** | 3.6000 | 2.9167 | 3.5333 |
| 互动推进 | **4.0833** | 3.3833 | 3.1167 | 3.5833 |
| 玩家自主权 | 2.5333 | 2.6833 | 2.3667 | **3.2000** |
| 严重玩家自主权标记次数（满 60） | 22 | 16 | 25 | **6** |

- 严重自主权至少被一位评审标记的**不同题目**数：Gold 11/20、Base 6/20、v0.1 10/20、v0.2 **3/20**。60 是同一 20 题×3 评审的相关观测，**不是 60 个独立测试样本**。
- Gold 在文笔、人物性格与互动推进上领先；v0.2 在玩家自主权与指令遵循上领先。Gold 仅领先 v0.2 一题多数胜出、两张票、0.0861 综合分，不能对新故事泛化作统计显著性结论。
- `eval-016`、`eval-019` 有**所有四份回复均被多位评审标记严重自主权问题**；相对优选≠合格。
- **不要把 R47 v0.2 11/20 和 R48 v0.2 7/20 当作质量退步**：候选集合由三份增加至四份，盲审条件也改变。

## 3. GitHub 证据和代码索引

仓库：`https://github.com/sunxu/storyforge`（private）。

| 资源 | 路径 |
|---|---|
| R46 GPU 训练验收 | `docs/evidence/V02_R46_GPU_TRAINING_ACCEPTANCE_20261014.md` + `.json` |
| R46 Git 原生 GPU 操作记录 | `docs/V02_R46_GIT_NATIVE_GPU.md` |
| R47 三模型操作与盲审协议 | `docs/V02_R47_THREE_MODEL_REGRESSION.md` |
| R47 结果分析 | `docs/evidence/V02_R47_2_THREE_MODEL_UNBLIND_RESULTS_20261014.md` + `.json` |
| R48 Gold 四回复构建与离线评审 | `docs/V02_R48_GOLD_FOUR_ARM_COMPARISON.md` |
| R48 身份匿名评审指南 | `docs/V02_R48_FOUR_ARM_BLIND_REVIEWER_GUIDE.md` |
| R48 评分原始完成版 | `evaluations/v0.2/r48/reviews/round1/R48_Reviewer_0{1,2,3}_completed.csv` |
| R48 评分原文对齐冻结 | `docs/evidence/V02_R48_PREUNBLIND_SCORING_FREEZE_20261014.md` + `.json` |
| **R48 已归档的四方结论** | **`docs/evidence/V02_R48_FOUR_ARM_UNBLIND_ANALYSIS_20261014.md` + `.json`** |
| **R48 文件校验清单** | **`docs/evidence/V02_R48_ARCHIVE_MANIFEST_20261014.json`** |
| 四回复构建 | `scripts/v02_r48_four_arm_build.py`、`scripts/v02_r48_prepare_git.sh` |
| 四回复评分收回/解盲 | `scripts/v02_r48_review_aggregate.py`、`scripts/v02_r48_unblind_git.sh` |
| 四回复预解盲审计 | `scripts/v02_r48_review_freeze.py` |

### R48 归档哈希与 CI

- 已归档 MD：`docs/evidence/V02_R48_FOUR_ARM_UNBLIND_ANALYSIS_20261014.md`，SHA256 **`07196257f3eec91a20f70f5b03c58307fcfc7405962b26aba20a9ae6d8e49783`**。
- 已归档 JSON：`docs/evidence/V02_R48_FOUR_ARM_UNBLIND_ANALYSIS_20261014.json`，SHA256 **`4f11fc51b5656c164dc2407d79b1b46ce6e233abd5207196335352d18a39ec2f`**。
- CI `[R48 Original Gold Four-Arm Offline Test](https://github.com/sunxu/storyforge/actions/runs/38580602545)`：**SUCCESS**（包括原始 Gold 哈希、20×4 评分原文冻结和 MD/JSON 产物 SHA256 验证）。
- 仓库默认 `CI` `[run 38580602539](https://github.com/sunxu/storyforge/actions/runs/38580602539)`：**FAIL at Ruff**，日志显示 **35 个 lint 错误**，跨旧源文件、R46/R47/R48 代码。未通过完整通用 CI；不能把 R48 专项 CI PASS 等同仓库所有检查通过。下一会话如修 Ruff，应局部补正并跑完整测试，不应扩大训练/评估范围。
- R40–R46 审计的 [Draft PR #1](https://github.com/sunxu/storyforge/pull/1) 尚在 Draft 状态，不能误作已合并的正式准入结论。主分支已包含 R46–R48 可执行及结果报告。

## 4. 交接时绝对不能混淆的约束

1. R45 Train49 / Val15 是**有边界的探索性样本**；完整 Gold195 与正式准入不可混写。唯一已执行的 v0.2 GPU 训练是 R46。
2. R47 和 R48 全部用**旧 v0.1 20 Test**，并且历史结果已暴露；只能作为回归诊断。**尚未收到真正全新封存的独立 Held-out**。
3. v0.2 训练时用通用无角色卡 System，旧 v0.1 Test 则在 System 中包含完整角色卡/世界设定；两者协议不同，需要在正式评测时固定部署合同。
4. 玩家自主权和长期禁令违规是单独的硬错误；即便某回复“多数最优”，仍可能核心不合规。原始 Gold 自身亦存在失败。
5. 不重新评审或改写 R47/R48 源 CSV，不重排 20 行，不猜测历史评审者身份。需要补正时提交**新增、可追踪的独立证据**。
6. 不把 R47/R48 多项投票当成独立样本量；不能从二者对比直接证明 v0.2 优于新故事上的其他模型。
7. 不提交私有答案映射、密钥、HF Bucket 私有运行日志的原始故事全文、Adapter/基座权重；小型 MD/JSON 哈希与验证脚本用普通 Git，无必要不使用 LFS。
8. 不因“继续”而自动启动任何收费 GPU 或重新跑过的推理任务；必须明确授权。

## 5. 建议的下一阶段（由新会话执行，不是已经完成）

**优先级 P0：全新独立 Held-out。** 等待用户提供独立撰写的 **40–60** 组、至少 **4 个未参与训练/历史评审的新故事世界**，每组仅需世界背景、必要历史、当前玩家输入；不要提前生成最佳回复或交模型答案。需执行故事世界/人物别名隔离、与训练及旧 R47/R48 问题去重、封存 SHA256 与样本索引，严格保存成仅测推理输入。

**优先级 P1：预注册同条件比较。** 在打开新测试模型答案前冻结 System Prompt 策略、温度/种子/生成长度、统一 context 截断规则、六维评分表与硬错误门槛；检查是否需要让 Base/v0.1/v0.2 同测有卡与无卡两套部署条件；不要临时根据成绩改 Prompt。

**优先级 P2：独立盲审。** Base/v0.1/v0.2 同一批新输入，分发 A/B/C 匿名评分表给没有看到模型映射的评审者；独立回收、冻结原文 SHA 和评分，然后解盲。既报三路多数偏好，也报每个故事世界的分布、严重禁句和玩家自主权错误数、置信不确定性。

**优先级 P3：质量决定。** 如果新题集 v0.2 依然领先且通过硬错误门槛，再考虑正式晋升；如失败，先归因 R47/R48 指令/自主权问题，提出有证据支持的训练数据调整方案，禁止直接在旧 Test 上过拟合。

**并行维护：** 对通用 CI 的 35 个 Ruff lint 错误做仅代码风格/小范围修复，跑整套 CI；但不要把 CI 修复误写成模型质量改进。

## 6. 新会话可复制的启动文本

```text
继续 StoryForge v0.2，先读取私有 GitHub sunxu/storyforge 的
docs/handoffs/StoryForge_v02_Handoff_After_R48_20261014.md
和 docs/handoffs/StoryForge_v02_State_After_R48_20261014.json。
R46 GPU 工程训练和 R47/R48 旧题回归盲审已完成；R48 Gold 8/20、v0.2 7/20、v0.1 3/20、Base 2/20，均不等于正式晋升。
R48 结果报告、机器可读汇总和 SHA256 清单已提交 GitHub，专用 CI PASS。
不要重新训练或推理旧题；不要编辑 Gold、已冻结的评审 CSV 或私有答案映射。
下一步优先设计全新独立 Held-out（40–60 题、至少 4 个全新世界）的数据接收、隔离、封存、预注册评测和三模型匿名盲审；另记录默认 CI 的 Ruff 失败。
只在明确授权后提交新的收费 GPU Job；所有重要决策附机器可读状态与 SHA256。
```

**交接总状态：`R48_OLD_TEST_FOUR_ARM_DONE__V02_ENGINEERING_PASS__NO_MODEL_PROMOTION__FRESH_HELDOUT_PENDING`。**
