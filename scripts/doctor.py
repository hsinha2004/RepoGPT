#!/usr/bin/env python3
"""
RepoGPT Doctor - Diagnostic tool to check environment, dependencies, ports, and services.
"""
import os
import shutil
import socket
import sys
from pathlib import Path

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def check_status(name: str, passed: bool, details: str = ""):
    status_str = f"{GREEN}OK{RESET}" if passed else f"{RED}FAIL{RESET}"
    if not passed and "optional" in details.lower():
        status_str = f"{YELLOW}WARN{RESET}"
    detail_str = f" - {details}" if details else ""
    print(f"[{status_str:^10}] {name:<30}{detail_str}")
    return passed


def check_port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        res = s.connect_ex(("127.0.0.1", port))
        return res != 0  # 0 means port is occupied / in use


def main():
    print("=" * 60)
    print("           RepoGPT System Diagnostics (Doctor)            ")
    print("=" * 60)

    root = Path(__file__).resolve().parent.parent

    # 1. Environment & Files
    env_file = root / ".env"
    check_status(".env file exists", env_file.exists(), str(env_file))

    # 2. Tooling
    check_status("Python 3.12+", sys.version_info >= (3, 12), f"{sys.version_split()[0] if hasattr(sys, 'version_split') else sys.version.split()[0]}")
    docker_bin = shutil.which("docker")
    check_status("Docker CLI available", docker_bin is not None, docker_bin or "Not found in PATH (optional for local dev)")
    
    node_bin = shutil.which("node")
    check_status("Node.js available", node_bin is not None, node_bin or "Not found in PATH")

    # 3. Ports check for dev mode
    ports = {
        5173: "Frontend Vite dev",
        8000: "Backend FastAPI",
        27017: "MongoDB",
        6379: "Redis",
        8001: "ChromaDB (or 8000 in container)"
    }
    print("-" * 60)
    print("Port Availability:")
    for port, service in ports.items():
        is_free = check_port_free(port)
        check_status(f"Port {port} ({service})", is_free, "Free" if is_free else "Occupied")

    # 4. Disk space
    total, used, free = shutil.disk_usage(root)
    free_gb = free / (1024 ** 3)
    check_status("Disk Space (> 5 GB free)", free_gb >= 5.0, f"{free_gb:.1f} GB free")

    print("=" * 60)


if __name__ == "__main__":
    main()
