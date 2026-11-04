"""Business-agnostic, CPU-first Hugging Face Jobs runtime primitives."""

__version__ = "0.1.0"

from .context import RuntimeContext
from .diagnostics import DiagnosticReporter, ErrorCode
from .inputs import InputManager, VerifiedInput
from .outputs import OutputManager, OutputCapability, WriteReceipt
from .paths import PathResolver, ResolvedPath
from .receipts import ReceiptValidator, RuntimeReceipt
from .resources import ResourceGuard, ResourceReport

__all__ = [
    "DiagnosticReporter",
    "ErrorCode",
    "InputManager",
    "OutputCapability",
    "OutputManager",
    "PathResolver",
    "ReceiptValidator",
    "ResourceGuard",
    "ResourceReport",
    "ResolvedPath",
    "RuntimeContext",
    "RuntimeReceipt",
    "VerifiedInput",
    "WriteReceipt",
]
