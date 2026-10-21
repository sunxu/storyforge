# StoryForge R52/v0.3 — owner-approved no-card experimental input design

Date: 2026-10-21. Status: `OWNER_APPROVED_INPUT_DESIGN_ONLY__NO_TRAINING_ADMISSION__NO_GPU_AUTHORIZATION`.

## Explicit decision and scope

The project owner replied "批准" to the narrowly scoped question: may R52/v0.3 reuse the R27 **generic no-character-card System Prompt + unchanged frozen model-visible conversation + supervised final Assistant response only** for the new experimental input contract? This is **YES to the input design only**.

This consent does not admit any source case into Train/Validation, approve content/safety/rights/world separation, approve paid CPU/GPU runs, open R50 sealed heldout, or promote an adapter.

## Exact frozen System prompt

The 449-byte UTF-8 string below was recovered from the *original* R27 private source archive, and the same string was verified in all 117 R27 rows. It is a **new synthetic training instruction, not the historical generation request**.

```text
你是互动叙事模型。仅根据本次给出的可见历史对话与当前玩家输入继续故事。
保持已经在对话中出现的人物事实和关系、时间空间连续性、角色口吻与玩家自主权；不编造已确定的旧事，不提前使用未来剧情。
不替玩家作出未表达的选择，不越过内容安全边界。若必要信息不足，在故事内自然保留未确定部分，不将假设写成既定事实。
```

- System UTF-8 SHA256: `5e1b28cd9181f5d334f1f10a54a251f9255e655a3e597519c7cfcc530d8c5e83`
- Original R27 private ZIP SHA256: `cfedf6935babd12c9fc214b46dc2078381b55de9487afe25212bf54e8706794f`
- Original R27 private JSONL SHA256: `cdecc311f05e2c700f1038f3afca09c889ff681d4ef55dc18dc7426c9d14a92a`

## Derived R52/v0.3 message contract

1. Exactly the pinned generic System instruction, `loss=false`.
2. Preserve only the original R52 frozen model-visible history in source order (including the last User message), all `loss=false`. Do **not** insert unverified export-time cards, preceding source previews, future text or unknown hidden facts.
3. Append the frozen original target Assistant reply unchanged, `loss=true`, as the **only supervised message**. Do not silently rewrite defective targets.
4. Keep limitations explicit: this derivative is not a reconstruction of historical prompts and cannot certify unseen canon/role-card constraints. Owner originality/training rights and adulthood declarations are attestations requiring appropriate evidence and case-level review.
5. History truncation and actual tokenizer/chat template/ms-swift collator/label mask details are **not** auto-approved; verify on exact finally admitted input bytes under a separately controlled R53 preflight.

## Engineering evidence checked (not a release gate)

An offline input-*shape* check against the unmodified 46-case R52 blind source ZIP and post-adjudication Owner ledger confirmed **46** original target hashes, **487** source-visible message hashes, exactly one final supervised Assistant target for every in-memory candidate, 37 histories starting with Assistant, and 9 starting with User. This is a **format and provenance check only**, not an actual Qwen tokenizer or ms-swift collator check.

- Frozen R52 blind ZIP SHA256: `937b27ea2a9ec3c504f0592a23be831855540bb7203cd4d74f3c0487ed9912cb`
- Owner post-adjudication ledger SHA256: `a9a4319a49cbe88f22d0b09b77fa315654b6c75c2bb43aae9bd16c733dce562c`
- Known routes: 43 contextual quality-possible HOLD; 3 substantive defect HOLD.
- Required before any GPU release: case-specific Owner content/safety/age/consent signoffs; rights evidence; true R45/R46 model exposure mapping; signed world-component-disjoint Train/Val; actual tokenizer/collator/labels; and a **separate explicit paid GPU authorization**.
- Current release state: Owner final approvals **0/46**, world signoffs **0/7**, Train **0**, Val **0**, R50 unopened, new paid GPU **not authorized**.

This file contains no private narrative bodies, sample identifiers, crosswalks, or sealed R50 content. R52 owner-private packets remain **off ordinary Git**.
