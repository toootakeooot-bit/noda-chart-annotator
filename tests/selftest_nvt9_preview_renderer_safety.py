from __future__ import annotations

from pathlib import Path


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    src = (repo / "mt4" / "NCA_NVT9_Preview_Renderer.mq4").read_text(encoding="utf-8")

    assert 'string PREFIX = "NVT9_PREVIEW__";' in src
    assert '_live_snapshot_V6_0919.csv' in src
    assert "DeletePreviewOwnedObjects" in src
    assert 'StringFind(n, PREFIX, 0) == 0' in src
    assert "NCA_DRAW__" not in src
    assert "OrderSend" not in src
    assert "OrderClose" not in src
    assert "EventSetTimer" not in src
    assert "OnStart()" in src
    assert "CountRenderableRows" in src

    print("NVT9 PREVIEW RENDERER SAFETY SELFTEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
