"""CDK app. Region locked to us-east-2 (ADR 011). Secrets from repo-root .env only."""

from __future__ import annotations

import os
from pathlib import Path

from aws_cdk import App, Environment
from dotenv import load_dotenv

from turboimmi_dev_stack import TurboImmiDevStack

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = App()
TurboImmiDevStack(
    app,
    "TurboImmiDev",
    env=Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
        region=os.environ.get("CDK_DEFAULT_REGION", "us-east-2"),
    ),
)
app.synth()
