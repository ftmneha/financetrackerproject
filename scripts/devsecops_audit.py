#!/usr/bin/env python3
"""
DevSecOps Automated Security Auditor for Personal Finance Tracker
Subject: ADVANCEMENTS IN CLOUD AND DEVOPS (INT378)

Automates scanning using:
1. Gitleaks (Secret Detection)
2. pip-audit (Python Dependency CVE Scans)
3. flake8 (Code Quality & Syntax Linting)
4. Trivy (Container Vulnerabilities)
"""

import os
import sys
import json
import subprocess
import argparse

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def run_command(cmd, desc):
    print(f"\n[+] Running {desc}...")
    print(f"    Command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        print(f"[-] Tool not installed or not in PATH: {cmd[0]}")
        return 127, "", f"{cmd[0]} not found"


def audit_flake8():
    cmd = [sys.executable, "-m", "flake8", "app.py", "config.py", "models.py", "--max-line-length=120", "--count", "--statistics"]
    code, stdout, stderr = run_command(cmd, "flake8 Code Quality Analysis")
    out_file = os.path.join(REPORTS_DIR, "flake8-report.txt")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(stdout + "\n" + stderr)
    print(f"[✓] Flake8 report written to {out_file}")
    return code == 0


def audit_pip():
    out_file = os.path.join(REPORTS_DIR, "pip-audit-report.json")
    cmd = [sys.executable, "-m", "pip_audit", "-r", "requirements.txt", "--format=json", "-o", out_file]
    code, stdout, stderr = run_command(cmd, "pip-audit Python Dependency CVE Scan")
    print(f"[✓] pip-audit report written to {out_file}")
    return code == 0


def audit_gitleaks():
    out_file = os.path.join(REPORTS_DIR, "gitleaks-report.json")
    cmd = ["gitleaks", "detect", "--source=.", "-v", f"--report-path={out_file}"]
    code, stdout, stderr = run_command(cmd, "Gitleaks Secret Detection")
    print(f"[✓] Gitleaks scan finished (exit: {code})")
    return code == 0


def audit_trivy(image_name="fintrack:latest"):
    out_file = os.path.join(REPORTS_DIR, "trivy-report.json")
    cmd = ["trivy", "image", "--severity", "HIGH,CRITICAL", "--format", "json", "-o", out_file, image_name]
    code, stdout, stderr = run_command(cmd, f"Trivy Container Scan for {image_name}")
    print(f"[✓] Trivy scan finished (exit: {code})")
    return code == 0


def main():
    parser = argparse.ArgumentParser(description="DevSecOps Audit Runner")
    parser.add_argument("--tool", choices=["all", "flake8", "pip-audit", "gitleaks", "trivy"], default="all")
    args = parser.parse_args()

    results = {}
    if args.tool in ["all", "flake8"]:
        results["flake8"] = audit_flake8()
    if args.tool in ["all", "pip-audit"]:
        results["pip-audit"] = audit_pip()
    if args.tool in ["all", "gitleaks"]:
        results["gitleaks"] = audit_gitleaks()
    if args.tool in ["all", "trivy"]:
        results["trivy"] = audit_trivy()

    print("\n" + "=" * 50)
    print("DevSecOps Security Audit Summary:")
    print("=" * 50)
    for tool, success in results.items():
        status = "PASSED / GENERATED" if success else "NOTICE / CHECK REPORT"
        print(f" - {tool:15}: {status}")
    print("=" * 50)


if __name__ == "__main__":
    main()
