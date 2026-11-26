# R50 W17 — full-message semantic review: evidence-limit decision

Latest owner-local private AI workpaper: SHA256
`6482dd02b27d80f72763b23b848cf7c0b2765853f09ef0beb2ae4961d50b7ce3`.

- 7/7 gap assessments remained `INSUFFICIENT_CONTEXT`;
  zero `SUPPORTED_IN_FULL_MESSAGE_SCOPE` or `WORLD_LINK` proof.
- 344 complete original message **entries** across seven dossiers
  (not necessarily 344 unique global message IDs); 75 citations total.
- No historical card-at-cutoff checks, all 7 `NOT_CHECKED`.
- 20 remaining requirement mentions, possible duplicates.
- The original 46 retained R50 cases and existing private workpapers
  remain frozen. Global semantic graph and final Held-out seal remain HOLD.

## One critical new finding from frozen Git W17 card metadata

W17 `story-cards.json` records **zero** `content_versions`
and **zero** `moderation_source_snapshots`. Its last recorded export-card
update is **before the reported first chat message**, unlike some other
worlds. That metadata may be useful: it is *not* proof that the export
snapshot matches the effective model-request card, its public projection,
masks, rule overlays or all earlier context fields for a retained case.

We must distinguish (a) timestamp ordering, (b) actual snapshot
version contents, (c) which card fields were sent at a given prompt
cutoff, and (d) whether another world shares unique identities/events.
These are separate tests. Do not infer an alias graph PASS from absent
historical versions or a pre-chat last-edit timestamp.

## Next run: safe message timestamp crosscheck, not another AI blind review

In the Mac checkout:

```bash
cd ~/workspace/storyforge
git fetch origin audit/r49-r50-source-intake-20261015
git switch audit/r49-r50-source-intake-20261015
git pull --ff-only

ROOT="$HOME/.local/share/storyforge/r50/private-ai-review"
python3 scripts/v03_r50_w17_timepoint_metadata_gate.py \
  --repo . \
  --dossiers-dir "$ROOT/W17_SEVEN_GAP_FULL_SOURCE_DOSSIERS_20261019" \
  --workpaper "$ROOT/W17_SEVEN_GAP_FULL_MESSAGE_AI_REVIEW_PRIVATE_20261019.json"
```

The checker confirms the exact immutable private dossiers/workpaper,
reads W17 Git-pinned source transcript/card, crosschecks original
message bodies SHA256 and timestamp ordering for all W17 source
citations; prints only **counts and booleans**, no story content,
private missing-evidence strings, prompt IDs or character names.

It cannot discover lost historical card versions, certify runtime
inference prompts or decide the 04↔07 transitive link. If source
timepoints do not prove card/rule applicability, do **not** run another
identical limited-context AI review. Request authenticated model-input
request logs, actual historical card versions, rules as-of-cutoff, or
full-story provenance (as required by the private missing-evidence list).

**Explicit STOP:** until such *new* evidence exists, the seven W17
world-link verdicts cannot be promoted beyond `INSUFFICIENT_CONTEXT`.
No new paid HF/GPU job, no model inference, no R50 cases altered,
no merge, no final Held-out seal.
