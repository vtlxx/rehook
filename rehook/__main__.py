"""CLI: python -m rehook generate | report."""
import argparse
import sys

from rehook.report import run_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rehook", description="Hook variants for winning ad scripts")
    sub = parser.add_subparsers(dest="command", required=True)

    rep = sub.add_parser("report", help="compare AI vs manual modifications")
    rep.add_argument("--ads", required=True, help="Ads Manager export (csv)")
    rep.add_argument("--ltv", type=float, default=68.0)
    rep.add_argument("--min-spend", type=float, default=500.0)
    rep.add_argument("--min-romi", type=float, default=1.25)
    rep.add_argument("--meta-undercount", type=float, default=0.12)
    rep.add_argument("--out", default="out/")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "report":
            run_report(args)
    except (OSError, ValueError, KeyError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
