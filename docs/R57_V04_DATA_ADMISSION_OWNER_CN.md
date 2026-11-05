# R57-B — Dataset v0.4 私有样本准入 CPU 流程（准备版）

**Status:** `R57_V04_SCHEMA_AND_CPU_GATE_DRAFT__NO_SAMPLES_ADMITTED__NO_R50`

## 安全边界

1. 本仓库只提交 **Schema、CPU 只读验证工具、合成测试、脱敏统计**；实际训练样本、消息历史、小说原文、世界 token、完整审核理由和 Reviewer token 放在 `~/.local/share/storyforge/r57/private/` 或经批准的私有存储，**不要放在普通 Git 工作区**。
2. 本脚本不会访问网络、HF、R50、GPU，不构建训练集，不生成新候选、不批准样本。仅依赖 Python 标准库。
3. JSON Schema 是**格式合同**；配套 Python 验证器覆盖核心枚举、SHA 格式、两份审核、签核、来源隔离、Train/Validation 世界组件隔离与显式 HOLD。两个验证均不能凭空证明故事世界语义独立、版权/年龄/同意状态真实或评审者真正独立。
4. 历史 `Gold87 + Gold108 = 195` 只是候选池。R55 79 项是 AI 辅助拟确认类别裁决，不能自动给 Gold195 打错标签。
5. 不从封存的 R50 寻找样本、比较题目或训练目标；非封存数据的相似度审查只在已授权的来源集合内进行。保护集隔离依赖独立保管方的**元数据级**证明，未出具时必须 HOLD。

## 本地仅运行合成测试

```bash
cd ~/workspace/storyforge-r55-tooling
python3 -m unittest discover -s tests -p 'test_r57_v04_*.py' -v
```

## 创建私有空白准入清单（不是可训练集）

```bash
PRIVATE="$HOME/.local/share/storyforge/r57/private"
mkdir -p "$PRIVATE"
chmod 700 "$PRIVATE"
python3 - "$PRIVATE/R57_V04_INTAKE_PRIVATE.json" <<'PY'
import json, pathlib, sys
out = pathlib.Path(sys.argv[1])
if out.exists():
    raise SystemExit("HOLD: private intake already exists; refusing overwrite")
data = {
    "schema": "storyforge-r57-v04-private-intake-v1",
    "no_r50_content_accessed": True,
    "training_authorized": False,
    "records": []
}
out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
out.chmod(0o600)
print("PRIVATE_V04_INTAKE_INITIALIZED__RECORDS_0__NO_R50")
PY
python3 scripts/r57_v04_admission_gate.py \
  --private-manifest "$PRIVATE/R57_V04_INTAKE_PRIVATE.json" \
  --mode draft \
  --safe-out "$PRIVATE/R57_V04_INTAKE_SAFE_COUNT_ONLY.json"
```

**新增的输出安全约束：** `--safe-out` 只允许创建不存在的报告；若目标文件或符号链接已经存在，将返回 HOLD，不覆盖原文件。再次审核时请使用新的版本化报告文件名，不要删除或复写旧回执。输入必须是普通文件且不得为最终符号链接；大于 64 MiB 的元数据清单拒绝读取。工具检查的仍是元数据自述，不会通过字段为真的声明自行证明来源正确性。

注意：空的或仅有 HOLD 的清单在 `--mode draft` 可以通过，但**不是**准入 PASS。`--mode admission` 至少需要一条具备两位审核、Owner 批准且 Train/Val 隔离的候选，否则 fail-closed。

## 建议的候选筛选顺序

1. 在已审阅授权范围内，按世界组件抽样 40–60 条（当前实际选择数为 **0**）。原始 Gold 不覆盖。
2. 单条样本的原始目标 SHA256、来源文件 SHA256、目标时点规则/连续历史 SHA256 必须可追溯；脚本当前仅检查哈希形状，**不重新打开原始小说源文件**。实际源文件字节回放是另一个 Owner-local 门禁。
3. 标记旧 v0.1/R46/R54 的 Train/Val 和 R47/R48/R55 Dev 历史曝光；UNKNOWN 一律阻止 ACCEPT，R50 内容不得开封。
4. 做案例级权利、成人/同意、玩家自主权、世界背景的独立检查；涉及后导出角色卡推断先 HOLD。
5. 两个可区分 Reviewer 引用原始证据，Owner 再签核。当前协议允许 AI 辅助评审身份如实记录，但不会把 AI 审查冒充为人类独立审查。是否增设人工必审须 Owner 在正式实验合同批准。
6. 原始 Gold 和派生 Gold 分别保存；派生目标须保留 `parent_target_sha256` 和 `derivation_delta_sha256`。合成负例单独诊断，不进入 SFT Train。
7. 只有在真实原文可用、Train/Val 世界连通分量无交叉、验证目标/角色输入隔离后，才可以申请 CPU actual tokenizer/collator 检验；付费 GPU 仍需另行授权。

## 来源与版本约束

- `docs/plans/R57_V03B_EXPERIMENT_CONTRACT.md`
- `evaluations/v0.3/r57/R57_DATASET_V04_ADMISSION_SCHEMA.json`
- `docs/evidence/R57_DATA_SOURCE_INVENTORY_SAFE.json`
- `scripts/r57_v04_admission_gate.py`
- `tests/test_r57_v04_admission_gate.py`

**Known limitation:** the verifier does not implement the full JSON Schema Draft 2020-12 specification; rather it checks the same known keys/enums and critical cross-row invariants. For later formal releases use a separately pinned JSON Schema validator as well. Strings like `NO_OBSERVED_MATCH` report an auditor determination, not proof of semantic independence. 
