# Gold48 Owner 本地：已冻结输入物化、Adapter 签收、单独签名授权

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
