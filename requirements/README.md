# HF CPU dependency profiles

## Runtime core

`storyforge_dataset.hf_runtime` uses Python 3.11 standard library only. Do not install Transformers, PyTorch, ms-swift or HF Hub for Runtime-only checks.

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
