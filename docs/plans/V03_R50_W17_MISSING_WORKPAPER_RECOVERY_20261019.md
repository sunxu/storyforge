# R50 W17 — recover missing seven-gap independent AI workpaper

The owner reported WORKPAPER_MISSING. This indicates that the expected
private output has not been created at that path. It is NOT a failed
semantic review; the verifier cannot generate the missing workpaper.

Use the opt-in script (after reviewing your provider's data handling):

```bash
cd ~/workspace/storyforge
git fetch origin audit/r49-r50-source-intake-20261015
git switch audit/r49-r50-source-intake-20261015
git pull --ff-only

# This command sends private story excerpts to the remote Codex AI model.
STORYFORGE_AUTHORIZE_PRIVATE_AI_TRANSFER=YES \
  bash scripts/v03_r50_run_seven_gap_ai_review.sh
```

It first verifies the frozen SHA256 of the seven private source packets,
then runs Codex CLI in a read-only ephemeral session and captures logs
only within a local 0700 private directory. Once Codex returns, the
existing source-anchored workpaper validator checks the generated JSON.
Only after validation does the script create the named 0600 private
decision file, never overwriting a previous file.

On CLI or validator failure it prints ONLY a safe error marker and the
local private log directory. Local Codex logs can contain source text;
NEVER upload them to Git or paste them publicly. Review failure details
locally and share only redacted error categories.

Read-only sandbox restricts local writes, not disclosure to the remote
AI service. This script does not use HF Jobs, GPU training, held-out
answer generation, or Git writes. Global semantic HOLD and no final
Held-out seal persist, even on successfully validated reviewer output.

If cloud review is not authorized, do not run. Use an approved offline
reviewer or keep the evidence-review stage pending.
