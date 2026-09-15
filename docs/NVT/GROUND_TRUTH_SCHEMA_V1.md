# NVT Ground Truth Schema v1

Status: **FIXED**  
Fixed date: 2026-09-15

## 1. Purpose

Ground Truth is the structured representation of what is actually observable in a Noda-sensei reference image/video at a specific market-data cutoff.

Ground Truth records evidence. It must not silently infer rules that were not observed.

## 2. Required case identity

Each case must have:

```text
case_id
source_id
source_type: IMAGE | VIDEO
symbol
timeframe
decision_time or decision_bar
market_data_cutoff
source_confidence
annotation_status
```

`market_data_cutoff` is mandatory for replay validation.

## 3. Source locator

For images:

```text
source_file_name or external source identifier
optional crop / frame region
```

For videos:

```text
source_file_name or external source identifier
video_timestamp_start
video_timestamp_end or event timestamp
```

Original large media is not required in Git. The manifest must be sufficient to locate the evidence externally.

## 4. Teacher object record

Each observed drawing object should record, where observable:

```text
object_id
object_type: TL | CH | ZONE | OTHER_REFERENCE
direction: UP | DOWN | FLAT | UNKNOWN
teacher_role: MAJOR | CURRENT | REFERENCE | UNKNOWN
action: ADD | KEEP | MOVE | REPLACE | DELETE | UNKNOWN
anchor1_bar / anchor1_time / anchor1_price
anchor2_bar / anchor2_time / anchor2_price
opposite_anchor_bar / time / price   # for CH where observable
line_extent: RAY | SEGMENT | UNKNOWN
style_class
anchor_bar_status: CLOSED | FORMING | UNKNOWN
confidence
notes
```

Do not fabricate an exact anchor when the source image/video does not support one. Use `UNKNOWN` and record confidence.

## 5. Event record for video

Video cases may contain ordered teacher events:

```text
event_id
video_timestamp
market_data_cutoff
action
object_id_before
object_id_after
observed_reason_text        # only if explicitly stated by teacher
annotator_note
confidence
```

`observed_reason_text` and `annotator_note` must remain distinct. Teacher-stated rationale must not be mixed with analyst inference.

## 6. NCA comparison fields

Comparison results are not Ground Truth itself, but may reference the case with:

```text
candidate_present
selected_candidate_id
anchor_match
channel_match
lifecycle_match
role_match
style_match
failure_class
```

Allowed top-level failure classes for v1:

```text
PASS
CANDIDATE_ABSENT
SELECTION
ANCHOR
CHANNEL
LIFECYCLE
ROLE
RENDER_STYLE
INSUFFICIENT_EVIDENCE
```

## 7. Ground Truth states

```text
DRAFT       = evidence registered but not fully annotated
REVIEWED    = annotation checked against source
LOCKED      = accepted for regression use
SUPERSEDED  = replaced by a newer corrected annotation
```

Only `LOCKED` cases may be used as hard regression acceptance evidence.

## 8. Minimum confidence discipline

Where an anchor or teacher action is visually ambiguous, the case must not be forced into a hard PASS/FAIL comparison. Mark the field unknown or the case as `INSUFFICIENT_EVIDENCE` for that dimension.

## 9. File format

Ground Truth cases should be stored as JSON under:

```text
nvt/ground_truth/
```

A canonical template is stored with the NVT scaffold.
