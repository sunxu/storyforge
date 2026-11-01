# R58 G2 — 冻结三目标对照 Owner 历史切流声明的时间窗口（待 Owner 本机执行）

日期：2026-11-01；工作分支 `r58/roleplay-sft-skill-v01`，Draft PR #7。

## 已完成，无需 Owner 重复的 GitHub 证据

上一轮 Owner 本机 SAFE 回执：原始冻结 3 目标、12 项指纹重校通过；目标的 UTC 粗日期分布为 2026-10-28/29 两条、2026-10-30 或以后 1 条；旧区间全零。Owner 回执原样证据与局限已存 `docs/evidence/R58_G2_FROZEN_THREE_TARGET_RELEASE_DATE_OWNER_SAFE_20261101.json`。本对话未收到此前 9 个合成测试的执行摘要，不能额外记为测试 PASS。

GitHub 历史发布源码：已有 13 个 Git commit + 本轮新增 2 个；新增 2 个 Git commit 有效，八个固定聊天源码 Git Blob 与当前固定 PIN 相同。历史文档还记录四个 2026-10-28/29 的发布切流声称时间，以及 2026-10-28 一次**不重新部署源码**的动态模型目录 revision 9→10 变更。详见 `docs/evidence/R58_G2_ROLEPLAY_LATE_OCT_ADDITIONAL_RELEASE_AND_RUNTIME_EVENTS_SAFE_20261101.json`。

**注意：这些时间是 Owner Git 文档记录的历史事件，不是独立认证的不可变部署账本。** `sunxu/RolePlay` 的最新 main Git HEAD 也不等于三条历史目标实际请求时的服务器版本；受其他后端、回滚、配置和时差影响，不得通过日期相近宣布 G2 PASS。

## 仅需运行一次的新工具

Owner 如授权使用本机**第一次冻结**的 Priority3 PRIVATE 目录作较粗的日期区间比较，可在已切换正确分支的本机仓库执行：

```bash
git pull --ff-only
python3 -m unittest discover -s experiments/r58_roleplay_replay \
  -p 'test_r58_g2_frozen_target_cutover_window_triage_safe_20261101.py' -v

python3 experiments/r58_roleplay_replay/r58_g2_frozen_target_cutover_window_triage_safe_20261101.py \
  --private-dir "$HOME/.storyforge-r58-private/priority3_source_20261030_first_capture"
```

**隐私边界：** 第二条 Python 脚本将通过已有 `fixed_targets()` 验证冻结三目标、0600/0700 文件权限和 12 个内容指纹，所以会在本机内存中读取并解析完整的 PRIVATE JSONL（其中包含用户对话、故事、回复正文）。只提取三个 `target_created_at` 做比较；不会上传、打印真实时刻、真实 ID、内容、hash、PRIVATE 路径或逐目标映射。输出最多是 7 个匿名 `window_0...window_6` 计数，但这些汇总也会比此前按日计数更细；**执行前由 Owner 自行决定是否同意此进一步的时间分组**。所有文件均只读，无数据库、网络、HF 或训练行为。

事件顺序与固定内部边界（全部是未独立认证的 Owner 声明）：

| 输出窗口 | 相对于固定声明的 UTC 边界 |
| --- | --- |
| `window_0` | 早于 2026-10-28 01:36:59 |
| `window_1` | 从 10-28 01:36:59 至 07:28:16 |
| `window_2` | 从 10-28 07:28:16 至 08:57:00 |
| `window_3` | 从 10-28 08:57:00 至 10-29 01:02:47 |
| `window_4` | 从 10-29 01:02:47 至 04:07:06 |
| `window_5` | 从 10-29 04:07:06 至 10-30 00:00:00 |
| `window_6` | 10-30 00:00:00 以后 |

上列半开时间区间内的参考事件不代表整个区间没有其他部署、没有回滚，也没有声明固定目标的实际后端；window_6 特别表示**尚未认证的后续部署历史**，不是自动归属 10 月 29 日最后一个提交。10 月 28 日 08:57 的模型目录更改不等于本案当时使用了受更改影响的具体模型。

如拒绝授权进一步时间分组，可以只运行 9 项合成测试并反馈 `NOT_AUTHORIZED`；不能靠当前 G2 日期分布猜分组。若返回 HOLD（退出 42），不重复原始 SQL，不重建或覆盖冻结源包，不放宽权限或略过 SHA 校验。

需要回传：9 项测试的 PASS/FAIL 摘要，及第二条命令输出的 SAFE JSON（不额外粘贴 PRIVATE 信息）。脚本执行本身并不证明原始 Provider 字节、历史部署、实际后端或请求 ID 的因果绑定。

`G1=HOLD`、`G2=HOLD`、`G3=NOT_STARTED`；Train/Validation/Teacher=0，`expansion_allowed=false`。无 HF Jobs，无主分支合并，无数据库与生产操作。
