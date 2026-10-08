from __future__ import annotations

import argparse
import json
from pathlib import Path

from .analyze import analyze_dataset, write_token_report
from .compiler import RawBundle, compile_samples, write_compiled
from .validator import validate_raw


def main() -> None:
    parser = argparse.ArgumentParser(prog="storyforge-dataset")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="validate a raw StoryForge export")
    validate.add_argument("root", type=Path)
    validate.add_argument("--expected-selected", type=int)

    compile_cmd = sub.add_parser("compile", help="compile raw export to Qwen-style SFT JSONL")
    compile_cmd.add_argument("root", type=Path)
    compile_cmd.add_argument("--output", type=Path, required=True)
    compile_cmd.add_argument("--history-messages", type=int, default=12)
    compile_cmd.add_argument(
        "--story-card-profile",
        choices=("full", "compact"),
        default="full",
        help="full preserves v0.1 behavior; compact emits Dataset v0.2 prompts",
    )

    analyze = sub.add_parser("analyze", help="analyze token budget using the target model tokenizer")
    analyze.add_argument("root", type=Path)
    analyze.add_argument("--model", required=True)
    analyze.add_argument("--output", type=Path)

    args = parser.parse_args()
    if args.command == "validate":
        report = validate_raw(args.root, args.expected_selected)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit(0 if report["ok"] else 1)

    if args.command == "analyze":
        report = analyze_dataset(args.root, args.model)
        output = args.output or (args.root / "token_report.json")
        write_token_report(report, output)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    bundle = RawBundle.load(args.root)
    samples, manifest = compile_samples(
        bundle,
        history_messages=args.history_messages,
        story_card_profile=args.story_card_profile,
    )
    write_compiled(samples, manifest, args.output)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
