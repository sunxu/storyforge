# StoryForge v0.1 — Gold-reference six-reviewer addendum (2026-10-10)

**State:** `SIX_REVIEW_FILES_VALIDATED / THIRD_PARTY_IDENTITY_NOT_VERIFIED`.

This directory is a post-freeze addition on `main`, **NOT** part of the immutable `v0.1-evidence-frozen` tag (`d1186a731a81219f86eb81b89ac1440dd116e9f4`). The historical quality disposition remains `ENGINEERING_PASS / QUALITY_PROMOTION_NOT_APPROVED`.

## Evidence

- `raw/StoryForge_R01.csv` through `raw/StoryForge_R06.csv`: six **byte-identical** original scored uploads (20 rows each). SHA256s in `source_manifest.json`. Source files' BOM and CRLF/LF are retained.
- `organizer/identity_map.json`: compact 120-case decode of the earlier organizer's `ANON_MAP_ORGANIZER_ONLY.json`, with reviewer ID, anonymized case, original source sample, comparison arm, and which side is Gold. The original organizer map's SHA256 and source ZIP SHA256 are in `source_manifest.json`. Map published by user authorization.
- `results/sample_majorities.csv`: original 40-pair majority table; original bytes preserved.
- `results/quality_summary.json`: key machine-readable results.
- `reports/StoryForge_v01_Gold_六评审原始回收审计_20261010.md`: original evidence analysis with detailed ratings and limitations.
- `source_manifest.json`: SHA256 of scored uploads and original distribution ZIPs, including original (not committed) Excel workbook checksum.

The source Excel workbook and the 6 original reviewer **distribution ZIPs** are not duplicated here; they are derivative/convenience packaging, while the scored CSVs preserve full stories, outputs and human notes. The ZIP SHA256s permit comparisons against the distributed copies; source distribution is retained by the project owner.

## Reproducibility

The 120-item `organizer/identity_map.json` was decoded directly from the original organizer package's mapping, before publishing the six scores. Use it to map each `R01-001` etc to the frozen eval sample ID and gold/model A/B roles. Recalculate votes, 5-dimension scores and majorities from the original scored CSVs, not from editorial examples. The underlying original held-out prompts and Base/Adapter response map remain in `evaluations/v0.1/test/`.

Verify the original CSV hashes with Python:

```bash
python3 - <<'PY'
import hashlib, json, pathlib
root = pathlib.Path("evaluations/v0.1/gold-reference/2026-10-10")
manifest = json.loads((root / "source_manifest.json").read_text())
for filename, expected in manifest["archive_original_sha256"].items():
    actual = hashlib.sha256((root / filename).read_bytes()).hexdigest()
    assert actual == expected, (filename, actual, expected)
print("SIX_ORIGINAL_REVIEW_CSV_SHA256_PASS")
PY
```

Observed preferences: Gold vs Base `38:22` (Gold-majority `14/20`); Gold vs Adapter `45:15` (Gold-majority `16/20`). Model quality differences are **retrospective**, and the judge identities/independence were **not** externally verified. Do not claim six independent people or a statistically proven production improvement from six file submissions.
