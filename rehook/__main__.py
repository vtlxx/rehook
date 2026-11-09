"""CLI: python -m rehook generate | report."""
import argparse
import os
import sys
import time

import anthropic
from rich.console import Console

from rehook import llm as llm_module
from rehook.export import print_summary
from rehook.llm import LLM, LLMError
from rehook.pipeline import run_generate
from rehook.report import run_report
from rehook.similarity import DEFAULT_THRESHOLD


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rehook", description="Hook variants for winning ad scripts")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="generate hook variants for a winning script")
    gen.add_argument("--winner", required=True, help="winning script (txt)")
    gen.add_argument("--brand", required=True, help="brand brief (yaml)")
    gen.add_argument("--history", help="already launched hooks (csv)")
    gen.add_argument("--ads", help="Ads Manager export (csv), for best/worst examples")
    gen.add_argument("--n", type=int, default=20, help="how many variants to keep")
    gen.add_argument("--out", default="out/")
    gen.add_argument("--mock", action="store_true", help="use recorded model replies, no API key needed")
    gen.add_argument("--model", default=llm_module.MODEL)
    gen.add_argument("--sim-threshold", type=float, default=DEFAULT_THRESHOLD)
    gen.add_argument("--seed", type=int, default=42, help="shuffle seed for ranking")

    rep = sub.add_parser("report", help="compare AI vs manual modifications")
    rep.add_argument("--ads", required=True, help="Ads Manager export (csv)")
    rep.add_argument("--ltv", type=float, default=68.0)
    rep.add_argument("--min-spend", type=float, default=500.0)
    rep.add_argument("--min-romi", type=float, default=1.25)
    rep.add_argument("--meta-undercount", type=float, default=0.12)
    rep.add_argument("--out", default="out/")
    return parser


def run_generate_command(args) -> None:
    if not args.mock and not os.environ.get("ANTHROPIC_API_KEY"):
        raise LLMError("ANTHROPIC_API_KEY is not set (use --mock to run without it)")
    llm = LLM(model=args.model, mock=args.mock)
    console = Console(width=max(Console().width, 100))
    started = time.monotonic()
    with console.status("Generating hook variants…"):
        result = run_generate(llm, args.winner, args.brand, args.history, args.ads, args.n, args.out,
                              args.sim_threshold, args.seed)
    print_summary(console, result, llm, time.monotonic() - started)
    console.print(f"Saved {args.out.rstrip('/')}/variants.csv, rejected.csv, brief.md")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "generate":
            run_generate_command(args)
        else:
            run_report(args)
    except (LLMError, OSError, ValueError, KeyError, anthropic.APIError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
