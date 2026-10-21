# StoryForge R53 — Explicit Owner authorization for frozen private 31/9 dataset

Date: **2026-10-21**, Asia/Singapore.

**Current status:** `OWNER_EXPLICIT_DATA_ONLY_RELEASE_AUTHORIZED__PUBLISH_PENDING_ORIGINAL_CPU_LOG__NO_GPU__R50_SEALED`.

## Actual Owner authorization received

The Owner explicitly instructed in the current ChatGPT conversation:

> 授权正式发布 R53 冻结的 31 Train / 9 Validation 数据，清单 SHA256 为 `00b8182812d8bbc33eaacede962506ec718c6b987ef82c429f75401c4c107261`。仅批准私有训练数据准入，不授权 GPU，不开放 R50。

This authorization is accepted for the **exact 31 Train / 9 Validation private data release only**. It is a recorded conversational Owner instruction, **not** a verified cryptographic signature. It does not authorize GPU/model training, public posting, or opening sealed R50.

Frozen source-inclusive Stage SHA256s:
- Train, 31 rows: `f17fc33f566b5a1ddd424de2d26a032a812453255c76e0f5fa321fb0f3a9ecf9`.
- Validation, 9 rows: `83e3d1ab4cc955c4b5bba2afc63f355a227934a89203bcc058cfb922a093b01d`.

Expected formally released **message-only** hashes, subject to remaining V4 verifier:
- `train.jsonl`: `d0425c54b534307047457d05e6890b50076ad2d23ce9ab3d52f94d1a3db585a7`.
- `validation.jsonl`: `b5ea4075419ce02a1340f6ece875068746918ce1d4c6d72ee2f799b3fe58754d`.

Owner declaration-based rights policy and source-bounded Reviewer E world evidence policy were accepted on separate prior user instructions. The original source contents, six excluded HOLD records, owner-machine R46 source export receipt, authentic CPU40 report and owner-machine intake receipt are unchanged.

## Authorization artifact and portable private handoff

The new owner-authorization record `private_evidence/R53_OWNER_DATA_RELEASE_AUTHORIZATION.json` SHA256 is `068068ff7ac714ac19ff385b9ae608814be3f1974fe538c26877184b53cc8c4f`.

PRIVATE ZIP **not uploaded to ordinary Git**: `StoryForge_R53_OWNER_AUTHORIZED_DATA_ONLY_RELEASE_HANDOFF_PRIVATE_20261021.zip`, SHA256 `7720ff56cd4054a761353da44f109fb7bc7e32168fc0047f7443bed75e5883a1`. 36 members, ZIP CRC PASS and all member SHA256 verification PASS. Bundle includes unchanged V4 release verifier and V1/V2/V3 historical guards, actual frozen stage, accepted evidence, new scoped authorization, a single read-only-log-fetch-and-verify local release script and Chinese instructions.

Safe status receipt `R53_OWNER_DATA_ONLY_RELEASE_AUTHORIZATION_INTAKE_SAFE_20261021.json`, SHA256 `a1cb3354fbaf1abf1d64fb50ed322e48b191d4459ee2899e37f387c63f816fee`, has no story contents or private case identifiers.

## Actual tests and remaining evidence check

The historical V1/V2/V3 and new V4 negative-test sets all re-executed on the authorized private source bundle:
- V4 **15/15 PASS**
- V3 **12/12 PASS**
- V2 **14/14 PASS**
- V1 **10/10 PASS**
- Total **51/51 PASS**.
- Wrapper shell syntax PASS, release authorization exact stage hashes and no-GPU/no-R50 properties PASS.
- The actual unchanged V4 release CLI was executed with the authorized Owner JSON. It returned **exit 2** due solely to absence of `evidence/R53_CPU40_RUNTIME_LOG_PRIVATE.txt` from the current conversation environment. **No formal release directory or partial train/validation files were created**. A blocked-download offline wrapper regression also failed closed with exit 2.

The earlier CPU-only HF Job `6ad8a7af0a35baab53a1ced2` succeeded, and the Owner-machine original strict verifier successfully checked its runtime log. But the original log file was not attached to this conversation. Its required SHA256, recorded from that intake, is `7ebe369f83b168d2c3f0830c91cd77370154638d74482fe57cdc93e55d8ca39f`; we cannot independently rehash unseen bytes here.

## Next completion step (no billable Job)

On the **Owner's already authenticated Mac**, extract the private ZIP into a new directory and run `bash scripts/r53_authorized_data_release_local.sh`. It only fetches the **existing original CPU runtime log** from the private HF Bucket (if absent), verifies its exact SHA256, then invokes the unchanged V4 gate with the exact Owner authorization and atomically issues:
- private `R53_FORMAL_DATA_ONLY_RELEASE_31_9/train.jsonl`
- private `R53_FORMAL_DATA_ONLY_RELEASE_31_9/validation.jsonl`
- `R53_FORMAL_DATA_ONLY_RELEASE_31_9/R53_RELEASE_RECEIPT.json`.

If a hash/source/owner gate fails, it refuses the release. Existing destinations are not overwritten. The release script does **not** call `hf jobs run`, `swift sft`, or access R50. Formal Train/Val remains **0/0 in this execution environment** until the script's authentic V4 PASS receipt is returned.

This report is aggregate-only, without confidential story texts, credentials or case identifiers.
