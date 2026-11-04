# R60 CPU Volume Smoke Runner — Implementation Evidence

日期：2026-11-04  
PR：#12  
分支：`r60/hf-jobs-runtime`

## 1. 本轮实现

新增：
- `experiments/r60_hf_runtime/r60_cpu_smoke.py`：Owner-invoked synthetic-only HF managed-volume smoke adapter。
- `tests/test_r60_cpu_volume_smoke.py`：10 项合成测试。
- R60 CI 纳入 runner Ruff、compile 和独立 smoke adapter pytest 门禁。

Smoke adapter 在 Runtime 核心包之外；不改变七个 Runtime 模块的公共 API，不向 Runtime core 增加 HF API 或网络依赖。

## 2. 验收逻辑

输入：
- 显式指定 input root 和单一文件名。
- 必须提供预期 SHA256。
- JSONL 仅接受精确字段 `schema`、`case`。
- schema 必须为 `storyforge-r60-smoke-input-v1`。
- case 必须按序为 `synthetic-001` 至 `synthetic-NNN`。
- 最大记录数 100，默认最大输入字节 65536。

RO 验证：
- 读取 `statvfs` 的只读挂载标志。
- 使用随机唯一文件名进行 O_EXCL / O_NOFOLLOW 创建探针。
- 必须同时观察到 mount read-only flag 和创建被拒绝；仅有目录权限拒绝不能冒充 RO 证据。
- 若意外创建成功，仅尝试删除本次创建且 inode 身份匹配的探针文件；不做递归清理。

RW 验证：
- 对预先存在的 output root 执行真实 create/write/fsync/remove probe。
- 使用 Runtime `OutputManager.write_safe` 以 create-only 方式写入固定 SAFE 回执。
- 通过 SHA256 readback 验证落盘字节。
- 已存在目标文件会失败，不覆盖、不重试。

SAFE 输出：
- Schema：`storyforge-r60-hf-volume-smoke-v1`
- 固定文件名：`R60_CPU_VOLUME_SMOKE_SAFE.json`
- 只包含 SHA256、字节数、合成记录数、allowlisted 平台信息、状态与检查结果。
- 不输出输入内容、任意路径、环境转储、异常文本或凭据。
- 固定声明 `private_values_emitted=false`、`gpu_started=false`、`training_performed=false`。

## 3. 本地 CLI 形式

在仓库根目录、Runtime 包已安装（例如 editable install）的环境中：

```bash
python experiments/r60_hf_runtime/r60_cpu_smoke.py \
  --input-root /input \
  --input-name synthetic.jsonl \
  --output-root /results \
  --expected-sha256 <64位小写SHA256> \
  --expected-records 3
```

这是 CLI 参数示例，不代表本地目录就是 HF 实际挂载点。远端必须使用 HF Job 中明确配置的挂载路径。输入文件须由 Owner 预先生成并核对 SHA256；不得使用任何 Gold/R50/R59 数据。

## 4. CI 验证

最终通过的 PR HEAD：
`2f4030115e90b95c36d3aca2bd2b0d25aa62ca4a`

R60 HF Runtime CI：
- Run：`41799784104`
- Job：`126472439622`
- Ubuntu GitHub-hosted runner：PASS
- Ruff：PASS
- Python compile：PASS
- Runtime suite：28 passed
- CPU volume smoke adapter：10 passed
- token_preflight core regression：OK
- Runtime dependency boundary：PASS

Existing repository CI：
- Run：`41799790796`
- Job：`126472460692`
- 全仓测试：`659 passed, 5 skipped, 24 subtests passed`
- Evidence integrity：`V01_LOCAL_EVIDENCE_INTEGRITY_PASS__EXTERNAL_LIMITS_RETAINED`

## 5. 尚未完成 / 不可越权

- 没有创建 HF bucket。
- 没有提交 HF CPU Job。
- 没有验证 HF managed Volume 的真实 RO/RW 行为。
- 没有验证 SAFE receipt 从 HF Volume 同步回本地后的 SHA256。
- 没有 GPU、模型下载、推理或训练。
- 没有访问 Gold/R50/R59 冻结私有数据。

提交 HF CPU Smoke 前，仍须 Owner 在当时明确授权；且必须使用独立的临时测试存储，严禁复用 `storyforge-training`。

## 6. 状态

`R60_CPU_SMOKE_RUNNER_IMPLEMENTED__CI_PASS__HF_MANAGED_VOLUME_NOT_RUN`
