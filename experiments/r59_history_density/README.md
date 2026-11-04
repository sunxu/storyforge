# R59 Pilot8 History Density

Owner-local, CPU-only analysis for the frozen 8-case R59 Pilot8 prompt file.

## Safety and scope

- Reads the frozen input only; never modifies it.
- Verifies the exact input SHA256 and prompt fingerprint.
- Requires the frozen prompt schema, case order, history scope and coverage counts.
- Does not emit prompt text, character names, target text, source identifiers or message contents.
- Writes a local JSON SAFE summary and Markdown report with create-only publication and mode 0600.
- Uses Python 3.11 standard library only; no model, tokenizer, network, HF Job, GPU or training.
- The report is evidence about staged-history volume and coverage metadata, not a semantic-quality judgement or training admission.

The staged JSONL contains one `system` wrapper message and one `user` serialized-prompt message per case. Those wrapper roles are **not** the underlying historical dialogue role distribution. Upstream-removed message bodies are unavailable in this staged input; only their declared counts are reported.

## Owner command

Run from the repository root. Reuse the existing Python 3.11 environment at `~/.venvs/storyforge-r60`; do not install dependencies or copy the private JSONL into the repository.

```bash
set -euo pipefail
RUN="$HOME/.local/share/storyforge/r59/private/r60-pilot8-cpu-20261104T095803Z"
INPUT="$RUN/input/R59_PILOT8_REVIEW_PROMPTS_PRIVATE.jsonl"
TOKEN_SAFE="$RUN/output/R59_PILOT8_R60_CPU_TOKEN_SAFE.json"

# Load identity pins from the Owner-private file; never print or commit them.
set -a
. "$RUN/secrets.env"
set +a
: "${R59_INPUT_SHA256:?missing R59_INPUT_SHA256 in private secrets.env}"
: "${R59_PROMPT_FINGERPRINT:?missing R59_PROMPT_FINGERPRINT in private secrets.env}"

PY="$HOME/.venvs/storyforge-r60/bin/python"
"$PY" experiments/r59_history_density/r59_history_density.py \
  --input "$INPUT" \
  --expected-sha256 "$R59_INPUT_SHA256" \
  --expected-fingerprint "$R59_PROMPT_FINGERPRINT" \
  --token-safe "$TOKEN_SAFE" \
  --output-dir "$RUN/history-density"

"$PY" -m unittest discover \
  -s experiments/r59_history_density \
  -p 'test_*.py' -v
```

**Important:** the input SHA256 and prompt fingerprint are loaded from the Owner-private `$RUN/secrets.env`; they are intentionally not embedded in this public README. Do not print, paste, commit, or upload those values. The output directory must not already exist. Both generated files remain under the Owner's private local directory. Do not commit or upload either generated report or SAFE JSON to the public repository.

## Test

```bash
"$PY" -m unittest discover -s experiments/r59_history_density -p 'test_*.py' -v
"$PY" -m compileall -q experiments/r59_history_density
```
