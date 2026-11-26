# StoryForge R58 — 现存历史部署回执的离线区间核验（SAFE）

日期：2026-10-31。只允许用于固定三目标、现存 Owner 私有元数据。不取得原始材料不得创建“已验证发布区间”。**G1/G2 仍 HOLD，训练准入 0。**

## 本轮新增

- `skills/storyforge-roleplay-sft/v02/r58_deployment_interval_audit.py`：离线校验三个 Owner 已冻结目标时间与最多 96 个部署区间之间的**结构**关系；不查询线上服务，不访问 HF/Supabase、Provider 请求、故事正文或模型权重。
- `skills/storyforge-roleplay-sft/v02/test_r58_deployment_interval_audit.py`：19 项虚构数据单元测试，在隔离环境通过，GitHub Git blob 已与测试代码逐字节对照。
- 复用 `r58_g1_scope_reconcile.read_private`：仅接受 `~/.storyforge-r58-private/` 下 owner-private 0700 目录中的 0600 文件，禁用 symlink、`..` 路径穿越和不安全权限；只向 stdout 输出计数，不打印原始 SHA/时间/服务器/请求标识。

## 为什么这项工具只能检查结构，不能宣布历史部署 PASS

冻结的 `sunxu/RolePlay@e9fe29c42434caeb0bac5acc91845ab4741ecb2b` 部署逻辑有成功部署后 `DEPLOYED_SHA`，但它是可覆盖文件；`workflow_run_id` 在部署脚本中被写为常量 `manual-local-build`；旧 staging 可以被轮换清理。详见已提交的 `R58_G2_DEPLOYMENT_SHA_SOURCE_PROVENANCE_SAFE_20261031.json`。

本工具**不接入可独立认证的历史部署档案系统**。从文件中读到的 SHA256 和回执类型都只是一份 Owner 本地申报，能防止篡改/格式漂移，却不能证明该回执历史存在、当时确实切流，或者目标时间/目标所经后端真实准确。因此：

- 即使 `structurally_covered_target_count=3`、`claimed_source_pin_target_count=3`，仍 **`target_time_deployed_sha_proven=false`**；
- 即使区间记录自称成功切流与下一次切流，并有两个不相同的 SHA256，也不证明原始记录签名/出处、时序、回滚正确；
- 非某后端的 target、`UNKNOWN` 后端、没有足够历史边界的区间，不算有效结构覆盖；
- `g1_clearance=g2_clearance=HOLD`，Train/Validation/Teacher=0；`gate/freeze` 仍不执行。

## 私有输入契约：**只能整理已有经授权的部署元数据**

默认路径仅作为预留（文件**不要求存在**）：

`~/.storyforge-r58-private/round1_pilot_20261030/g2_existing_deployment_intervals_PRIVATE.json`

顶层必须仅有 `schema`、`source_pin`、`frozen_target_claims`、`deployment_intervals`。固定：

`schema=r58_g2_private_deployment_interval_manifest_v1`，`source_pin=e9fe29c42434caeb0bac5acc91845ab4741ecb2b`。

每个 `frozen_target_claims` 元素只能有 `generated_at_utc`（UTC 秒精度 `YYYY-MM-DDTHH:MM:SSZ`）及 `serving_backend`。**严格三项、升序、时间不同**，不得从本次聊天推算或用当前新数据补造；未知后端填 `UNKNOWN`，合法后端仅 `PRIMARY` / `V2_REPLICA` / `FALLBACK` / `MIGRATION` / `UNKNOWN`。

每个 `deployment_intervals`（最多 96 个）严格包含：

| 字段 | 说明 |
|---|---|
| `serving_backend` | 已知后端，不接受 `UNKNOWN` |
| `deploy_sha` | 40 位小写完整提交 SHA，不能用公开 8 位 Build ID |
| `active_from_utc` / `active_until_utc` | UTC 秒精度、严格半开区间 `[from, until)` |
| `activation_receipt_type` | `SUCCESS_CUTOVER_RECEIPT_REPORTED` / `ARCHIVED_STAGE_ONLY` / `CURRENT_DEPLOYED_SHA_ONLY` / `UNKNOWN` |
| `termination_receipt_type` | `NEXT_CUTOVER_RECEIPT_REPORTED` / `ROLLBACK_RECEIPT_REPORTED` / `UNKNOWN` |
| `activation_receipt_sha256` / `termination_receipt_sha256` | 已存在原始元数据工件**内容**的 SHA256，64 位小写十六进制；同一记录两端必须不同，但**不是签名和真实性证明** |

区间按 `serving_backend` 名称、`active_from_utc` 升序；同一后端区间不得重叠。若不存在独立保留的原始记录，**不要生成伪造的日期/哈希**，也不要把当前 `DEPLOYED_SHA` 强行解释成有起止边界的历史区间。

**不允许放入**用户/会话/消息 ID、私有 Job ID、密钥、服务器登录信息、IP、原始日志、故事文段、Provider payload 或 R50 数据。请勿上传 PRIVATE JSON。

## Owner Mac：只读操作

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only

python3 -m unittest discover \
  -s skills/storyforge-roleplay-sft/v02 -p 'test_*.py' -q
ruff check skills/storyforge-roleplay-sft/v02/ --statistics && echo RUFF_V02_PASS

ROOT="$HOME/.storyforge-r58-private/round1_pilot_20261030"
PRIVATE="$ROOT/g2_existing_deployment_intervals_PRIVATE.json"
if [ -f "$PRIVATE" ] && [ ! -L "$PRIVATE" ]; then
  python3 skills/storyforge-roleplay-sft/v02/r58_deployment_interval_audit.py \
    --private-manifest "$PRIVATE"
else
  echo "HOLD: no existing authorized historical deployment interval metadata"
fi
```

此前 Owner Mac 已报告 v0.2 **61/61 PASS 与 Ruff PASS**；本轮新增 19 项，故最新源码**预期 80 项**，不能用旧的 61 项证明新代码通过。没有现存 PRIVATE manifest 时，只需回传 80 项测试和 Ruff 输出，不要求创建该文件。

成功时 SAFE 输出状态 `PRIVATE_DEPLOYMENT_INTERVALS_STRUCTURALLY_CHECKED__HISTORICAL_SOURCE_UNAUTHENTICATED_HOLD`，退出 0 **只表示结构可解析**；失败退出 42，stderr 固定不泄密。永不将该状态提升为 G2 PASS。

若未来确有可信历史发布归档，必须另行执行证据来源认证、生产切流/回滚区间连续性与目标请求实例关联核验，仍须独立解决目标消息↔request_id 和 Provider 原始请求字节阻塞。
