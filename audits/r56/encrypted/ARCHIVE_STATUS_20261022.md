# StoryForge R56 — Owner-key age encrypted private audit archive

This directory only stores **ASCII-armored age v1/X25519 ciphertext** and count-only SHA256 metadata. It does not authorize new model evaluation, training or access to R50.

Owner supplied recipient public key:
`age10ffvkjh0cq3fcknk8q7h0jkjtmvay35v8ft2yw59y08md3f4nf2qz5d6wp`

## Committed files (remote byte equality verified in this conversation)

| Archive | Ciphertext SHA256 | Status |
|---|---|---|
| `stage2-review-input-20261022.zip.age` | `443623eef32f8a33c85cd4df2ed6bb823a2fe3d69eb42940f6881896f3afc8a6` | GIT VERIFIED |
| `stage2-gold32-review-20261022.zip.age` | `bd614913f185329a28b1abb9d1b2c47bb8f86d60d46584e4ccb9f514cf1fb82d` | GIT VERIFIED |
| `original03-05-replay-20261022.zip.age` | `0b1a3fe4368d86819b4479656c11547b6efe7c33aaf396a4a03b1e2835e2cf44` | GIT VERIFIED |
| `stage5-world11-review-20261022.zip.age` | `06d8e1c6f138156f1a1790af1a37200958c8b898b499bacc82c67d3cecf6b6d4` | LOCAL ENCRYPTED / GIT UPLOAD PENDING |

`MANIFEST_COUNTS_ONLY.json` lists the four SHA256 fingerprints, including the pending upload. **Do not mistake its listing for a claim that all four ciphertexts are present on GitHub.**

## Validation limits

- Four input ZIPs passed CRC before encryption; four ciphertext files passed local SHA256 integrity checks and format/header checks.
- Encryption was implemented according to the public C2SP age v1/X25519 format using the installed cryptography library. A round-trip on a disposable test identity passed different lengths, including chunk boundaries; the Owner's secret identity never entered the assistant runtime.
- The official `age -d` executable was **not available in the assistant runtime** and could not be downloaded. Therefore **interoperability and decryptable ZIP CRC have NOT been independently validated against the Owner's private key**. Owner must first test `age -d -i ~/.config/storyforge/r56-age-identity.txt` and `unzip -t` in a secure temporary folder outside Git.
- User's Owner public key was checked as checksum-valid age Bech32. No private identity is or may be committed.
- Even encrypted reviewer reports should be accessible only to appropriately authorized repository readers. Audit ciphertext is not a blind-test key or formal reviewer signoff.
- All R56 24 provisional cases remain HOLD, formal test admissions 0, R50 sealed, no GPU/training/model promotion.

To complete the pending Stage5 encrypted file, use the downloadable artifact `StoryForge_R56_PrivateAudits_Encrypted_age_20261022.zip` and the companion Mac verification/push script. Keep decrypted ZIPs **outside** the Git worktree.

**Status**: `OWNER_AGE_KEY_VALID__THREE_GIT_CIPHERTEXTS_VERIFIED__ONE_LOCAL_PENDING__NO_TEST_ADMISSION`.
