"""Create-only SAFE receipt example; no private text or overwrite."""
from pathlib import Path
from storyforge_dataset.hf_runtime import OutputManager, ReceiptValidator

def publish(path: Path, payload: dict[str, object]) -> str:
    OutputManager.probe(path.parent)
    written = OutputManager.write_safe(path, payload)
    return written.sha256

# Business-specific payloads must be validated by their own schema validator.
# RuntimeReceipt validation applies only to storyforge-hf-runtime-diagnostic-v1.
