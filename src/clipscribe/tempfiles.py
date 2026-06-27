"""Safe temporary-file lifecycle management (FR-10, privacy).

Groundwork for the M3 Streamlit upload flow, where uploaded media must live in a
randomized temporary location and be removed on success *or* failure. The M1/M2
CLI reads local files directly and does not use this yet.
"""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def temporary_workspace(prefix: str = "clipscribe-") -> Iterator[Path]:
    """Yield a randomized temp directory, always removed on exit.

    The directory (and anything written inside it) is deleted whether the body
    completes normally or raises, so uploaded media never lingers.
    """
    workspace = Path(tempfile.mkdtemp(prefix=prefix))
    try:
        yield workspace
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
