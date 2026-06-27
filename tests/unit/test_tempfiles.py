"""Unit tests for the temporary-workspace lifecycle."""

import pytest

from clipscribe.tempfiles import temporary_workspace


def test_workspace_created_and_removed():
    with temporary_workspace() as ws:
        assert ws.exists() and ws.is_dir()
        (ws / "uploaded.bin").write_bytes(b"data")
        saved = ws
    assert not saved.exists()  # removed on normal exit


def test_workspace_removed_on_exception():
    saved = None
    with pytest.raises(RuntimeError):
        with temporary_workspace() as ws:
            saved = ws
            (ws / "uploaded.bin").write_bytes(b"data")
            raise RuntimeError("boom")
    assert saved is not None and not saved.exists()  # removed even on failure
