# StoryForge R56 — Git-first (CPU-only)

This folder holds **versioned, non-secret tooling only**. The audited originals, case IDs, Gold targets, private reviewer decisions, source-to-case mappings, stage4/5 raw-source report JSON and sealed R50 prompts **must never be committed as plaintext**.

## What was imported

Scripts and corresponding synthetic regression tests from R56 CPU preflight, Owner receipt validation and the Stage2 source/decision validators (as explicitly listed in `SAFE_SOURCE_MANIFEST.json`). **Some later-stage specialized scripts were deliberately withheld:** they embed private world UUIDs, character aliases or source hashes, and still require parameterization and a second privacy audit before public-source check-in.

## How to test

```bash
python3 -m unittest discover -s tools/r56/tests -p 'test_*.py' -v
```

This tests code behavior with synthetic examples; it does **not** independently replay the 195 Gold records, 32 content audits or 18 KSG cases. Original evidence receipts remain in `docs/evidence/`.

## Run policy

- Do not overwrite source archives, original Gold or R50.
- All model test candidates remain `HOLD_NOT_TEST_ADMITTED`; the content/replay tools do not grant admission.
- No GPU / HF Job / training / promotion invoked by this source commit.
- Local private source and reviewer audit material: `~/.local/share/storyforge/r56/`, mode `0700` directories and `0600` files.
- If archiving private material in Git, first encrypt it to a recipient **controlled by Owner** via `age`. The key must live outside the repository. The scripts here do not create, retain or upload the secret key.
- Prefer keeping even encrypted archives in a dedicated restricted repository rather than ordinary `main`. Never assume a private repository or Git LFS alone guarantees reviewer blinding.
- Before any private ciphertext is committed, verify its intended recipient, decryptability and scope. Do not commit plaintext alongside it.

## Source integrity

`SAFE_SOURCE_MANIFEST.json` includes SHA256 for every imported source/test text and only file paths; the manifest does not include raw Gold bodies or private case identifiers. Future changes should be reviewed against the manifest and captured in Git history.
