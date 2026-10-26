import os
from pathlib import Path
import struct
import subprocess
import sys
import sysconfig

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="Windows entry-point launchers")
def test_noarch_entrypoint_is_native(tmp_path):
    prefix = tmp_path / "entry-point"
    standalone = os.environ.get(
        "CONDA_STANDALONE", Path(sys.prefix) / "standalone_conda" / "conda.exe"
    )
    subprocess.run(
        [
            standalone,
            "create",
            "--yes",
            "--prefix",
            prefix,
            "--override-channels",
            "--channel",
            "conda-forge",
            f"python={sys.version_info.major}.{sys.version_info.minor}",
            "pygments",
        ],
        check=True,
    )
    launcher = prefix / "Scripts" / "pygmentize.exe"
    data = launcher.read_bytes()
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    assert data[pe_offset : pe_offset + 4] == b"PE\0\0"
    machine = struct.unpack_from("<H", data, pe_offset + 4)[0]
    expected = {"win-arm64": 0xAA64, "win-amd64": 0x8664}[sysconfig.get_platform()]
    assert machine == expected, (hex(machine), hex(expected))
    result = subprocess.run([launcher, "-V"], check=True, capture_output=True, text=True)
    assert result.stdout.startswith("Pygments version"), result.stdout
