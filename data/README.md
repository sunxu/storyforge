# Data directory

Do not commit private/raw story exports or compiled training data.

Expected local layout:

```text
data/
├── raw/
│   └── 100条作品回答范例_完整上下文_JSONL_20260930/
└── compiled/
    └── v0.1/
        ├── train.jsonl
        ├── validation.jsonl
        ├── test.jsonl
        └── manifest.json
```

The top-level `.gitignore` intentionally excludes `data/raw/`, `data/private/`, and `data/compiled/`.

Validate the raw export:

```bash
storyforge-dataset validate data/raw/100条作品回答范例_完整上下文_JSONL_20260930 --expected-selected 100
```

Compile Dataset v0.1:

```bash
storyforge-dataset compile data/raw/100条作品回答范例_完整上下文_JSONL_20260930 --output data/compiled/v0.1 --history-messages 12
```
