# HF CPU dependency profiles

## Runtime core

`storyforge_dataset.hf_runtime` uses Python 3.11 standard library only. Do not install Transformers, PyTorch, ms-swift or HF Hub for Runtime-only checks.

## R60 literary reviewer compatibility profile

- Inputs: `hf-quality-reviewer.in` → hash-pinned `hf-quality-reviewer.lock`
- Direct pins: Transformers 4.57.1, SentencePiece 0.2.1, Jinja2 3.1.6; Hugging Face Hub remains `>=0.35,<3`.
- The lock resolves every transitive dependency and records SHA256 hashes; CI regenerates and compares it.
- This profile is intentionally separate from the R59 Qwen3.8 tokenizer profile below, which pins Transformers 5.16.1. Do not downgrade or merge those profiles.
- GitHub Actions installs this profile in an isolated Python 3.11 environment, runs `pip check`, verifies versions/imports, and executes a synthetic `apply_chat_template` smoke test.
- Use the committed hash lock for every HF Job. The `.in` file is only the direct-dependency source used to regenerate the lock.

Install for local compatibility checks:

```bash
python -m pip install --no-cache-dir --require-hashes -r requirements/hf-quality-reviewer.lock
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

| Lock | SHA256 |
|---|---|
| `hf-cpu-tokenizer.lock`（R59 / Transformers 5.16.1） | `2ed75a4057c01a3f6310aa790157b721d0bc640cfc27cd3a94d5e1718681da75` |
| `hf-quality-reviewer.lock`（R60 / Transformers 4.57.1） | `4a909bf5029245ead71ce28512e6f0f718f1097544a238e5c55db15736a3148f` |

GitHub Actions Run `42495819470`（commit `32c4965d18ef98cacc25f14de86b8ce824fb0bb5`）：两份 lock 均重新解析并与提交内容一致；hash-verified install、`pip check`、CPU-only boundary 与 R60 合成 `apply_chat_template` smoke 全部 PASS。
