import os
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
E2E_SCRIPT = REPO_ROOT / "scripts" / "e2e_smoke.sh"


def _run_e2e(mode: str) -> None:
    subprocess.run(
        [str(E2E_SCRIPT), mode],
        cwd=REPO_ROOT,
        check=True,
    )


@pytest.mark.smoke_ollama
def test_smoke_ollama() -> None:
    if os.getenv("RUN_OLLAMA_SMOKE") != "1":
        pytest.skip("Set RUN_OLLAMA_SMOKE=1 to run Ollama smoke test")
    _run_e2e("ollama")


@pytest.mark.smoke_bedrock
def test_smoke_bedrock() -> None:
    if os.getenv("RUN_BEDROCK_SMOKE") != "1":
        pytest.skip("Set RUN_BEDROCK_SMOKE=1 to run Bedrock smoke test")
    _run_e2e("bedrock")
