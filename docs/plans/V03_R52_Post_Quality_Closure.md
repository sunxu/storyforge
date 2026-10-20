# R52 Post-quality closure — 62 source-verified no-card judgments

**2026-10-20 · no training admission · no split · no GPU**

The project owner locally validated R52 Batch 04 with `R52_QUALITY_RESULTS_VALIDATED__NO_ADMISSION`: 14/14 decisions and 47 source citations. Together with prior batches, quality screening is **62/62**, **205** citations: **46** no-card target/context first-pass possible, **9** target player-agency defects, **3** continuity/fact defects and **4** hidden-premise/card dependencies.

The 46 are a **private shortlist for further source, quality, safety and world-isolation review**, not final training examples. The user has attested ownership of all StoryForge content; we preserve that declaration without converting it into independent legal certification. Source-message hash validity is not historical model prompt reconstruction.

## Generate reproducible private closure

From the GitHub audit branch worktree on the Mac:

```bash
cd ~/workspace/storyforge
git pull --ff-only

d="$HOME/.local/share/storyforge"
install -d -m 700 "$d/r52/post_quality"

python3 scripts/v03_r52_post_quality_closure.py \
  --context-queue "$d/r52/R52_PRIVATE_CONTEXT_62_QUALITY_CARD_QUEUE.jsonl" \
  --private-packets "$d/r51/R51_GOLD108_PRIVATE_CONTEXT_REVIEW_v1.jsonl" \
  --quality-dir "$d/r52/quality" \
  --out-dir "$d/r52/post_quality"
```

Expected status: `R52_ALL_62_QUALITY_REVIEWS_REVERIFIED__NO_ADMISSION`.

The script **reconstructs all four task batches** from pinned source packets, checks the recorded tasks byte-level equivalent at the JSON object level, revalidates every private reviewer source citation and its index/hash, checks batch-by-batch frozen route and citation counts, and checks case uniqueness. It does not rely only on previously printed counters. Outputs are created exclusively in a 0700 private directory, with 0600 files, without overwriting files or modifying the originals. No story text or candidate IDs reach stdout or GitHub.

Private outputs:

- `R52_PRIVATE_FIRST_PASS_46_SHORTLIST.jsonl`: target/source pin, original history fingerprint, story identity, quality-route provenance, **all downstream gates pending**, `split=null`.
- `R52_PRIVATE_QUALITY_16_HOLD_REGISTER.jsonl`: 16 unsuited-as-is quality cases; no altered story or model target.
- `R52_PRIVATE_WORLD_COMPONENT_PREFLIGHT.jsonl`: preliminary **source_story_id** grouping, never an independently verified linked-world/component split.
- `R52_POST_QUALITY_SAFE_AGGREGATE.json`: counts and SHA256 of input documents (no content or case IDs), safe to share.

The close-out does **not** output a `train.jsonl`, `val.jsonl`, `tokenizer-PASS`, admission status, or permission to run a paid GPU job.

## Independent next gates

1. **Quality owner signoff:** review first-pass positives as a new generic-no-card task, preserving all R51 and R52 reviewer warnings. A citation verifier cannot certify literary quality, age/consent restrictions, content safety or player-agency acceptance.
2. **Linked-world isolation:** obtain a private linked-world/alias component map (including v0.1 train overlap and world 04/07 linkage), plus heldout intersection checks. Source story UUID alone is not proof of separation. Choose Train and Val only across disjoint connected story components.
3. **Experimental input freeze:** explicitly approve the R52 derivative's exact neutral System Prompt, role-preserving frozen visible history, training target, and max-token/truncation policy. R30's pinned R27 no-card prompt is a prior experimental contract, not a claim about historical source cards nor automatic admission of R52.
4. **Actual tokenizer/collator gate:** run pinned Qwen tokenizer/handler on every eventual candidate. Verify full input length <= 16,384, prompt role boundaries and *only final target Assistant tokens* have supervised labels; inspect actual ms-swift last-round loss mask.
5. **Admission manifest and train authorization:** after all gates, have the owner sign a separate immutable training manifest with sample hash, story-component split, explicit PASS status and exact experiment identity. Do not touch sealed R50 tests or mutate original Gold195.

Synthetic-only GitHub Actions workflow `R52 Post-quality Closure (synthetic only)` checks closure partition and tampering rejection. Real private cases must be run locally by the owner.
