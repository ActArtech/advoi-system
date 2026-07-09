"""Minimal CLI entrypoint."""

import argparse
import json
import sys

from advoi import __version__


def _cmd_aether_status() -> int:
    from advoi.aether.service import get_aether_service

    payload = get_aether_service().status()
    print(json.dumps(payload, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="advoi", description="ADVoi executive OS CLI")
    parser.add_argument("--version", action="version", version=f"ADVoi {__version__}")
    sub = parser.add_subparsers(dest="command")

    aether = sub.add_parser("aether", help="Aether portfolio manager")
    aether_sub = aether.add_subparsers(dest="aether_cmd", required=True)
    aether_sub.add_parser("status", help="Gate + venture lifecycle status")

    args = parser.parse_args()
    if args.command == "aether" and args.aether_cmd == "status":
        sys.exit(_cmd_aether_status())

    print(f"ADVoi v{__version__}")
    print("Modules: voice, aether, guardian, squads, decision, memory")
    print("         ingestion, reporting, routing, ontology, observability")
    print("Run: advoi-api | advoi-voice | advoi-supervisor | advoi-orchestrate")
    print("     advoi aether status")
    sys.exit(0)


if __name__ == "__main__":
    main()