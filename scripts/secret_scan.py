#!/usr/bin/env python3
"""Look for secrets in the repository's history and in the built storefront.

    python scripts/secret_scan.py            history of every branch + frontend/dist
    python scripts/secret_scan.py --dist     the built storefront only

Reports where something that looks like a secret was added: commit, file and
the kind of secret. It never prints the value itself. It changes nothing: if a
real secret is in the history, rotate it first; rewriting history is a separate
decision.

Exit code 1 if anything was found that is not a known placeholder.
"""
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

PATTERNS = {
    "Razorpay live key id": re.compile(r"rzp_live_[A-Za-z0-9]{10,}"),
    "Razorpay test key id": re.compile(r"rzp_test_[A-Za-z0-9]{10,}"),
    "JWT (e.g. Supabase service key)": re.compile(r"eyJ[A-Za-z0-9_-]{15,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"),
    "Resend API key": re.compile(r"\bre_[A-Za-z0-9_]{24,}"),
    "Google API key": re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Private key block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "Database URL with a password": re.compile(r"postgres(?:ql)?://[^:\s/'\"]+:[^@\s'\"]{6,}@[^\s'\"]+"),
    "Secret assigned in a file": re.compile(
        r"(?i)\b(?:SECRET_KEY|JWT_SECRET_KEY|ADMIN_PASSWORD|RAZORPAY_KEY_SECRET|RAZORPAY_WEBHOOK_SECRET|"
        r"SHIPROCKET_PASSWORD|SUPABASE_SERVICE_KEY|RESEND_API_KEY)\s*[=:]\s*[\"']?([^\s\"'#]{8,})"),
}

# Values that are documentation or test fixtures, not secrets.
PLACEHOLDER = re.compile(
    r"(?i)(change[-_ ]?me|your[-_ ]|example|placeholder|<[^>]+>|xxx|\$\{|\$\(|os\.environ|getenv|"
    r"test[-_]?secret|contract|dummy|sample|generate|localhost|127\.0\.0\.1|postgres:test@|"
    r"user:pass|password@|:password|AdminPass123|secrets\.|token_urlsafe|process\.env|import\.meta|sync: false|"
    r"rzp_test_x\b|rzp_test_contract|rzp_test_abc|whsec_|fromDatabase|postgres:postgres@|aanga:aanga@|\*\*\*|\.\.\.)")

SKIP_FILES = re.compile(r"(package-lock\.json|\.lock$|node_modules/|\.min\.js$|schema\.sql$)")


def findings_in(text):
    for kind, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            if not PLACEHOLDER.search(match.group(0)):
                yield kind


def scan_history():
    log = subprocess.run(
        ["git", "log", "--all", "-p", "--no-color", "--unified=0", "--format=@@commit %h %ad %s", "--date=short"],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
    ).stdout
    found, commit, path = {}, "", ""
    for line in log.splitlines():
        if line.startswith("@@commit "):
            commit = line[9:]
        elif line.startswith("+++ b/"):
            path = line[6:]
        elif line.startswith("+") and not line.startswith("+++") and not SKIP_FILES.search(path):
            for kind in findings_in(line):
                found.setdefault((commit, path, kind), 0)
                found[(commit, path, kind)] += 1
    return found


def scan_dist():
    found = {}
    dist = ROOT / "frontend" / "dist"
    if not dist.exists():
        print("frontend/dist does not exist: build the storefront first (npm run build).")
        return found
    names = re.compile(r"(?i)(KEY_SECRET|WEBHOOK_SECRET|SERVICE_KEY|JWT_SECRET|ADMIN_PASSWORD|SHIPROCKET_PASSWORD|RESEND_API_KEY|DATABASE_URL)")
    for file in dist.rglob("*"):
        if file.suffix not in (".js", ".html", ".css", ".json", ".map", ".txt"):
            continue
        text = file.read_text(encoding="utf-8", errors="replace")
        rel = str(file.relative_to(ROOT)).replace("\\", "/")
        for kind in findings_in(text):
            found[("built storefront", rel, kind)] = found.get(("built storefront", rel, kind), 0) + 1
        for match in names.finditer(text):
            key = ("built storefront", rel, f"mentions the name of a server-side secret ({match.group(1)})")
            found[key] = found.get(key, 0) + 1
    return found


def main():
    found = scan_dist()
    if "--dist" not in sys.argv:
        found.update(scan_history())
    if not found:
        print("Nothing that looks like a secret was found.")
        return 0
    print(f"{len(found)} place(s) where something that looks like a secret was added (values not shown):\n")
    for (commit, path, kind), count in sorted(found.items()):
        print(f"  {kind}\n      {path}\n      {commit}" + (f"   ({count} lines)" if count > 1 else ""))
    print("\nIf any of these is a real secret: change it at the provider first. That makes the copy in the "
          "history worthless. Removing it from the history is optional and needs a decision (it rewrites every commit).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
