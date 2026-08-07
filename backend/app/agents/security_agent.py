"""
Security vulnerability scanner.
Detects 4 vulnerability types using regex pattern matching,
then uses the LLM to generate a plain-English explanation + fix suggestion.

Vulnerability types:
  - sql_injection      → f-strings/string concat in SQL queries
  - hardcoded_secret   → passwords/API keys assigned as string literals
  - command_injection  → os.system() or subprocess with string concatenation
  - path_traversal     → open() with user-controlled filename input
"""

import os
import re

from ..llm import chat
from ..parser.repo_parser import _EXT_TO_LANG, SKIP_DIRS

# ---------------------------------------------------------------------------
# Patterns — each is a list of regex strings
# ---------------------------------------------------------------------------
PATTERNS: dict[str, list[str]] = {
    "sql_injection": [
        r'f["\'].*SELECT.*WHERE.*\{',          # f-string SQL
        r'["\'].*SELECT.*["\'].*\+',           # string concat SQL
        r'execute\s*\(\s*["\']SELECT',         # raw execute("SELECT...")
        r'\.execute\s*\(.*%.*%',               # %-format in execute
    ],
    "hardcoded_secret": [
        r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']{6,}["\']',
        r'(?i)(secret|api_key|apikey|token|access_key)\s*=\s*["\'][^"\']{8,}["\']',
        r'(?i)(aws_secret|private_key|client_secret)\s*=\s*["\']',
    ],
    "command_injection": [
        r'os\.system\s*\(.*\+',               # os.system("cmd" + var)
        r'subprocess\.(run|call|Popen)\s*\(.*\+',  # subprocess with concat
        r'os\.popen\s*\(.*\+',
        r'eval\s*\(.*input\s*\(',              # eval(input(...))
        r'child_process\.(exec|execSync)\s*\(.*\+',  # Node.js exec("cmd" + var)
        r'Runtime\.getRuntime\(\)\.exec\s*\(.*\+',   # Java Runtime.exec
        r'\bexec\s*\(.*\$_(GET|POST|REQUEST)',        # PHP exec($_GET[...])
    ],
    "path_traversal": [
        r'open\s*\(.*\+.*filename',            # open("path/" + filename)
        r'open\s*\(.*request\.',               # open(request.args["file"])
        r'open\s*\(.*\bparams\b',
        r'\.\./\.\.',                          # literal "../.." in string
    ],
}

SEVERITY: dict[str, str] = {
    "sql_injection": "HIGH",
    "hardcoded_secret": "HIGH",
    "command_injection": "CRITICAL",
    "path_traversal": "MEDIUM",
}

EXPLAIN_SYSTEM = (
    "You are a security engineer. Given a vulnerable code snippet, "
    "explain in exactly 2 sentences: (1) why it is dangerous, "
    "(2) how to fix it. Be concrete and direct."
)


# ---------------------------------------------------------------------------
# Core scanning
# ---------------------------------------------------------------------------

def scan_file(filepath: str) -> list[dict]:
    """
    Scan a single file for vulnerabilities.
    Returns a list of finding dicts.
    """
    findings: list[dict] = []

    try:
        with open(filepath, "r", errors="ignore") as f:
            lines = f.readlines()
    except (OSError, PermissionError):
        return []

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue  # skip blank lines and comments

        for vuln_type, patterns in PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, line):
                    findings.append({
                        "type": vuln_type,
                        "severity": SEVERITY[vuln_type],
                        "file": filepath,
                        "line": line_num,
                        "code": stripped,
                        "explanation": None,  # filled in later by explain_findings()
                    })
                    break  # one finding per line per vuln type


    return findings


def scan_repo(repo_path: str) -> list[dict]:
    """
    Walk every source file in a repo (any language CodeScope parses —
    not just Python) and collect security findings.
    Returns findings sorted by severity (CRITICAL first).
    """
    all_findings: list[dict] = []

    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]

        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext in _EXT_TO_LANG:
                filepath = os.path.join(root, filename)
                all_findings.extend(scan_file(filepath))

    all_findings.sort(key=lambda f: severity_order.get(f["severity"], 99))
    return all_findings


def explain_findings(findings: list[dict], max_explanations: int = 5) -> list[dict]:
    """
    Add LLM-generated explanations to the top N findings.
    Mutates and returns the findings list.
    """
    for finding in findings[:max_explanations]:
        try:
            user_msg = (
                f"Vulnerability type: {finding['type']}\n"
                f"File: {finding['file']}\n"
                f"Line {finding['line']}: {finding['code']}"
            )
            finding["explanation"] = chat(EXPLAIN_SYSTEM, user_msg)
        except Exception as e:
            finding["explanation"] = f"(explanation unavailable: {e})"

    return findings
