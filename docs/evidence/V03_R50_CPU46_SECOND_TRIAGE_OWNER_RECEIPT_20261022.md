# StoryForge R50 CPU46 — Owner Mac second offline diagnostic

2026-10-22. Scope: Owner-reported **count-only** offline diagnostic, not an independent read of raw protected R50 source or stderr.

- HF Job `6ada2b71c191903149a728b1`; run key `r50-cpu46-20261022T151846Z-950025`.
- Original private preflight SHA256 `235b92a668a1f4f0afbea7cd951df695f9d1a487a659ce46d315938a2880b959`; captured private output SHA256 `097234a52f0726dacfe4a2905d10b2670949204d34d3a8165c1be69dee3f3120`.
- Preflight exit `1`; stderr 112 characters; recognized `ValueError` token; no traceback frames.
- The private original script parses as Python AST. Line **72** calls `AutoTokenizer.from_pretrained(DYNAMIC)` with `local_files_only=True`, `use_fast=True`, `trust_remote_code=False`; exception-handler lines **70** and **116**.
- Safe stderr code `ERR_EXPLICIT_HOLD` is a broad classification. Specific `ValueError` **message unknown**; no reproduced tokenizer-load cause.
- HF public Qwen repo has a `config.json` and `tokenizer_config.json`, but existing `scripts/v03_r50_hf_cpu46_audit.py` allow_patterns for tokenizer-only files does **not** include `config.json`. This difference is a possible compatibility area to test with a **public-tokenizer-only smoke**, not proof of root cause; do not change old frozen stage based on speculation.

**No retry of the consumed run key; no paid Job submitted here.** No R50 protected prompt content or stderr text committed. A future patched version should verify public tokenizer initialization (with pinned HF revision), classify failures without private values, and only access 46 protected prompts after public smoke PASS. New code hash, run key and separate Owner paid CPU authorization are necessary.

Status: `R50_CPU46_VALUE_ERROR__TOKENIZER_INIT_SUSPECTED__ROOT_CAUSE_UNKNOWN__NO_JOB_RETRY__SEMANTIC_HOLD__NO_FINAL_SEAL`. Official heldout admission 0, no model inference or GPU.
