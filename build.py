"""Build the static React app before the FastAPI deployment is packaged."""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"
NPM = "npm.cmd" if os.name == "nt" else "npm"


def main() -> None:
    subprocess.run(
        [NPM, "ci", "--cache", str(ROOT / ".npm-cache"), "--no-audit", "--no-fund"],
        cwd=FRONTEND,
        check=True,
    )
    subprocess.run([NPM, "run", "build"], cwd=FRONTEND, check=True)


if __name__ == "__main__":
    main()
