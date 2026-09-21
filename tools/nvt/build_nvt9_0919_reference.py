from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

ROLES = ("TL", "CH", "TL_ZONE_EDGE", "CH_ZONE_EDGE")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def mt4_time(value: str) -> str:
    return datetime.fromisoformat(value).strftime("%Y.%m.%d %H:%M:%S")


def points(line: dict, role: str) -> tuple[float, float]:
    p1 = float(line["anchor1_price"])
    p2 = float(line["anchor2_price"])
    offset = float(line["ch_offset"])
    width = float(line["zone_width"])
    direction = line["direction"]
    if role == "TL":
        return p1, p2
    if role == "CH":
        return p1 + offset, p2 + offset
    if role == "TL_ZONE_EDGE":
        z = width if direction == "RISING" else -width
        return p1 + z, p2 + z
    if role == "CH_ZONE_EDGE":
        z = -width if direction == "RISING" else width
        return p1 + offset + z, p2 + offset + z
    raise ValueError(role)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build frozen 09/19 reference drawing with stable numbering.")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()

    manifest_path = Path(args.manifest)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    payload = load_json(manifest_path)

    rows = []
    index_rows = []
    for line in payload["lines"]:
        rid = line["reference_id"]
        tf = line["timeframe"]
        level = line["structure_level"]
        level_code = "L" if level == "LARGE_DOW" else "M"
        for role in ROLES:
            p1, p2 = points(line, role)
            oid = f"{rid}_SRC_{tf}_{level_code}_{role}"
            rows.append([
                oid,
                payload["symbol"],
                tf,
                level,
                role,
                mt4_time(line["anchor1_time"]),
                f"{p1:.8f}",
                mt4_time(line["anchor2_time"]),
                f"{p2:.8f}",
                "REFERENCE",
                str(line["generation"]),
                line["status"],
                "RAY_RIGHT",
            ])
        index_rows.append({
            "reference_id": rid,
            "reference_no": line["reference_no"],
            "timeframe": tf,
            "structure_level": level,
            "direction": line["direction"],
            "source_line_id": line["line_id"],
            "anchor1_id": f"{rid}-A1",
            "anchor1_time": line["anchor1_time"],
            "anchor1_price": line["anchor1_price"],
            "anchor2_id": f"{rid}-A2",
            "anchor2_time": line["anchor2_time"],
            "anchor2_price": line["anchor2_price"],
            "ch_offset": line["ch_offset"],
            "zone_width": line["zone_width"],
        })

    header = [
        "object_id","symbol","timeframe","structure_level","role",
        "t1","p1","t2","p2","generation_role","generation","status","extent",
    ]
    csv_path = outdir / "NVT9_0919_REFERENCE_DRAW.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)

    index_json = outdir / "NVT9_0919_REFERENCE_INDEX.json"
    index_json.write_text(json.dumps({
        "schema": "nvt9-0919-reference-index/1.0",
        "audit_id": "ID10IQ200",
        "status": "PASS_REFERENCE_REBUILT_FROM_FROZEN_MANIFEST",
        "manifest": str(manifest_path),
        "reference_count": len(index_rows),
        "draw_row_count": len(rows),
        "lines": index_rows,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    txt = [
        "NVT9 09/19 FROZEN REFERENCE INDEX",
        "Audit ID: ID10IQ200",
        "",
    ]
    for x in index_rows:
        txt += [
            f"{x['reference_id']}  {x['timeframe']} {x['structure_level']} {x['direction']}",
            f"  source={x['source_line_id']}",
            f"  A1={x['anchor1_id']} {x['anchor1_time']} {x['anchor1_price']}",
            f"  A2={x['anchor2_id']} {x['anchor2_time']} {x['anchor2_price']}",
            f"  CH offset={x['ch_offset']}  zone={x['zone_width']}",
            "",
        ]
    txt_path = outdir / "NVT9_0919_REFERENCE_INDEX.txt"
    txt_path.write_text("\n".join(txt), encoding="utf-8")

    print(json.dumps({
        "status": "PASS_REFERENCE_REBUILT_FROM_FROZEN_MANIFEST",
        "reference_count": len(index_rows),
        "draw_row_count": len(rows),
        "csv": str(csv_path),
        "index_json": str(index_json),
        "index_txt": str(txt_path),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
