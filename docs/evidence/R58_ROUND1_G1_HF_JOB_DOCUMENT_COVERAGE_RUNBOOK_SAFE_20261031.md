# R58 G1 — HF 历史 Job 与冻结 Git SAFE 文档引用覆盖率（2026-10-31）

**范围：只读 / 不启动 HF Job / 不读取命令、环境变量、日志或训练数据 / 不触碰 R50 / 不更新 PRIVATE 账本。**

## 已有 Owner 回执

Owner Mac：`Ran 188 tests ... OK`；`HfApi.list_jobs(namespace='adradar')` 返回 69 Job（COMPLETED 36、ERROR 31、CANCELED 2）。已经记录的五个发生参数更新的训练或 smoke/capacity Job 均找到，均为 COMPLETED；其他 64 个未分类。不能把 ERROR/CANCELED 自动排除为非训练任务，不能把 HF Jobs 列表误称完整历史：可能有被删除任务、其他命名空间、保留期差异或在其他运行平台执行的训练。

先前的六个冻结 split 合计 184 个训练/验证数据位置，27 个去重故事 UUID，并不包含所有可能的历史 Job 运行数据。R04 150 - Gold108 108 所剩两个世界与当前剩余四个候选 UUID 零交集，已经由冻结 06–15 编号目录证实为历史编号 07/11。以上只用于当前已知来源排除，不是全部保护来源准入。

## 本轮目的和方法

新增 `experiments/r58_round1/check_hf_job_documentation_coverage.py`：

1. 在 Owner Mac 通过本地现有 HF 身份以只读 `HfApi.list_jobs(namespace=...)` 枚举 Job，**仅访问 `id` 和 `status.stage`**，不读取 `command`、`arguments`、`environment` 或 `secrets`；
2. 只扫描当前 Git `HEAD` 冻结的受控文档 Git blob：`docs/HF_RUN_REGISTRY.md`、`docs/evidence/`、`docs/handoffs/` 下 `.md` / `.json`。使用 `git ls-tree` + `git cat-file`，**不读取工作区未跟踪文件、外部私有根目录或 R50 保护正文**。文件数、大小、类型有上限，任何错误直接 HOLD；
3. 以严格 24 字节十六进制 Job ID 形态做精确引用匹配，只对 64 个未知 Job 汇总：有仓库证据文档引用、无仓库证据文档引用，以及按 Job 状态的两个聚合子组；
4. **有文档引用不代表任务无训练，缺文档引用也不代表任务有训练**。文档可能仅记录一个失败任务或旁证。没有尝试解析命令，更没有把任务类型升级为已认证；所有历史运行的完整性和远程实际输入 SHA256 仍为 false。

所有输出仅 SAFE 计数，不包含 Job ID、故事 UUID、私有路径、原始文档内容、训练输入、HF token，也不写私有账本。

## Mac 执行

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only

python3 -m unittest discover \
  -s experiments/r58_round1 -p 'test_*.py' -q

python3 experiments/r58_round1/check_hf_job_documentation_coverage.py \
  --repo-root "$PWD" --namespace adradar
```

新模块 **22/22 合成回归 PASS**，包括临时真实 Git 仓库端到端的只扫描 HEAD 跟踪文档测试；预期原有 188 项 + 22 项 = **210**，以 Owner Mac 为准。完成后只返回 SAFE JSON 和测试摘要。

## 后续门禁

分类仅限文档引用：`all_job_roles_proven=false`、`all_historical_jobs_including_deleted_other_namespaces_proven_complete=false`、`remote_trainer_primary_input_bytes_verified=false`、`all_actual_sft_runs_and_input_sources_proven_complete=false`、`source_registry_complete=false`、`g1_clearance=HOLD`、Train/Validation/Teacher=0、`expansion_allowed=false`。

要真正证明排除全集，需要对可能发生参数更新的每个历史 Job 确认真实运行数据/角色和输入 SHA256（不混淆 train 与 validation），并获得历史清单覆盖边界声明；不能凭一次 `list_jobs` 的 69 个结果替代这些证据。PR #7 继续 Draft；不训练、不扩样、不自动收费。
