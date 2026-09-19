from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import fitz

A4 = fitz.Rect(0, 0, 841.89, 595.28)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def hms(seconds: float) -> str:
    s = int(round(seconds))
    return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"


def label_frame(frame, label: str):
    out = frame.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = max(0.7, out.shape[1] / 1800.0)
    thick = max(2, int(round(scale * 2)))
    (tw, th), _ = cv2.getTextSize(label, font, scale, thick)
    pad = max(8, int(round(8 * scale)))
    cv2.rectangle(out, (0,0), (tw + 2*pad, th + 2*pad), (0,0,0), -1)
    cv2.putText(out, label, (pad, pad+th), font, scale, (255,255,255), thick, cv2.LINE_AA)
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--registration", required=True)
    ap.add_argument("--inspection-lock", required=True)
    ap.add_argument("--windows", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--sample-seconds", type=float, default=5.0)
    args=ap.parse_args()

    reg=load_json(args.registration)
    lock=load_json(args.inspection_lock)
    win=load_json(args.windows)

    if reg.get("status")!="REGISTERED_HELD_OUT":
        raise ValueError("held-out registration is not valid")
    if lock.get("status")!="LOCKED_BEFORE_TEACHER_CONTENT_DECODE":
        raise ValueError("inspection lock missing/invalid")
    if win.get("source_id") != reg.get("source_id") or lock.get("source_id") != reg.get("source_id"):
        raise ValueError("source_id mismatch")
    if args.sample_seconds <= 0:
        raise ValueError("sample-seconds must be positive")

    video=Path((reg.get("asset") or {}).get("local_path_recorded") or "")
    if not video.exists():
        raise FileNotFoundError(video)

    outdir=Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    pdf_path=outdir/"NVT8_HELDOUT_EVENT_ZOOM_BUNDLE.pdf"
    manifest_path=outdir/"NVT8_HELDOUT_EVENT_ZOOM_MANIFEST.json"

    cap=cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise RuntimeError("cannot open video")
    duration=(cap.get(cv2.CAP_PROP_FRAME_COUNT)/cap.get(cv2.CAP_PROP_FPS))
    doc=fitz.open()
    tmp=outdir/"_nvt8_zoom.jpg"
    records=[]

    for w in win.get("windows") or []:
        wid=w["id"]
        start=max(0.0,float(w["start_seconds"]))
        end=min(float(duration),float(w["end_seconds"]))
        if end < start:
            continue
        times=[]
        t=start
        while t <= end + 1e-9:
            times.append(round(t,3))
            t += args.sample_seconds

        cover=doc.new_page(width=A4.width,height=A4.height)
        cover.insert_text((40,80), f"{wid}  TF={w.get('tf_hint')}  {hms(start)}-{hms(end)}", fontsize=18)
        cover.insert_text((40,120), f"Focus: {w.get('focus')}", fontsize=11)
        cover.insert_text((40,155), "Strict NVT8 evidence localization only - no rule tuning.", fontsize=10)

        for n,t in enumerate(times, start=1):
            cap.set(cv2.CAP_PROP_POS_MSEC,t*1000)
            ok,frame=cap.read()
            if not ok or frame is None:
                records.append({"window_id":wid,"requested_time_seconds":t,"status":"FRAME_READ_FAILED"})
                continue
            actual=(cap.get(cv2.CAP_PROP_POS_MSEC) or t*1000)/1000.0
            label=f"NVT8 ZOOM | {wid} | {n}/{len(times)} | {hms(actual)} | TF={w.get('tf_hint')}"
            frame=label_frame(frame,label)
            if frame.shape[1]>1600:
                sc=1600/frame.shape[1]
                frame=cv2.resize(frame,(1600,int(round(frame.shape[0]*sc))),interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(tmp),frame,[int(cv2.IMWRITE_JPEG_QUALITY),82])

            page=doc.new_page(width=A4.width,height=A4.height)
            margin=18
            page.insert_text((margin,margin+12),label,fontsize=9)
            usable=fitz.Rect(margin,margin+26,A4.width-margin,A4.height-margin)
            pix=fitz.Pixmap(str(tmp))
            ratio=min(usable.width/pix.width,usable.height/pix.height)
            ww,hh=pix.width*ratio,pix.height*ratio
            rect=fitz.Rect(usable.x0+(usable.width-ww)/2,usable.y0+(usable.height-hh)/2,
                           usable.x0+(usable.width-ww)/2+ww,usable.y0+(usable.height-hh)/2+hh)
            page.insert_image(rect,filename=str(tmp),keep_proportion=True)
            records.append({"window_id":wid,"requested_time_seconds":t,"actual_time_seconds":round(actual,3),"timecode":hms(actual),"status":"OK"})

    cap.release()
    if tmp.exists():
        tmp.unlink()
    doc.save(pdf_path,garbage=4,deflate=True)
    pages=doc.page_count
    doc.close()

    manifest={
      "schema":"nvt8-held-out-event-zoom-bundle/1.0",
      "status":"EVENT_ZOOM_BUNDLE_GENERATED",
      "source_id":reg.get("source_id"),
      "filename":(reg.get("asset") or {}).get("filename"),
      "inspection_lock_frozen_nvt_git_head":lock.get("frozen_nvt_git_head"),
      "coarse_windows_schema":win.get("schema"),
      "sample_seconds":args.sample_seconds,
      "window_count":len(win.get("windows") or []),
      "pdf_page_count":pages,
      "review_pdf":str(pdf_path),
      "records":records,
      "teacher_event_registry_frozen":False,
      "rule_tuning_after_teacher_review_allowed":False,
      "production_writeback":False,
      "normal_run_modified":False,
      "mt4_object_writeback":False
    }
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"status":manifest["status"],"pdf":str(pdf_path),"manifest":str(manifest_path),"pages":pages},ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
