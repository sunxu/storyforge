# StoryForge v0.2 — R47.1 three-arm historical regression: generation reported complete, collection pending

**Recorded 2026-10-14.** User's private HF Job log shows a completed Job after 20/20 v0.2 generations were persisted. **The full R47_PRIVATE_RUN_REPORT.json and blind package have not yet been fetched in this chat.** Do not confuse Job completion with final blind package acceptance.

## Execution identity

- Resumed HF GPU Job: `6acf48935ccb47ba0f79853d` (owner-reported status `completed`).
- R47 resume RUN_KEY: `r47-20261014T091647Z-637890`.
- Result prefix: `hf://buckets/adradar/storyforge-training/evaluation-runs/v02-r47/r47-20261014T091647Z-637890/`.
- v0.2 generation console output: **20/20**; reported prompt tokens 245,735, generated tokens 10,078, inference runtime 2,470.8365s; saved `v02-results.jsonl`.
- Prior failed source Base Job: `6acf3b8fc66288145223b41e`, run key `r47-20261014T082109Z-820409`.
- Recovery Mac CPU/no-GPU check produced `R47_RECOVERY_BASE_20_20_PASS` and `R47_RECOVERY_CHECK_PASS_NO_GPU`; original Base response SHA256 `becd890268edb1002c3f7195a1906f73045a86643fdac45eaf7090ee82d4dcfe`.
- v0.1 completion, all three arm hashes, random A/B/C mapping and three reviewer CSVs are **not independently accepted until collection verification**.

## Collection without ZIP, Git LFS, new GPU or extra provider apps

Added `scripts/v02_r47_collect_git.sh` and `scripts/v02_r47_collect_validate.py`.

```bash
cd ~/workspace/storyforge
git switch main
git pull --ff-only origin main
hf auth whoami
bash scripts/v02_r47_collect_git.sh
```

These scripts fetch the existing HF private result JSON, exact Base/v0.1/v0.2 response JSONL, anonymous `blind-review` JSONL, three independent CSVs, and **private** answer key and audit summary. Nothing in this step creates a GPU Job or changes model weights.

The local destination is outside the repository:
`~/.local/share/storyforge/r47/r47-20261014T091647Z-637890/`

- `reviewers/R47_Reviewer_01.csv`
- `reviewers/R47_Reviewer_02.csv`
- `reviewers/R47_Reviewer_03.csv`
- `reviewers/R47_BLIND_THREE_WAY_20.jsonl`
- `coordinator/R47_PRIVATE_RUN_REPORT.json`, Base/v0.1/v0.2 results JSONL
- `coordinator/private/R47_PRIVATE_ANSWER_KEY.json` **do not distribute to reviewers**
- `coordinator/private/R47_AUDIT_SUMMARY.json`
- `coordinator/R47_LOCAL_INTEGRITY_PASS.json` **created only on complete validation PASS**

Validation checks: completed three-arm status, old Test prompt and manifest hashes, exact 20/20/20 input-role/content matching, raw result hashes, recovered Base hash, fixed checkpoint and model revision evidence, blind package and answer key hashes, randomized response permutations, and every reviewer sheet's model reply text.

Output on acceptance: `R47_THREE_ARM_20_60_BLIND_INTEGRITY_PASS_NO_PROMOTION` and `R47_COLLECTION_COMPLETE_NO_GPU`.

**If this fails: do not relaunch GPU.** Preserve the fetched data and provide the failure details. The script fails closed, refuses to overwrite an existing local output folder and never uploads narrative text or private answer mappings to GitHub. The local collection must be treated as private. You may set `STORYFORGE_R47_LOCAL_OUT` to a new, unique path if re-collection is required.

## Next blind review steps

Send **only one** of the separate reviewer CSVs to each independent reviewer, and withhold the private key, named raw model result files and historical grader results. Reviewers score all 20 cases, six dimensions 1–5, label A/B/C/TIE, cite verbatim context, and record severe player-agency issues. Once all 3 completed sheets are frozen, run `scripts/v02_r47_review_aggregate.py` to validate and then unblind with the coordinator-owned key.

Scientific limits: these 20 Test questions are previously exposed retrospective v0.1 questions, not new independent Held-out, and the v0.2 no-character-card training prompt differs from the historical Test contract. This evaluation **cannot** establish generalization or authorize product promotion.

No LFS or ZIP assets created. Dedicated [R47 CPU GitHub Actions run 38554817894](https://github.com/sunxu/storyforge/actions/runs/38554817894) passed the new reader/validator checks; **this is CPU-only**, not proof that remote private HF reports pass.
