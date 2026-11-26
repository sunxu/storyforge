# R58 G1 — 五类元数据来源可用性与完整性检查操作书（SAFE）

**日期**：2026-10-30。目的不是直接评估训练质量或宣告 G1 PASS，而是判断**五类必要索引是否真的存在、从哪里生成、覆盖谁、能否与同一世界命名空间核对**。不得读取 R50 保护题、私有故事正文、任何聊天文本；不得上传真实 ID、来源文件名、私有 hash/索引至 GitHub/聊天。

## A. 四级证据状态（分开判断）

| Level | 条件 | 正确解释 |
|---|---|---|
| L0 `MISSING` | 没有可定位的元数据专用源文件或可信来源回执 | 缺证据，HOLD；不是没有重叠 |
| L1 `PRESENT_UNVERIFIED` | 路径存在或只有 count-only SAFE 回执 | 仅存在/统计，不代表来源真实性或覆盖 |
| L2 `OWNER_DOCUMENTED` | 可定位源 revision/freeze、覆盖范围、当前数据截至点、统一 world key namespace 与完整性证据，Owner 签署 | 可以交给独立 Reviewer 检查，但不得自动 PASS |
| L3 `INDEPENDENTLY_VERIFIED` | 独立核对源 SHA/冻结、必要全集覆盖、同一世界的别名/派生连通图及候选逐项交集，具有可追溯 reviewer receipt | 仅对已覆盖且审核通过的候选解除对应 G1 门禁；其余 HOLD |

**不能用一个空交集代替证明全集的覆盖**；文件名 / checksum / story UUID / 不同作者或标题都不能单独证明世界独立。

## B. 已查到的材料与限制

- **语义世界图**：R52 私有 `~/.local/share/storyforge/r52/world_full`、`world_isolation`、`world_review`、`graph21` 等是历史工作路径线索，**未验证 Owner Mac 本次仍有这些目录或可核实完整性**。R57 G2 的 55 对语义别名审核曾全部 UNREVIEWED，因此历史图不等同已签署独立性结论。
- **R50**：已有 R50 冻结 / 隔离历史及元数据审查流程，但本轮**未核实一个覆盖 R50 全部保护世界、可访问且被允许仅供元数据比较的完整索引**。R50 保持封存，禁止为扫描而打开原始测试题。
- **历史 SFT 曝光**：`r57/v03b-data-design` 分支存在并已通过工具核实以下只含 SAFE 汇总的回执：`docs/evidence/R57_G2_EIGHT_SOURCE_OWNER_EXACT_REPLAY_SAFE_20261026.json`、`R57_G3_OWNER_EXPOSURE_LEDGER_COUNTS_SAFE_20261026.json`、`R57_G2_EIGHT_SOURCE_TARGET_ANCHORED_UUID_OWNER_SAFE_20261026.json`。R57 也有真实训练/Gold 来源回放代码 `scripts/r57_trainer_exact_replay.py`、`r57_g3_private_exposure_ledger.py`、`r57_g2_target_anchored_world_audit.py`、`r57_g2_owner_world_review_roster.py`。**但 count-only SAFE 汇总不能逐个核对当前五条故事的世界映射；旧 27 个训练故事 UUID 不一定等于 27 个独立语义世界。**
- **R55/R57 开发世界**：R55/R57 的审核和开发题元数据有历史出处，但本轮尚未证明全集/别名覆盖的完整 `world_component` 索引。
- **其他保护世界**：需要定义“全部相关保护”的冻结范围（v0.1 Test、R50、其他独立 Held-out/Dev/HOLD 等），并防止重复计入；没有统一冻结清单时仍缺证据。

## C. Mac 执行：先以五行私有清单为证据索引

将已提供的模板复制到 repo 外的私有目录（若已存在，绝不覆盖）：

```bash
cd ~/workspace/storyforge-r58-run
git pull --ff-only
umask 077
ROOT="$HOME/.storyforge-r58-private/round1_pilot_20261030"
mkdir -p "$ROOT"
chmod 700 "$ROOT"
if [ ! -e "$ROOT/g1_evidence_inventory_private.csv" ]; then
  cp experiments/r58_round1/G1_METADATA_EVIDENCE_INVENTORY_BLANK.csv \
    "$ROOT/g1_evidence_inventory_private.csv"
  chmod 600 "$ROOT/g1_evidence_inventory_private.csv"
fi

python3 -m unittest discover -s experiments/r58_round1 \
  -p 'test_*.py' -v

python3 experiments/r58_round1/audit_g1_index_readiness.py \
  --private-inventory "$ROOT/g1_evidence_inventory_private.csv"
```

新增预检仅使用 `stat/lstat` 判断**清单中明确指定的五个元数据来源路径**是否有非空普通文件；只打开五行的 Owner 私有证据清单，不打开任何被引用的 R50/历史训练/作品数据文件。不读取源内容、不计算源数据哈希、不遍历 R50，输出只有固定类别名、布尔值和汇总数字。原有 41 项 + 本次新增 9 项，**预期 50 项，Owner 运行结果待回报**。

### C1. 如何查找本地已经存在的来源

在 Mac **本地**检查历史 SAFE 元数据归档，不查看保护题原文。可以从以下既有根路径检查已经生成的 *SAFE 回执、世界索引或覆盖清单的文件名*：

- `$HOME/.local/share/storyforge/r52/world_isolation`
- `$HOME/.local/share/storyforge/r52/world_review`
- `$HOME/.local/share/storyforge/r52/history_exposure_with_r45`
- `$HOME/.local/share/storyforge/r57/private`
- 私有 `r50` *安全元数据登记* 的既有授权位置（**不扫描 R50 原始数据目录**）

只能将**确认是元数据专用文件**的具体路径填入 `private_source_reference`。若路径是原文 ZIP、完整 JSONL、角色卡或保护题正文，则不能用它冒充元数据索引，保持空白。GitHub 的 SAFE count-only 回执也不能冒充“候选 world IDs 全集索引”。

五行私有清单字段：
- `private_source_reference`：精确指向专用元数据索引的本地绝对路径。未知留空。
- `source_revision`：有可审计的 commit/tag/冻结版本或来源修订；无则留空。
- `coverage_status`：`UNKNOWN`、`PARTIAL`、`OWNER_COVERAGE_ATTESTED`。最后一项仅指 Owner 的**覆盖声明**，不是独立验证。
- `world_identity_namespace`：同一语义 world component 命名空间/归一化规则；没有规则留空，不要用故事 UUID 冒充。
- `independent_review_status`：`PENDING`、`OWNER_REVIEWED` 等；即使填写 `INDEPENDENT_VERIFIED`，本工具也不会当作证明，需要独立回执核对。

## D. 必须有的「覆盖完整性」证据

| 分类 | 覆盖全集最低要求 | 严格反例 |
|---|---|---|
| semantic_world_graph | 当前五条候选及其已知别名/派生/跨作品关联的组件，并有人工语义审查 | 五个互异 story_id 或相似度 0 |
| r50_protected_worlds | **所有** R50 保护世界的冻结 metadata-only component 视图与受控覆盖回执 | 只核对 46 条处理过的 case |
| prior_sft_exposure | 历次 Train/Val/Dev 实际送训及开发时使用的故事世界来源；R46/R54 无逐项 story metadata 时需恢复并注明方法 | 只有 v0.1 或只有 Gold195 target SHA |
| r55_r57_dev_worlds | R55/R57 所有开发/审核世界的元数据冻结表和实际使用状态，含并入/交叉边界 | 单次开发题表或只看本轮故事标题 |
| other_protected_or_holdout | 当前受保护范围的完整注册表和冻结范围定义，涵盖未并入上述三组的 v0.1 Test、独立 Held-out 等 | 仅有“本轮没有命中”的查询结果 |

## E. 回报与下一门禁

将预检 SAFE JSON 中的 `scope_readiness` 发给助手即可。若五项都是 `MISSING_SOURCE_REFERENCE`，说明**私有证据清单尚未填写**，并不证明历史文件不存在。若仅 `source_file_exists_unopened=true`，只能说**路径存在，源文件内容和覆盖未检查**。

后续须由独立审阅者核验来源、覆盖和世界键等价性，再由 Owner 对候选与受保护全集做 metadata-only world-component 交集；不取得完整来源就不能勾 `clear`，不能读正文，不自动增加候选范围。

**始终：G1 HOLD、Train/Validation/Teacher = 0、首轮 <=5 世界/20 回复、未批准不扩样、PR #7 Draft、Skill v0.1 不变。**
