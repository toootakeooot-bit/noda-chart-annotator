from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ALLOWED_EXTENSIONS = {".mkv", ".mp4", ".mov", ".m4v", ".webm"}


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


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Register a previously unseen USDJPY teacher video for strict NVT8 before any teacher-event inspection. "
            "This tool hashes file bytes only; it does not decode frames, audio, subtitles, or teacher content."
        )
    )
    ap.add_argument("--video", required=True)
    ap.add_argument("--known-corpus", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--recording-date", default=None)
    ap.add_argument("--source-id", default=None)
    ap.add_argument("--attest-unseen", action="store_true", required=True)
    args = ap.parse_args()

    video = Path(args.video).expanduser().resolve()
    if not video.exists() or not video.is_file():
        raise FileNotFoundError(f"video file not found: {video}")
    if video.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError(f"unsupported video extension: {video.suffix}")

    corpus = load_json(args.known_corpus)
    known_sources = corpus.get("sources") or []
    known_titles = {str(s.get("title") or "").strip() for s in known_sources}
    known_source_ids = {str(s.get("source_id") or "").strip() for s in known_sources}

    if video.name in known_titles:
        raise ValueError(
            "this filename is already in the NVT0-NVT7 development corpus and cannot be registered as strict held-out"
        )

    digest = sha256_file(video)
    source_id = args.source_id or f"NVT8_HOLDOUT_{digest[:12].upper()}"
    if source_id in known_source_ids:
        raise ValueError("source_id collides with an existing development source")

    report = {
        "schema": "nvt8-held-out-source-registration/1.0",
        "status": "REGISTERED_HELD_OUT",
        "purpose": "Strict NVT8 source registration performed before teacher-event inspection.",
        "source_id": source_id,
        "asset": {
            "filename": video.name,
            "type": "VIDEO",
            "symbol": "USDJPY",
            "recording_date": args.recording_date,
            "sha256": digest,
            "size_bytes": video.stat().st_size,
            "local_path_recorded": str(video),
        },
        "registration": {
            "registered_at_utc": datetime.now(timezone.utc).isoformat(),
            "registered_before_teacher_event_review": True,
            "previously_inspected_in_nvt0_to_nvt7_1": False,
            "previously_used_for_rule_tuning": False,
            "source_level_holdout": True,
            "future_hidden_market_replay_required": True,
            "user_attested_unseen": bool(args.attest_unseen),
            "teacher_content_inspected_during_registration": False,
            "registration_method": "FILE_METADATA_AND_SHA256_ONLY",
        },
        "known_development_corpus_check": {
            "known_corpus_id": corpus.get("corpus_id"),
            "known_development_source_count": len(known_sources),
            "filename_matches_known_development_source": False,
            "note": "Hash-level duplicate detection against old sources is unavailable unless their hashes are separately registered; unseen-source status also relies on the user attestation.",
        },
        "frozen_rule_inputs": {
            "nvt7_scoped_beta_required": True,
            "nvt7_frozen_scope_regression_required": True,
            "nvt7_1_semantic_freeze_schema": "nvt7.1-usdjpy-semantic-freeze-candidate/0.2",
        },
        "inspection_lock": {
            "teacher_event_review_allowed_after_this_registration": True,
            "rule_tuning_after_teacher_review_allowed": False,
            "failures_must_be_recorded_not_tuned_away": True,
        },
        "strict_nvt8_only": True,
        "nvt8h_is_not_substitute": True,
        "production_writeback": False,
        "normal_run_modified": False,
        "mt4_object_writeback": False,
        "trade_authority": False,
    }

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "status": report["status"],
        "source_id": source_id,
        "filename": video.name,
        "sha256": digest,
        "output": str(out),
        "teacher_content_inspected": False,
        "production_writeback": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
