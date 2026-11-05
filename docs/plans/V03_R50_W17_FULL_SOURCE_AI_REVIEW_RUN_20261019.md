# R50 W17 — optional consent-gated FULL-message AI review

**Not executed.** The source dossier manifest is owner-reported and SHA-pinned.
Input manifest SHA256: `189f84e0e2891499723ba7e9e14cc866c057c9ab5ead727ff4c192e717510476`.

The private full-message dossier directory contains unredacted source text
for old 02/04/07/10 and W17. The independent reviewer must analyze the
actual seven gap requirements and their complete original-message evidence.
Even complete messages do NOT prove the whole story was exhaustively read;
historically valid cards at prompt cutoff are still NOT CHECKED.

The included runner sends these private dossier texts to the remote Codex
service **only after explicit owner opt-in**. Local read-only sandbox is
not a guarantee of local inference or confidentiality from the model provider.
Do not invoke it unless this exact transfer is authorized.

```bash
cd ~/workspace/storyforge
git fetch origin audit/r49-r50-source-intake-20261015
git switch audit/r49-r50-source-intake-20261015
git pull --ff-only

# Optional: purely local dossier SHA verification, NO model call:
ROOT="$HOME/.local/share/storyforge/r50/private-ai-review"
python3 scripts/v03_r50_verify_w17_full_source_review.py --repo . \
  --dossiers-dir "$ROOT/W17_SEVEN_GAP_FULL_SOURCE_DOSSIERS_20261019"

# Explicit, optional consent to disclose private text to remote Codex:
STORYFORGE_AUTHORIZE_PRIVATE_AI_TRANSFER=YES \
  bash scripts/v03_r50_run_full_source_ai_review.sh
```

The runner keeps error logs only in a private local directory, validates
all seven dossiers and cites only source rank/index pairs present there.
It creates the 0600 private workpaper only if Codex actually returns a
schema-valid JSON AND the strict source validator passes. No overwrite,
no Git write, no HF/GPU jobs, and no test-model answer generation.

Stop if the model fails or the validator reports a HOLD: do not fabricate
supporting evidence, automatically mark world-independent, or bypass
historical-card limitations. A successful full-message review is only
a scoped intermediate result; all broader R50 semantic seals remain HOLD.
