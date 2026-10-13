# StoryForge v0.2 — R29 bounded content triage and training-release decision packet

**Date:** 2026-10-13. **Formal GPU training admission: `PENDING_NOT_APPROVED`.** No model training was run and no frozen Gold target text was modified.

## Durable evidence and latest HF verification

The private R27 source archive has SHA256 `cfedf6935babd12c9fc214b46dc2078381b55de9487afe25212bf54e8706794f`, containing the **117-row provisional** JSONL with SHA256 `cdecc311f05e2c700f1038f3afca09c889ff681d4ef55dc18dc7426c9d14a92a`.

The actual R27 HF Job `6ace19935ccb47ba0f787af5` and [GitHub LFS report replay](https://github.com/sunxu/storyforge/actions/runs/38400578892) confirm **117/117** reported ms-swift `last_round` collator internal checks, with max **3,694** ms-swift tokens and **30,517** supervised tokens. This confirms diagnostics on those exact provisional input bytes, **not formal age/content or linked-world admission**. The report SHA256 is `e23f166226142e28a04f42a3d481776b6ac84d9b30f92e30a55de838e5d2b213`.

## R29 review-ready triage

A new source-bound private review packet has been constructed with all **117** candidate IDs, exact frozen target SHA256 references, the current User and adjacent Assistant evidence excerpts, per-story review obligations and **explicitly unsigned** age, policy, player-autonomy, story-link and split decisions.

- **40/117** contain a previous R21 **bounded current-turn** manual observation (20 had additional attention flags; 20 did not trigger the same bounded checks). Those R21 observations were never global policy approval.
- **77/117** are R27 source-restored prefixes **without equivalent prior signed full-context review**.
- The new R29 keyword-scope indicators are a mechanical tool for ordering a review: campus/age, medical dependence, children, intimacy, player-action narration and control language. They are **not human semantic judgments, policy violations, or PASS results**.
- **0/117** have final policy/age/content signature. **0** of the 96 Train or 21 Validation proposal rows is formally approved.
- All 11 source-story UUIDs are distinct. That observation does not prove linked-world, alias, character/IP or semantic test independence.
- User's additional source export `處女之死` has a different UUID from `处女之死` but a near-identical title. Record the potential relationship as `NOT_PROVEN` and do **not** reserve it as a freshly unexposed held-out case on title/UUID alone.

## Explicit choices required before GPU training

1. **Training task definition:** sign an explicit **new generic no-card/System-Prompt derivative** contract (with quality/canon tradeoffs) *or* restore request-effective historical cards, change the derived input and rerun model Token/Mask. Neither has yet been chosen or approved. The existing R27 generic System Prompt is synthetic, not the original generation request.
2. **Content and participant age:** authorize final full-context review of selected examples; reject or hold questionable examples rather than rewriting Gold. Previous R21 40-row bounded observations are not a substitute.
3. **Graph-based story partition:** independently map all character aliases, common works/IP and world connections, then sign a Train/Validation/Test component-disjoint split. Current 96/21 is only a story-UUID proposal.
4. **Genuinely fresh held-out:** obtain and freeze a new unexposed story/component with predeclared evaluation protocol. **None is presently available.** Disclosed v0.1 held-out and already-scored extra exports cannot silently become untouched test.
5. **Approved final dataset:** only after (1)–(4), freeze the exact subset and verify its SHA256; rerun HF Token/Mask if *any* prompt prefix or included sample set changed. Require signed release certificate and explicit billable GPU authorization.

## R29 source custody

- R28 unmodified parent SHA256: `dbbc3f295c450c9b18e005f2b07864018e6a22a02cf064a23bbe0c75ed6b5aab`.
- R29 **private** handoff ZIP: `StoryForge_v02_R29_Content_Split_Release_20261013.zip`; SHA256 `242612ccd79eec6c8eb72bb4913f52b49fb83141a7fbe94d39f389b1b24dbdac`.
- The private ZIP contains individual original excerpts and identifiers; **do not commit the excerpt JSONL or the private ZIP to public Git**, and do not treat it as an approved train input. It is retained in the ChatGPT conversation and may be stored privately with Git LFS if separately authorized.
- Independent unpack verifier: `R29_SOURCE_BOUND_TRIAGE_INTEGRITY_PASS__TRAINING_ADMISSION_BLOCKED`; intentional candidate status tamper was rejected with exit 2. This checks inventory, provenance references and nonrelease statuses, **not final human safety approval**.

**Next:** obtain the no-card training objective decision and genuinely new held-out intake, then finish signoffs by group; do not repeat the already successful R27 Token/Mask checks on unchanged inputs.
