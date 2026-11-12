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


## 2026-11-12 Owner新Stage远端同步完成与提交前最后HOLD

Owner固定新RUN_KEY：`r60-common2-cpu2-20261112T050556Z-d26519574fe7`。新Stage构建结果`CPU2_V2_NEW_STAGE_READY__NO_SYNC_NO_JOB`，27文件且原Stage未修改；CLI 2.4.0真实`CLI_DRY_RUN_PASS__NO_JOB`；Mac hf-cli Python hub1.6.0 的Bucket Guard `REMOTE_EMPTY_PASS`→`sync-existing`→`REMOTE_READY_PASS`；独立结果前缀 `OUTPUT_PREFIX_FILES=0`。Owner可见Job列表100条，匹配新键0；这不是完整Job历史排除凭证。所有核验均未创建新HF Job。

进一步源码核对发现上一版dry-run命令**遗漏Worker必需的**`STORYFORGE_R60_COMMON2_RUN_KEY`，即使dry-run PASS，真正运行会在shell入口立刻失败。已在`r60_common2_hf_cpu_cli_dry_run.py::prepare`增加 `--env STORYFORGE_R60_COMMON2_RUN_KEY=<NEW_KEY>`，并用合成测试绑定；只改CLI启动参数，**不改已冻结的27文件Stage**。Job name现在携带新键以便远端搜索。旧`--dry-run` PASS属于修正前版本；Owner必须同步GitHub新HEAD后重新执行dry-run。

新增 `scripts/r60_common2_hf_cpu_final_read_only.py`，复用原SHA256检查和Bucket Guard，核查本地 `<RUN_KEY>.cpu-submit-v2-attempted` 标记、远端输入ready、结果前缀为空、可见Jobs匹配；不会提交Job也不会读取/输出私有正文。100条列表按`JOB_HISTORY_INCOMPLETE_HOLD`处理，绝不自动推导“完全无重复Job”。它是诊断入口，返回42/HOLD属于预期，**不得为绕过HOLD删除标记、修改Job列表判断或直接提交**。

当前`worker_v2.sh`已写入已同步Stage，使用Image Tag而非digest，runtime的锁定依赖尚待完整核验（`decord`、`torchvision`等以本项目已冻结R59环境标准为准）；HF CLI dry-run不能证明这些实际可用，也不能证明新输出子前缀可远端写入。仍不得启动付费Job。后续先补齐CI和运行时依赖证据，再在原Stage完全不变前提下选择最小兼容方案；不可静默覆盖已同步前缀。


## 2026-11-12 Jobs服务端分页证据及修复

Owner在Mac读官方 `GET /api/jobs/adradar` 得到 HTTP 200、`RETURNED_JOBS=100`、`PAGINATION_LINK=True`，但无`Content-Range`或`X-Total-Count`。说明原SDK1.6.0 `HfApi.list_jobs` 只处理首页，`MATCHING_JOBS=0`不能用于全量排重，且不能以“100一定完整”作判断。官方HF Jobs管理文档支持全状态查询/命名标签过滤；分页查询需跟随服务端`Link: rel=next`。

已更新 `scripts/r60_common2_hf_cpu_final_read_only.py`：通过同一已认证session按`Link rel=next`只读遍历，要求每一页HTTP成功、JSON是数组、Job ID有效且不重复、下一URL与原HF endpoint同host且路径固定`/api/jobs/adradar`、禁止重定向、禁止循环与超出100页；发现任一匹配RUN_KEY（name/labels/environment/command）则HOLD，无法完整走到无next的最后一页亦HOLD。只有完整遍历且0匹配时返回 `CPU2_HISTORY_PAGINATED_PASS__NO_JOB`、退出码0。对返回的Job ID、命令与环境变量不公开打印。测试增加多页101条、隐藏在第二页Job、跨域Link和HOLD回归。**这只是可见服务端分页完整性证明，不是未发生任何并发提交的锁，也不能解除镜像/依赖合同HOLD。**

请Owner先同步GitHub分支并运行新合成回归，再以`$HOME/.local/share/storyforge/venvs/hf-cli/bin/python scripts/r60_common2_hf_cpu_final_read_only.py --run-key r60-common2-cpu2-20261112T050556Z-d26519574fe7 --stage $HOME/.local/share/storyforge/r60/hf-cpu2-stages/r60-common2-cpu2-20261112T050556Z-d26519574fe7`执行只读分页验收。**未重新提交Job，没有训练准入。**


## 2026-11-12 SDK_API_INCOMPATIBLE 只读分页修复

Owner在`hf-cli` venv的Hub SDK 1.6.0运行分页门禁，返回`SDK_API_INCOMPATIBLE`、可见Jobs0，但Stage本地PASS、远端输入READY、输出EMPTY。这是请求尚未返回第一页时的Python `TypeError` 分类，并不表示HF服务端没有Job。核对HF Hub 1.x使用`httpx.Client`：`httpx.Client.get`禁重定向参数为`follow_redirects=False`，**不是requests风格**`allow_redirects=False`。更正分页调用参数并加Mock测试强制检查；不安装依赖、不访问私有正文、不改stage或远端前缀。修复尚待Owner复测。分页遍历成功且0匹配才放行这一项；镜像/依赖及最终唯一提交门禁仍分开HOLD。


## 2026-11-12 214条完整Job历史PASS，R59依赖复用修复

Owner实际回执：`CPU2_HISTORY_PAGINATED_PASS__NO_JOB`；`history_exhaustive=true`，`visible_jobs=214`，`matching_jobs=0`，`submit_marker=ABSENT`；本地Stage PASS、远端输入READY、输出EMPTY。这是该检查时刻的全部可见历史记录，不是未来并发提交互斥锁。未提交HF Job。

已核对R59成功的真实Qwen Processor经验：`ms-swift==4.5.3`、`transformers==5.16.1`、`qwen-vl-utils==0.0.14`、`decord` 和 `torchvision==0.29.2`，需 `USE_HF=true` 才能解析HF固定revision。当前仓库版本 `scripts/r60_common2_hf_cpu_worker_v2.sh` 仅修复pip依赖行（增加decord/torchvision并将qwen-vl-utils由范围改为0.0.14）；其余真实ms-swift Collator审计仍复用原`hf_label_mask_audit.py`，且新测试检查这些字符串及CPU-only策略。**此前已同步的27文件Stage没有被修改或重新上传**。

执行策略：从2026-11-12原始不可变冻结Stage `r60-common2-cpu2-20261112T032815Z-71c840b37254` 使用现有`scripts/r60_common2_hf_cpu_stage_v2.py` 重新构建一个全新run key。原始失败Stage和最近一次已上传Stage `r60-common2-cpu2-20261112T050556Z-d26519574fe7` 均保留不动；不要从后者作为stage_v2的old_stage。新Stage只变化Worker及清单，业务私有输入保持原始字节，且未来采用新独立run/output前缀。先通过本地pytest、bash -n、compileall，再按现有CLI dry-run与Bucket empty→sync-existing→ready流程。若任何一步HOLD，不自动重复提交或覆盖。

**仍未解决的生产阻塞**：v2 CLI镜像目前只是`pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime`可变Tag，没有已验证镜像Digest；pip依赖没有完整离线锁定，且R59环境为Python3.11而此镜像中的Python/已预装torch可能不同。依赖更改仅证明源码合同对齐，**不能宣称运行时安装与Processor import可用**。在完成镜像与基础环境版本验证前，继续真实CPU Job提交HOLD，不能把生成新Stage等同于授权启动。


## 2026-11-12 Docker Manifest与Torch/Torchvision官方版本矩阵复核

Owner在Mac运行`docker manifest inspect pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime`取得Schema2 manifest：config digest为`sha256:40472de84a38292fd1a8f38fbd75ca2e96804c314a18601ec1ccd06bacb525fc`、5个layers。**此hash是image config digest，不是可用于 image@sha256 引用的manifest digest**。清单读取成功仅证明镜像Tag存在，不证明容器内Python及pip依赖可用；不能因此解除真实Job HOLD。

查阅PyTorch官方版本矩阵（`https://docs.pytorch.org/get-started/previous-versions/`）和TorchVision官方兼容矩阵（`https://github.com/pytorch/vision`）后发现：`torch==2.6.0`官方配套`torchvision==0.21.0`，而之前从R59运行注记直接继承的`torchvision==0.29.2`是与torch>=2.14兼容的新版，**不能在保留torch2.6基础镜像时无验证复用**。本轮将尚未重新上传的GitHub Worker源码改为`torchvision==0.21.0`，保持`decord`和`qwen-vl-utils==0.0.14`，并更改合成测试断言。R59历史成功记录不能作为“不同torch基础镜像上任意torchvision版本兼容”的证明。

已上传的`r60-common2-cpu2-20261112T050556Z-d26519574fe7`仍完全不可变；最新Worker修订只会进入**未来新的**Stage。仍必须取得manifest digest，核对运行时Python/torch版本和依赖安装一致性，之后才考虑新Stage与CPU Collator单次验收。没有Job提交，没有训练准入。


## 2026-11-12 镜像Manifest Digest 固定（Owner实际回执）

Owner运行 `docker buildx imagetools inspect pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime`，返回Docker schema2 **manifest digest** `sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee`。这与之前`docker manifest inspect`中的**config digest** `sha256:40472de84a38292fd1a8f38fbd75ca2e96804c314a18601ec1ccd06bacb525fc`不同，不能混用。Owner在该次依赖修复后本地3组测试`15 passed in 0.75s`（不是远端容器实跑）。

已把只读`scripts/r60_common2_hf_cpu_cli_dry_run.py`的镜像从可变Tag替换成不可变 `pytorch/pytorch@sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee`，并加合成断言；**不改已同步Stage**。镜像Tag清单可访问、Manifest Digest已知，但尚未验证HF Jobs服务端接受此digest引用及镜像内部的Python、torch、torchvision / ms-swift依赖能按目标CPU-only Worker安装，所以下一次必须先真实`--dry-run`，且`train_admitted=0`。

下一步从**最初冻结Stage**（`r60-common2-cpu2-20261112T032815Z-71c840b37254`）用现有stage_v2创建另一独立键；不要在已经远端ready的`r60-common2-cpu2-20261112T050556Z-d26519574fe7`内替换Worker。新键只用于这个修订的27文件Stage，先校验SHA与依赖文本、CLI dry-run，再新前缀empty、sync-existing、ready；所有检查通过后仍需真实容器环境兼容性证据、Job最新排重/原子防重复门禁。严禁把本节当作真实HF Job已启动。


## 2026-11-12 HF插件RW403后Mac CLI单次提交恢复

已连接HF插件成功执行**无Bucket挂载**的依赖Smoke，Job `6af55450ab34849891aed739` 在远端COMPLETED，结果`CPU2_DEPENDENCY_SMOKE_PASS`：Python 3.11.11，torch 2.6.0+cu124，torchvision 0.21.0+cu124，Transformers 5.16.1，ms-swift 4.5.3，qwen-vl-utils 0.0.14，decord 0.6.0，CUDA=false。然后仅一次用HF插件提交带独立private RO和RW Bucket挂载的Common2 Collator Job，收到`403 Forbidden`无Job ID，判为不确定提交、未自动重试。Owner随后以Mac HF CLI的只读工具重新遍历**215**个可见历史Job，0匹配；当前新RUN_KEY`r60-common2-cpu2-20261112T054440Z-d5ad72dc667c`，远端Input READY、Output EMPTY、标记ABSENT，再次`CPU2_HISTORY_PAGINATED_PASS__NO_JOB`。此前HF插件只返回100条不等于全量；后续禁止再走HF插件私有RW挂载路径。

新增独立Mac单次提交入口 `scripts/r60_common2_hf_cpu_cli_submit_once.py`，调用现有`final_read_only.check`（SHA、Bucket READY、输出EMPTY、完整分页0匹配）、`cli_dry_run.prepare`（复用共享HF Guard，固定镜像SHA、唯一RO/RW挂载、Worker路径、run_key环境变量）、HF CLI `--dry-run`、`hf auth whoami`。全部通过后才于本地Stage父目录以`O_EXCL`创建0600持久标记 `<RUN_KEY>.cpu-submit-v2-attempted`，**先标记，再执行一次** `hf jobs run --attempts 1 --detach`。不支持再次提交相同RUN_KEY，不删除失败/不确定提交标记；仅在CLI成功输出可识别的唯一Job ID后返回`CPU2_JOB_SUBMITTED__TRAIN_HOLD`。任何CLI失败、超时、日志不明都HOLD并要求重新检查远端，不自动重试；不打印原始CLI输出或私有内容。对应4个纯合成测试覆盖无--execute、首轮成功、失败保留marker、最终门禁HOLD禁止提交。**这些新增测试和入口尚待Owner在Mac真实本地环境验收。**

Owner命令：

```bash
set -euo pipefail
cd ~/workspace/storyforge-r60-4router-review
git status --short
git fetch origin r60/common2-cpu2-owner
git merge --ff-only origin/r60/common2-cpu2-owner
PY="$HOME/.local/share/storyforge/venvs/r60-tests/bin/python"
"$PY" -m pytest -q tests/test_r60_common2_hf_cpu_cli_submit_once.py tests/test_r60_common2_hf_cpu_cli_dry_run.py tests/test_r60_common2_hf_cpu_final_read_only.py
export PATH="$HOME/.local/share/storyforge/venvs/hf-cli/bin:$PATH"
KEY="r60-common2-cpu2-20261112T054440Z-d5ad72dc667c"
STAGE="$HOME/.local/share/storyforge/r60/hf-cpu2-stages/$KEY"
python3 scripts/r60_common2_hf_cpu_cli_submit_once.py --run-key "$KEY" --stage "$STAGE" --execute
```

该命令实际可能提交一条**付费CPU-only** Job；只有Owner明确希望提交时才执行。不得运行历史禁用的 `scripts/r60_common2_hf_cpu_submit.sh submit`，不得改用 `hf_job_guard.py --submit`（历史Guard在当前CLI下会把`--`传到错误位置），不得在失败时重放。`R50`全量隔离仍HOLD，`train_admitted=0`，不能自动开始GPU/训练。


## 2026-11-12 真实CPU Collator Job首次运行：仅依赖门禁HOLD

Owner经Mac Homebrew HF CLI 2.4.0成功一次性提交真实Common2 CPU-only Job `6af55aa9ab34849891aed9f4`（运行键`r60-common2-cpu2-20261112T054440Z-d5ad72dc667c`）。HF插件inspect确认`ERROR`，exit 42；Worker日志尾行`R60_CPU2_V2_DEPENDENCY_HOLD`。pip实际完成ms-swift4.5.3、transformers5.16.1、qwen-vl-utils0.0.14、decord0.6.0等安装；失败发生于`python -m pip check`。Tokenizer snapshot、ms-swift Collator、SAFE最终回执均**未执行**。该RUN_KEY与本地原子尝试标记永久保留，严禁对相同键重试、删除标记、覆盖Stage/远端前缀。

为定位问题，HF插件以同一镜像及依赖集另行运行**无私有挂载**的独立CPU-basic诊断Job `6af55b6fab34849891aeda20`，状态`COMPLETED`，标准pip check返回1，**完整唯一**报错：`decord 0.6.0 is not supported on this platform`。这是pip平台元数据检查，尚不能代表实际视频解码能力；早先无挂载依赖Smoke仅确认过decord import，不能证明VideoReader运行。

已修订GitHub Worker `scripts/r60_common2_hf_cpu_worker_v2.sh`：仅在pip check恰好返回1且stdout恰好为**唯一已知报错字符串**、stderr为空时允许进入额外`decord==0.6.0`、`import decord`、`from decord import cpu, VideoReader`、`cpu(0)`可用性验证；其他任何依赖冲突、信息变化、导入失败仍exit42，日志仅输出固定SAFE HOLD代码，不泄漏原始pip输出。此例外只解决已实测平台声明误报，**不表示实际VideoReader打开视频成功**；CPU Collator本身不处理视频。新增合成合同测试 `tests/test_r60_common2_cpu2_decord_dependency_gate.py`。禁止修改原远端Stage。新源码只会用于**下一个create-only RUN_KEY的Stage**，必须重新做单测、Stage SHA、HF CLI dry-run、远端empty→sync-existing→ready、完整Job分页排重、一次性marker。无新Common2私有Job提交、训练准入0、GPU禁用。
