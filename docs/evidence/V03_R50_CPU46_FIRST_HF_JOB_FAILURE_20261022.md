# StoryForge R50 CPU46 — first HF Job failed; keep HOLD

Date: 2026-10-22. Evidence type: Owner-provided HF Job terminal output, plus source-code review of existing pinned CPU46 Worker. No private R50 prompt or task mapping was opened.

- Namespace: `adradar`; HF Job ID `6ada2b71c191903149a728b1`; run key `r50-cpu46-20261022T151846Z-950025`.
- Result: HF Job `ERROR`, exit code `2`.
- Worker reached original private tokenizer-preflight invocation after `R50_CPU46_LOCAL_STAGE_SHA256_PASS` and tokenizer-only HF snapshot download.
- The wrapper reported `R50_CPU46_HOLD__SOURCE_PREFLIGHT_RETURNED_ERROR`. Actual exception type and failure reason are **unknown** until the restricted private output file is inspected.
- Existing Worker captures the original command's stdout/stderr into `R50_CPU46_PREFLIGHT_OUTPUT_PRIVATE.txt` under the protected Bucket's **results** prefix. It intentionally does not emit these contents into public Job logs.
- `pip` root warning and missing PyTorch informational warning do not by themselves explain this failure; PyTorch is not needed for tokenizer-only work.
- No valid successful R50 Tokenizer audit receipt was produced or independently accepted. Held-out formal test admitted `0`; final seal `false`; semantic world-isolation `HOLD`.

## Read-only owner diagnostic next action

Retrieve only the protected private failure output from:

`hf://buckets/adradar/storyforge-r50-audit/preflight/r50/cpu46/results/r50-cpu46-20261022T151846Z-950025/R50_CPU46_PREFLIGHT_OUTPUT_PRIVATE.txt`

Do **not** upload the raw private output, which may contain source snippets or case IDs, to ordinary Git. Extract a count-only diagnostic preserving only exit code / exception class / traceback source line numbers / error-category signatures / raw-file SHA256 using the Owner Mac Python standard library. If the object is unavailable, keep HOLD; no speculative retry.

The existing run key is **consumed**. Do not rerun `submit` on it, silently edit its staged bytes, launch another paid Job, or grant model/test admission. If a root cause is established and code correction is approved, freeze a *new* stage and get a separate explicit paid-CPU authorization.

**Status:** `R50_CPU46_FIRST_JOB_SOURCE_PREFLIGHT_ERROR__PRIVATE_DIAGNOSTIC_PENDING__NO_RETRY__NO_FINAL_SEAL`.
