#!/usr/bin/env python3
"""
Clinivara Unified Execution Runner.

Single-command entrypoint to launch the complete Clinivara platform:
- Usage:
    python run.py          # Starts the live REST API server & Swagger docs
    python run.py --test   # Executes all 69 automated security and unit tests
    python run.py --eval   # Runs the clinical privacy & AI benchmark
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Automatically switch to project's .venv environment if running via external/system Python
_root = Path(__file__).resolve().parent
_venv_python = _root / ".venv" / "Scripts" / "python.exe"
if not _venv_python.exists():
    _venv_python = _root / ".venv" / "bin" / "python"

if _venv_python.exists() and Path(sys.executable).resolve() != _venv_python.resolve():
    sys.exit(subprocess.call([str(_venv_python)] + sys.argv))


def start_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = True):
    """Launch the live FastAPI server via Uvicorn."""
    import uvicorn

    print("=" * 70)
    print("🏥 CLINIVARA: PRIVACY-FIRST CLINICAL DOCUMENT INTELLIGENCE")
    print("=" * 70)
    print(f"🚀 Server running at: http://{host}:{port}")
    print(f"📖 Swagger API Docs:  http://{host}:{port}/docs")
    print(f"🩺 Health Check:     http://{host}:{port}/api/v1/health")
    print(f"🤖 AI Capabilities:  http://{host}:{port}/api/v1/ai/capabilities")
    print(f"🌐 Supported Langs:   http://{host}:{port}/api/v1/ai/languages")
    print("=" * 70)
    print("Press CTRL+C to stop the server.\n")

    uvicorn.run(
        "clinivara.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


def run_tests():
    """Execute complete pytest test suite."""
    print("Running complete Clinivara test suite...")
    res = subprocess.run([sys.executable, "-m", "pytest", "-v"])
    sys.exit(res.returncode)


def run_evaluation():
    """Run privacy and clinical extraction evaluation benchmark."""
    eval_script = Path("evaluation") / "evaluate_privacy.py"
    print(f"Running evaluation benchmark: {eval_script}...")
    res = subprocess.run([sys.executable, str(eval_script)])
    sys.exit(res.returncode)


def main():
    parser = argparse.ArgumentParser(description="Clinivara Single-Command Platform Runner")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run all automated unit, integration, and security tests",
    )
    parser.add_argument(
        "--eval",
        action="store_true",
        help="Run privacy and clinical de-identification benchmark",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host address to bind the server (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind the server (default: 8000)",
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Disable auto-reload for production execution",
    )

    args = parser.parse_args()

    if args.test:
        run_tests()
    elif args.eval:
        run_evaluation()
    else:
        start_server(host=args.host, port=args.port, reload=not args.no_reload)


if __name__ == "__main__":
    main()
