# StoryForge v0.2 — Conversation handoff index (after R48)

**Latest historical stage:** R46 exploratory GPU SFT engineering PASS; R47 old 20-case 3-arm retrospective review complete; R48 old 20-case Gold+3-model retrospective review complete; **no model promotion**.

**Next-stage plan (proposed, NOT executed):** [v0.3 R49–R57 detailed Test & Training plan](../plans/StoryForge_v03_Test_and_Training_Plan_20261014.md) and [machine-readable phase gates](../plans/StoryForge_v03_Test_and_Training_Gates_20261014.json). This is the current forward workplan, not a change to the frozen R46–R48 evidence; new paid GPU work remains unauthorized.

**Read these first in the new conversation:**

1. [Complete new-chat handoff](StoryForge_v02_Handoff_After_R48_20261014.md) — scope, job IDs, exact input/adapter hashes, model scores, CI gates, and next steps.
2. [Machine-readable state](StoryForge_v02_State_After_R48_20261014.json) — frozen status and safety gates for programmatic continuation.
3. [R48 full analysis](../evidence/V02_R48_FOUR_ARM_UNBLIND_ANALYSIS_20261014.md) and [JSON](../evidence/V02_R48_FOUR_ARM_UNBLIND_ANALYSIS_20261014.json).
4. [R48 archive checksum manifest](../evidence/V02_R48_ARCHIVE_MANIFEST_20261014.json) — original submitted report digest and the exact committed MD/JSON SHA256.
5. [R47 3-arm unblind analysis](../evidence/V02_R47_2_THREE_MODEL_UNBLIND_RESULTS_20261014.md).
6. [R46 GPU engineering acceptance](../evidence/V02_R46_GPU_TRAINING_ACCEPTANCE_20261014.md).

The source-of-truth repo is **private** `sunxu/storyforge`. This index and its related documents contain **no new private answer keys, secrets or checkpoint weights**. The 20 old v0.1 Test questions have already been exposed and cannot substitute for the **new independent 40–60 sample/4-world Held-out** still required.

**Verification:** R48 dedicated no-GPU [CI #38580602545](https://github.com/sunxu/storyforge/actions/runs/38580602545) was **SUCCESS**, including analysis output SHA verification; the general default [CI #38580602539](https://github.com/sunxu/storyforge/actions/runs/38580602539) **FAILED at Ruff**, with 35 lint findings; do not merge those two gate states.

**No billing:** New GPU/remote inference actions require explicit user approval; do not automatically rerun already completed experiments.
