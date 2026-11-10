# R60 P4 Generation Eval Framework（2026-11-10）

## 决策

采用方案 B：新建独立 storyforge_dataset.generation_eval，复用现有 HF Jobs Runtime；不改写 hf_runtime、token_preflight.py、旧 hf_job_guard.py 或训练 Runner。

## P3 实际前置结果

最近一次 P3 SAFE 状态为 P3_SYNTHETIC_CPU_PREFLIGHT_PASS__GENERATION_PROFILE_PENDING：

- 三个模型的 tokenizer / chat template 合成预检完成，90 条合成输入 × 3 个模型 = 270/270。
- 三模型 Revision 与模板来源已固定；A 使用 tokenizer 内嵌模板，B 与 challenger 使用独立 chat_template.jinja。
- 共享上下文上限 32,768 tokens；输入预算 28,672，生成预留 4,096。
- 本次仅做 CPU tokenizer/template 检查；没有下载模型权重、提交 HF Job、初始化 GPU 或执行推理。
- 运行依赖基线：transformers==4.57.1、sentencepiece==0.2.1、jinja2==3.1.6。

P3 PASS 只证明合成 tokenizer/template 路径可用，不代表逐模型 Generation Profile 已冻结，也不构成推理/GPU 授权。现有 P3 候选配置中的预算、seed、runtime digest、tokenizer hashes 与授权字段仍需正式写入并复核；不得仅凭 SAFE 摘要自动修改源配置。

## 当前实现范围

本阶段仅实现 P4 配置结构校验和 readiness assessment。它是 CPU-only 的配置检查，不导入 Transformers/PyTorch、不访问网络、不提交 HF Job、不下载权重、不运行推理或训练。

```bash
PYTHONPATH=src python -m storyforge_dataset.generation_eval \
  experiments/r60_quality/p3_model_profiles_candidate_v1.json
```

当前候选配置应返回 P4_PROFILE_INCOMPLETE_HOLD，并明确列出缺失的模型采样配置、预算、seed、runtime digest、tokenizer hashes 和授权字段。不会用 Qwen 参数替代 GLM 参数。

## 固定边界

- 模型与 revision 必须与 P3 冻结候选一致：A / B / challenger 三个角色，不允许 main 或自动升级。
- 每个模型单独 Generation Profile；不同模型的采样参数不可隐式继承。
- profile freeze、inference、GPU 三项授权必须分别显式为 true；训练授权不由本框架推导。
- 只有 context ceiling、input/output budget、seed、runtime digest、tokenizer hashes、模板 hash 和逐模型 sampling 参数完整时，assessment 才可报告 ready。
- SAFE assessment 仅输出角色名、状态和固定 blocker code，不输出模型仓库路径、prompt、输入、输出或凭据。
- readiness PASS 仍不等于 HF Job 已提交或推理已授权；提交必须经过后续独立 orchestrator 与 Owner 授权。

## 已知模型参数证据与未决项

- Qwen3-32B 官方模型卡给出 thinking 模式 temperature=0.6, top_p=0.95, top_k=20, min_p=0；当前 P3 候选已记录该配置。
- GLM-4-32B-0414 与 GLM-Z1-32B-0414 的模型卡示例/建议并不构成当前 R60 评估任务已批准的逐模型 generation profile。特别是 GLM-4 文档示例 do_sample=True，GLM-Z1 文档给出 temperature=0.6, top_p=0.95, top_k=40, max_new_tokens=30000，但这些不能自动覆盖既定评估设计或消解采样/greedy 冲突。因此两个 GLM profile 暂时保持未配置，等待明确 Owner 决策。
- 三模型 template hash 已在 P3 SAFE 结果中核验；P4 仍需核对各 tokenizer 的独立文件 hash、运行镜像 digest 与依赖锁 hash，再完成 profile freeze。
- training_authorized=false；P4 Generation Eval 不会启动训练。

## 下一阶段

1. 将 P3 最终 CPU SAFE 回执与三模型配置逐项对齐，确认 revision/template/tokenizer hash。
2. 解决 GLM-4 与 GLM-Z1 的采样模式冲突，冻结每模型独立参数。
3. 将 28,672 输入预算、4,096 生成预算、seed、runtime 镜像 digest 和依赖 lock 写入独立 P4 profile candidate，并完成校验。
4. 实现通用 worker（模型加载、输入校验、生成、输出隔离、SAFE 回执）及单 Job 计划生成器。
5. 本地/CI 合成测试全绿后，才提交一项独立的 HF GPU Synthetic Smoke；提交前再次核验 namespace、flavor、timeout、挂载和成本上限。

## 当前授权状态

inference_authorized=false、gpu_authorized=false、training_authorized=false。当前提交不创建或运行任何 Hugging Face Job。
