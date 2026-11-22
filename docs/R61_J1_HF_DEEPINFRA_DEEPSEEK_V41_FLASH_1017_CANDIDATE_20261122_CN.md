# StoryForge R61 — J1 候选路由登记：HF DeepInfra × DeepSeek-V4.1-Flash-1017（2026-11-22）

> **状态：`CANDIDATE_REGISTERED__SYNTHETIC_SMOKE_PASS__FULL_JUDGE_HOLD`**。本文件为用户明确要求的**下一轮 R61 J1 候选路由**登记，不是 R61 Judge 正式选择/配置冻结，不替换历史 Gold48 J1，不授权真实私有语料外发、重新评分或收费批量请求。

## 1. 候选身份

| 字段 | 登记值 |
|---|---|
| 目标工作流 | R61 新一轮中文互动剧情六维质量评估的 **J1 候选** |
| HF 模型 ID | `deepseek-ai/DeepSeek-V4.1-Flash-1017` |
| Hugging Face Inference Provider | `deepinfra` |
| HF 计费组织参数 | `bill_to="adradar"`（合成请求成功；最终归属以组织账单为准） |
| SDK 调用接口 | `huggingface_hub.InferenceClient.chat_completion` |
| API 身份凭据 | 本地环境变量 `HF_TOKEN`（不得写入仓库、日志或回执） |
| 请求温度 | `temperature=0`（本轮两个合成探针） |
| 模型仓库 | https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash-1017 |
| 评审框架 | **复用现有** `src/storyforge_gold_quality/gold48_hf_judge.py` 的六维与逐字引文校验合同；未来新一轮版本化适配，不复制评分器 |
| 模型权重 / Provider 部署版本固定 | **尚未完成**；HF 模型 ID ≠ Provider 实际部署权重、版本或官方 API 完全等价证明 |
| 组织权限与私有外发批准 | 合成请求能成功 ≠ 未来 R61 私有故事外发已获批准 |

## 2. 已由 Owner 终端实际返回的两个合成调用

所有结果均仅依赖 Owner 在会话中提供的**不含私有作品文本**的终端回执；未由当前 GitHub 操作或本文件重新调用模型。

| 探针 | 已验证结果 | Token（输入/输出） | 预估费用 |
|---|---|---|---:|
| 基础 chat completion | `{"status":"OK","score":5}`，调用成功 | 18 / 10 | USD 0.000004704 |
| `response_format={"type":"json_schema", ...}` 严格结构化输出 + 引文 substring 核验 | `SCHEMA_AND_EXACT_QUOTE_PASS` | 41 / 30 | USD 0.000012838 |

- 第二项已由本地测试程序验证：JSON 可解析，恰好包含 `score` 和 `quote` 字段；分数是 1–5 整数；`quote` 为非空字符串且逐字存在于合成来源文本。
- **并未验证**引用是否语义支持评分、完整句子边界、六维完整 Rubric、三个 severe flags、证据数量/来源跨度、多轮场景、上下文长度、`max_tokens=2048`、错误码/重试策略、批量收费/并发/响应稳定性。
- 前一尝试：`provider="together"` + `bill_to="adradar"` 返回 HTTP 403 `Only Inference Providers with accurate pricing are available for organizations.`；**Together 组织计费路由当前未通过 Owner 实测**，不建议自动重试，也不推断 HF Token 或模型无效。
- 估价来自实际响应的 `estimated_cost`，非正式费率、未来价格承诺或最终结算证明。

## 3. 进入 R61 J1 正式选择之前的门禁

1. **模型与计费版本冻结：**核对 HF Provider 路由、HF 模型提交/精度或可提供的版本信息、组织计费权限、费用上限和私有数据处理范围；第三方推理不能视为 DeepSeek 官方 API 字节等价。
2. **复用既有 Gold48 校验代码进行合成端到端：**固定六维字段、三个严重标记、证据引用条数、严格原文引用及所有校验失败路径；先用合成输入检验，禁止重新给 Gold48 私有卷宗打分。
3. **评审质量校准：**在合法、独立且经批准的 R61 校准材料上比较分数偏差、误引率、严重标记分歧、输出完整率与成本；不要仅根据本轮 1 次合成成功判断稳定性或评审可靠性。
4. **独立正式授权：**只有 Owner 另外明确批准 R61 的 J1 模型/Provider/费用、调用范围、外发语料、并发/失败策略并冻结 R61 评审合同后，才可对新评估材料调用正式 Judge。
5. **新评估集限制：**Gold48 已经在 R60 质量决策中暴露，不能再宣称为 R61 全新未暴露晋升测试。现有冻结的 Gold48 478/480 评分、2 项缺失、33 份修订和 Owner 映射全部不动。

## 4. 最小调用形态（仅供以后另行批准的合成兼容测试）

```python
import os
from huggingface_hub import InferenceClient

client = InferenceClient(
    provider="deepinfra",
    token=os.environ["HF_TOKEN"],
    bill_to="adradar",
    timeout=120,
)
# 仅说明候选路由的初始化；本文件不执行任何请求。
# 后续复用现有 Gold48 Judge 的完整 messages/schema/validator，
# 经 R61 新评审合同批准后再执行请求。
```

## 5. 本次操作边界与状态

- 本次仅在 GitHub 的 R60/Gold48 工作 PR 分支上登记**未来 R61 候选**；R61 分支不存在，不擅自创建或启动新训练。
- 本次不发 HF API、不启动 Job/GPU、不连接生产数据、不生成或修改私有评分、不变更 runtime config、不部署。
- 不改变 R60 决议：`quality_v1_admitted=0`、`model_promoted=false`、`NO_PROMOTE`。
- **接手唯一建议动作**：若后续 Owner 选择继续 R61 Judge 评估，再依据本候选卡对已有校验器做一次**合成的完整六维兼容性测试**，随后独立冻结实际模型、Provider、费用与授权。

**登记结论：`R61_J1_HF_DEEPINFRA_DEEPSEEK_V41_FLASH_1017_CANDIDATE_REGISTERED`，`synthetic_basic_pass=true`，`synthetic_schema_quote_pass=true`，`full_judge_contract_status=NOT_TESTED`，`formally_selected=false`。**
