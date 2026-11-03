# R59 Context Window Rebuild Implementation Plan

> **For agentic workers:** This plan records the implementation and verification contract for the R59 context-window adapter.

**Goal:** Add a repeatable CPU-only tool that rebuilds R59 engineering-preview rows by removing only a leading history prefix until the complete recent suffix fits 16,384 tokens.

**Architecture:** A thin adapter validates with the existing R59 preview contract, measures candidates with the pinned ms-swift Qwen template and the shared StoryForge token-ID extraction core, then runs the existing actual Collator before writing a new private artifact. It never edits the source preview or grants Quality-v1 admission.

**Tech Stack:** Python 3.11, ms-swift 4.5.3, transformers 5.16.1, shared `storyforge_dataset.token_preflight.extract_input_ids`, existing R59 Collator.

**Spec:** Approved R59 continuation scope in the 2026-11-04 handoff and owner approval in this conversation.

## Global Constraints

- Model: `Qwen/Qwen3.8-27B`.
- Immutable revision: `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`.
- Token budget: exactly 16,384.
- `loss_scale`: `last_round`.
- System Prompt and final target bytes must remain unchanged.
- Keep full message order and only drop a leading history prefix at a User-message boundary.
- Historical messages remain `loss=false`; only final Assistant target remains `loss=true`.
- Use shared token preflight core; do not reimplement input_ids extraction.
- Private inputs/outputs remain outside GitHub; file mode 0600, output directory mode 0700, create-only.
- CPU only; no inference, GPU, training, admission, or dataset freeze.

## Review Focus

- An over-budget current User plus target must HOLD without partial target truncation.
- Assistant-first full history must remain intact whenever it fits.
- A trimmed suffix must start at a User boundary and retain all later messages in order.
- Recomputed input-context hash must differ when history is dropped while preserving the original source hash.
- Any target/System Prompt mutation must be rejected by the existing preview validator.

---

### Task 1: Specify context-window selection behavior

**Files:**
- Create: `experiments/r58_quality/test_r59_sft_context_window.py`

**Interfaces:**
- Produces: tests for `rebuild_preview_rows(rows, measure_tokens, max_length=16384, validate_row=None)`.

- [x] Write the failing tests first.
- [x] Run the tests against a not-implemented stub and observe the expected `NotImplementedError`.
- [x] Implement the adapter in Task 2.

### Task 2: Implement deterministic rebuild and actual Collator gate

**Files:**
- Create: `experiments/r58_quality/r59_sft_context_window.py`

**Interfaces:**
- Consumes: `r59_sft_collator_cpu.validate_preview_row`, `r59_sft_collator_cpu.run`, and shared `extract_input_ids`.
- Produces: `rebuild_preview_rows` and CLI `run(private_input, output_dir)`.

- [x] Preserve the full history when it fits.
- [x] Otherwise select the longest fitting complete suffix beginning at a User boundary.
- [x] Recompute the current input hash and retain the original input hash as provenance.
- [x] Run the existing actual ms-swift Collator before creating output artifacts.
- [x] Keep SAFE output aggregate-only and private artifacts create-only.

### Task 3: Document execution and safety contract

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/HF_JOBS.md`
- Modify: `experiments/r58_quality/test_r59_sft_collator_cpu.py` (fix missing `os` import in existing test)

- [ ] Document directory-prefix mounts and the exact shared-core bundle requirement.
- [ ] Document that CPU PASS is not Quality-v1 admission or training authorization.
- [x] Run focused unit tests (8/8 context-window; 10/10 existing Collator), Python compileall, and Ruff check (3 files).\n- [ ] GitHub Actions CI: retry attempted; runner still fails before steps start, so code has not been evaluated by Actions.

## Verification

Focused command:
`python3 -m unittest discover -s experiments/r58_quality -p 'test_r59_sft_context_window.py' -v`

Expected: all context-window unit tests pass. Real HF CPU execution of the new committed adapter remains a separate verification after the exact code and shared core are synchronized to the private Bucket.
