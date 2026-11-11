# R60 GLM 优先 + Qwen 并行故障修复任务书（2026-11-11）

## 现有确定事实

GLM B25：H200 定向诊断 Job `adradar/6af3f4e09737d9a9e092936e` 完成，12/12 重试 `MODEL_NONEXACT_QUOTE_HOLD`，新增有效 0，历史有效 13 保留。引文错误具体是 source 8 条/16 处、target 7 条/13 处，3 条重叠；全部字段均为合法 list，且未见数量超限或超长、空值。**模型生成引文未能逐字出现在原文**，不等于来源错误、质量本身 PASS/HOLD/REJECT，也不能擅自修复为任意其他证据。

Qwen A25：保留原始 6 个完整 Checkpoint，样本7在调用链中出现 `ValueError / UNKNOWN_REVIEW_FAILURE`。既有 Guidance 构造 CPU 预检均通过，但**仍未确认错误发生于 SamplingParams、generate、校验、修复或 checkpoint**。与 GLM 引文不匹配的运行时签名不同，不能直接认定同类错误。

## GLM P0 修复路径：只修标点空白，不修改正文证据

已新增 `experiments/r58_quality/r60_glm4_exact_quote_repair.py` 与 `tests/test_r60_glm4_exact_quote_repair.py`：

- 只有本来就已接近原文的长引用（至少10字符）、能在对应历史消息或目标正文中找到长度近似且有连续6字锚点的候选，才考虑修复。
- 编辑距离最多2，且去掉标点/空白后正文字符必须 **完全一致**；任何中文字词、否定词的增删改均不允许。候选须具有唯一最小编辑距离，否则拒绝。只能在源引用上取对应消息、在目标引用上取目标正文；禁止跨字段。
- `HOLD`/评分/严重标记/注释/不确定性等所有非引用字段绝不改。若多项引文只有一部分能修复，**整个修复回滚**，原校验器继续给出原始技术失败；不得因挑选无关原文拼凑 PASS。
- `r60_glm4_b25_continuous_review.py` 增加显式 `--quote-literal-repair`，仅允许原25条历史验证后挑出的12条隔离重试，禁止与旧 `--quote-shape-diagnostic` / `--repair-quote-shape` 同时启用；可与 `--quote-match-observer` 并用。无该参数时完全不改旧逻辑。
- 修复后的 Checkpoint 仍由 frozen `checkpoint_record` → `validate_response` 走原认证流程。试验产生的新 checkpoint 必须独立输出，不能覆盖原13个有效或12个技术失败回执。
- 这是有限、安全的字面误差修复，不是已有12条都可以救回的保证。**语义改写、虚假引用仍为技术失败。** 后续如需更广泛修复，必须设计新的证据选择/语义裁决实验并独立记录版本，不能把引用改写直接宣称质量通过。

## Qwen P0 并行路径：CPU 身份门槛 + 单位置诊断

已新增 `experiments/r58_quality/r60_qwen_resume7_cpu_gate.py` 和 `tests/test_r60_qwen_resume7_cpu_gate.py`。CPU-only：固定 A25 源文件 SHA、严格要求 6 个有效且没有外来文件的 Checkpoint、通过冻结 Runner 对原6条读取再校验。失败直接 HOLD，绝不启动 GPU。

Qwen 原 `experiments/r58_quality/r60_qwen_guidance_diagnostic.py` 已支持 SAFE 分阶段事件：`GUIDED_PARAMS_START/PASS/FAILURE`，`SAMPLING_PARAMS_START/PASS/FAILURE`，`GENERATE_START/PASS/FAILURE`，不输出原文、异常消息、模型生成文本。下一次（由 Owner Mac 明确提交）应仅 `--resume --case-limit 7 --diagnose-generation-stages`，**不要把 GLM 的引文修复引入 Qwen，也不要在错误归类前增加模型重试次数**。该路径会复用旧6个受签名约束的 checkpoint，只尝试第7条；在原6个 checkpoint 所在原输出目录操作，有新增7号回执的风险，因此需先独立复制原6个验证后的 checkpoint 到全新测试目录，并对副本再次校验，再提交新 Job。

## 执行优先级

1. GitHub CI、CPU 合成测试 PASS；Owner Mac 本地私有冻结 Runner 核对；不开 H200。
2. 优先 GLM：在本地用真实12条历史输入执行**不含 GPU 的 quote repair 静态/合成预演**，检查修复候选的覆盖率（只输出计数，不输出引文）。若覆盖率很低，应直接转向候选列表受约束的模型引用重审设计，而不是再次全量 H200 重试。
3. Qwen：CPU 验证前6个 checkpoint、冻结运行路径，再决定单条7号有明确诊断阶段的 HF Job。若复用 GLM 的某个结构化输出 API 问题被证实，优先修复 GLM 的共用工具后再迁移；否则两者分开推进。
4. **本次没有发起 GPU Job、没有改动原始回执，没有开启训练准入**。结论由 Owner 返回的 SAFE 结果再定，不能预判 GPU 实验成功。

