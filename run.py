import argparse
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent


def run(command: list[str]) -> None:
    subprocess.check_call(command, cwd=ROOT_DIR)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CentrAlign Autonomous AP Worker launcher"
    )

    parser.add_argument(
        "command",
        choices=["seed", "ap", "streamlit", "test"]
    )

    args = parser.parse_args()

    if args.command == "seed":
        run([
            sys.executable,
            "-m",
            "scripts.generate_data"
        ])

    elif args.command == "ap":
        run([
            sys.executable,
            "-m",
            "uvicorn",
            "simulated_ap.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--reload",
        ])

    elif args.command == "streamlit":
        run([
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(ROOT_DIR / "streamlit_app" / "dashboard.py"),
        ])

    elif args.command == "test":
        run([
            sys.executable,
            "-m",
            "pytest",
            "-q"
        ])


if __name__ == "__main__":
    main()