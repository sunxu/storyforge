# R58 G2 — 历史部署 SHA 的可验证证据与恢复顺序（SAFE）

日期：2026-10-31。目标：固定三条历史 RolePlay 目标消息的 **target-time 实际部署版本**；不是证明其 Provider 消息字节，更不能代替 target↔request_id 直接映射。

## 本轮已从冻结源码核实（非线上运行证明）

源码固定：`sunxu/RolePlay@e9fe29c42434caeb0bac5acc91845ab4741ecb2b`。完整源文件 blob SHA、行号和字段见 `R58_G2_DEPLOYMENT_SHA_SOURCE_PROVENANCE_SAFE_20261031.json`。

- GitHub CI `.github/workflows/deploy.yml` 构建时将 `ROLEPLAY_BUILD_SHA` 设为 `github.sha`，远程部署脚本以完整 SHA 调用；实际是否运行、成功、在哪个生产后端生效，需要**另外验证**。
- `ops/deploy/deploy-standalone-release.sh` 在成功部署阶段写 `DEPLOYED_SHA`：`sha`、`ref`、`actor`、`deployed_at`、`workflow_run_id`、`stage_dir`。这是**可变的当前状态文件**，不是逐次追加的历史部署账本。
- 在该固定源码中 `workflow_run_id` 是字面量 `manual-local-build`，**不能**当作真实 GitHub Actions Run ID；尤其不能因 GitHub Actions 入口运行就将其误认作 GH 运行号。
- 部署暂存 `/tmp/deploy-.../deploy.status` 若尚存，包含 `state=succeeded` 和 `sha`，但并不自带目标消息时间、生产流量路由或实际 Provider payload 证明。暂存清理保留参数默认最近 **3** 份、超过 **604800 秒（7 天）** 的旧目录可能被删除；因此“未发现目录”不能证明历史上没有部署。
- `scripts/deploy-production-local.ps1` 在部署时比对 `DEPLOYED_SHA` 的完整 SHA 和公开 build-version 的 **8 位 SHA 前缀**。只靠公开前缀无法替代完整历史部署 SHA。
- RolePlay 可以存在主要部署、迁移 VPS 与回滚等多路径；必须证明历史目标实际经过哪个后端/入口，**不能把某个环境曾部署的版本当作全部请求均使用的版本**。

## 先查已经存在的可信发布回执，不扫描线上消息

按以下证据等级顺序，由有权访问部署记录的 Owner 核对（本轮助手**没有** SSH/生产环境权限，未执行任何命令）：

1. **最优：**原始不可变发布审计或集中日志，包含完整 40 位提交 SHA、成功切流/回滚时间、实际服务端/路由、证据来源身份，能形成覆盖三条已冻结目标请求时刻的连续版本区间。
2. **局部：**已有成功部署记录与下一次部署/回滚时间配对，能证明期间生产流量确由对应版本服务；单条成功记录若缺后续切换历史，仍是 `HOLD`。
3. **线索：**目前服务器的 `DEPLOYED_SHA`、`.deployment-window`、现存暂存 `deploy.status`、旧制品清单、GitHub Actions 工作流成功记录等；分别说明某时执行过什么，不能单独证明**固定历史请求**实际使用的部署版本。
4. **无记录：**明确 `NOT_AVAILABLE`，不能用当下 `main`、固定源码 PIN 或其他时间邻近替代。

注意：读取生产运行日志、环境变量、服务器本地目录、私有配置或原始消息仍属于另一个敏感访问范围；未经明确授权不要自动扫描。优先已经导出的 **仅包含部署元数据的既存回执**。如日志可能含凭据、故事片段、用户与请求 ID，不得向聊天或 GitHub 上传。

## 如 Owner 已持有历史发布证据，仅返回 SAFE 结果

每一条固定历史目标只汇总如下**布尔/枚举**，不回传目标 UUID、私有请求 ID、真实时间戳或服务器路径：

| SAFE 字段 | 允许取值 | 条件 |
|---|---|---|
| `pinned_roleplay_source_sha` | `EXACT_MATCH` / `DIFFERENT` / `UNVERIFIED` | 实际部署 SHA 与固定源码严格 40 位一致 |
| `successful_deploy_receipt_present` | bool | 有认证成功切换记录，不仅有构建/排队 |
| `deployment_rollback_interval_complete` | bool | 明确后续部署和回滚边界 |
| `target_time_interval_covered` | bool | 冻结目标实际生成时间处在被认证区间内 |
| `target_serving_backend_identified` | bool | 证明实际请求所走服务端/路由 |
| `historical_deploy_verdict` | `SOURCE_ONLY` / `PARTIAL` / `DIRECTLY_BOUND` | 只有多个独立条件同时满足才可记录 DIRECTLY_BOUND，但仍不改变 Provider 请求字节门禁 |

**禁止**以 Owner 自称 `DIRECTLY_BOUND`、文件哈希相等、8 位公开 Build ID、某次 GitHub CI PASS 或当前 `DEPLOYED_SHA` 单独放行历史请求。真实性、完整历史区间、实际后端与目标时间必须分别核对。新的证据复核仅在完成授权和来源认证后进行；没有历史材料时保留 `G2=HOLD`。

本阶段不要求重新测试已通过的 Skill v0.2 61 项；不启动 HF Job，不访问 R50，不读取生产用户消息，不改动 Skill v0.1 或训练队列。**G1/G2=HOLD；Train/Validation/Teacher=0；PR #7 继续 Draft**。
