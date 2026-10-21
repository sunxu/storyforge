# StoryForge R53 — Owner-side formal private 31/9 data release receipt accepted

Date: 2026-10-21 (Asia/Singapore)

**Accepted status:** `R53_PRIVATE_31_9_OWNER_RELEASE_RECEIPT_ACCEPTED__NO_GPU__R50_SEALED`

## Scope, evidence, and authority

The Owner explicitly authorized formal **PRIVATE** release of the frozen R53 31 Train + 9 Validation data, with exact Stage manifest SHA256 `00b8182812d8bbc33eaacede962506ec718c6b987ef82c429f75401c4c107261`. This does **not** authorize paid GPU, starting model training, public dataset publication, or accessing sealed R50. Seven-story training rights are admitted under the project's **Owner self-attestation policy**, not claimed as independently verified by a third party.

The Owner uploaded the resulting **Mac-side V4 release receipt** `R53_RELEASE_RECEIPT.json`; its independently computed byte SHA256 is:

`3d8078ee3b4528521b7f67ba1dd7983f0d20bfeb4d7c79e92d9cabe2c6b2e836`

The receipt status is exactly `DATA_ONLY_RELEASE_APPROVED__GPU_NOT_AUTHORIZED`, with `train_rows=31`, `validation_rows=9`, `gpu_authorized=false`, `r50_sealed=true`.

## Independently recomputed checks from locally retained frozen private stage

Original V4 check_staged() re-executed successfully on the frozen Stage, yielding 31 Train / 9 Validation rows and the unchanged source data and component boundaries. Original V4 compiled_payload() was re-executed from the frozen source to recompute the expected formal output byte hashes:

- **train.jsonl** SHA256: `d0425c54b534307047457d05e6890b50076ad2d23ce9ab3d52f94d1a3db585a7`
- **validation.jsonl** SHA256: `b5ea4075419ce02a1340f6ece875068746918ce1d4c6d72ee2f799b3fe58754d`

Both hashes match the returned final release receipt, the original HF CPU40 report's compiled input hashes, and the prior pinned Stage.

A total of **24/24 local receipt cross-check conditions passed**, including recomputing nine referenced original evidence-file hashes from the retained private packet:

- world certificate and scoped Owner world policy;
- **Reviewer E corrected DELIVERY ZIP** `StoryForge_R52_WORLD7_21PAIR_INDEPENDENT_REVIEWER_E_CORRECTED_DELIVERY_20261021.zip` SHA256 `678d60c69176645808006c2d742109b28b5d10bb2e7faac06d13b5cb4ee4103f` (distinct from the **Adjudication ZIP**, which has its own digest);
- original HF CPU40 report `8624c21b6d9fff5e74006bca000c69f0d39870f1fb030c2ff4fb96cc523f1f45` and Owner-machine intake `b3bff2625c360aad10d985b42884263a26a72e85e7d1ddc7d0df916b6598381e`;
- exact Owner data-only authorization, Owner-attested seven-story rights policy, original provenance inventory and R45/R46 historical exposure receipt;
- pinned model `Qwen/Qwen3.8-27B@1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`, source-bounded world policy, declaration-limited rights basis, GPU prohibited and R50 sealed.

The CPU runtime log SHA256 quoted in the release receipt matches the earlier Owner-machine original CPU intake receipt:
`7ebe369f83b168d2c3f0830c91cd77370154638d74482fe57cdc93e55d8ca39f`.

Local aggregate-only acceptance JSON:
`R53_FORMAL_PRIVATE_RELEASE_RECEIPT_INDEPENDENT_INTAKE_SAFE_20261021.json`, SHA256 `0f98c7ba621f74d737cd32c2d8018d6a9db00759c2aa120ed3bb33161947ab72`.

## Integrity limits and decision

**Accept** the returned Owner-side V4 formal private data-only release receipt as sufficient under this project's scoped audit process: formally admitted **31 Train / 9 Validation**, no GPU/model training authorized or performed by this action, and R50 sealed.

**Do not overstate** this finding. The locally generated final `train.jsonl` and `validation.jsonl` on the Owner's Mac were **not** themselves uploaded to or byte-read in this conversation; their deterministic contents were independently reconstructed and hashed from the original frozen private Stage. Original runtime worker log bytes were not present here to rehash independently; prior Owner-machine official-verifier log digest was cross-matched. The JSON receipt is an Owner-returned record, **not a cryptographic HF-provider attestation**.

The data may be used for separately authorized later private training; **a future GPU/model training task remains separately blocked until explicit Owner approval**. Historical 6 HOLD candidates remain excluded and R50 remains sealed.

No story prose, private candidate IDs, training samples, secrets or complete private receipts are included in this GitHub documentation.
