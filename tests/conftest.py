"""Fixture bersama untuk tes yang memerlukan direktori sementara."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_path():
    """Gunakan folder sementara dalam proyek, bukan Windows Temp."""
    project_root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory(prefix="pytest-", dir=project_root) as temp_dir:
        yield Path(temp_dir)
