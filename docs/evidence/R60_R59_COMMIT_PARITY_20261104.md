# R60 / R59 Commit Parity Evidence

Date: 2026-11-04
Repository: `sunxu/storyforge`
Branch: `r60/hf-jobs-runtime`
R59 HF CPU Job: `6aeb0f8f0e0338d1bb7fb6c1`

## Commit identity

- Job label commit: `96cdb76d4b7e`
- Full Job commit: `96cdb76d4b7e61d2a34216d70d45396e66163e2a`
- R60 branch HEAD: `96cdb76d4b7e61d2a34216d70d45396e66163e2a`
- GitHub compare status: `identical`
- Ahead / behind: `0 / 0`

The branch HEAD is exactly the commit named by the completed R59 Job. This establishes repository revision identity; the per-file Git blob IDs below make the audited code set explicit.

## Runtime and adapter Git blob identities

| File | Git blob SHA |
|---|---|
| `src/storyforge_dataset/hf_runtime/context.py` | `2d24c8ffed6fbf102fd206acdbf5f814ea73b29d` |
| `src/storyforge_dataset/hf_runtime/paths.py` | `203e5a1d8c06641d5cce176fe4daca59b631a7c3` |
| `src/storyforge_dataset/hf_runtime/inputs.py` | `0c59bff129858d7129c931e3cdc415c93356de49` |
| `src/storyforge_dataset/hf_runtime/outputs.py` | `69838b603b43663eaa12b1b1947ce14abad524bc` |
| `src/storyforge_dataset/hf_runtime/diagnostics.py` | `840c621bc2a9860e342f1eb805f9b0fa2d41a7ce` |
| `src/storyforge_dataset/hf_runtime/resources.py` | `22d7084d6c75d7c62e05eb6e53d248f59a35d3f0` |
| `src/storyforge_dataset/hf_runtime/receipts.py` | `58de5b98f01c914390700e4eddc5f8e8620bfd3d` |
| `experiments/r58_quality/r59_semantic_prompt_token_cpu.py` | `ca3a1cc450fd1b1e20118898fe33e63b91f357aa` |

## Immutable tokenization core

Path: `src/storyforge_dataset/token_preflight.py`

- Architecture baseline commit `adc3876d6d0350c270e2b5fa5ccc832438fdf7ee`: `9ea7596c2151ee10aa1394beedc36ffeb9a7fca8`
- R59 Job commit `96cdb76d4b7e61d2a34216d70d45396e66163e2a`: `9ea7596c2151ee10aa1394beedc36ffeb9a7fca8`

Result: exact Git blob match. The shared tokenization core was not modified by R60.

## Conclusion

`R60_R59_COMMIT_PARITY_PASS`

The R59 Job commit, current R60 branch HEAD, seven approved Runtime modules, R59 adapter, and unchanged tokenization-core identity are recorded above. This proves code revision parity, not business acceptance: the R59 token budget result remains `R59_PILOT8_HF_CPU_TOKEN_OVER_BUDGET__HOLD`.

No private prompt text, private input SHA256, prompt fingerprint, or per-case content is included in this public evidence file.

GPU authorization remains NONE. No GPU, inference, training, or Quality-v1 admission was performed.
