# StoryForge R49/R50 — 16–20 候选新世界来源接收（2026-10-15）

**状态：** `FIVE_SOURCE_WORLDS_RECEIVED__METADATA_FROZEN__FRESH_HELDOUT_NOT_ADMITTED`  
**来源：** `main@a197923e1e15344e8c98bd96e593e84781b68c83`；35 files / 70,383,383 bytes  
**清单：** [V03_R50_SOURCE_16_20_RECEIPT_20261015.json](V03_R50_SOURCE_16_20_RECEIPT_20261015.json)

## 事实与范围

1. GitHub `evaluations/v0.2/source-archives/16-20/` 已收到故事 16–20 五个目录，各七个文件（原始 JSON、JSONL、story-cards、runtime-context、relationship-checkpoints、age-review、age-prose-hits）。
2. 已冻结来源 Git commit、35 个文件的 Git blob SHA-1、字节大小和五个不同的 `story_id`。Git blob SHA-1 不是原始文件 SHA256；本报告不谎称已经对 70MB 全文重新下载计算 SHA256。
3. **所有角色成年、姓名不指向现实人物**：项目所有者于 2026-10-15 在对话中明确声明；作为 `OWNER_ATTESTED` 记录。该声明不等价于逐题内容/权利/来源独立性审核；文件中保留的年龄审核仍要求 sample-level review。
4. 源档案包含原对话与旧 Assistant 回复，属于**候选来源数据**，绝不是已经独立撰写的无目标 Held-out 问题。原历史中的后续 Assistant 回复不得被注入测试 prompt，不得作为本次隐含评分标准。
5. 五个来源故事有不同的 `story_id`，但世界/人物别名语义隔离、与 R45 Train49/Val15、Gold195、v0.1/旧 R47/R48 Test 交叉重合等仍为 **PENDING**。

## R49 预注册边界

沿用 [R49–R57 v0.3 计划](../plans/StoryForge_v03_Test_and_Training_Plan_20261014.md)，该计划当前为 `PROPOSED_NOT_YET_APPROVED`，不可改写为已经获批。

- 五个新世界拟对应 50 条独立题（每世界 10 条）；实际提交仍需满足总计 40–60、至少 4 个已核实独立世界。
- 原始 16–20 源档案已经进入私有 Git，但新题输入、私有模型输出与答案映射默认不再提交 Git；在独立私有目录处理。
- 冻结测试输入后，优先保留给 R56 一次性、正式封存评测；若提前用该集分析/修复模型错误，必须将其降级为开发诊断集，重新准备正式新题。
- R49 评测生成合同与 R56 晋升门槛须由所有者批准后单独冻结；目前仅 DRAFT，无模型推理与新收费 GPU 授权。

## R50 本地源完整性门禁

在**本地已经拉取完整源文件**的 StoryForge 工作目录：

```bash
python3 scripts/v03_r50_verify_sources.py \
  --repo . \
  --receipt docs/evidence/V03_R50_SOURCE_16_20_RECEIPT_20261015.json \
  --output /private/r50-source-sha256.json
```

该工具在严格核对全部 35 个文件的 Git blob 与字节大小之后，生成**不含故事原文**的逐文件 SHA256 清单；失败则不产出验收。校验通过仅代表 Git 来源的字节完整性，不会自动改变独立性/合规/正式 Held-out 状态。

## 下一个不能跳过的门禁

- 独立编写者依据 16–20 世界的**时间点正确**背景、前文和当前玩家输入编写 40–60 条新测试输入；不含预设答案；附独立创作、未见历史解盲评分及授权声明。
- 验证世界与人物别名关联，排除旧 Train/Val/Test 世界组件；执行逐字和语义近重检查、逐题敏感内容及可答性审核。
- 只允许在独立评审、摘要 SHA256、评测参数和固定模型身份全部冻结后进入 R56。不得将测试答案回流训练。
- 另行处理默认 CI Ruff 35 个问题；R48 专项 CI PASS 不能替代通用 CI。

**最终状态：** `R49_R50_SOURCE_RECEIPT_CREATED__LOCAL_SHA256_PENDING__FRESH_HELDOUT_PENDING__NO_GPU__NO_PROMOTION`。
