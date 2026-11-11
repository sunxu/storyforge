"""R60 GLM snapshot-first experiment: skip costly secondary model repair.

The actual frozen validator must still run and reject a nonexact quotation.
Only when the *exact* frozen QuoteValidationError is raised, turn it into the
existing, whitelisted technical error before the frozen inference function
would invoke its second engine.generate(). The original primary model output
is already preserved by GenerationSnapshotStore.

Opt-in experimental mode; it never produces a checkpoint for invalid quotes
and must never be mistaken for a complete original two-generation review.
"""
from __future__ import annotations


def make_primary_only_checkpoint(worker: object, emit: object):
    original = worker.checkpoint_record

    def checkpoint(position, row, response, model, revision):
        try:
            return original(position, row, response, model, revision)
        except worker.QuoteValidationError:
            emit("SECONDARY_MODEL_REPAIR_SKIPPED", position=position,
                 reason_code="MODEL_NONEXACT_QUOTE_HOLD",
                 original_frozen_validator_rejected=True,
                 checkpoint_created=False)
            # Convert to the frozen reviewer's own known ReviewError.
            # Do not change the content, decision, rubric or validator.
            raise worker.ReviewError("MODEL_NONEXACT_QUOTE_HOLD") from None

    return checkpoint
