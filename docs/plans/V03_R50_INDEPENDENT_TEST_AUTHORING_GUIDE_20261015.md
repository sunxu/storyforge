# StoryForge R50 — Independent Held-out authoring guide (DRAFT)

Date: 2026-10-15. Source archive: evaluations/v0.2/source-archives/16-20 at commit a197923e1e15344e8c98bd96e593e84781b68c83.
Status: R50_FIVE_CANDIDATE_WORLDS_RESERVED__AUTHORING_PENDING__NOT_SEALED.

## Reservation and scope

Treat the complete story components 16–20 as **prospective test-only candidates** until world/character-alias audit demonstrates separation from historic R45 Train49/Val15, Gold195, and exposed R47/R48 Test20. Do not reuse any of their source replies or derived cases for future Train, Validation or iterative model tuning. If a source-world overlap emerges, replace the affected world before test sealing; distinct UUIDs alone do not establish semantic isolation.

The candidate target is **50 prompt-only tests**, 10 newly authored cases per world:
- story 16: SFH50-W16-001 through -010
- story 17: SFH50-W17-001 through -010
- story 18: SFH50-W18-001 through -010
- story 19: SFH50-W19-001 through -010
- story 20: SFH50-W20-001 through -010

Each world should include 2 long-term constraint / forbidden-line tests; 2 player-agency tests; 2 timeline and continuity tests; 2 character/relationship-consistency tests; 1 literary/interactive progress test; and 1 mixed-stress test. The 50-case target is a drafting plan, **not permission to invent low-quality cases to fill quotas**.

## Authoring contract

Tests must be written or independently validated by an author who has not seen R47/R48 model outputs, anonymous-to-model mappings, grading results, or data-selection decisions. Provide only world facts, historically available prior messages, long-term constraints, and a newly authored current User input; no reference Assistant answer, Gold, grading hints or pairwise preference.

Follow the existing R50 JSONL intake schema:
- required: case_id, world_id, world_card, long_term_rules, history, user_input
- optional: focus_tags
- world_card identical for all cases of a given world under the current intake script.
- history contains only preceding user/assistant dialogue. Source Assistant messages can be historical context, never the model target.

**Point-in-time requirement:** Choose a definite story cutoff and reconstruct the known facts at that cutoff; do not import later revisions of character cards or state changes backward into earlier messages. The relationship checkpoints are saved state records and their narrative turn indices are not guaranteed to match physical chat message indices.

The project owner stated that all characters are adults and the names are fictional, with no real-person referents. Record the statement, but still conduct case-by-case source/age/content/rights review.

## Integrity and privacy requirements

New test originals, SHA256 sealed canonical JSONL, and later private answer mappings must stay in controlled local/private storage, **not** the tracked source archive or ordinary Git. Only nontextual evidence manifests, version hashes and scripts belong in Git. The added Git ignore rules are defensive only; explicit forced staging can bypass them.

Before sealed-test inference: verify author/source independence; 40–60 cases from at least four truly separate worlds; exact and near-duplicate text overlap against frozen Train, Val, Gold195 and old Test20; world and character alias connectivity; per-case source cutoff; content boundaries; stable hashes; fixed prompt contract and model settings; independent anonymized evaluation rubric.

If any of these cases are used early for model-specific debugging, they become development/diagnostic cases and cannot be reused as a never-exposed v0.3 promotion Held-out.

## Grounded current gates

- Git checkout byte integrity: PASS, R50 no-GPU workflow run 38690298664.
- Exact story/session metadata IDs vs historic Gold195: PASS for available IDs, run 38690665714.
- Semantic world / aliases, near-duplicates, private R45 Train/Val, independent prompt authorship, final sealing: PENDING.
- R49 eval preregistration owner sign-off: PENDING.
- New paid GPU/inference: NOT AUTHORIZED.
- Model promotion: NO.

Marker: R50_AUTHOR_GUIDE_READY__TEST_INPUT_PENDING__NO_GPU.
