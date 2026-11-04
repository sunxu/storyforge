# R60-03 SAFE Volume Edge Tests

Date: 2026-11-04  
Scope: synthetic filesystem behavior only. No HF Job, private input, model, GPU, or training.

## Added implementation

- `outputs.py` now retains the inode identity immediately after no-replace hard-link publication, so verification failures can remove only the object created by this call.
- File and directory fsync failures are distinguished as `OUTPUT_FSYNC_FAILED`.
- Cleanup failures are surfaced as `OUTPUT_CLEANUP_FAILED` rather than silently ignored.
- Temporary and published objects are removed only after an inode identity check.

## New tests

File: `tests/test_hf_runtime_volume_edges.py`

1. Two concurrent writers race to publish one SAFE path; exactly one may succeed.
2. ENOSPC after a partial temporary write must not publish a partial SAFE file.
3. File fsync failure must clean the temporary object.
4. Directory fsync failure must remove the not-committed published name.
5. Filesystem hard-link unsupported error must fail closed without publication.
6. Cleanup failure must be surfaced as `OUTPUT_CLEANUP_FAILED`; test removes its deliberately retained synthetic temp file after restoring the test filesystem function.

## Current status

- Code committed: YES.
- Mac execution of new edge suite: NOT RUN.
- Linux ARM64 execution of new edge suite: NOT RUN.
- GitHub Actions: BLOCKED_BEFORE_RUNNER_ALLOCATION (`runner_id=0`, no steps).
- Real HF Volume: NOT TESTED.

## Acceptance gate

Run Ruff, compileall, both Runtime test files, Tokenizer core regression, and Doctor in the persistent Python 3.11 Docker image. The new edge suite must pass on Linux ARM64 before R60-03 can be marked PASS.

The hard-link and directory-fsync behavior on HF-managed RO/RW Volumes remains a separate remote Smoke acceptance item. Local ext4/overlayfs results do not establish HF Volume compatibility.
