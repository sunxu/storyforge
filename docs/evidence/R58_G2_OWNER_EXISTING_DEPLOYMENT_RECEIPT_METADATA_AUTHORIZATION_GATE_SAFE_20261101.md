# R58 G2 — 现存历史部署回执的元数据核验：等待 Owner 授权

日期：2026-11-01；Draft PR #7，分支 `r58/roleplay-sft-skill-v01`。

## 最新固定证据

三条原冻结目标的 Owner SAFE 粗窗口回执已归档：`window_1=1`、`window_5=1`、`window_6=1`，原先 12 项逐案内容指纹均由 Owner Mac 复核；不能输出具体目标时间与身份。见 `R58_G2_FROZEN_TARGET_CUTOVER_OWNER_AGGREGATE_SAFE_20261101.json`。

GitHub 只读检查将历史被报告的发布 commit 候选扩大至 15 个，另确认 `release/husband-round2-20261030` 等现存分支的代码身份。但 Git 分支、Commit、GitHub Actions 空结果和 Owner 发布报告，都不是目标时刻真实部署 SHA 或原始 Provider 请求字节证据。参见 `R58_G2_RELEASE_RECEIPT_RECOVERY_SOURCE_CONTRACT_SAFE_20261101.json`。

## 发布器源码约束

固定 `sunxu/RolePlay@e9fe29c42434caeb0bac5acc91845ab4741ecb2b` 中，`scripts/deploy-production-local.ps1` 调用 `ops/deploy/deploy-standalone-release.sh`。成功后后者将含 `sha/ref/actor/deployed_at/workflow_run_id/stage_dir` 的部署标记写入当前 `DEPLOYED_SHA`，将 `state=succeeded`、`sha=...` 写入暂存区 `deploy.status`。

已确认 2026-10-28/29 的四个候选发布 Git Commit 的发布入口、原子发布器、回滚库和保留器源码 Blob 与固定 PIN 相同。**但当前 `DEPLOYED_SHA` 在后续成功发布时覆盖旧值，历史 `deploy.status` 不包含可靠的成功切流时间，仅其目录名包含部署启动时间；服务端或 Owner 保留的原始控制日志/已存后验回执才可能补强真实时间线。**

仓库 `ops/deploy/deploy-retention.sh` 默认保留最近 3 个 staging；其他目录若同时满足比最近 3 个更旧、且年龄超过 604800 秒（7 天）才可能被删除。实际留存仍未知。禁止为了通过核验恢复/修改/重建历史回执。

## 授权前停止，不访问 VPS

当前没有 Owner 授权读取生产 VPS 的历史发布元数据。**本次未对 VPS 执行任何操作。** 先询问 Owner 是否允许在自己的 Mac 上，经现有 SSH 配置，**只读**列出现存 `/tmp/deploy-*/deploy.status` 的允许字段及当前部署标记的白名单字段，以 SAFE 聚合形式检查哪些候选发布有残留。若 Owner 持有原始成功部署控制日志，须另行授权元数据专用读取；不得默认扫描日志、PM2、进程环境、客户请求、数据库或 Provider 记录。

授权时的限定条件：

- 只读；不重启服务，不触发部署、`nginx -T`、健康检查、脚本运行或文件系统修改；遵守受控目录权限与无符号链接；
- 不向聊天/GitHub输出服务器地址、账号、私有路径、真实日志、部署 actor、访问令牌、原始请求标识、用户或故事内容；
- 即使找到 `state=succeeded` 也只能称为“保留的历史部署事务标记”；若无可认证的时钟/切流及无回滚序列，仍不能提升为目标实际部署 SHA；
- 如元数据文件已过期或不存在，明确记录 `HISTORICAL_RELEASE_RECEIPT_UNAVAILABLE__G2_HOLD`，不另起时间猜测。

下次仅需 Owner 答复是否授权该**既存发布元数据的本地只读查询**；不需要提供 SSH 凭据或真实路径。本轮无新命令、新 HF Job 或 PRIVATE 故事读取。

**全部门禁**：`G1=HOLD`、`G2=HOLD`、`G3=NOT_STARTED`、Train/Validation/Teacher=0，`expansion_allowed=false`；不合并主分支，不修改 Skill 或 Dataset。
