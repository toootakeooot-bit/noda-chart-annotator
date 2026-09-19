from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import cv2
import fitz

A4_LANDSCAPE = fitz.Rect(0, 0, 841.89, 595.28)


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def git_head(repo: Path) -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return out.strip()
    except Exception:
        return None


def put_label(frame, label: str):
    out = frame.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = max(0.7, out.shape[1] / 1800.0)
    thickness = max(2, int(round(scale * 2)))
    (tw, th), _ = cv2.getTextSize(label, font, scale, thickness)
    pad = max(8, int(round(8 * scale)))
    x, y = pad, pad + th
    cv2.rectangle(out, (0, 0), (tw + pad * 2, th + pad * 2), (0, 0, 0), -1)
    cv2.putText(out, label, (x, y), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)
    return out


def format_hms(seconds: float) -> str:
    s = int(round(seconds))
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:02d}"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build a deterministic coarse review bundle for the registered strict NVT8 held-out video."
    )
    ap.add_argument("--registration", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--sample-seconds", type=float, default=10.0)
    args = ap.parse_args()

    if args.sample_seconds <= 0:
        raise ValueError("sample-seconds must be > 0")

    registration_path = Path(args.registration)
    repo = Path(args.repo)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    reg = load_json(registration_path)
    if reg.get("schema") != "nvt8-held-out-source-registration/1.0":
        raise ValueError("unexpected registration schema")
    if reg.get("status") != "REGISTERED_HELD_OUT":
        raise ValueError("held-out source is not registered")
    r = reg.get("registration") or {}
    if r.get("registered_before_teacher_event_review") is not True:
        raise ValueError("registration was not frozen before teacher review")
    if r.get("teacher_content_inspected_during_registration") is not False:
        raise ValueError("registration indicates teacher content was inspected")
    if r.get("source_level_holdout") is not True:
        raise ValueError("registration is not source-level held-out")

    asset = reg.get("asset") or {}
    video = Path(asset.get("local_path_recorded") or "")
    if not video.exists():
        raise FileNotFoundError(f"registered video not found: {video}")

    actual_hash = sha256_file(video)
    if actual_hash != asset.get("sha256"):
        raise ValueError("video SHA256 no longer matches the registered held-out source")

    head = git_head(repo)
    lock = {
        "schema": "nvt8-held-out-inspection-lock/1.0",
        "status": "LOCKED_BEFORE_TEACHER_CONTENT_DECODE",
        "source_id": reg.get("source_id"),
        "filename": asset.get("filename"),
        "sha256": actual_hash,
        "locked_at_utc": datetime.now(timezone.utc).isoformat(),
        "frozen_nvt_git_head": head,
        "rule_tuning_after_teacher_review_allowed": False,
        "failures_must_be_recorded_not_tuned_away": True,
        "teacher_content_review_begins_after_this_lock": True,
        "production_writeback": False,
        "normal_run_modified": False,
        "mt4_object_writeback": False,
        "trade_authority": False,
    }
    lock_path = out_dir / "NVT8_INSPECTION_LOCK.json"
    lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=2), encoding="utf-8")

    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {video}")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = (frame_count / fps) if fps > 0 and frame_count > 0 else 0.0
    if duration <= 0:
        raise RuntimeError("could not determine positive video duration")

    sample_times = []
    t = 0.0
    while t < duration:
        sample_times.append(round(t, 3))
        t += args.sample_seconds
    if not sample_times or abs(sample_times[-1] - duration) > 1.0:
        sample_times.append(max(0.0, duration - min(0.5, 1.0 / max(fps, 1.0))))

    pdf_path = out_dir / "NVT8_HELDOUT_REVIEW_BUNDLE.pdf"
    doc = fitz.open()
    samples = []
    tmp_jpg = out_dir / "_nvt8_review_frame.jpg"

    for idx, sec in enumerate(sample_times, start=1):
        cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000.0)
        ok, frame = cap.read()
        if not ok or frame is None:
            samples.append({"index": idx, "time_seconds": sec, "timecode": format_hms(sec), "status": "FRAME_READ_FAILED"})
            continue

        actual_sec = float(cap.get(cv2.CAP_PROP_POS_MSEC) or (sec * 1000.0)) / 1000.0
        label = f"NVT8 HELD-OUT | {idx}/{len(sample_times)} | {format_hms(actual_sec)} | source={reg.get('source_id')}"
        labeled = put_label(frame, label)

        max_width = 1600
        if labeled.shape[1] > max_width:
            scale = max_width / labeled.shape[1]
            labeled = cv2.resize(labeled, (max_width, int(round(labeled.shape[0] * scale))), interpolation=cv2.INTER_AREA)

        if not cv2.imwrite(str(tmp_jpg), labeled, [int(cv2.IMWRITE_JPEG_QUALITY), 78]):
            raise RuntimeError("failed to write temporary review frame")

        page = doc.new_page(width=A4_LANDSCAPE.width, height=A4_LANDSCAPE.height)
        margin = 18
        header_h = 22
        usable = fitz.Rect(margin, margin + header_h, A4_LANDSCAPE.width - margin, A4_LANDSCAPE.height - margin)
        page.insert_text((margin, margin + 12), label, fontsize=9)
        pix = fitz.Pixmap(str(tmp_jpg))
        ratio = min(usable.width / pix.width, usable.height / pix.height)
        w = pix.width * ratio
        h = pix.height * ratio
        rect = fitz.Rect(
            usable.x0 + (usable.width - w) / 2,
            usable.y0 + (usable.height - h) / 2,
            usable.x0 + (usable.width - w) / 2 + w,
            usable.y0 + (usable.height - h) / 2 + h,
        )
        page.insert_image(rect, filename=str(tmp_jpg), keep_proportion=True)

        samples.append({
            "index": idx,
            "requested_time_seconds": sec,
            "actual_time_seconds": round(actual_sec, 3),
            "timecode": format_hms(actual_sec),
            "status": "OK",
        })

    cap.release()
    if tmp_jpg.exists():
        tmp_jpg.unlink()

    doc.set_metadata({
        "title": "NVT8 Strict Held-Out Coarse Review Bundle",
        "subject": f"source_id={reg.get('source_id')} deterministic {args.sample_seconds:g}s sampling",
        "keywords": "NVT8, held-out, USDJPY, research-only",
    })
    doc.save(pdf_path, garbage=4, deflate=True)
    page_count = doc.page_count
    doc.close()

    verify = fitz.open(pdf_path)
    verified_page_count = verify.page_count
    verify.close()
    ok_samples = sum(1 for s in samples if s.get("status") == "OK")
    if verified_page_count != ok_samples:
        raise RuntimeError(
            f"PDF verification failed: pages={verified_page_count} successful_samples={ok_samples}"
        )

    manifest = {
        "schema": "nvt8-held-out-review-bundle/1.0",
        "status": "REVIEW_BUNDLE_GENERATED",
        "source_id": reg.get("source_id"),
        "filename": asset.get("filename"),
        "sha256": actual_hash,
        "inspection_lock": str(lock_path),
        "frozen_nvt_git_head": head,
        "sampling_policy": {
            "mode": "DETERMINISTIC_FIXED_INTERVAL",
            "sample_seconds": args.sample_seconds,
            "content_adaptive_selection": False,
            "teacher_event_selection_performed": False,
            "purpose": "coarse inspection only; exact teacher events/cutoffs must be registered after review without rule tuning",
        },
        "video": {
            "fps": fps,
            "frame_count": frame_count,
            "duration_seconds": round(duration, 3),
        },
        "review_pdf": str(pdf_path),
        "review_pdf_page_count": verified_page_count,
        "sample_count_requested": len(sample_times),
        "sample_count_ok": ok_samples,
        "samples": samples,
        "rule_tuning_after_teacher_review_allowed": False,
        "production_writeback": False,
        "normal_run_modified": False,
        "mt4_object_writeback": False,
        "trade_authority": False,
    }
    manifest_path = out_dir / "NVT8_HELDOUT_REVIEW_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": manifest["status"],
        "source_id": manifest["source_id"],
        "duration_seconds": manifest["video"]["duration_seconds"],
        "sample_seconds": args.sample_seconds,
        "pdf_pages": verified_page_count,
        "review_pdf": str(pdf_path),
        "manifest": str(manifest_path),
        "inspection_lock": str(lock_path),
        "frozen_nvt_git_head": head,
        "production_writeback": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
