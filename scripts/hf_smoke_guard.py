"""ms-swift 4.5.3 runtime gates for the StoryForge smoke job.

Loaded by ``swift sft --custom_register_path``.  The hook checks the parsed
arguments and the model after ms-swift has loaded it, so the checks observe the
same objects that training will use and do not load the model a second time.
"""
from __future__ import annotations

import collections
import json


def _fail(message: str) -> None:
    raise RuntimeError(f"STORYFORGE_SMOKE_GUARD_FAIL: {message}")


def _check_args(args) -> None:
    expected = {
        "loss_scale": "last_round",
        "torch_dtype": "torch.bfloat16",
        "quant_method": "bnb",
        "quant_bits": 4,
        "bnb_4bit_compute_dtype": "torch.bfloat16",
    }
    observed = {key: str(getattr(args, key, None)) for key in expected}
    print("STORYFORGE_PARSED_ARGS", json.dumps(observed, sort_keys=True), flush=True)
    if getattr(args, "loss_scale", None) != "last_round":
        _fail(f"parsed loss_scale is {getattr(args, 'loss_scale', None)!r}")
    if getattr(args, "add_non_thinking_prefix", None) is not False:
        _fail("automatic non-thinking prefix must be disabled for exact Gold supervision")
    for key in ("quant_method", "quant_bits"):
        if getattr(args, key, None) != expected[key]:
            _fail(f"parsed {key} is {getattr(args, key, None)!r}, expected {expected[key]!r}")
    if str(getattr(args, "torch_dtype", None)) != expected["torch_dtype"]:
        _fail(f"parsed torch_dtype is {getattr(args, 'torch_dtype', None)!r}")
    if str(getattr(args, "bnb_4bit_compute_dtype", None)) != expected["bnb_4bit_compute_dtype"]:
        _fail(f"parsed bnb_4bit_compute_dtype is {getattr(args, 'bnb_4bit_compute_dtype', None)!r}")


def _check_model(model) -> None:
    import bitsandbytes as bnb
    import torch

    print("STORYFORGE_CUDA_DEVICE", torch.cuda.get_device_name(0), flush=True)
    dtype_counts = collections.Counter()
    for parameter in model.parameters():
        dtype_counts[str(parameter.dtype)] += parameter.numel()
    modules = [module for module in model.modules() if isinstance(module, bnb.nn.Linear4bit)]
    compute_dtypes = collections.Counter(str(getattr(module, "compute_dtype", None)) for module in modules)
    report = {
        "parameter_dtype_distribution": dict(sorted(dtype_counts.items())),
        "Linear4bit_modules": len(modules),
        "Linear4bit_compute_dtype_distribution": dict(sorted(compute_dtypes.items())),
        "Linear4bit_quantized_modules": sum(
            getattr(module.weight, "quant_state", None) is not None for module in modules),
    }
    print("STORYFORGE_QUANTIZATION", json.dumps(report, sort_keys=True), flush=True)
    if not modules:
        _fail("no bitsandbytes Linear4bit modules were loaded")
    if report["Linear4bit_quantized_modules"] != len(modules):
        _fail("some Linear4bit weights have not actually been quantized")
    if set(compute_dtypes) != {str(torch.bfloat16)}:
        _fail(f"Linear4bit compute dtype is not exclusively bfloat16: {dict(compute_dtypes)!r}")


def _check_template(template) -> None:
    strategy = getattr(getattr(template, "loss_scale", None), "base_strategy", None)
    print("STORYFORGE_TEMPLATE_LOSS_SCALE", repr(strategy), flush=True)
    if strategy != "last_round":
        _fail(f"template loss_scale.base_strategy is {strategy!r}")


try:
    from swift.pipelines.train.sft import SwiftSft

    if not getattr(SwiftSft, "_storyforge_guard_installed", False):
        _prepare_model_tokenizer = SwiftSft._prepare_model_tokenizer
        _prepare_template = SwiftSft._prepare_template

        def guarded_prepare_model_tokenizer(self, *args, **kwargs):
            _check_args(self.args)
            result = _prepare_model_tokenizer(self, *args, **kwargs)
            _check_model(self.model)
            return result

        def guarded_prepare_template(self, *args, **kwargs):
            result = _prepare_template(self, *args, **kwargs)
            _check_template(self.template)
            return result

        SwiftSft._prepare_model_tokenizer = guarded_prepare_model_tokenizer
        SwiftSft._prepare_template = guarded_prepare_template
        SwiftSft._storyforge_guard_installed = True
        print("STORYFORGE_SMOKE_GUARD_INSTALLED", flush=True)
except Exception as exc:
    raise RuntimeError(f"unable to install StoryForge smoke guard: {exc}") from exc
