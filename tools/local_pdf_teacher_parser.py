from __future__ import annotations

import argparse
import base64
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import fitz
import requests

SCHEMA_VERSION = "noda-draw-teacher-observation-local/0.5"
ALLOWED_TYPES = {"TL", "CH", "CHANNEL_STRUCTURE", "HL", "ZONE", "LOCAL_STRUCTURE", "FIB", "SCENARIO", "SCENARIO_PATH", "CONTEXT_SERIES"}
PROHIBITED_KEYS = {"entry", "entry_price", "long_short", "trade_direction", "sl", "stop_loss", "tp", "take_profit", "rr", "risk_reward", "lot", "order_type", "ticket"}
IGNORE_PATH_WORDS = {"video", "frames", "youtube", "fundamental", "transcript", "audio"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def contains_ignored_part(path: Path) -> bool:
    return any(any(word in part.lower() for word in IGNORE_PATH_WORDS) for part in path.parts)


def discover_chart_sources(package_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    for ext in ("*.pdf", "*.png", "*.jpg", "*.jpeg", "*.webp"):
        for p in package_dir.rglob(ext):
            if contains_ignored_part(p):
                continue
            candidates.append(p)
    candidates.sort(key=lambda p: (0 if any(k in str(p).lower() for k in ("chart", "teacher", "analysis")) else 1, str(p).lower()))
    return candidates


def pdf_to_pngs(pdf_path: Path, out_dir: Path, dpi: int = 150, max_pages: int = 8) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    paths: list[Path] = []
    matrix = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    for i, page in enumerate(doc):
        if i >= max_pages:
            break
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        out = out_dir / f"{pdf_path.stem}_p{i+1:02d}.png"
        pix.save(out)
        paths.append(out)
    return paths


def image_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def load_rules(project_root: Path) -> dict[str, Any]:
    rule_path = project_root / "spec" / "noda_rules_current.json"
    return json.loads(rule_path.read_text(encoding="utf-8"))


def build_prompt(rules: dict[str, Any]) -> str:
    return f'''You are the local observation parser for NODA Chart Annotator.
Analyze ONLY the attached Teacher chart PDF pages/images. Video is intentionally unavailable.
Do not invent Teacher intent. If a reason is not directly visible, set rationale_status to UNKNOWN or VIDEO_RATIONALE_PENDING.
Do not make any trading decision.

Current fixed rule context:
{json.dumps(rules, ensure_ascii=False, indent=2)}

Return JSON only with: schema_version, teacher_case, teacher_date, symbol, sources, objects, observed_noncomparable, warnings.
Each object may contain: object_id, type, timeframe, role, geometry, visual_geometry, renderability, geometry_quality, evidence_status, matched_rules, rationale_status, notes.
visual_geometry uses page plus normalized p1_norm/p2_norm coordinates in [0,1].
Use geometry=null unless exact market time/price is explicitly readable and reliable from source; do not infer exact price/time from pixels.
TL/CH/HL/ZONE are active scope. FIB/SCENARIO are observation-only HOLD unless an existing fixed rule enables them.
Color does not globally define semantic role. Timeframe does not define structural level.
Never create numeric strength scores, pips, ATR thresholds, entry triggers, targets, stops, position size, or orders.
If material is insufficient, return objects=[] with a warning; do not fabricate.'''


def call_ollama(model: str, prompt: str, images: Iterable[Path], timeout: int = 900) -> dict[str, Any]:
    payload = {"model": model, "stream": False, "format": "json", "messages": [{"role": "user", "content": prompt, "images": [image_b64(p) for p in images]}], "options": {"temperature": 0.1}}
    r = requests.post("http://127.0.0.1:11434/api/chat", json=payload, timeout=timeout)
    r.raise_for_status()
    content = r.json().get("message", {}).get("content", "")
    if not content:
        raise RuntimeError("Ollama returned empty content")
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.I | re.S)
        return json.loads(content)


def validate_no_trade_fields(node: Any, path: str = "$") -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            if k.lower() in PROHIBITED_KEYS:
                raise ValueError(f"Forbidden trade field detected at {path}.{k}")
            validate_no_trade_fields(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, item in enumerate(node):
            validate_no_trade_fields(item, f"{path}[{i}]")


def normalize_output(data: dict[str, Any], source_paths: list[Path]) -> dict[str, Any]:
    validate_no_trade_fields(data)
    data["schema_version"] = SCHEMA_VERSION
    data["generated_at_utc"] = now_iso()
    data["pipeline_mode"] = "PDF_ONLY_LOCAL"
    data["video_used"] = False
    data["openai_api_used"] = False
    data["sources"] = [{"kind": "TEACHER_CHART", "path": str(p)} for p in source_paths]
    clean_objects = []
    for obj in data.get("objects") or []:
        if not isinstance(obj, dict):
            continue
        t = str(obj.get("type", "")).upper()
        if t not in ALLOWED_TYPES:
            continue
        obj["type"] = t
        if t in {"FIB", "SCENARIO", "SCENARIO_PATH", "CONTEXT_SERIES"}:
            obj["renderability"] = "NOT_READY"
            obj.setdefault("notes", "Observed only; automatic generation is HOLD in v0.5.")
        if obj.get("rationale_status") in (None, ""):
            obj["rationale_status"] = "UNKNOWN"
        clean_objects.append(obj)
    data["objects"] = clean_objects
    data.setdefault("observed_noncomparable", [])
    data.setdefault("warnings", [])
    return data


def write_status(package_dir: Path, status: str, **extra: Any) -> None:
    payload = {"status": status, "updated_at_utc": now_iso(), **extra}
    (package_dir / "pdf_only_status.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True)
    parser.add_argument("--model", default=os.environ.get("NODA_VLM_MODEL", "qwen3-vl:8b"))
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    package_dir = Path(args.package).resolve()
    project_root = Path(args.project_root).resolve()
    if not package_dir.exists():
        print(f"ERROR: package not found: {package_dir}")
        return 2
    sources = discover_chart_sources(package_dir)
    if not sources:
        write_status(package_dir, "NO_CHART_WEEK", video_used=False, openai_api_used=False)
        print("NO_CHART_WEEK / PASS")
        return 0
    image_paths: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="noda_pdf_only_") as td:
        tmp = Path(td)
        for src in sources:
            if src.suffix.lower() == ".pdf":
                image_paths.extend(pdf_to_pngs(src, tmp))
            else:
                image_paths.append(src)
        if not image_paths:
            write_status(package_dir, "REVIEW_REQUIRED", reason="chart source could not be rasterized")
            return 3
        try:
            result = call_ollama(args.model, build_prompt(load_rules(project_root)), image_paths)
            result = normalize_output(result, sources)
        except requests.RequestException as e:
            write_status(package_dir, "LOCAL_VLM_ERROR", reason=str(e))
            print(f"LOCAL_VLM_ERROR: {e}")
            return 4
        except Exception as e:
            write_status(package_dir, "REVIEW_REQUIRED", reason=str(e))
            print(f"REVIEW_REQUIRED: {e}")
            return 5
    out = package_dir / "teacher_observation.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    write_status(package_dir, "PDF_ONLY_OBSERVATION_READY", model=args.model, observation=str(out), video_used=False, openai_api_used=False)
    print(f"PDF_ONLY_OBSERVATION_READY / PASS: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
