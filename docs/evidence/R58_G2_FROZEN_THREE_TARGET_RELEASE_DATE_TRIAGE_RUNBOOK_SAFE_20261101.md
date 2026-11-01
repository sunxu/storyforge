# R58 G2 — 冻结三案与历史发布文档的日期范围预检（Owner 可选）

日期：2026-11-01。目标分支：`r58/roleplay-sft-skill-v01`，Draft PR #7。

## 已独立完成：GitHub 代码与发布文档对账

只读核查了 `sunxu/RolePlay@e9fe29c42434caeb0bac5acc91845ab4741ecb2b` 已归档的 2026-10 部署文档：13 个被历史记录引用的完整 Git SHA 均可从 GitHub 读取对应 commit 对象。按八个固定聊天相关路径对比 Blob 身份：7 个旧版本中 chat route + message service 与 PIN 不同；4 个只有 message service 不同；2 个八路径全部相同。详见 `docs/evidence/R58_G2_ROLEPLAY_OCT_RELEASE_CODE_BLOB_PARITY_SAFE_20261101.json`。

**严格局限：**Git commit 存在 ≠ 实际生产发布成功；Owner 发布记录 ≠ 不可变切流日志；八路径字节相同 ≠ 全部依赖、模型调用及 Provider 请求字节相同；文档日期排列不能被自动填充为无间隙的生产服务时间线。不能把任何历史记录直接当作三个冻结 target 在当时承载的服务版本。

## 为什么需要 Owner 本机一步操作

现有 GitHub SAFE 记录没有三个冻结目标的具体 `target_created_at`。为了知道这批 10 月历史发布记录是否属于相关时间范围，必须从**第一次已经固定的本地三条源记录**读取时刻，而不能再查数据库或从邻近 request metrics 猜时间。

准备好的工具：`experiments/r58_roleplay_replay/r58_g2_frozen_target_release_date_triage_safe_20261101.py`；测试：`experiments/r58_roleplay_replay/test_r58_g2_frozen_target_release_date_triage_safe_20261101.py`（新增 9 项纯合成测试，尚待 Owner Mac 执行）。

**隐私与权限说明：**工具通过已有的 `verify_priority3_private.verify()` 与 `audit_priority3_request_timeline.fixed_targets()` 对被冻结的 JSONL、manifest、0600/0700 权限及 12 项内容指纹进行验证。因此**会在 Owner Mac 内存中读取、解析三条原始 PRIVATE JSONL，包括其中的故事/用户/Assistant 正文字段**；不在 STDOUT 输出内容、时间戳、路径、story ID、message ID、request ID、SHA 或逐案与日期的映射；不写文件、不连接生产数据库，不访问 HF、R50 或网络。只限原有固定目录，拒绝新数据导出与其他目录。

日期计数按照 UTC **日界**分为五个粗窗口：10 月 9 日之前、10 月 9–17 日、10 月 18–27 日、10 月 28–29 日、10 月 30 日及之后。它们只是对已存在的 Git 文档做粗略相关性筛选，并**不**表示当时使用的部署版本，也不标记任何 byte-exact PASS。

## 需要 Owner 决定是否运行

如确认允许本机上述只读范围，在已经位于 R58 分支、配置好上游的工作区执行：

```bash
git pull --ff-only
python3 -m unittest discover -s experiments/r58_roleplay_replay \
  -p 'test_r58_g2_frozen_target_release_date_triage_safe_20261101.py' -v

python3 experiments/r58_roleplay_replay/r58_g2_frozen_target_release_date_triage_safe_20261101.py \
  --private-dir "$HOME/.storyforge-r58-private/priority3_source_20261030_first_capture"
```

若用户**不同意读取完整冻结源包**，请仅运行测试，不执行最后一条命令，并答复 `NOT_AUTHORIZED`。无需上传原始数据、完整私有路径、终端 traceback 或含故事内容的日志。

只向本对话返回 unittest 通过数量、以及检查器 STDOUT 的固定 SAFE JSON。若返回退出码 42，保持 HOLD，不删除、不覆盖或重新导出固定源包；不要通过跳过指纹/权限检查来强行生成日期统计。

## 后续门禁

成功仅表明三条冻结目标的时间**分别落入哪些粗日期区间的聚合计数**。如这批 10 月文件完全不相关，继续寻找其他经认证的历史发布资料；如日期相符，仍要先获得可信成功切流/回滚时间、实际目标服务端、同一请求因果标识、原始 Provider 输入字节等证明。不得把日期接近、旧发布文档、六/七/八个 Git Blob 相同转换成真实部署 PASS。

`G1=HOLD`、`G2=HOLD`、`G3=NOT_STARTED`；Train/Validation/Teacher=0、`expansion_allowed=false`。不重开 R50、不启动 HF Job、不进入 G3、不合并 main。
