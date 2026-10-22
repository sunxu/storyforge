# StoryForge R50 HF CPU46 — Tokenizer-load signature, cause still unknown

Date: 2026-10-22. Derived from the Owner's local **sanitized** classification of failed HF CPU-only Job `6ada2b71c191903149a728b1`, run key `r50-cpu46-20261022T151846Z-950025`. Do not reuse the old job/run key.

The original preflight exited `1`; the outer Worker exited `2`. An authorized local-only tool read the protected Worker log but released only whitelisted metadata:

- Private log SHA256: `097234a52f0726dacfe4a2905d10b2670949204d34d3a8165c1be69dee3f3120`.
- Private log length: 183 characters; stderr: 112 characters; no captured traceback and no recognized exception class.
- Classification: `TOKENIZER_LOAD_ERROR`. **This is a broad pattern classification and can match references to `tokenizer.json`; it is NOT proof of corrupted tokenizer files, a broken HF download, or a specific package error.**
- The pinned tokenizer-only Hub files were downloaded before the original script invocation, but remote `AutoTokenizer.from_pretrained` success was **not** established.

**Next action: NO NEW PAID JOB.** On the Owner Mac, perform a read-only static inspection of the original already-staged `private/R50_CPU_TOKENIZER_PREFLIGHT_46.py` together with the existing protected `R50_CPU46_PREFLIGHT_OUTPUT_PRIVATE.txt`. Release only script SHA256, whitelisted stderr error flags and tokenizer load call metadata (source line numbers, flags such as `use_fast`, `local_files_only`, `trust_remote_code`), never the original code or stderr itself.

Do **not** change the already-uploaded stage, restart the same key, reupload sealed candidate data or report any tokenizer PASS. After the specific root cause is established, make a versioned code correction, synthetic smoke tests, new stage and separately authorized paid CPU Job.

R50 candidate set remains 46 PRESEAL, official admitted 0, semantic isolation HOLD, final seal not performed, GPU/training/model inference disabled; R54 NOT_PROMOTED.

**Status:** `R50_CPU46_TOKENIZER_LOAD_SIGNATURE_ONLY__ROOT_CAUSE_UNKNOWN__OFFLINE_SOURCE_INSPECTION_NEXT__NO_RETRY`.
