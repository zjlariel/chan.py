import subprocess
import sys
from pathlib import Path


def test_editable_install_exposes_primary_modules(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "from Chan import CChan; from ChanConfig import CChanConfig; print(CChan.__name__, CChanConfig.__name__)",
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "CChan CChanConfig"
