# R60 Base336：最短探索性GPU训练执行合同（2026-11-16）

## Owner当前目标
仅使用冻结V1/V2/V3双PASS交集339中剔除Known5精确R50重复3条后的**336个候选**，尽快做一次Qwen Base QLoRA**探索性**训练。禁止引入Gold72、P2B、R50、旧R45或任何其他来源为本次Train/Val数据。**“只使用336候选”并不强制全部336条变成梯度样本：Train、内部Validation均必须从336池出，且不能同一条两边共用。**

本合同是新实验路线，不修改/追认既有六门禁正式准入标准。没有完整R50跨世界语义隔离、历史Provider独立证据和源时间戳来源时，不得宣称正式训练准入或模型晋升。真实训练输出状态只能是 `EXPLORATORY_GPU_..._NOT_PROMOTED`。

## 已验证可以直接复用
- `r60_real1000_candidate_identity_audit.verified_cases_report` 严格重建冻结339候选；
- `r60_real1000_r50_known5_quarantine.construct` 与已保存隔离文件恒等对照，原3条永久隔离；
- R50完整原始50条的story/session/message精确ID差集已有Owner检查PASS，不能冒充跨UUID语义隔离；
- 已验收的HF CPU336实际Qwen3.8 tokenizer / ms-swift collator / R18 last-assistant-only mask，**无需重复CPU336无System技术包**；
- 冻结336的A/B质量回执、评审模型来源和双PASS已验证（Provider独立认证HOLD）；
- `r60_base336_world_cross_split_private_roster_cpu.py`已创建8组私有roster，涉及38 Story/82条；7通用模板、1语义证据不足，当前全部HOLD；
- GPU实现复用R54 `scripts/v03_r54_gpu_runner.py`所证明的**方法与校验模块**，不能直接运行该脚本：R54 hardcode 31/9、dataset SHA、16步及老release。
- HF当前远端只有`preflight/r60/base-start/cpu336/runs/r60-base-cpu336-20261114T165256Z-9e35795990aa`技术Stage，**不是GPU训练release**。

## 唯一新批次路线：冻结336子集的训练和内部验证
1. Owner Mac只读核验原339 crosswalk + 已保存3/336 quarantine + 原始50精确隔离Owner回执 + 8组原始roster SHA；不得重做336条文学评审、不得补抽数据。
2. 按Story的确定性旧hash划分作为初始方案，读取8组roster中确证**相同JSON world**的Story连通边；把**整个跨旧Train/Val的连通组件统一归Train**，并再次重算全局组件划分。不得只挪样本，必须挪整个Story/组件；不得把`7个通用模板`自动称为语义同世界，也不得把相同JSON导致的跨组边忽略。
3. 从336中生成不相交`train.jsonl`和`validation.jsonl`，每条只有已验证3条历史user/assistant/user + 原冻结assistant target监督，明确`THREE_PERSISTED_MESSAGES_NO_SYSTEM`实验合同；不要伪造Source-bound世界卡或历史实际System。世界/卡缺失影响外推，应作为实验限制而不是隐性补写。
4. 划分验收：训练+验证总数336（除非明确产生新的隔离清单，严禁悄悄丢行）；3条Known5永不出现；无任何case跨组；story_ID不跨组；8组关联component不跨组；各split非空；保持原始目标hash、输入三消息及来源hash；评测保护只声明已证实的原始50**精确ID**差集，任何未确认的语义关系显式HOLD。
5. 在Owner Mac新建0700/0600、create-only的新私有发布目录，保存输入证据SHA、split组件信息与`train.jsonl`/`validation.jsonl`、来源336身份及格式审计回执、`EXPLORATORY_ONLY__NO_TRAIN_ADMISSION`标签。**不得复用HF CPU336技术Stage或R54正式release**。
6. 最终Train/Val按照实际发布字节运行一次真实ms-swift actual collator+last-assistant label mask（可以使用现有已验证HF CPU环境，不下载27B权重）。这一项是本次新split特有的预检，不是重复跑旧336技术包。
7. GPU新建R60独立run_key和Bucket前缀`experiments/r60-base336-exploratory/<RUN_KEY>`，输出和stage强制create-only；从R54复制参数合同：`Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`、NF4/bfloat16、LoRA rank64/alpha128/dropout0.05、max_length16384、last_round、1 Epoch。**训练步数、eval/save节奏必须按实际最终Train数量计算**，并保证最后一步checkpoint与adapter reload。不能沿用R54的16step和硬编码SHA。
8. GPU发送前严格验证私有stage完整文件清单、SHA、model revision、ms-swift/transformers/bitsandbytes版本、单A100-80GB VRAM、资源额度、Bucket RW隔离和GPU计费任务的唯一提交锁。先写submit marker再提交；不自动重试不覆盖旧Run。用户本轮“尽快推进GPU训练”作为推进新实验的请求，但GPU提交仍必须以实际Stage可核验且预检PASS为前提。
9. 开始模型评测时，旧R47/R48/R55已暴露20题只能作为开发回归；R50在世界语义/曝光未完成审计前不能声称正式独立测试。Gold72/P2B既不作为训练源，也不必自动提升为本轮正式独立测试；其历史暴露用途需留档。

## 不做的工作
不重做Gold72/P2B全量Story身份扫描作为**本探索性GPU试验**的强制前提；不重跑336×2双Reviewer；不全面重审16条试验批次；不从336以外新增训练样本；不做R46/R54旧LoRA续训；不变更正式训练的A/B/HOLD历史结论。

## 当前真实状态
- `FROZEN_336_CANDIDATE_TECHNICAL_PASS__GPU_RELEASE_NOT_PREPARED`
- GPU训练数据release与可独立提交的R60 GPU worker**尚未生成**。
- 不得用已有CPU技术Stage直接作为可训练正式发布包。
- 未提交GPU Job，`train_admitted=0`，未通过独立测试集模型晋升。

## 交付清单（只输出SAFE）
本次实验有效执行前应得到：336原始身份匹配统计、Train/Val数量、两组Story数量、跨组已知World JSON组件数=0、Known5排除=3、R50原始50精确身份交集=0、各数据文件SHA、真实Collator PASS、固定GPU模型配置SHA、独立GPU RUN_KEY、远端Bucket stage READY回执。任一校验失败则不submit并说明HOLD类别，不伪称GPU已启动。
