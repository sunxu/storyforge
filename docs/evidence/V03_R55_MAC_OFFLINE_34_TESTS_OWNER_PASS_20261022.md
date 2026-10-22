# StoryForge R55 — Mac offline preparation test receipt

Date: 2026-10-22 (Asia/Singapore).

Owner supplied the console output from the private R55 package's `python3 -m unittest discover -s tests -p 'test_*.py' -v` command.

**Owner-reported status: `R55_MAC_OFFLINE_PREPARATION_TESTS_34_OF_34_PASS__NO_GPU__R50_SEALED`.**

The console listed 34 `... ok` test cases across:
- `test_r55_dev_pairwise`: 18/18
- `test_r55_review_freeze`: 13/13
- `test_r55_source_preflight`: 3/3

Final unittest output: `Ran 34 tests in 0.082s` and `OK`.

An earlier Bash process-group warning `setpgid ... Operation not permitted` appeared before the Python test output, but **did not cause Python unittest to fail**. Its exact environmental origin is not established by this log alone.

Scope of evidence: actual Mac-side test terminal transcript reported by Owner; this is **not** proof of:
- Verification of original R47 private HF responses using the real `r55_dev_source_preflight.py` command;
- R54 generation of the 20 previously exposed retrospective prompts;
- Three new independent blind reviews;
- A completed formal R55 evaluation, model quality improvement or model promotion.

Original R47/R48 exposed questions are the **same 20 questions** (2 old story worlds) and remain **development-only**, not a fresh sealed heldout. R50 stays sealed.

Next free step is to fetch the **existing** R47 R46 `v02-results.jsonl` and `R47_PRIVATE_RUN_REPORT.json`, verify them against exact Git prompts/manifest and produce `R55_OLD_R47_SOURCE_PREFLIGHT_SAFE.json` locally. Only after this is complete should a separately authorized R54 20-response inference be considered. No new paid GPU authorization is implied by these tests.
