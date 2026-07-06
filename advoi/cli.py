"""Minimal CLI entrypoint."""

import sys

from advoi import __version__


def main() -> None:
    print(f"ADVoi v{__version__}")
    print("Modules: voice, aether, guardian, squads, decision, memory")
    print("         ingestion, reporting, routing, ontology, observability")
    print("Run: advoi-api | advoi-voice (Stage 1 Pipecat + LiveKit)")
    sys.exit(0)


if __name__ == "__main__":
    main()