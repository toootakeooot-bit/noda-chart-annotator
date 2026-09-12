from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def is_complete(pkg: Path) -> bool:
    status = pkg / "pdf_only_status.json"
    if not status.exists():
        return False
    try:
        value = json.loads(status.read_text(encoding="utf-8")).get("status")
    except Exception:
        return False
    return value in {"PDF_ONLY_OBSERVATION_READY", "NO_CHART_WEEK"}


def find_next_package(root: Path) -> Path | None:
    roots = [root / "teacher_observation_packages" / "pending_api", root / "teacher_observation_packages" / "pending", root / "teacher_observation_packages"]
    seen = set()
    candidates = []
    for base in roots:
        if not base.exists():
            continue
        for p in base.glob("pkg_*"):
            if not p.is_dir() or p in seen:
                continue
            seen.add(p)
            if not is_complete(p):
                candidates.append(p)
    candidates.sort(key=lambda p: p.name)
    return candidates[0] if candidates else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live-root", default=".")
    ap.add_argument("--model", default="qwen3-vl:8b")
    args = ap.parse_args()
    live = Path(args.live_root).resolve()
    pkg = find_next_package(live)
    if pkg is None:
        print("NO_WORK / PASS")
        return 0
    parser_script = Path(__file__).resolve().parent / "local_pdf_teacher_parser.py"
    print(f"RESUME PACKAGE: {pkg.name}")
    return subprocess.call([sys.executable, str(parser_script), "--package", str(pkg), "--model", args.model])


if __name__ == "__main__":
    raise SystemExit(main())
