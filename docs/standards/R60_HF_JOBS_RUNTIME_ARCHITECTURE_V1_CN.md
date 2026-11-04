# R60 Architecture Baseline v1.0 — HF Jobs Runtime

> Status: APPROVED / FROZEN FOR IMPLEMENTATION  
> Date: 2026-11-04  
> Repository: `sunxu/storyforge`  
> Development base: `gold-quality/quality-v1-sft-candidates` @ `adc3876d6d0350c270e2b5fa5ccc832438fdf7ee`  
> Target branch: `r60/hf-jobs-runtime`  
> Python: 3.11  
> GPU authorization: NONE

## 1. Scope and invariants

R60 builds reusable, business-agnostic execution infrastructure for StoryForge Hugging Face Jobs. It is not an R59 hotfix branch.

Hard invariants:

- Runtime code MUST NOT import Gold, R50, R57, R58 or R59 business data, schemas, prompts, ledgers, checkpoints or private paths.
- Runtime MUST NOT submit jobs, call Hugging Face APIs, download models, initialize CUDA, infer, train, or admit data.
- Runtime MUST NOT import or refactor `storyforge_dataset.token_preflight`; that module remains unchanged and is consumed only by explicit adapters.
- Core Runtime has no third-party runtime dependencies. It uses Python 3.11 standard library only.
- CPU/GPU policy is deny-by-default. `doctor --profile cpu` diagnoses; it does not acquire resources or execute work.
- SAFE diagnostics never contain private input values, raw exception messages, credentials, environment dumps, or arbitrary paths.
- All writes are create-only by default. No implicit overwrite, retry, namespace fallback, or partial success.
- The Runtime reports technical execution facts only. It cannot assert data quality, dataset admission, training authorization, or model performance.

## 2. Package layout

```text
src/storyforge_dataset/hf_runtime/
  __init__.py
  __main__.py
  context.py
  paths.py
  inputs.py
  outputs.py
  diagnostics.py
  resources.py
  receipts.py
```

The seven approved modules are exactly:

1. `context.py` — immutable runtime/environment context.
2. `paths.py` — host/container path mapping and path policy.
3. `inputs.py` — safe input open, bounded read, digest and identity.
4. `outputs.py` — output capability probe and create-only SAFE write.
5. `diagnostics.py` — stable error taxonomy, phase tracking and SAFE JSON.
6. `resources.py` — CPU profile enforcement and GPU denial checks.
7. `receipts.py` — strict schema and invariant validation for Runtime receipts.

`__main__.py` is the module CLI entry point, not an eighth Runtime subsystem.

## 3. Public API contract (v1)

The following API is the initial public surface. Implementations may add private helpers, but must not silently change these contracts within v1.

### context.py

- `RuntimeContext.detect(*, profile: str = "cpu", environ: Mapping[str, str] | None = None) -> RuntimeContext`
- `RuntimeContext.to_safe_dict() -> dict[str, object]`

Context fields: schema/version, Python implementation/version, OS/platform, execution profile, detected container/HF hints (boolean or allowlisted enum only), and Runtime package version. Never serialize the complete environment.

### paths.py

- `PathResolver.resolve(path: str | Path, *, kind: Literal["host", "container", "auto"]) -> ResolvedPath`
- `PathResolver.validate_input_root(path: Path) -> Path`
- `PathResolver.validate_output_root(path: Path) -> Path`

Path mapping is explicit. `auto` is diagnostic convenience only and MUST NOT be used to resolve security-sensitive paths where host/container identity is ambiguous. Reject traversal, unexpected roots, NUL, symlinks in protected path components, and non-absolute paths where absolute paths are required.

### inputs.py

- `InputManager.open_verified(path: Path, *, max_bytes: int, expected_sha256: str | None = None, require_regular: bool = True) -> VerifiedInput`
- `VerifiedInput.read_bytes() -> bytes`
- `VerifiedInput.to_safe_dict() -> dict[str, object]`

Open with no-follow semantics where supported; validate the opened descriptor with `fstat` (not only a prior path check); require a regular file; enforce size limits before and during reads; calculate SHA256 while reading; compare an expected digest when supplied. Do not follow symlinks. File mode and link count are evidence, not portable identity guarantees: HF-managed mount metadata can be normalized. The policy MUST distinguish permission metadata from content integrity and descriptor identity.

### outputs.py

- `OutputManager.probe(root: Path) -> OutputCapability`
- `OutputManager.write_safe(path: Path, payload: Mapping[str, object], *, mode: int = 0o600) -> WriteReceipt`

The output parent must already exist, be a directory, and pass a real create/write/fsync/remove probe. The destination must not exist and must not be a symlink. Create-only publication must be race-safe (exclusive creation or same-filesystem no-replace publication); never use a check-then-overwrite sequence. Use restrictive mode where the filesystem honors it, flush and fsync, and verify the final object. Failure cleanup may remove only the inode created by this operation. Never recursively chmod/chown a managed mount.

### diagnostics.py

- `DiagnosticReporter.start_phase(name: str) -> None`
- `DiagnosticReporter.fail(code: ErrorCode, *, phase: str | None = None) -> Diagnostic`
- `DiagnosticReporter.to_safe_dict() -> dict[str, object]`
- `DiagnosticReporter.write_safe(path: Path) -> WriteReceipt`

Diagnostics use allowlisted fields and error codes. Exception text, stack traces, arbitrary paths, environment values and user data are excluded from SAFE output. Full local debugging, if ever needed, must be a separately authorized private channel and is not part of v1.

### resources.py

- `ResourceGuard.check_cpu_only(*, environ: Mapping[str, str] | None = None) -> ResourceReport`
- `ResourceGuard.check_profile(profile: str, *, environ: Mapping[str, str] | None = None) -> ResourceReport`

CPU profile requires CUDA visibility to be disabled and rejects positively detected CUDA devices or GPU execution indicators. Unknown states fail closed for an execution authorization decision; diagnostic-only doctor reports UNKNOWN distinctly and exits non-zero for unmet CPU profile requirements. Runtime never changes profile to GPU.

### receipts.py

- `ReceiptValidator.validate_runtime_receipt(value: object) -> RuntimeReceipt`
- `ReceiptValidator.verify_file(path: Path, *, expected_schema: str, max_bytes: int = 32768) -> RuntimeReceipt`

Validate exact schema/version, required field types, enumerated status, SHA256 format, phase/error consistency and safety invariants. Unknown schema versions and extra private-bearing fields are rejected. Business-specific receipts remain the responsibility of their adapters.

## 4. Stable error code registry (v1)

Codes are stable public identifiers. Human-readable messages may evolve; code meanings may not.

| Domain | Error codes |
|---|---|
| CONTEXT | `RUNTIME_CONTEXT_UNSUPPORTED`, `RUNTIME_PROFILE_INVALID`, `RUNTIME_ENVIRONMENT_UNKNOWN` |
| PATH | `PATH_NOT_ABSOLUTE`, `PATH_TRAVERSAL_REJECTED`, `PATH_SYMLINK_REJECTED`, `PATH_ROOT_NOT_ALLOWED`, `PATH_KIND_AMBIGUOUS`, `PATH_NOT_FOUND`, `PATH_TYPE_INVALID` |
| INPUT | `INPUT_OPEN_FAILED`, `INPUT_NOT_REGULAR_FILE`, `INPUT_SYMLINK_REJECTED`, `INPUT_SIZE_LIMIT_EXCEEDED`, `INPUT_READ_FAILED`, `INPUT_SHA256_MISMATCH`, `INPUT_DESCRIPTOR_CHANGED` |
| OUTPUT | `OUTPUT_PARENT_INVALID`, `OUTPUT_PROBE_FAILED`, `OUTPUT_ALREADY_EXISTS`, `OUTPUT_SYMLINK_REJECTED`, `OUTPUT_CREATE_FAILED`, `OUTPUT_WRITE_FAILED`, `OUTPUT_FSYNC_FAILED`, `OUTPUT_VERIFY_FAILED`, `OUTPUT_CLEANUP_FAILED` |
| RESOURCE | `CPU_PROFILE_GPU_VISIBLE`, `CPU_PROFILE_CUDA_DEVICE_DETECTED`, `CPU_PROFILE_RESOURCE_UNKNOWN`, `RESOURCE_PROFILE_UNSUPPORTED` |
| RECEIPT | `RECEIPT_READ_FAILED`, `RECEIPT_SCHEMA_UNKNOWN`, `RECEIPT_SCHEMA_INVALID`, `RECEIPT_FIELD_INVALID`, `RECEIPT_DIGEST_INVALID`, `RECEIPT_INVARIANT_FAILED`, `RECEIPT_SIZE_LIMIT_EXCEEDED` |
| CLI | `CLI_ARGUMENT_INVALID`, `CLI_DOCTOR_FAILED` |
| INTERNAL | `RUNTIME_INTERNAL_ERROR` |

Never derive a public code from an exception class/message. Map known failures to this registry; unknown failures become `RUNTIME_INTERNAL_ERROR`.

## 5. Diagnostic and doctor schema

Diagnostic schema: `storyforge-hf-runtime-diagnostic-v1`.

Required top-level fields:

- `schema`
- `runtime_version`
- `profile`
- `status`: `PASS` | `HOLD` | `FAIL`
- `phase`
- `error_code`: registered code or null
- `checks`: fixed allowlisted check names with `PASS` | `FAIL` | `UNKNOWN`
- `environment`: safe platform/runtime facts only
- `private_values_emitted`: always false
- `gpu_started`: always false for this Runtime
- `training_performed`: always false

Doctor command (P0):

```bash
python -m storyforge_dataset.hf_runtime doctor --profile cpu --json
```

Doctor is read-only except for a bounded, uniquely named temporary output capability probe which it must clean up. It MUST NOT read business inputs, enumerate private directories, print environment variables, contact the network, invoke `hf`, import Transformers/ms-swift, or initialize torch/CUDA. JSON mode emits exactly one JSON object to stdout; human diagnostics go to stderr only in non-JSON mode. Exit codes: 0 = all required CPU checks PASS; 2 = one or more checks FAIL; 3 = required state UNKNOWN / doctor could not complete. Output must be deterministic apart from explicitly declared platform/version fields.

## 6. File and privacy security policy

- Reject symlinks for protected inputs, output roots and final destinations. Use descriptor-level checks to reduce TOCTOU exposure.
- Require regular files for input and receipt reads. Apply explicit byte limits before allocation and while streaming.
- Verify bytes with SHA256 when a source digest is available; hashes prove byte identity, not authorization or quality.
- Do not treat `chmod 0600`, `st_nlink == 1`, owner UID, or mountpoint mode as universal proofs. Report unavailable/normalized metadata as UNKNOWN; enforce the properties the mounted filesystem can actually guarantee.
- Output roots are caller-supplied, pre-created and outside Git checkout for private artifacts. The Runtime does not invent a private-data location.
- SAFE outputs contain aggregate technical facts only. No raw content, prompt, story text, user/character identifiers, credentials, tokens, DSNs, arbitrary paths, or exception messages.
- No overwrite, recursive cleanup, automatic retry, fallback namespace, or output-prefix reuse.
- Runtime tests use synthetic fixtures only. No production/private files in tests or CI.

## 7. Dependency and compatibility policy

- Python: 3.11 (project requires `>=3.11`; R60 CI and documented HF runtime baseline use 3.11).
- Runtime dependencies: Python standard library only; no new runtime packages.
- Existing project optional dev dependencies remain `pytest>=8.0`, `ruff>=0.8`, `PyYAML>=6.0`; R60 core must not require PyYAML.
- HF/model packages (`ms-swift`, `transformers`, `torch`, `huggingface-hub`) are explicitly outside Runtime dependency scope and must not be imported by doctor.
- Existing adapter-specific pins remain adapter-owned. R60 does not upgrade or change them.
- No edits to `pyproject.toml` dependency ranges are required for the core Runtime.

## 8. Test strategy and stage gates

1. Pure unit tests: synthetic temp directories, monkeypatched environment, deterministic fake descriptors where needed.
2. Security tests: symlink, traversal, race/no-overwrite, size limits, digest mismatch, descriptor metadata, partial-write cleanup, privacy allowlist.
3. Platform tests: macOS and Linux CI; platform-specific guarantees explicitly marked supported/unsupported/unknown.
4. CLI tests: subprocess invocation of `python -m ... doctor --profile cpu --json`, stdout purity, exit codes, no network/model imports.
5. Integration tests: synthetic HF-like RO/RW mount simulation locally. No real HF Job until all local tests and GitHub CI are green.
6. HF CPU Smoke is a separate paid gate requiring an explicit Owner go-ahead at the point of submission. GPU remains unauthorized.

Every stage must record commit SHA, exact test commands, exit codes, CI run URL/status and remaining risks. A test not run is NOT RUN, never PASS.

## 9. Explicit non-goals

No changes to R50; no Gold/Quality admission; no R59 private source, staged JSONL, prompt, checkpoint or training artifacts; no database access; no HF Job submission in implementation stages; no GPU; no model download; no training; no automatic data transformation.

## 10. Acceptance criteria

- Seven modules and P0 doctor CLI exist and have documented public contracts.
- Existing `token_preflight.py` has unchanged blob SHA.
- Runtime has zero third-party runtime dependencies and doctor has no network/model/GPU side effects.
- Local macOS/Linux synthetic test suite and GitHub CI pass.
- HF CPU Smoke is only considered after those gates; its result is separately recorded and does not imply dataset admission or training authorization.
- A new Skill and Chinese technical standard document the reusable Runtime contract after implementation stabilizes.
