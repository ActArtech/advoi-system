#!/usr/bin/env bash
# Capture staging latency baseline for docs/operations/latency-baseline.json
set -euo pipefail

BASE="${ADVOI_BASE_URL:-https://advoi.keyteller.com}"
OUT="${1:-docs/operations/latency-baseline.json}"

curl -sf "${BASE}/api/diagnostics/latency" | ADVOI_BASE_URL="${BASE}" OUT_PATH="${OUT}" python3 - <<'PY'
import json, os, sys
from datetime import datetime, timezone

data = json.load(sys.stdin)
baseline = {
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "base_url": os.environ.get("ADVOI_BASE_URL", "https://advoi.keyteller.com"),
    "ok": data.get("ok"),
    "sla_target_ms": data.get("sla_target_ms"),
    "sla_ok": data.get("sla_ok"),
    "sla_scope": data.get("sla_scope"),
    "timings_ms": data.get("timings_ms"),
    "frame_id": data.get("frame_id"),
    "intent_frame_id": data.get("intent_frame_id"),
}
out = os.environ["OUT_PATH"]
with open(out, "w", encoding="utf-8") as f:
    json.dump(baseline, f, indent=2)
    f.write("\n")
print(f"Wrote {out}")
print(json.dumps(baseline["timings_ms"], indent=2))
PY