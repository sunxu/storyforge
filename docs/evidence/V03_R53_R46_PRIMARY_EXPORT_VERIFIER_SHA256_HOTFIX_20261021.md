# StoryForge R53 — R46 primary-export SHA256 verifier hotfix

Date: 2026-10-21. Status: `VERIFIER_CODE_BUG_FIXED__REAL_PRIMARY_EXPORT_UNVERIFIED__DATA_RELEASE_BLOCKED`.

## Error and source-level diagnosis

After fetching the seven existing R46 first-party export files, the owner ran `r53_verify_r46_primary_export.py` and received:

```
R46_PRIMARY_EXPOSURE_UNVERIFIED__DATA_RELEASE_BLOCKED: object supporting the buffer API required
```

The released verifier imported `sha(b) = hashlib.sha256(b).hexdigest()` from `r53_reconcile_r45_r46_and_stage.py`. The seven-file receipt-manifest comprehension incorrectly called `sha(root/f)` with a `pathlib.Path`. It must call `sha((root/f).read_bytes())`. This was a **verifier programming defect**, not evidence that the R46 export files were corrupted.

Original verifier SHA256: `8045d46fbd11f55e36656917827767ec7f201eba4d418faa58ca592d07080afa`.

Corrected verifier SHA256: `30a927f8d4b82f950a5455fa8725cc1965c443b0f5f4e48079fb2438489dccb4`.

The fix changes exactly this type error; it does not rewrite previous audit files, bypass any fail-closed checks, or change private R45/R46/R53 source data.

## Regression evidence and boundaries

The corrected file was executed through **eight local synthetic-export tests**: an expected-success branch using genuine frozen R45 byte inputs plus explicitly simulated trainer logs/state, six controlled failures (changed Train compiled bytes, Validation source bytes, wrong global step, missing training invocation, changed R46 report, missing state), and source-level absence-of-old-code verification. All **8/8 PASS**.

The guarded local patcher also passed **3/3** tests (expected original replaced with backup, idempotent no-op on fixed file, reject unrecognized code digest). Source and patch are included in a self-contained hotfix package with SHA256 manifest. **Synthetic test success does not constitute authentic HF Bucket input verification.**

Private handoff ZIP: `StoryForge_R53_R46_PRIMARY_EXPORT_SHA256_HOTFIX_20261021.zip`, SHA256 `62cdac84fc503da412e87320f41985f2381eaa26ec8ea934ea6eecb625429dca`, six members, no story contents, credentials, or original run exports.

The owner must rerun the corrected verifier on **their actual previously fetched seven remote R46 artifacts** to determine the historical exposure gate. No new GPU/CPU job launched. `R53_REAL_40_MASK_AUDIT` and rights/data-release gates stay pending; R50 sealed, Train/Val formally 0/0.
