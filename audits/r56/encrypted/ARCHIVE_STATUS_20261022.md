# StoryForge R56 — Owner-key age encrypted private audit archive

**Status (2026-10-22):** `ALL_FOUR_CIPHERTEXTS_VERIFIED_ON_GITHUB_MAIN__STAGE5_OWNER_AGE_DECRYPT_ZIP_CRC_PASS__NO_TEST_ADMISSION`

All four audit archives are stored only as **ASCII-armored age v1/X25519 ciphertext**, encrypted to the Owner-controlled public key:

`age10ffvkjh0cq3fcknk8q7h0jkjtmvay35v8ft2yw59y08md3f4nf2qz5d6wp`

| Encrypted archive in this directory | Bytes | Ciphertext SHA256 | Git blob SHA-1 | Remote |
|---|---:|---|---|---|
| `stage2-review-input-20261022.zip.age` | 146562 | `443623eef32f8a33c85cd4df2ed6bb823a2fe3d69eb42940f6881896f3afc8a6` | `cf4fd6e7fb286e2e459a505fa44bf32312cc25e9` | VERIFIED |
| `stage2-gold32-review-20261022.zip.age` | 48900 | `bd614913f185329a28b1abb9d1b2c47bb8f86d60d46584e4ccb9f514cf1fb82d` | `71053746408c57b0ef52385e090864259fa51706` | VERIFIED |
| `original03-05-replay-20261022.zip.age` | 64890 | `0b1a3fe4368d86819b4479656c11547b6efe7c33aaf396a4a03b1e2835e2cf44` | `3bb3b9f4cdad0f9c6d5a44b58797f170b1e4ddd4` | VERIFIED |
| `stage5-world11-review-20261022.zip.age` | 217461 | `06d8e1c6f138156f1a1790af1a37200958c8b898b499bacc82c67d3cecf6b6d4` | `cc53e53625ac1c9f4896697de27ed3f19af5c327` | VERIFIED |

### Remote validation and provenance

- The final Stage5 ciphertext was committed to `main` as `1043f23254c3e294599dd53e7d9b912db930a65b` (`audit(r56): archive Owner-key encrypted Stage5 World11 private review`).
- A separate follow-up read of GitHub `main`'s **non-truncated full Git tree** confirmed the presence, exact size, and SHA-1 Git blob ID of **4/4 files**. All four blob IDs match independently computed Git blob hashes of the ciphertext copies retained for this audit.
- The Owner Mac returned `STAGE5_AGE_DECRYPTED_AND_ZIP_CRC_PASS__GIT_PUSH_ATTEMPTED`. The output establishes **Owner-reported successful official age decryption and ZIP CRC for Stage5**; the push was independently confirmed through the remote `main` tree and commit API, not inferred from the word `ATTEMPTED`.
- Other three input ZIP files passed local CRC *before encryption*; their ciphertexts passed local encryption-format / SHA256 checks. The available conversation does **not** contain independent Mac `age -d` receipts for these three files. Do not claim the same official Owner-private-key decryption check for them.
- The public count-only `MANIFEST_COUNTS_ONLY.json` lists the four file sizes and ciphertext SHA256 hashes; it includes no plaintext, characters, identities or unblinding keys.
- The Owner's private age identity and decrypted plaintext are **not present in Git**. Do not give the identity to Reviewers or commit temporary plaintext. Keep other authorized collaborators' access to audit ciphertext appropriately restricted.

### Evaluation boundary (unchanged)

Code and encrypted evidence archival is **not** independent Reviewer signoff or four-world Held-out approval. Original R56 provisional cases **24 HOLD**; official fresh Held-out admission **0**; world semantic independence **HOLD**. No access to sealed R50, new GPU inference/training, or R54 promotion was performed.

**Final archive status:** `FOUR_OF_FOUR_GIT_ENCRYPTED_FILES_PRESENT__STAGE5_DECRYPTED_BY_OWNER__OFFICIAL_TEST_ADMITTED_0`.
