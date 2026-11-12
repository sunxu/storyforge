# StoryForge R60 Common2 CPU2 — SDK 1.6.0 事故与可复用提交合同（2026-11-12）

## 实际证据

- Owner Mac 独立工作分支 `r60/common2-cpu2-owner`；旧 Job `6af53990ab34849891aecb44` 状态 ERROR，错误为 `docker.io/--name` 镜像解析；Worker 未运行。
- 原 RUN_KEY `r60-common2-cpu2-20261112T032815Z-71c840b37254`：27文件本地 Stage SHA256 与远端 Bucket READY 均 PASS；CPU2 只读探针 `R60_CPU2_RETRY_READ_ONLY_PROBE_PASS`。
- `cpu-submit-attempted=PRESENT`；`cpu-submit-image-fix-attempted=ABSENT`。后者与SDK修复在提交前失败相符，但并非远端绝对不存在其他 Job 的证明。
- HF SDK `huggingface_hub==1.6.0`：`inspect_job(*, job_id, namespace, token)`，不接受位置 ID；`run_job(*, image, command, env, secrets, flavor, timeout, labels, namespace, token)`，不接受 `name`/`volumes`。
- `list_jobs(namespace="adradar")` 返回100个可见Job对象，过滤结果仅见原Job；没有完整、可证实的第二Job排除证据。
- Mac 默认Python3.15缺少pytest；不能把 `No module named pytest` 当作测试 FAIL。

## 共享工程约束

优先复用 `scripts/hf_job_guard.py.validate_spec`，而不是在 R60 复制权限校验。依据 `AGENTS.md §2.3` 和 `skills/storyforge-hf-jobs/SKILL.md`：源挂载必须 RO、位于 `/input` 或 `/scripts`；独立输出前缀 RW 挂载至 `/output`；CPU flavor、120分钟以内、不可自动重试、不能whole-bucket RW。

旧冻结 Worker 仍依赖 `/workspace` 整Bucket可写，原始27文件Stage必须保持原样；仅改GitHub脚本不会改变它。SDK 1.6.0 `run_job` 不支持挂载参数，原 `r60_common2_hf_cpu_image_retry.py` 提交入口现显式 `LEGACY_SUBMISSION_MOUNT_POLICY_HOLD`，不会创建重试Marker，不调用`run_job`。

只读预检 `scripts/r60_common2_hf_cpu_submission_contract.py` 使用共享 Guard 验证拟议RO/RW挂载、静态检查HF SDK是否支持挂载参数、检查冻结 Worker 是否仍引用 `/workspace`。预期在Owner当前SDK下返回 `SDK_MOUNT_API_UNAVAILABLE`，**不是Job失败**，不可凭预检运行远端计算。

## 下一阶段（本轮不提交新Job）

1. 在Owner独立工作树同步本分支前先检查 `git status --porcelain`，不覆盖其他Agent。测试：
   `python -m pytest -q tests/test_r60_common2_hf_cpu_image_retry.py tests/test_r60_common2_hf_cpu_submission_contract.py tests/test_r60_common2_hf_cpu_image_probe.py`。
2. Python3.11纯标准库/HF CLI环境可只读运行：
   `python scripts/r60_common2_hf_cpu_submission_contract.py --run-key <原RUN_KEY> --stage <原Stage目录>`。
3. 另行研究并静态验证HF官方支持的Bucket挂载提交途径（CLI / HF Jobs兼容API），必须先让共享Guard校验通过。新版本 Worker 应改为 `/input` 只读读取和 `/output` create-only写SAFE回执，避免任何whole-bucket RW；新增独立SHA-verified工件，不原地覆盖原Stage/历史标记。
4. 需要完整检查HF Job历史及当前Owner认证范围，明确排除重复提交；再执行合成模拟、CI、受控CPU真实Collator检查。绝不直接运行旧 `submit` 或SDK `image_retry`。
5. 即使 `ms-swift==4.5.3`、`transformers==5.16.1` 的真实最后Assistant-only标签掩码2/2通过，也保持 `R50` 完整隔离HOLD、`train_admitted=0`，Wave40暂停、GPU/训练禁止。

## 验收状态

本次变更是**旧危险入口封禁 + 静态安全合同/合成测试**，不表示已解决实际挂载/部署兼容性，也不表示实际Collator验收。所有私有正文、R50保护集与密钥不进入GitHub。
