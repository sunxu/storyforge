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


## 2026-11-12 P2 v2 Worker / Stage 准备（优先于旧的运行命令）

新增 `scripts/r60_common2_hf_cpu_worker_v2.sh`，在 `/input/common2` RO 校验SHA256，将两条私有实验记录复制到CPU临时0700/0600空间；Tokenizer固定 `Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`，启用 `USE_HF=true`；复用R53固定 `hf_label_mask_audit.py` 与已有 `r60_common2_sft_cpu_template_audit.py --stage both` 的真实 `last_round`/Collator检查；结果只在独立 `/output` create-only写SAFE JSON（0600），不加载模型权重，不运行 `swift sft`，不启动GPU。当前仅为静态/合成实现，未真实HF CPU运行。

新增 `scripts/r60_common2_hf_cpu_stage_v2.py`：只读验证原冻结Stage的完整SHA，复制原样本及代码，**仅移除旧Worker并加入新Worker**，在新0700目录中重新生成SHA256SUMS；原始RUN_KEY、27文件、初次和重试标记不变。此过程不上传、不调用HF API或任何Job。新运行键必须独立、不可复用原RUN_KEY。新stage仍需在最终提交前进行远端唯一前缀、回执存储和精确字节核验；目前没有执行新stage的Owner回执。

本地合成验证（在独立Owner工作树fast-forward本分支之后，使用已有独立pytest环境，**不要在Mac安装Torch/Swift**）：

```bash
cd "$HOME/workspace/storyforge-r60-4router-review"
PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
"$PY" -m pytest -q \
  tests/test_r60_common2_hf_cpu_stage.py \
  tests/test_r60_common2_hf_cpu_image_probe.py \
  tests/test_r60_common2_hf_cpu_image_retry.py \
  tests/test_r60_common2_hf_cpu_submission_contract.py \
  tests/test_r60_common2_hf_cpu_legacy_cli_disabled.py \
  tests/test_r60_common2_hf_cpu_stage_v2.py
```

**暂不执行新stage生成或HF Bucket同步**，先完成上述测试和目标分支CI，再由Owner核对目标代码版本及运行环境。之后如果需要创建新stage，使用Owner现存原始冻结stage，不重新恢复Supabase、不重新抽样、不重新上传原Stage。新stage的键和目录应由Owner在本机创建并保留私有；不要在公开Issue记录真实私有输入哈希。

当前SDK 1.6.0不能通过`HfApi.run_job`传RO/RW挂载。共享`hf_job_guard.validate_spec`只能证明参数策略，**不代表CLI版本已支持对应实际提交参数**。未来应读取Owner CLI `hf jobs run --help` 对实际参数进行静态兼容检查；不得使用旧 `--name` 镜像误解析形式，且必须使用有效的镜像和真正独立的RO/RW挂载路径。如果无法证实兼容，继续HOLD而不是降级为整Bucket RW。

现有静态合同脚本`scripts/r60_common2_hf_cpu_submission_contract.py`已切换到v2 Worker、新RUN_KEY和共享Guard；真实Owner的1.6.0 SDK在无挂载API时应返回`SDK_MOUNT_API_UNAVAILABLE`，即使Worker本身已改造，也不等于可提交。

**全部工作状态仍为 NO_JOB / train_admitted=0 / R50全量隔离HOLD / Wave40暂停。**


## 2026-11-12 Owner 25/25 本地回归 PASS 与 R53 路径修复

Owner在Mac的`r60-tests`隔离虚拟环境运行6组R60合成测试：**25 passed in 0.58s**；`bash -n`两个脚本和`compileall`均无报错。这是Owner本地P2工程检查，不是HF Job PASS，也不是新代码修复后的再次验收。

对照R53历史成功报告：`6ad8a7af0a35baab53a1ced2` 的40/40真实单样本ms-swift Collator和final Assistant标签监督已有Owner原始回执接受；新R60无需改写`hf_label_mask_audit.py`。但R53的模板输入和这次2条真实历史衍生上下文不同，不能直接继承逐案PASS。R53早期也有 `transformers_vs_swift_input_identical=false` 和远程多样本padding未覆盖的限制。

从`experiments/r58_quality/r60_real_private_batch.py::private_dir`发现强制目录合同：只接受`$HOME/.local/share/storyforge/r60/private/<单层目录>`，其父目录必须0700，输入目录0700，文件0600。v2 Worker最初使用`$SCRATCH/private`会在Collator之前HOLD；已将它改为私有HOME路径、按RUN_KEY单层0700创建、0600复制、退出清理，并新增静态合成断言；**尚待Owner重新跑测试**。不更改审计核心，不触碰原Stage。

HF官方文档确认CLI 支持`hf jobs run -v hf://buckets/adradar/storyforge-training/preflight/r60/common2/cpu2/runs/<NEW_KEY>:/input/common2:ro`和独立结果前缀`.../results/<NEW_KEY>:/output:rw`；但SDK Volume API要求`huggingface_hub>=1.8.0`，Owner的1.6.0不具备此能力。具体HF CLI参数仍必须通过Owner本机`hf jobs run --help`静态核对，不能推导该已安装版本一定支持`--dry-run`、`--name`、`--attempts`或分段Bucket挂载。**禁用的旧submit入口继续禁用**；R60不得复用R53的整Bucket `/workspace:rw`。

后续严格顺序：Owner拉取最新独立分支并再次本地回归→验证本机HF CLI参数和调用参数位置→新Worker容器镜像/依赖校验与Linux CI→唯一RO/RW输入输出新前缀→完整远端Job历史排重→才考虑单次CPU真实Collator；不以R53技术成功豁免R60数据级测试。无付费提交、无训练准入、无GPU。


## 2026-11-12 HF CLI 2.4.0 直接实测帮助（Owner提供，已消除CLI参数未知）

Owner机器 `hf --version` 为 **2.4.0**，`hf jobs run --help` 明确接受 `--name`、`--namespace`、`-v/--volume`（`hf://buckets/...:/路径:ro|rw`）、`--flavor`、`--timeout`、`--attempts`、`--detach`、`--dry-run`。旧`docker.io/--name`错误来自过去命令语法/运行状态，而不能据此称当前CLI 2.4.0不支持`--name`。不再以SDK1.6.0挂载参数限制阻塞**CLI**路线，也不必升级SDK或重写ms-swift算法。

新只读入口 `scripts/r60_common2_hf_cpu_cli_dry_run.py`：在验证**新stage** SHA和Worker策略后，复用共享`hf_job_guard.validate_spec`、`build_hf_argv`产生`--dry-run`命令；不含`--submit`，不显示HF CLI原始输出，公开回执只包含SAFE状态。它不会同步Bucket或提交Job。对应合成回归 `tests/test_r60_common2_hf_cpu_cli_dry_run.py`。

执行次序必须先将新版本测试加入验收并重跑：`python -m pytest -q tests/test_r60_common2_hf_cpu_cli_dry_run.py tests/test_r60_common2_hf_cpu_stage_v2.py tests/test_r60_common2_hf_cpu_submission_contract.py`。之后Owner才可在本地用原冻结stage构建新的唯一stage（原数据内容不变、只更新独立v2 Worker）；再执行CLI只读/干运行验证。**注意：Dry-run能解析参数，不代表远端Bucket子目录挂载已经存在/具备权限，更不等于远端运行PASS。**

CLI路径不再依赖`scripts/r60_common2_hf_cpu_submission_contract.py`中旧SDK模拟的`sdk_mount_api_supported`布尔值。旧SDK只读探针保留为历史兼容性诊断，不是唯一执行路径。新工具并未加入任何真实Job提交函数；正式付费CPU2执行必须在CI、输入输出唯一前缀、独立/不可覆盖回执、Job排重与准入边界完成后另行决定。
