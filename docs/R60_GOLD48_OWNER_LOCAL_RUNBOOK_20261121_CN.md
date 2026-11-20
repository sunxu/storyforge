# Gold48 Owner 本地：已冻结输入物化、Adapter 签收、单独签名授权

## 0. 2026-11-21 Owner 已选单机简化调度（最高优先级）

### Gold48 RO 输入本地化与私有结果交付（代码已接，真实 Job 待验）

- 已在**原** `gold48_runtime_gate` 中加 `materialize_gold48_ro_input(source, target, expected_sha256)`：复用 `InputManager` 的 O_NOFOLLOW/长度限制/精确 SHA，再在 Job-local 0700 根写 0600 的 create-only 文件并 fsync、读回；用于解决 HF FUSE 只读文件不保存 POSIX 模式的问题。这个函数**必须由未来经 Owner 批准的 Job 包装在生产 pre-GPU 预检前调用**；当前尚无专门 GPU 提交动作，不可将工具函数的 CI 成功当成真实 HF 输入挂载 PASS。
- `run_authorized_gold48_production` 已在原 `run_gold48_generation_batch` 后直接调用 `deliver_gold48_private_result`。默认固定输出位置为私有 Bucket `hf://buckets/adradar/storyforge-training/experiments/r60-gold48/outputs/<run_id>/`，必须按 `<role>.private.json`、`<role>.private.json.launch.private.json`、`<role>.private.json.identity.private.json`、`<role>.private.json.result-sha256-manifest.private.json` 顺序上传；最后一个 SHA256 manifest 在本地由已有 `OutputManager` 原子发布，远端使用 `hf buckets cp` 而非要求 FUSE POSIX 原子性。每份传输后下载到本地 scratch 再校验 SHA 和字节数。**不能将已上传部分结果或单一 Job 回读当成 Owner 已签收**。
- 若上传、回读、完整性或私有目录检查失败，状态为 HOLD，绝不自动重跑模型。正式评测需要 Owner Mac 再使用既有 `hf buckets cp` / 下载 SHA 审计流程确认四个 Run ID 的每份远端文件、48 条与原始 Frozen 输入绑定。所有真实 GPU/Provider/Owner 签名公钥授权仍独立 HOLD；**本轮只完成 CPU 合成代码与 CI，尚无真实 HF 交付验收。**



**2026-11-21 最新已完成代码适配**：`gold48_runtime_gate.py` 的旧 HF Bucket / FUSE 共享消费根已换成当前 HF Job 的 **本地** `/tmp/storyforge-gold48-private/spent`（预先创建 0700）。`OutputManager` 仍负责 0600、原子不覆盖、文件及目录 fsync；运行进程按 `/proc/self/mountinfo` 拒绝 FUSE/远程文件系统作为消费根或生成私有输出。签名验收、Provider 身份、依赖锁、RO Adapter 挂载、Loader SHA 和 Worker 约束均未删除。此消费记录**只在当前 Job 生命周期内有效**；跨 Job 防重复依赖唯一可信 Owner Mac 的本地持久提交标记和完整 HF Job 历史，不能宣称全局分布式互斥。

**尚缺正式交付**：现有 Mac 的 CPU-only submit 和 Base336 GPU dry-run 并非 Gold48 GPU 正式提交；远程 `:ro` 证据/签名文件可能报告非 0600，必须经 SHA 校验安全复制到本地 0600 后校验；Job-local 输出与 Sidecar 必须完整送达私有 HF Bucket，再由 Owner Mac 下载验 SHA。尚未完成输出上传回收闭环、Provider/Owner 独立可信指纹注册与 GPU 授权，**不可启动真实推理**。不使用 Supabase/PostgreSQL，不重跑 HF Bucket 0700 探针。



不引入 Supabase/PostgreSQL 或新分布式锁；唯一调度者是可信 Owner Mac。复用 `r60_common2_wrapped_hf_cli.py` 的完整组织 Job 历史排重、标记先于提交、失败留标记，以及 `r60_base336_gpu_cli.py` 的 GPU 命令 dry-run 和镜像/挂载检查。Mac 本地提交标记已经改由 **既有** `OutputManager.write_safe` 发布（0600、原子拒绝覆盖、文件及目录 fsync），不复制写入算法。每臂唯一 Run ID；提交结果不确定时查旧 Job，不自动重试；真正的重新执行需要 Owner 新授权及新 Run ID。

本地 Mac 标记是**单一 Owner 可信边界**下的防重复提交，不能证明多个 HF Job 全局互斥；HF Bucket 仅作为输入/结果对象存储。历史第 7/13 节的远端共享目录 `0700` 与跨 Job 消耗账本方案不再是选用的执行架构，保留供审计追踪；**现有 `gold48_runtime_gate.py` 的旧强门禁尚未替换，绝不能在 HF Job 中直接绕过。** 下一步只有在 Owner 完成生产签名密钥注册、Provider 身份/实际输出交付边界核对以及单独 GPU/推理授权后，才能对旧强门禁做与单 Owner 流程相匹配的最小、有回归测试的安全适配。**本节不签发授权，不启用真实推理或新 CPU 探针**。


**仅用于执行本次已存在的代码和文件。** 无历史重审、无新 Tokenizer/SHA HF Job、不访问 R50 sealed、不自动 GPU。所有输入留在 Owner Mac，按既有目录的权限执行；仓库和 CI 不存私有回执内容。

## 1. 核对本地文件（不重构）

**2026-11-21 Owner 本地已验收（由 Owner 提供的 SAFE 回执）**：冻结输入已物化；目录 0700、输入/Manifest 0600、完整输入 SHA、48 条顺序与逐案 SHA 均 PASS；`OWNER_INPUT_SHA_ACCEPTANCE: PASS`。Adapter 绑定已签收为 `OWNER_GOLD48_ADAPTER_BINDING_ACCEPTED__MOUNT_UNVERIFIED`。**不得再次运行 create-only 物化和绑定签收，除非另立新的运行范围并获得 Owner 明确批准。** 此处仅记录 SAFE 状态，不存私有内容。Provider 挂载与真实远端权重仍 UNVERIFIED。

以下为 Owner 实际确认的文件位置，**不要**把私有文件复制进 Git 仓库或打印 JSON 内容：

```sh
umask 077
cd ~/workspace/storyforge
VIRTUAL_ENV="/Users/keedle/.local/share/storyforge/venvs/r60-owner"
export VIRTUAL_ENV PATH="$VIRTUAL_ENV/bin:$PATH"
export PYTHONPATH="$PWD/src"
OWNER_ROOT="/Users/keedle/.local/share/storyforge/r60/private"
BINDINGS="$OWNER_ROOT/GOLD48_ADAPTER_BINDINGS_CANDIDATE_PRIVATE.json"
R60_EVIDENCE="$OWNER_ROOT/r60-cpu-job-json-log-line.private.json"
FROZEN="$OWNER_ROOT/r60-gold48-generation-profile-20261121/gold48_four_arm_generation_profile_frozen_v1.json"
R54_EVIDENCE="$OWNER_ROOT/R54_ADAPTER_RELOAD_VERIFIED_PRIVATE.json"
R46_EVIDENCE="$OWNER_ROOT/r46_training_report.json"
OUT="$OWNER_ROOT/gold48-frozen-worker-input-v1"
INPUT_JSONL="$OUT/GOLD48_GENERATION_INPUTS_PRIVATE.jsonl"
INPUT_MANIFEST="$OUT/GOLD48_GENERATION_INPUT_MANIFEST_PRIVATE.json"
# Owner 未提供以下路径，不猜测：
OWNER_FREEZE="<owner-local>/GOLD48_SCOPED_FROZEN_MANIFEST_PRIVATE.json"
DRAFT="<owner-local>/GOLD48_RECONSTRUCTED_INPUTS_DRAFT_PRIVATE.json"
ACCEPTED="<owner-local>/GOLD48_ADAPTER_BINDINGS_OWNER_ACCEPTED_PRIVATE.json"
```

R46/R54 原报告必须是**原始文件字节**，不能重新格式化。R60 evidence 必须是此前 Job `6b00a44aefaf5e14f4b3c6b5` 的 JSON 回执**原始日志单行字节（末尾不附加换行）**；三份文件必须在私有目录且 mode `0600`。此步骤不读取 Adapter 权重。

## 2. 物化冻结 JSONL 和 Manifest

```sh
# 历史命令，仅在新的 Owner 授权范围内使用；当前已完成，不应重跑。
python3 scripts/r60_gold48_generation_input_materialize_cpu.py \
  --frozen-profile "$FROZEN" \
  --owner-freeze "$OWNER_FREEZE" \
  --reconstructed-draft "$DRAFT" \
  --private-root "$OWNER_ROOT" \
  --output-dir "$OUT"
INPUT_JSONL="$OUT/GOLD48_GENERATION_INPUTS_PRIVATE.jsonl"
INPUT_MANIFEST="$OUT/GOLD48_GENERATION_INPUT_MANIFEST_PRIVATE.json"
shasum -a 256 "$INPUT_JSONL" "$INPUT_MANIFEST"
```

该入口使用 Git Blob 锁验证 Frozen Profile，读取 Owner 冻结里的 Draft SHA 和 48 条逐案 canonical SHA，逐条严格对应，不重新生成任何 Prompt。create-only，第二次执行会 HOLD。核对输出文件均为 mode `0600`、目录 `0700`；只在 Owner 本地保存打印的 SHA。

## 3. Owner 对现有 Adapter 候选签收

```sh
# 历史命令，2026-11-21 已签收；不要重复执行 create-only。
python3 scripts/r60_gold48_owner_generation_authority_cpu.py \
  --mode accept-bindings \
  --frozen-profile "$FROZEN" \
  --owner-freeze "$OWNER_FREEZE" \
  --adapter-bindings "$BINDINGS" \
  --input-manifest "$INPUT_MANIFEST" --input-jsonl "$INPUT_JSONL" \
  --r46-evidence "$R46_EVIDENCE" \
  --r54-evidence "$R54_EVIDENCE" \
  --r60-evidence "$R60_EVIDENCE" \
  --explicit-owner-accept --accepted-output "$ACCEPTED"
shasum -a 256 "$ACCEPTED"
```

只有在 Owner 看过三个来源文件且同意**历史 SHA 来源与 R60 CPU Job 日志的有限证据范围**后才执行。验收状态是 `OWNER_GOLD48_ADAPTER_BINDINGS_ACCEPTED__MOUNT_PENDING`；仍然 **不声称** Provider 挂载或三份当前远端权重字节已独立签收。不重跑 R60 1.87 GB SHA。

## 4. 尚未授权：Owner 单独签发每臂的生产回执

这一段是**未来独立批准正式推理后**的执行说明；目前冻结 Profile 的 `inference_authorized=false`、Owner Trust 公钥指纹未登记，**不要执行签发或 GPU**。Owner 私钥只留 Mac、chmod `0600`；运行端只得到签名回执和公钥。由 Owner 单独审批 Run ID、角色、输出目录、资源与有效期，再执行脚本的 `--mode sign-one-arm --explicit-owner-generation-authorization`，其余参数用 `--help` 查看。脚本检验已签收 Adapter、源文件、48 输入、SHA 锁与镜像 Digest，回执原子 create-only 0600，输出不覆盖。

运行端的可信公钥 SHA256 需要由 Owner 独立核对后，经审查改为 `gold48_owner_receipt.py::OWNER_TRUSTED_PUBLIC_PEM_SHA256` 的固定值；现保持空值，强制 HOLD，不能把命令行传入的新公钥直接视为信任锚。

## 5. 验收口径

Owner 本地物化/签收 SAFE、GitHub 合成 CI、CPU 依赖 Hash Install、真实 GPU/PEFT 加载分别独立签收。GPU Smoke 必须另行授权；本 runbook 不发起任何 HF Job 或正式 192 条推理。

## 6. 选定 CPU 基础镜像中的 Hash-pinned 安装实证

CPU Job `6b00b0894fdc5ab3c55be7f0` 在固定基础镜像 `pytorch/pytorch@sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee` 中读取 Git 固定 Commit `c4dd8c8ceecf60a26ec476ebf46f07294c9d8f65` 的锁文件，先校验 77,715 字节、SHA256 `dc3425f4895e091c4f5981a4933a6ba2e8fdd8426d8e074069c8cfa2ff4f8d5e`，再执行 `pip install --require-hashes -r <lock>`，返回 0；`pip check` 通过。预装 Torch `2.6.0+cu124` 未改动，签名依赖 cryptography `46.0.4` 安装成功。此前 uv strict hash 安装因 torch 上游无版本约束而 HOLD，换用 pip 后闭环。**仅 CPU 基础镜像 + 哈希覆盖安装 PASS，不等于实际 GPU/PEFT 权重加载 PASS**。

## 7. 加载前授权与运行环境身份（后续真实 GPU 前必须满足）

本仓库新增 `gold48_runtime_gate.py::run_authorized_gold48_production` 作为正式调度入口；执行顺序固定为：冻结输入 / 三份来源证据核对 → **Owner Ed25519 验签** → **Provider 独立签名的实际镜像 Digest 验证** → 当前容器依赖版本与 SHA 锁核对、`pip check` → **共享持久目录 create-only 消耗本次 Owner 授权** → `load_pinned_gold48_backend(launch_permit=...)` → 既有 Worker。

Loader 不再接受 `runtime_authorized=True`。单纯给它一个布尔值或任意字典，必须在 GPU 初始化前 HOLD。Provider 公钥指纹 `PROVIDER_TRUSTED_PUBLIC_PEM_SHA256` 和 Owner 公钥指纹 `OWNER_TRUSTED_PUBLIC_PEM_SHA256` 需要分别由可信方审查并固定；当前均**未设置**。Provider 证明包含可追溯的 Job Inspect SHA、Job ID、运行范围及镜像 Digest，并必须由可信独立方使用预登记公钥签名；不能用用户输入的 `runtime_image_digest` 参数当实测值。

生产消耗账本路径固定为 `/mnt/storyforge-private/gold48-authorizations-spent`，须由生产平台提供跨运行共享、持久、0700、独立挂载目录；每份授权回执 SHA 映射一份 create-only 0600 消耗记录。**失败或崩溃后不允许自动重跑 GPU/模型调用**，必须另发 Owner 签名的新 Run ID 和输出命名空间。未经确认跨运行持久挂载的本地临时目录不可以代替此账本。

本轮的 CPU 模拟测试验证了这些门禁的拒绝路径和执行先后，并**没有**取得真实 Provider 镜像签名证明，也没有执行真实 GPU。当前 Loader 和正式生成应保持 HOLD。

## 8. Sidecar 失败的只读恢复（不重新生成 48 条）

生成开始前会写入 `<output>.launch.private.json` 作为 0600、create-only 运行意图证据。若 48 条输出已完整发布，但 `<output>.identity.private.json` 写入失败，可以调用 `gold48_contract_bridge.recover_gold48_identity_sidecar(...)`：重新检查冻结 Profile、Owner 签名、来源回执、运行意图和**已有**输出的 48 条顺序 / Seed / token 预算 / Schema / 文件 SHA，再 create-only 补写 Sidecar。

恢复函数**不要求 Backend、不载入任何模型、不调用 GPU 或 generate()**。对于真实 Provider 已测量的运行，还需传入 Provider 原始签名证明、公钥及依赖合同以复核身份；无法取得这些证据就 HOLD。已有 Sidecar、缺失 launch marker、缺失或不完整输出全部拒绝，不删除、更改或覆盖输出。授权有效期已经过期时不能绕过验签重写身份；应由 Owner 单独批准处理，而不是自动重复模型生成。

**2026-11-21 后续代码门禁收口：**签名回执现在新增不可省略的 `execution_environment`。生产 Owner CLI 只签出 `PRODUCTION_GPU_48_GENERATIONS`（`inference_authorized=true`、`gpu_authorized=true`）；合成测试密钥使用 `SYNTHETIC_CPU_ONLY_CONTRACT_TEST`（两个授权位均为 false），并且必须显示 `gpu_started=false`、`inference_started=false`。生产签名绝不能用于合成 Backend 的直接四臂入口；合成签名绝不能用于 GPU 前置门禁。真实 Backend 必须能够在共享持久账本中核对已消耗回执、输出范围、Adapter SHA、镜像测量与依赖锁。依赖合同的锁 SHA、镜像 Digest、包版本和已验收 CPU Job 身份在代码内有独立硬钉，不能通过修改传入 JSON 放宽。上述均为 CPU 合成防回归验证，**不代表真实 Provider 挂载、GPU 或正式生成已验收**。

## 9. 已签收 Adapter 的准确边界

Owner 回执为 `OWNER_GOLD48_ADAPTER_BINDING_ACCEPTED__MOUNT_UNVERIFIED`，它只签收 **R46/R54 历史报告 SHA、R60 原 CPU Job SHA 日志、三份来源证据、映射候选与48条冻结输入**。生产前置门禁要求明确保持 `provider_volume_attestation_verified=false`、`current_remote_weight_bytes_verified_all_three=false`；只有真正 Loader 加载精确文件时通过 Adapter 字节哈希，才能确认那次运行的实际本地 Adapter 文件。**`owner_receipt_verified=true` 不代表 Provider 已验明挂载或三份当前远端权重全部 PASS。**

## 10. 首次真实 HF Provider 三路只读挂载验收（CPU，不读权重）

已在 **HF CPU Job [`6b00c1024fdc5ab3c55bfcf3`](https://huggingface.co/jobs/adradar/6b00c1024fdc5ab3c55bfcf3)** 使用固定镜像 `pytorch/pytorch@sha256:77f17f843507062875ce8be2a6f76aa6aa3df7f9ef1e31d9d7432f4b0f563dee`，将现存三个冻结 checkpoint 子目录分别以 HF Jobs 原生 `:ro` 卷挂载到 `/ro_adapters/r46_v02`、`/ro_adapters/r54_v03a`、`/ro_adapters/r60_base336`。

探针读取容器 `/proc/self/mountinfo` 确认**三处精确挂载点均存在且 ro**；三个 `adapter_model.safetensors` 的文件大小均为 `1,867,797,544` 字节；三份 `adapter_config.json` 依次为 `1,282 / 1,282 / 1,288` 字节，读取配置并验证 LoRA 类型、r=64、alpha=128、12 个目标模块集合、基础模型固定 Revision。Job `COMPLETED`，且 `gpu_started=false`、`model_calls=0`、`weights_read=false`、`weights_hashed=false`。

SAFE 结构化实证：`experiments/r60_quality/gold48_provider_ro_mount_cpu_safe_receipt_20261121.json`。**仅本次 CPU Job 的挂载及元数据 PASS**，不等于后续 GPU Job 挂载 PASS、不等于当前三份权重 SHA PASS、也不等于 Owner 或 Provider 正式 GPU 授权。保留 Owner 原始 Adapter 签收及 `provider_volume_attestation_verified=false`、`current_remote_weight_bytes_verified_all_three=false`；**不修改任何冻结 Profile 和私有回执**。未来正式 HF Job 应复用已验证的相同三个 checkpoint 只读挂载配置，并由真实 Loader 在每一臂开始生成前核对相应 Adapter 精确字节 SHA，不重跑此前已完成的历史 CPU SHA 任务。

## 11. 正式运行进程的只读挂载实时校验（不重复 HF 探针）

在 `gold48_runtime_gate.authorize_and_consume_before_gpu` 中，三臂（非 base）必须于**消耗一次性 Owner 授权之前**，通过当前容器的 `/proc/self/mountinfo` 验证 `/ro_adapters/<role>` 是精确独立且 `ro` 的挂载点，同时检查非符号链接目录、权重文件大小 1,867,797,544 字节与三个 Adapter 原始配置文件固定大小。检查只用 `lstat` 和 mountinfo，不读取或 SHA 计算权重。正式 Loader 消费授权时及生成前继续复核该挂载观察，并由原 Loader 完成权重字节流 SHA。过去 CPU Job 的挂载 PASS 不会被当成新进程的挂载实证。若缺失、可写、路径错误、被替换为 symlink 或文件尺寸不同，必须在 GPU 及模型调用之前 HOLD；未签发的 Owner/Provider 许可仍不能被绕过。

## 12. 旧问题已定位：ChatGPT HF Connector 私有 Bucket RW 挂载 403（禁止重复排查）

**沿用 2026-11-03 与 2026-11-10 已核验结论，不再把 Connector 403 描述为未知的组织/Bucket 总体写入权限问题。** 同一组织 `adradar` 的 HF Jobs 在 ChatGPT Connector：无挂载 PASS、私有 Bucket `:ro` PASS、私有 Bucket `:rw` 在提交阶段 403（Job 不创建）。Mac 本地 HF CLI 使用相同组织与 Bucket 的默认 RW 挂载已经完成写入、读回、删除；实际成功 Job [`6af2ee90ab34849891ab2f6e`](https://huggingface.co/jobs/adradar/6af2ee90ab34849891ab2f6e) 于 2026-11-10 `COMPLETED`。这排除了 Bucket 整体不可写、组织总体缺乏 Jobs 资格及简单的卷语法错误。ChatGPT 侧失败点曾定位在 `/api/buckets/adradar/storyforge-training/xet-write-token`；OAuth scopes 未含 `write-repos` 是一个观察点，**尚不足以独立证明具体后端根因**。

2026-11-21 的 Gold48 可写账本探针在 ChatGPT Connector 上重复收到相同 403，未创建 Job、未写入任何 Bucket 文件；**这是已知连接器限制的再次出现，不是新的主线验收结果**。不得因它再提交一轮 ChatGPT RW 探针、重复更换 CPU flavor、切换个人 namespace、反复重新 OAuth 或重跑成功的 RO Adapter Job。后续需要 RW 时，优先复用**已经成功的 Owner Mac CLI 提交通道**，输入继续 `:ro`，输出/账本使用独立的私有 RW 卷；任何实际创建和 GPU Job 仍须按项目单独审批。

正式推理前剩余的**不同**技术门禁是：在 Owner Mac CLI 可以写入的**隔离私有目标目录**上，用原有 `OutputManager.write_safe` 核验 0700/0600、原子 create-only、拒绝覆盖、目录 `fsync` 以及**跨 Job 持久性**。过去 CLI 的简单写入成功并不等于该原子账本合同通过。生产代码 `gold48_runtime_gate.verify_atomic_private_publication_before_spend` 已加入对真实输出目录和持久账本目录的检查，并在消耗 Owner 签名、GPU/模型初始化前失败关闭。该测试不会授予任何推理权限；不得用无法保证原子性的 FUSE 挂载冒充已验证共享账本。


## 13. Gold48 授权账本的 HF Bucket 挂载实证与安全结论（2026-11-21）

**最新真实状态：此节原有双 Job 实验因关键前置门禁 HOLD 而暂停，下面历史命令仅供追溯，禁止直接执行第二份 Job 或通过 chmod/放宽 0700/省略门禁反复探测来取得表面 PASS。**

- **CLI 参数故障已单独关闭**：HF Job `6b00c8544fdc5ab3c55c02dd` 的 image 曾被错误解析为 `--attempts`，已于上一提交修正；它没有执行探针。
- **真正执行的第一份 CPU Job**：[`6b00ca46efaf5e14f4b3f8ca`](https://huggingface.co/jobs/adradar/6b00ca46efaf5e14f4b3f8ca) 使用 `python:3.11`、`cpu-basic` 和 Mac CLI `:ro` 输入、`:rw` 隔离输出，HF Inspect 为 `ERROR`（exit 2），SAFE 日志 `MOUNT_DIRECTORY_MODE_0700_HOLD`，`gpu_started=false`、`model_calls=0`、`weights_read=false`、`training_started=false`。检查在目录模式校验阶段停止，**没有执行**原子发布、拒绝覆盖或跨 Job 持久性验证。SAFE 没有记录挂载根的实际八进制权限，不能声称观察到了特定 mode。
- **官方挂载语义限制**：HF `hf-mount` 项目 [Best for / Not for](https://github.com/huggingface/hf-mount#best-for--not-for) 明确不支持跨节点文件锁和强一致性多写入用例；其 [mount options](https://github.com/huggingface/hf-mount#options) 说明远端对象不保存 POSIX 元数据，远端目录默认报告 `0755`、文件 `0644`，权限显示可能是挂载映射，不能当成安全持久账本的真实私有模式认证。**这解释了为什么 mode 需要核对，但不是对本 Job 实际 mode 的直接测量。** HF Jobs 的具体托管挂载实现仍未独立鉴定，故不据此推断更细的文件系统行为。
- **决策**：`HF_BUCKET_AS_PRODUCTION_ONE_SHOT_AUTHORIZATION_LEDGER=HOLD_UNPROVEN_CROSS_JOB_ATOMICITY`。即使未来某个 Bucket 单 Job 支持 `OutputManager.write_safe`，也不等于跨多个隔离 Job 的原子 compare-and-create、共享唯一性或崩溃恢复语义。**不要**尝试 `chmod 0700` 临时改变远端目录来绕过门禁，不修改 `DURABLE_CONSUMPTION_ROOT` 条件，不把 HF Bucket 的普通持久对象写入冒充一次性授权消耗。
- **主线下一依赖**：Owner/Provider 需选定能独立证明**全局原子唯一约束**、私有访问控制和跨 Job 崩溃持久性的授权账本承载（例如已审查、隔离的新 PostgreSQL 原子唯一键事务，或真实跨节点支持该语义的持久 POSIX 卷）；先对已有平台可复用能力做只读核对，禁止改写故事业务数据库或新建竞争的通用账本框架。原 `OutputManager` 继续用于与其能力相符的私有输出，当前 Gold48 正式推理保持 HOLD；需 Owner 对选定存储、密钥与 GPU 范围分别审批。

### PostgreSQL 现成能力只读复核（2026-11-21；不改生产库）

对既有 StoryForge Supabase 只查询 `pg_catalog` 的**表名/字段/唯一索引/约束/函数签名和权限**，未读取任何业务行或私有故事，未执行 DDL/DML。独立结果：

- 生产 PostgreSQL 已有基于 `UNIQUE` / 部分唯一索引的任务领取及防重复机制；部分 RPC 使用 `SECURITY DEFINER` 并向非授权角色禁用 `EXECUTE`，因此可以**复用数据库原子事务技术和已有权限审查模式**，不需开发新的通用分布式锁。
- 现有 `v2_generation_evidence_grants` 的 `purpose` CHECK **仅允许** `training-evidence`；`v2_generation_evidence_grant_operations` 的 `action` CHECK **仅允许** `issue/revoke`。**不能直接把 Gold48 GPU 推理消耗塞到这两张生产业务表、改约束或借训练证据授权**。目前未发现现成 Gold48 专用的持久消费关系/RPC。
- 当前只读 Connector **不可执行**所需的独立消费写入入口，也不能签发 Owner/Provider Ed25519；查到现有模式不等于实际 Gold48 执行能力已存在。连接账号曾被确认具有 BYPASSRLS，不得把它用于写入或读取受保护业务正文。
- **唯一下一步技术门槛**：由 Owner/平台维护者在**独立隔离权限域**审查一个每份签名回执 SHA 只能原子消耗一次的 PostgreSQL 唯一键事务入口（或另一个具有同等强保证的现成持久系统）；必须证明两个并发 Job 最多一个成功、故障后不能无授权重试、远端 Job 只能调用最小权限签收接口而不能重置或删除。尚无 Owner 储存/密钥批准时**不提交新 DDL、RPC 或 Python 后端**。既有 `gold48_runtime_gate.py` 目前使用**文件型** `DURABLE_CONSUMPTION_ROOT` 和 `OutputManager`；不得仅改文件路径或把数据库 INSERT 的配置字符串当成已接线，未来经批准再做最小原子消费适配，保留 Owner 签名、Provider 实测身份及现有 Worker。
- HF Bucket 原子账本探针已正式停止，不再重复前述 `0700`/RW 试错。**冻结输入/Adapter/Profile 不动；GPU、生成、训练及 Quality-v1 晋升仍 HOLD。**

### 历史双 Job 命令（当前暂停；不得直接继续执行）



**2026-11-21 Owner 首次提交的 CLI 兼容性纠正（优先遵循）：** Job [`6b00c8544fdc5ab3c55c02dd`](https://huggingface.co/jobs/adradar/6b00c8544fdc5ab3c55c02dd) 已在 HF Provider Inspect 中确认为 `ERROR`，`docker_image=--attempts`、`command` 以 `1 python:3.11` 开头，错误为 `docker.io/--attempts` 不是合法镜像。原 CLI 配置中的 `--attempts 1` 被当前 Mac 版 `hf jobs run` 误解析为镜像和命令。**探针尚未运行**，只读核对远端目标 `.gold48-atomic-20261121-v1.private.json` 不存在；此失败不是 Bucket RW、不支持原子写、权限不足或 OutputManager 的证据。下面两条命令均已删除当前 CLI 不兼容的 `--attempts 1`，保持 `--detach`、镜像 `python:3.11`、输入 RO、输出 RW、原 Probe ID 不变。再提交前应先确认 `hf jobs run --help` 中实际支持哪些选项；**不得为了单次尝试属性擅加未受支持的 flag**。没有确认服务端重试语义时，不将 CPU 探针的成功外推为正式 GPU 单次授权保证；正式 GPU 的一次性授权仍由独立 Owner 签名和持久消耗账本控制。不需要重传原有 Stage 或更换 Probe ID/路径。



**只验证前述未完成的原子发布及跨 Job 持久性，不再重复 HF Bucket 的普通 RW 通断测试。** 采用已经成功的 Owner Mac HF CLI `hf jobs run --namespace adradar` 路径，**不使用 ChatGPT Connector 提交 RW Job**。新增最薄入口 `scripts/r60_gold48_ledger_atomic_cpu_probe.py` 直接加载并验证仓库现有 `hf_runtime/outputs.py` Git Blob `69838b603b43663eaa12b1b1947ce14abad524bc`，调用原生 `OutputManager.write_safe`，不重新实现原子写算法。隔离 Probe 目录内只有公开合成标记；不读取或改动 Owner 私有签名账本、48 条文本、Adapter、模型或训练任务。

下方命令**须在 Owner Mac** 执行；每条真实 CPU Job 均独立提交一次，失败只报 HOLD、不改 image/flavor 重试。运行前检查当前分支的 Git 提交已含上述脚本，以及 HF CLI 已登录 `adradar`。务必使用**新的独立探针路径**，不要覆盖原有 `preflight` 其他文件。先用已确认可用的 `hf buckets cp` 上传两份公开源码及一份纯合成初始化文件，令 RO/RW 子目录实际存在：

```sh
umask 077
cd ~/workspace/storyforge
PROBE="hf://buckets/adradar/storyforge-training/preflight/r60/gold48-ledger-atomic-cpu-20261121-v1"
hf buckets cp scripts/r60_gold48_ledger_atomic_cpu_probe.py "$PROBE/input/probe.py"
hf buckets cp src/storyforge_dataset/hf_runtime/outputs.py "$PROBE/input/outputs.py"
printf '%s\n' 'SYNTHETIC_NO_OWNER_DATA' | hf buckets cp - "$PROBE/output/PROBE_ONLY.txt"
```

只把 `$PROBE/input` 以 `:ro` 挂到 `/input`；只把新建的 `$PROBE/output` 以 `:rw` 挂到**正式账本预计使用的容器路径**。第一份 Job：

```sh
ROOT="/mnt/storyforge-private/gold48-authorizations-spent"
hf jobs run --namespace adradar --name gold48-atomic-ledger-write-cpu \
  --flavor cpu-basic --timeout 10m --detach \
  -v "$PROBE/input:/input:ro" -v "$PROBE/output:$ROOT:rw" \
  python:3.11 -- python /input/probe.py --phase write \
  --root "$ROOT" --source /input/outputs.py \
  --probe-id gold48-atomic-20261121-v1
```

第一份 Job 日志须报告 `ATOMIC_CREATE_ONLY_CPU_PASS__SECOND_JOB_PENDING`，并证明 `direct_rw_mount_present=true`、`root_mode_0700=true`、`marker_mode_0600=true`、`atomic_create_only_verified=true`；如 Bucket FUSE 不能保持 0700、硬链接/原子无替换发布或目录 fsync，请保留精确 HOLD，**不得使用简单普通写文件的 PASS 替代**。第一份成功后，再执行与其**不同 Job ID** 的第二份：

```sh
hf jobs run --namespace adradar --name gold48-atomic-ledger-verify-cpu \
  --flavor cpu-basic --timeout 10m --detach \
  -v "$PROBE/input:/input:ro" -v "$PROBE/output:$ROOT:rw" \
  python:3.11 -- python /input/probe.py --phase verify \
  --root "$ROOT" --source /input/outputs.py \
  --probe-id gold48-atomic-20261121-v1
```

第二份日志须为 `ATOMIC_CREATE_ONLY_AND_CROSS_JOB_PERSISTENCE_CPU_PASS`，且 `marker_sha256` 与第一份一致、`cross_job_persistence_verified=true`。这是**独立合成存储验收**，与真实 Owner 账本的运行部署、独立签名信任锚、GPU Smoke / 192 条生成批准完全分离。不自动发第二份 Job、不自动重试；仅在第一份明确 PASS 后手动提交第二份。任何输出都不得包含私有数据。实际完成后回收两个 Job ID 和仅 SAFE 状态写入本手册，不修改已冻结 Profile。


### 2026-11-21 结果交付路径进一步简化（覆盖上方旧 CLI 说明）

按 [HF Jobs volumes 官方说明](https://huggingface.co/docs/hub/jobs-configuration#volumes)，Job 已原生支持独立 `:rw` Bucket 输出挂载，因此 **正式 Job 内不再调用 `hf buckets cp`、不需要注入 `HF_TOKEN`**。原 `deliver_gold48_private_result` 现在直接向准确挂载的 `/output` 写入 3 份私有对象，最后写 SHA256 manifest，并在同一挂载内回读 SHA。它要求 `/output` 在内核 mountinfo 中是**直接可写 FUSE 挂载**，拒绝用容器本地目录假冒远端交付；`/output` 的 POSIX mode **不是**授权锁条件。真正需要 `0700/0600 + fsync` 的只是 Job 内本地生成原件。

Mac 端在提交前必须核对结果前缀 `experiments/r60-gold48/outputs/<run_id>/` 为空，确认输入只读、唯一 Owner Mac、无自动重试；正式 Job 成功后，**由 Owner Mac 独立 `hf buckets cp` 下载四份结果并重算 SHA 与 48 条内容结构**，不能把 Job 内本地 FUSE 回读作为最终验收。此前手册关于“Job 内 `hf buckets cp` 上传并下载校验”的说法是历史方案，以本段为准。未签名/未批准 GPU 时仍保持 HOLD。


### 2026-11-21 Owner Mac 独立下载核验入口（代码/合成测试；未执行真实下载）

已有 `scripts/r60_gold48_gpu_result_audit.py` 复用原 `r60_common2_wrapped_hf_cli.remote_set` 的 HF Bucket 全量文件集检查、原 `InputManager` 的 O_NOFOLLOW/SHA 读取，以及 `gold48_contract_bridge._read_existing_gold48_output` 的 48 条逐条数据结构/Seed/token 上限检查；它**不新建生成器、不提交 HF Job、不调用模型**。

Owner Mac 只有在真实 Job 完成且拿到四份输出后执行（`--owner-download-root` 是已存在的本地 mode 0700 私有目录，`--frozen-input-manifest` 是已有 Owner 私有 0600 输入清单）：

```sh
PYTHONPATH="$PWD/src:$PWD/scripts" python scripts/r60_gold48_gpu_result_audit.py \
  --run-id "<Owner 本次单臂已批准的 Run ID>" \
  --model-role base \
  --owner-download-root "$HOME/.local/share/storyforge/r60/private/gold48-owner-results" \
  --frozen-input-manifest "<已有 Owner 0600 输入 Manifest 路径>"
```

该入口先只读查验远端前缀**恰好**有 4 份既定文件，随后一次性创建本地 `0700` 下载子目录，逐个下载、转为 `0600`，核对 manifest 的全部文件 SHA、文件大小与次序，再比对 48 条生成内容、输入 SHA、Provider image SHA、Owner receipt 摘要等私有 Sidecar/launch 字段。SAFE 结果 `OWNER_GOLD48_RESULT_BYTES_AUDITED__SIGNATURE_REVIEW_PENDING` **不是**独立核验 Ed25519 签名，不表示 Quality-v1 已准入。下载目录已存在、远端不完整、回执不一致或下载失败均 HOLD；没有自动重试或任何远端写操作。此入口待正式 GPU 运行后由 Owner Mac 使用真实私有数据验收，不得预先操作未来 Run ID。
