import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "configure-ip-tls.sh"


def test_rejects_non_ipv4_public_address_before_calling_kubectl(tmp_path: Path) -> None:
    kubectl_called = tmp_path / "kubectl-called"
    kubectl_stub = tmp_path / "kubectl"
    kubectl_stub.write_text(
        f"#!/bin/sh\ntouch {kubectl_called}\n",
        encoding="utf-8",
    )
    kubectl_stub.chmod(0o755)
    environment = {
        **os.environ,
        "KUBECTL": str(kubectl_stub),
        "PUBLIC_IP": "example.invalid",
    }

    result = subprocess.run(
        [str(SCRIPT)],
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )

    assert result.returncode != 0
    assert "valid IPv4 address" in result.stderr
    assert not kubectl_called.exists()
