from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEWER = ROOT / "mt4" / "NCA_NVT9_Reference0919_View.mq4"


def main() -> None:
    text = VIEWER.read_text(encoding="utf-8")

    required = [
        'string PREFIX = "NVT9_REF0919__"',
        '"NVT9_TFMAP__"',
        '"NVT9_PREVIEW__"',
        '"NVT9_AB_CUTOFF__"',
        'if(role=="HL")',
        'SourceVisibleOnDestination',
        '[UPDATED CH]',
        'rowTf+" CONT TL"',
        'rowTf+" DECISION HL"',
        '[ZONE]',
    ]
    for token in required:
        assert token in text, token

    forbidden = [
        'NCA_DRAW__',
        'ObjectsDeleteAll',
        'ObjectDeleteAll',
    ]
    for token in forbidden:
        assert token not in text, token

    # Reference viewer may clean research-only overlays but must not have a
    # generic "delete everything" path.
    assert 'IsNVT9AuditOwnedObject' in text
    assert 'if(IsNVT9AuditOwnedObject(n)) ObjectDelete(chartId,n);' in text

    print("NVT9_REFERENCE0919_VIEWER_SAFETY_PASS")


if __name__ == "__main__":
    main()
