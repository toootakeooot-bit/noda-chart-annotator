from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

COMPLETE={"PDF_GEOMETRY_READY","NO_CHART_WEEK"}

def is_complete(pkg:Path)->bool:
    p=pkg/"pdf_only_status.json"
    if not p.exists(): return False
    try: return json.loads(p.read_text(encoding="utf-8")).get("status") in COMPLETE
    except Exception: return False

def find_next(root:Path)->Path|None:
    roots=[root/"teacher_observation_packages"/"pending_api",root/"teacher_observation_packages"/"pending",root/"teacher_observation_packages"]
    seen=set(); c=[]
    for base in roots:
        if not base.exists(): continue
        for p in base.glob("pkg_*"):
            if not p.is_dir() or p in seen: continue
            seen.add(p)
            if not is_complete(p): c.append(p)
    c.sort(key=lambda p:p.name)
    return c[0] if c else None

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--live-root",default="."); args=ap.parse_args()
    root=Path(args.live_root).resolve(); pkg=find_next(root)
    if pkg is None:
        print("NO_WORK / PASS"); return 0
    tool=Path(__file__).resolve().parent/"pdf_geometry_extractor.py"
    print(f"RESUME PACKAGE: {pkg.name}")
    return subprocess.call([sys.executable,str(tool),"--package",str(pkg)])

if __name__=="__main__": raise SystemExit(main())
