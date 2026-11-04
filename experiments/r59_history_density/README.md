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

Run from the repository root. Use the existing protected local RUN directory; do not copy the private JSONL into the repository.

```bash
set -euo pipefail
RUN="$HOME/.local/share/storyforge/r59/private/r60-pilot8-cpu-20261104T095803Z"
INPUT="$RUN/input/R59_PILOT8_REVIEW_PROMPTS_PRIVATE.jsonl"
TOKEN_SAFE="$RUN/output/R59_PILOT8_R60_CPU_TOKEN_SAFE.json"

python3 experiments/r59_history_density/r59_history_density.py \
  --input "$INPUT" \
  --expected-sha256 5add3f7e2f09ddd210835722fa0578b11c7766b14754ab3980f403c063b8006f \
  --expected-fingerprint 177f602331b06d90b68606bd796bd4705f90a7ee6dc7b260003075a9eeaa59c4 \
  --token-safe "$TOKEN_SAFE" \
  --output-dir "$RUN/history-density"

python3 -m unittest discover \
  -s experiments/r59_history_density \
  -p 'test_*.py' -v
```

**Important:** the command above pins the input using its actual SHA256. Use the verified value from the R59 input manifest:
`5add3f7e2f09ddd210835722fa0578b11c7766b14754ab3980f403c063b8006f`.
The output directory must not already exist. Both generated files remain under the Owner's private local directory. Do not commit or upload either generated report or SAFE JSON to the public repository.

## Test

```bash
python3 -m unittest discover -s experiments/r59_history_density -p 'test_*.py' -v
python3 -m compileall -q experiments/r59_history_density
```
