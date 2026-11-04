"""Run local, synthetic-only Runtime checks; no HF credentials or network."""
import subprocess
import sys

commands = [
    [sys.executable, "-m", "storyforge_dataset.hf_runtime", "doctor", "--profile", "cpu", "--json"],
    [sys.executable, "-m", "pytest", "-q", "tests/test_hf_runtime.py", "tests/test_hf_runtime_volume_edges.py"],
    [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_token_preflight_core.py", "-q"],
]
for command in commands:
    subprocess.run(command, check=True)
