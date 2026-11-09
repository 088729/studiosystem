"""Zero-residue scan: fail the build if internal-network values or secrets
appear anywhere in the repository (Q10 CI gate).

Scans every text file tracked in the repo (respecting .gitignore) for:
- internal hostnames / IP ranges
- internal ports/paths
- obvious credential literals in example/config files

This mainly guards against copy-pasting internal values into docs and config
examples. Exit code 0 = clean, 1 = hits found.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Internal-network fingerprints. Keep this list aligned with the main repo's
# sanitize() rules; values must be generic (no real secrets in this file!).
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("internal-domain", re.compile(r"wys\.core\.com", re.IGNORECASE)),
    ("internal-lan-ip", re.compile(r"192\.168\.31\.\d+")),
    ("internal-service-port", re.compile(r"5080/studio")),
    ("kubeconfig-abs-path", re.compile(r"/home/\w+/\.kube/config")),
    ("private-key-block", re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("jwt-literal", re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}")),
]

# Files that legitimately mention the patterns above (this scanner itself,
# docs explaining the rules).
ALLOWLIST = {
    "scripts/zero_residue_scan.py",
}


def _iter_text_files():
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        if rel in ALLOWLIST or ".git" in rel or ".venv" in rel:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary or unreadable — skip
        yield rel, content


def main() -> int:
    hits: list[str] = []
    for rel, content in _iter_text_files():
        for name, pattern in PATTERNS:
            for m in pattern.finditer(content):
                line_no = content.count("\n", 0, m.start()) + 1
                hits.append(f"{rel}:{line_no}: {name}: {m.group(0)[:60]!r}")
    if hits:
        print("ZERO-RESIDUE SCAN FAILED — internal values detected:")
        for h in hits:
            print("  ", h)
        return 1
    print("zero-residue scan: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
