from __future__ import annotations

import argparse
import json
import math
import tempfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import fitz
import numpy as np

SCHEMA_VERSION = "noda-draw-pdf-geometry/0.6"
IGNORE_PATH_WORDS = {"video", "frames", "youtube", "fundamental", "transcript", "audio"}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def contains_ignored_part(path: Path) -> bool:
    return any(any(word in part.lower() for word in IGNORE_PATH_WORDS) for part in path.parts)


def discover_chart_sources(package_dir: Path) -> list[Path]:
    candidates: list[Path] = []
    for ext in ("*.pdf", "*.png", "*.jpg", "*.jpeg", "*.webp"):
        for p in package_dir.rglob(ext):
            if contains_ignored_part(p):
                continue
            if "geometry_debug" in [part.lower() for part in p.parts]:
                continue
            candidates.append(p)
    candidates.sort(key=lambda p: (0 if any(k in str(p).lower() for k in ("chart", "teacher", "analysis")) else 1, str(p).lower()))
    return candidates


def normalize_angle_deg(x1: float, y1: float, x2: float, y2: float) -> float:
    a = math.degrees(math.atan2(y2 - y1, x2 - x1))
    while a > 90:
        a -= 180
    while a <= -90:
        a += 180
    return a


def orientation(angle: float) -> str:
    a = abs(angle)
    if a <= 2.5:
        return "HORIZONTAL"
    if a >= 87.5:
        return "VERTICAL_GUIDE"
    return "OBLIQUE"


def rgb_to_hex(rgb: tuple[int, int, int] | None) -> str | None:
    if rgb is None:
        return None
    return "#%02X%02X%02X" % rgb


def fitz_color_to_rgb(color: Any) -> tuple[int, int, int] | None:
    if color is None:
        return None
    try:
        vals = list(color)
        if len(vals) >= 3:
            return tuple(int(round(clamp01(v) * 255)) for v in vals[:3])
    except Exception:
        return None
    return None


@dataclass
class LinePrimitive:
    primitive_id: str
    source: str
    source_mode: str
    page: int
    p1_norm: list[float]
    p2_norm: list[float]
    angle_deg: float
    orientation: str
    length_norm: float
    stroke_hex: str | None
    stroke_width: float | None
    detection_quality: str
    semantic_status: str = "UNKNOWN"
    rationale_status: str = "UNKNOWN"


def line_key(line: LinePrimitive, precision: int = 3) -> tuple:
    p1 = tuple(round(v, precision) for v in line.p1_norm)
    p2 = tuple(round(v, precision) for v in line.p2_norm)
    ends = tuple(sorted((p1, p2)))
    return (line.page, ends, round(line.angle_deg, 1), line.stroke_hex)


def dedupe_lines(lines: list[LinePrimitive]) -> list[LinePrimitive]:
    out: list[LinePrimitive] = []
    seen: set[tuple] = set()
    for line in sorted(lines, key=lambda x: (x.page, -x.length_norm, x.primitive_id)):
        key = line_key(line)
        if key in seen:
            continue
        seen.add(key)
        out.append(line)
    return out


def mk_line(*, idx: int, source: Path, source_mode: str, page: int, x1: float, y1: float, x2: float, y2: float,
            width: float, height: float, stroke_rgb: tuple[int, int, int] | None, stroke_width: float | None,
            quality: str) -> LinePrimitive | None:
    diag = math.hypot(width, height)
    length = math.hypot(x2 - x1, y2 - y1)
    if diag <= 0 or length / diag < 0.055:
        return None
    angle = normalize_angle_deg(x1, y1, x2, y2)
    near_border = min(x1, x2) < width * 0.006 or max(x1, x2) > width * 0.994 or min(y1, y2) < height * 0.006 or max(y1, y2) > height * 0.994
    if near_border and length / diag > 0.75:
        return None
    return LinePrimitive(
        primitive_id=f"P{page:02d}_L{idx:04d}", source=str(source), source_mode=source_mode, page=page,
        p1_norm=[clamp01(x1 / width), clamp01(y1 / height)], p2_norm=[clamp01(x2 / width), clamp01(y2 / height)],
        angle_deg=round(angle, 3), orientation=orientation(angle), length_norm=round(length / diag, 5),
        stroke_hex=rgb_to_hex(stroke_rgb), stroke_width=None if stroke_width is None else round(float(stroke_width), 3),
        detection_quality=quality,
    )


def extract_vector_lines(pdf: Path) -> tuple[list[LinePrimitive], list[dict[str, Any]]]:
    doc = fitz.open(pdf)
    result: list[LinePrimitive] = []
    page_meta: list[dict[str, Any]] = []
    seq = 0
    for pidx, page in enumerate(doc, start=1):
        rect = page.rect
        vector_count = 0
        for drawing in page.get_drawings():
            color = fitz_color_to_rgb(drawing.get("color"))
            sw = drawing.get("width")
            for item in drawing.get("items", []):
                if not item:
                    continue
                kind = item[0]
                segments: list[tuple[float, float, float, float]] = []
                if kind == "l" and len(item) >= 3:
                    p1, p2 = item[1], item[2]
                    segments.append((p1.x, p1.y, p2.x, p2.y))
                elif kind == "re" and len(item) >= 2:
                    r = item[1]
                    segments.extend([(r.x0,r.y0,r.x1,r.y0),(r.x1,r.y0,r.x1,r.y1),(r.x1,r.y1,r.x0,r.y1),(r.x0,r.y1,r.x0,r.y0)])
                for x1,y1,x2,y2 in segments:
                    seq += 1
                    line = mk_line(idx=seq, source=pdf, source_mode="PDF_VECTOR", page=pidx, x1=x1,y1=y1,x2=x2,y2=y2,
                                   width=rect.width,height=rect.height,stroke_rgb=color,stroke_width=sw,quality="HIGH")
                    if line:
                        result.append(line)
                        vector_count += 1
        page_meta.append({"page": pidx, "width": rect.width, "height": rect.height, "vector_candidate_count": vector_count})
    return dedupe_lines(result), page_meta


def render_pdf_page(page: fitz.Page, dpi: int = 150) -> np.ndarray:
    scale = dpi / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
    else:
        arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    return arr


def segment_mean_rgb(img_bgr: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> tuple[int,int,int] | None:
    mask = np.zeros(img_bgr.shape[:2], dtype=np.uint8)
    cv2.line(mask, (x1,y1), (x2,y2), 255, thickness=3)
    pixels = img_bgr[mask > 0]
    if pixels.size == 0:
        return None
    bgr = np.median(pixels, axis=0)
    return int(bgr[2]), int(bgr[1]), int(bgr[0])


def extract_raster_lines_from_image(img_bgr: np.ndarray, source: Path, page_num: int, source_mode: str = "RASTER_HOUGH") -> list[LinePrimitive]:
    h, w = img_bgr.shape[:2]
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    s = hsv[:,:,1]
    v = hsv[:,:,2]
    colored = np.where((s >= 55) & (v >= 75), 255, 0).astype(np.uint8)
    bright = np.where((s <= 45) & (v >= 205), 255, 0).astype(np.uint8)
    mask = cv2.bitwise_or(colored, bright)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3,3), np.uint8), iterations=1)
    edges = cv2.Canny(mask, 50, 150, apertureSize=3)
    min_len = max(45, int(w * 0.11))
    raw = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=max(35, int(w*0.025)), minLineLength=min_len, maxLineGap=max(8, int(w*0.012)))
    if raw is None:
        return []
    lines: list[LinePrimitive] = []
    diag = math.hypot(w, h)
    seq = 0
    for row in raw[:,0,:]:
        x1,y1,x2,y2 = map(int,row)
        length_norm = math.hypot(x2-x1,y2-y1) / diag
        if length_norm < 0.055:
            continue
        seq += 1
        quality = "HIGH" if length_norm >= 0.30 else "MEDIUM" if length_norm >= 0.16 else "LOW"
        rgb = segment_mean_rgb(img_bgr,x1,y1,x2,y2)
        line = mk_line(idx=seq, source=source, source_mode=source_mode, page=page_num, x1=x1,y1=y1,x2=x2,y2=y2,
                       width=w,height=h,stroke_rgb=rgb,stroke_width=None,quality=quality)
        if line:
            lines.append(line)
    return dedupe_lines(lines)


def extract_raster_lines(source: Path) -> tuple[list[LinePrimitive], list[dict[str,Any]], dict[int,np.ndarray]]:
    all_lines: list[LinePrimitive] = []
    meta: list[dict[str,Any]] = []
    rendered: dict[int,np.ndarray] = {}
    if source.suffix.lower() == ".pdf":
        doc = fitz.open(source)
        for pidx,page in enumerate(doc,start=1):
            img = render_pdf_page(page)
            rendered[pidx] = img
            lines = extract_raster_lines_from_image(img, source, pidx)
            all_lines.extend(lines)
            meta.append({"page": pidx, "raster_candidate_count": len(lines), "pixel_width": img.shape[1], "pixel_height": img.shape[0]})
    else:
        img = cv2.imread(str(source), cv2.IMREAD_COLOR)
        if img is not None:
            rendered[1] = img
            lines = extract_raster_lines_from_image(img, source, 1, source_mode="IMAGE_HOUGH")
            all_lines.extend(lines)
            meta.append({"page": 1, "raster_candidate_count": len(lines), "pixel_width": img.shape[1], "pixel_height": img.shape[0]})
    return dedupe_lines(all_lines), meta, rendered


def dominant_line_set(vector: list[LinePrimitive], raster: list[LinePrimitive]) -> tuple[list[LinePrimitive], str]:
    useful_vector = [x for x in vector if x.orientation != "VERTICAL_GUIDE"]
    if len(useful_vector) >= 3:
        return useful_vector, "PDF_VECTOR"
    useful_raster = [x for x in raster if x.orientation != "VERTICAL_GUIDE"]
    return useful_raster, "RASTER_FALLBACK"


def line_mid(l: LinePrimitive) -> tuple[float,float]:
    return ((l.p1_norm[0]+l.p2_norm[0])/2, (l.p1_norm[1]+l.p2_norm[1])/2)


def parallel_pairs(lines: list[LinePrimitive]) -> list[dict[str,Any]]:
    obs = [l for l in lines if l.orientation == "OBLIQUE" and l.length_norm >= 0.10]
    pairs: list[dict[str,Any]] = []
    used: set[tuple[str,str]] = set()
    for i,a in enumerate(obs):
        for b in obs[i+1:]:
            if a.page != b.page or abs(a.angle_deg - b.angle_deg) > 2.5:
                continue
            ratio = min(a.length_norm,b.length_norm) / max(a.length_norm,b.length_norm)
            if ratio < 0.45:
                continue
            am,bm = line_mid(a),line_mid(b)
            sep = math.hypot(am[0]-bm[0], am[1]-bm[1])
            if sep < 0.015 or sep > 0.40:
                continue
            key = tuple(sorted((a.primitive_id,b.primitive_id)))
            if key in used:
                continue
            used.add(key)
            pairs.append({"pair_id":f"PAIR_{len(pairs)+1:03d}","page":a.page,"line_a":a.primitive_id,"line_b":b.primitive_id,
                          "angle_deg":round((a.angle_deg+b.angle_deg)/2,3),"pair_kind":"PARALLEL_PAIR_CANDIDATE",
                          "semantic_status":"UNKNOWN","rationale_status":"UNKNOWN"})
    return pairs


def observation_from_geometry(package_dir: Path, sources: list[Path], lines: list[LinePrimitive], pairs: list[dict[str,Any]], mode: str) -> dict[str,Any]:
    objects: list[dict[str,Any]] = []
    for l in lines:
        role = "HORIZONTAL_LINE" if l.orientation == "HORIZONTAL" else "OBLIQUE_LINE"
        objects.append({"object_id":l.primitive_id,"type":"LOCAL_STRUCTURE","role":role,"geometry":None,
                        "visual_geometry":{"page":l.page,"p1_norm":l.p1_norm,"p2_norm":l.p2_norm},"renderability":"APPROXIMATE",
                        "geometry_quality":l.source_mode,"evidence_status":"TEACHER_DRAWN_GEOMETRY","matched_rules":[],
                        "rationale_status":"UNKNOWN","notes":"Directly extracted Teacher-drawn geometry. TL/CH/HL semantic role is not asserted from pixels alone."})
    for p in pairs:
        objects.append({"object_id":p["pair_id"],"type":"CHANNEL_STRUCTURE","role":"PARALLEL_PAIR_CANDIDATE","geometry":None,
                        "visual_geometry":{"page":p["page"],"line_refs":[p["line_a"],p["line_b"]]},"renderability":"APPROXIMATE",
                        "geometry_quality":mode,"evidence_status":"GEOMETRY_MATCH","matched_rules":["R06"],"rationale_status":"UNKNOWN",
                        "notes":"Parallel geometry matches the channel geometry portion of R06; which side is TL vs CH remains UNKNOWN."})
    return {"schema_version":"noda-draw-teacher-observation-geometry/0.6","generated_at_utc":now_iso(),"pipeline_mode":"PDF_GEOMETRY_DETERMINISTIC",
            "teacher_case":package_dir.name,"teacher_date":None,"symbol":None,"video_used":False,"openai_api_used":False,"ollama_used":False,
            "sources":[{"kind":"TEACHER_CHART","path":str(s)} for s in sources],"objects":objects,"observed_noncomparable":[],
            "warnings":["Teacher rationale is not inferred. Semantic TL/CH/HL assignment remains UNKNOWN unless a later rule-mapping stage can prove it."]}


def draw_debug(img: np.ndarray, lines: list[LinePrimitive], out: Path, page: int) -> None:
    h,w = img.shape[:2]
    canvas = img.copy()
    for l in lines:
        if l.page != page:
            continue
        p1=(int(l.p1_norm[0]*w),int(l.p1_norm[1]*h)); p2=(int(l.p2_norm[0]*w),int(l.p2_norm[1]*h))
        cv2.line(canvas,p1,p2,(0,255,0),2)
    out.parent.mkdir(parents=True,exist_ok=True)
    cv2.imwrite(str(out),canvas)


def write_status(package_dir: Path, status: str, **extra: Any) -> None:
    payload = {"status":status,"updated_at_utc":now_iso(),"pipeline_mode":"PDF_GEOMETRY_DETERMINISTIC",**extra}
    (package_dir/"pdf_only_status.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")


def process_package(package_dir: Path, write_debug: bool = True) -> int:
    sources = discover_chart_sources(package_dir)
    if not sources:
        write_status(package_dir,"NO_CHART_WEEK",video_used=False,openai_api_used=False,ollama_used=False)
        print("NO_CHART_WEEK / PASS"); return 0
    all_lines: list[LinePrimitive] = []
    source_reports: list[dict[str,Any]] = []
    debug_images: list[tuple[np.ndarray,Path,int,list[LinePrimitive]]] = []
    modes: list[str] = []
    for src in sources:
        vector: list[LinePrimitive] = []; vmeta: list[dict[str,Any]] = []
        if src.suffix.lower() == ".pdf":
            vector,vmeta = extract_vector_lines(src)
        raster,rmeta,rendered = extract_raster_lines(src)
        chosen,mode = dominant_line_set(vector,raster)
        modes.append(mode); all_lines.extend(chosen)
        source_reports.append({"path":str(src),"selected_mode":mode,"vector_count":len(vector),"raster_count":len(raster),"page_meta":vmeta or rmeta})
        if write_debug:
            for page,img in rendered.items(): debug_images.append((img,src,page,chosen))
    all_lines = dedupe_lines(all_lines)
    if not all_lines:
        write_status(package_dir,"REVIEW_REQUIRED",reason="No stable line geometry detected",video_used=False,openai_api_used=False,ollama_used=False)
        print("REVIEW_REQUIRED: No stable line geometry detected"); return 3
    pairs = parallel_pairs(all_lines)
    geometry = {"schema_version":SCHEMA_VERSION,"generated_at_utc":now_iso(),"pipeline_mode":"PDF_GEOMETRY_DETERMINISTIC",
                "video_used":False,"openai_api_used":False,"ollama_used":False,"sources":source_reports,
                "primitives":[asdict(x) for x in all_lines],"parallel_pairs":pairs,
                "audit":{"semantic_policy":"Geometry is extracted directly; semantic role is not invented.","teacher_rationale":"UNKNOWN / deferred"}}
    (package_dir/"teacher_geometry.json").write_text(json.dumps(geometry,ensure_ascii=False,indent=2),encoding="utf-8")
    observation = observation_from_geometry(package_dir,sources,all_lines,pairs,"+".join(sorted(set(modes))))
    (package_dir/"teacher_observation.json").write_text(json.dumps(observation,ensure_ascii=False,indent=2),encoding="utf-8")
    if write_debug:
        dbg=package_dir/"geometry_debug"
        for img,src,page,chosen in debug_images: draw_debug(img,chosen,dbg/f"{src.stem}_p{page:02d}_detected.png",page)
    write_status(package_dir,"PDF_GEOMETRY_READY",primitive_count=len(all_lines),parallel_pair_count=len(pairs),video_used=False,openai_api_used=False,ollama_used=False)
    print(f"PDF_GEOMETRY_READY / PASS primitives={len(all_lines)} parallel_pairs={len(pairs)}")
    return 0


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="noda_geom_selftest_") as td:
        root=Path(td); pkg=root/"pkg_selftest"; pkg.mkdir(); pdf=pkg/"teacher_chart_test.pdf"
        doc=fitz.open(); page=doc.new_page(width=800,height=500)
        page.draw_line(fitz.Point(80,400),fitz.Point(650,180),color=(0,0.8,1),width=3)
        page.draw_line(fitz.Point(90,330),fitz.Point(660,110),color=(0,0.8,1),width=3)
        page.draw_line(fitz.Point(100,250),fitz.Point(700,250),color=(1,1,1),width=3)
        doc.save(pdf); doc.close()
        rc=process_package(pkg,write_debug=False)
        if rc!=0: return rc
        data=json.loads((pkg/"teacher_geometry.json").read_text(encoding="utf-8"))
        if len(data.get("primitives",[])) < 3:
            print("SELFTEST FAIL: expected >=3 primitives"); return 8
        if len(data.get("parallel_pairs",[])) < 1:
            print("SELFTEST FAIL: expected parallel pair"); return 9
        print("SELFTEST PASS: deterministic PDF geometry extraction works."); return 0


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument("--package"); ap.add_argument("--self-test",action="store_true"); ap.add_argument("--no-debug",action="store_true"); args=ap.parse_args()
    if args.self_test: return self_test()
    if not args.package: ap.error("--package is required unless --self-test is used")
    pkg=Path(args.package).resolve()
    if not pkg.exists(): print(f"ERROR: package not found: {pkg}"); return 2
    return process_package(pkg,write_debug=not args.no_debug)

if __name__ == "__main__":
    raise SystemExit(main())
