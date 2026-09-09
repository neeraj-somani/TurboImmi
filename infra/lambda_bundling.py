"""Install Lambda deps for Amazon Linux without Docker (Windows-safe)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import jsii
from aws_cdk import ILocalBundling

REPO = Path(__file__).resolve().parent.parent


@jsii.implements(ILocalBundling)
class LambdaLocalBundling:
    def try_bundle(self, output_dir: str, options: object) -> bool:
        del options
        out = Path(output_dir)
        req = REPO / "backend" / "requirements-lambda.txt"
        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-r",
            str(req),
            "-t",
            str(out),
            "--platform",
            "manylinux2014_x86_64",
            "--implementation",
            "cp",
            "--python-version",
            "312",
            "--only-binary",
            ":all:",
            "--upgrade",
            "--quiet",
        ]
        subprocess.check_call(cmd)
        shutil.copytree(REPO / "backend" / "app", out / "app", dirs_exist_ok=True)
        shared = out / "shared"
        shared.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / "shared" / "disclaimer.json", shared / "disclaimer.json")
        return True
