# StoryForge v0.2 — R35 conditional 89-row review subset (2026-10-13)

**Status: `PENDING_NOT_APPROVED` — no GPU training authorization or launch.** The original 87+108 = 195 curator-quality Gold and 117 provisional R27 examples remain untouched.

## R35 evidence-grounded decision

R34 completed reading the **92/92 non-IP R27-visible histories**, but those readings never conferred final age/content/rights or cross-world admission. R35 creates a **new conditional review subset** by copying byte-for-byte original JSONL rows from the frozen 117-row R27 private file; this is not `train.jsonl`, a new Gold corpus, or an SFT release.

| R35 mutually exclusive route | Rows | Status |
|---|---:|---|
| Two stories with third-party character names/source-rights unresolved | **25** | Provisional provenance/IP quarantine, not a finding of infringement |
| Original source fact exists, but unchanged R27 input lacks that earlier User premise | **3** | Exclude unchanged short-window derivative / hold for versioned context repair |
| **Conditional, still unsigned review shortlist** | **89** | Full policy, age, player agency, visible-canon, rights and component signoff required |
| **Total** | **117** | No formal admission |

The **three** held original target IDs are `bh-gold-t0578`, `bh-gold-t2404`, `virgin-death-gold-t01860`. Their earlier facts were located in original chats in R33; this does **not** make them visible in the frozen shorter R27 input. The original Gold quality decisions remain valid.

The unchanged R27 draft grouping produces **70 Train-proposal rows across 7 story UUIDs**, and **19 Validation-proposal rows across 2 story UUIDs**. There is **no Test group**, **zero signed splits**, and no claim of character/world-level disjointness. Removing two quarantined Train-proposal stories and the three window-gap examples yields this new partition. No row content/metadata is rewritten.

Among the 89 pending signoffs, **32** have explicit R31–R34 review evidence triggers, **37** have only automatic keyword-scope prioritization, and **20** have neither. These are review scheduling categories, not safety results or an allocation for training. All 89 signoff sheets remain **PENDING**, with no reviewer's signature invented.

## Reproducible hashes

- R34 private parent evidence ZIP SHA256: `0b07207725d0f129a6b5e906c4a029efeca532ab1edd43f4ea6e2d4dfdef8abd`.
- Original R27 input JSONL (117) SHA256: `cdecc311f05e2c700f1038f3afca09c889ff681d4ef55dc18dc7426c9d14a92a`.
- R35 conditional 89 original-byte-line subset SHA256: `b07451301120ab570544a47a63f08f652ec0d95c852e1985ab6beaa042871d29`.
- R35 Train **proposal only** 70-row SHA256: `32b40cfe20f2508d595b17ff3d28f26b87b2fd97d7f9bb17491ef9e36b3e4ade`.
- R35 Validation **proposal only** 19-row SHA256: `44061a11fc2e0bdef74a163c7d6b5106c3eb4168b374de58e1f0a5f5b8c113b5`.
- Private complete R35 audit handoff ZIP SHA256: `7547ebada5365248a197b01a5c4a380a560cfe090b01430ae41e60740a2bd939`.

Offline `verify_r35.py` independently unzipped the package and rechecked 117 source identities, original target hashes, exact line copies, **25+3+89** route closure, **70+19** draft split, 7/2 UUID groups and zero approval metadata. Outcome: `R35_FROZEN_SOURCE_ROWS_117_PASS__89_CONDITIONAL_ONLY_70_19_PROPOSAL__TRAINING_NOT_APPROVED`; intentional approval-status tampering was rejected. A separate read-only `r35_release_gate.py` exits 2 and reports the outstanding approvals.

The private R35 package contains raw story text and private candidate IDs. It is **not uploaded as ordinary Git data**. All confidential source archives remain under the protected prior Git LFS arrangement; GitHub gets only a safe aggregate state file and this non-text report.

## Exactly what remains blocked

1. **All 89** individual content, character ages, consent/player autonomy, as-visible-canon, and source rights final decisions are still unsigned. Previous context reading is not this signoff.
2. Component-level alias/IP cross-story graph remains unproved. Different story UUIDs alone are not enough to authorize 70/19 Train/Validation.
3. **Zero** genuinely new and unexposed independent sealed heldout story components exist. The private handoff includes `R35_FRESH_HELDOUT_INTAKE.md` with data requirements, not invented test stories.
4. The previous real HF R27 full **117/117** last-round/Tokenizer diagnostic is valid for those unchanged individual source examples, but cannot be misrepresented as a separately executed final compiled R35 Train/Validation audit. An actual final-assembled input audit remains a release prerequisite.
5. Explicit model-training approval and authorization of a paid GPU job have not been given. The user approved the **generic no-card experiment definition only**.

**Result:** deterministic **89-item conditional review ceiling**, two sets of isolated exclusions (25+3), and clear next signatures/evidence; **formally approved Train=0, Validation=0, Test=0**.
