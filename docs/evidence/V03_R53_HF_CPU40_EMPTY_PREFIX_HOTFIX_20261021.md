# StoryForge R53 — HF CPU40 empty-prefix and remote-ready guard hotfix

Date: 2026-10-21

**Status:** `HF_CPU40_PREFIX_CHECK_FIXED_OFFLINE__REMOTE_SYNC_PENDING__PAID_CPU_NOT_AUTHORIZED__NO_DATA_RELEASE`.

## Symptom and verified diagnosis

The owner attempted `bash scripts/v03_r53_hf_cpu40_submit.sh sync <private_stage>`. It completed `R53_STAGE_PREFLIGHT_PASS 31/9` and `R53_PINNED_AUDITOR_SOURCE_PASS`, then stopped with `R53_REMOTE_RUN_PREFIX_ALREADY_EXISTS`.

Previous launcher lines treated `hf buckets ls "$PREFIX/runs/$RUN_KEY"` **exit code 0** as proof that the run prefix had existing objects. Bucket prefix listing can succeed even for an empty prefix, so this is not a valid existence check. The previous `submit` path also used a listing exit code as a manifest-presence test.

## Fix / anti-bypass protections

- Added `scripts/v03_r53_hf_bucket_prefix_guard.py` (Git blob `2313febc173a6b1ee924c6edfddd1124846bac3a`), using documented `HfApi.list_bucket_tree(bucket_id, prefix=..., recursive=True)` to enumerate actual remote objects.
- Updated `scripts/v03_r53_hf_cpu40_submit.sh` (Git blob `461fc9ccddfbda3efb819ab80dfcc63ffcbb7fe4`).
- **sync** proceeds only if the exact randomly generated run prefix has zero objects. Existing partial/full contents, malformed listing, authentication failure and network errors all fail closed before upload. It never overwrites an occupied prefix.
- **submit** checks that the exact seven expected remote run objects are present, with no extras, before the `hf jobs run` command. The in-Job frozen data SHA256 and original audit-source checks are unchanged.
- The same two explicit paid CPU scope gates are preserved. No GPU, no `swift sft`, no training authorization.
- Added `tests/test_v03_r53_hf_bucket_prefix_guard.py`, 10/10 network-free tests PASS, shell syntax PASS. Git copies of helper, launcher and tests were verified against matching local Git blobs.

Local-only hotfix ZIP: `StoryForge_R53_HF_CPU40_PREFIX_GUARD_HOTFIX_20261021.zip`, SHA256 `159746630700e8ac4098329fe5a4180ba67e731f0b39bdedf785222f43fd9733`, 5 CRC+manifest checked members; **no private source text or credentials**.

## Next safe user step

From the latest `main` checkout, rerun:

```bash
python3 -m unittest discover -s tests -p 'test_v03_r53_hf_bucket_prefix_guard.py' -v
bash scripts/v03_r53_hf_cpu40_submit.sh sync "$HOME/.local/share/storyforge/r53-cpu40/private_stage"
```

If local HF CLI and Python environments differ, the helper may require running with the Python environment where `huggingface_hub` is installed and authenticated. An environment/API failure is **BLOCKED**, never treated as an empty prefix.

Do not infer remote 31/9 sync PASS or actual ms-swift/Qwen 40/40 from local testing. No billable CPU Job is launched by `sync`; Bucket storage/transfer billing is separate. R50 stays sealed; 31/9 formally NOT ADMITTED; GPU not authorized.
