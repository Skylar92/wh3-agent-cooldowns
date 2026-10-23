from tools.preview import make_preview, save_preview


def test_preview_size_and_weight(tmp_path):
    out = tmp_path / "agent_cooldowns.png"
    save_preview(make_preview(), out)
    assert make_preview().size == (512, 512)
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert out.stat().st_size < 1_000_000


def test_preview_is_deterministic():
    assert make_preview().tobytes() == make_preview().tobytes()
