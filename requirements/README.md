# HF CPU dependency profiles

## Runtime core

`storyforge_dataset.hf_runtime` uses Python 3.11 standard library only. Do not install Transformers, PyTorch, ms-swift or HF Hub for Runtime-only checks.

## R60 literary reviewer compatibility profile

- Input: `hf-quality-reviewer.in`
- Direct pins: Transformers 4.57.1, SentencePiece 0.2.1, Jinja2 3.1.6; Hugging Face Hub remains `>=0.35,<3`.
- This profile is intentionally separate from the R59 Qwen3.8 tokenizer profile below, which pins Transformers 5.16.1. Do not downgrade or merge those profiles.
- GitHub Actions installs this profile in an isolated Python 3.11 environment, runs `pip check`, verifies versions/imports, and executes a synthetic `apply_chat_template` smoke test.
- **Before using this profile for a paid HF Job**, resolve and commit a hash-pinned lock file with pip-tools; the current `.in` file is the reusable direct-dependency source, not a hash lock.

Install for local compatibility checks:

```bash
python -m pip install --no-cache-dir -r requirements/hf-quality-reviewer.in
python -m pip check
```

## Tokenizer-only CPU profile

- Input: `hf-cpu-tokenizer.in`
- Hash-pinned resolution: `hf-cpu-tokenizer.lock`
- Direct pins: Transformers 5.16.1, Tokenizers 0.23.3, huggingface-hub 1.33.0, Jinja2 3.1.6, SentencePiece 0.2.1.
- Lock resolver: pip-tools 7.5.0 under pip 24.3.1, Python 3.11.
- Lock contains hashes for all resolved packages.
- Verified by GitHub Actions using `pip install --no-cache-dir --require-hashes`, `pip check`, and an assertion that PyTorch is not installed.

Install only for a CPU Tokenizer Job:

```bash
python -m pip install --no-cache-dir --require-hashes -r requirements/hf-cpu-tokenizer.lock
python -m pip check
```

Do not install this profile for Runtime-only jobs. It intentionally excludes PyTorch, ms-swift, vLLM, torchvision, decord and CUDA packages. The tokenizer-only Runner uses `AutoTokenizer`; it does not load model weights or execute inference.

To regenerate the lock, use the dedicated `.github/workflows/r60-hf-cpu-lock-resolve.yml` workflow. Review changes to every direct and transitive pin before committing; do not update dependencies automatically.


当前 lock SHA256：

```text
a48957b2337d703f4629206663e74d9986482c6905e63013a46dc8662204cfba
```

GitHub Actions lock resolution Run `41807222164`：提交锁与新解析结果一致，clean hash-verified install、`pip check` 通过，且 `torch` 不存在。
