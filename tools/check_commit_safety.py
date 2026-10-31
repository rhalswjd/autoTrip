"""Read-only, redacted Git-candidate checks. Not a replacement for dependency audits.

Run from any directory: python tools/check_commit_safety.py [--history].
No network calls, file mutations, credential values or source lines are printed.
"""
import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(rb'(?<![A-Za-z0-9_])(?:secret_|ntn_|gh[pousr]_|github_pat_|sk-(?:proj-)?)[A-Za-z0-9_-]{20,}')
RULES = {
    'access-key': re.compile(rb'AKIA[0-9A-Z]{16}'),
    'private-key': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'credential-url': re.compile(rb'https?://[^\s/:@]+:[^\s/@]+@'),
    'private-notion-url': re.compile(rb'(?:notion\.so|app\.notion\.com)/[^\s"\']*?([0-9a-f]{32})'),
}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str


def git(*args: str) -> bytes:
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def synthetic(value: bytes) -> bool:
    return len(set(value)) == 1 or value == b'0123456789abcdef0123456789abcdef'


def inspect_text(path: str, data: bytes, local_values: tuple[bytes, ...] = ()) -> list[Finding]:
    findings = []
    for match in TOKEN.finditer(data):
        # Explicit documentation examples only; exact local-value checks below
        # are never suppressed by this placeholder classification.
        if any(word in match.group().lower() for word in (b'your_', b'example_', b'placeholder_')):
            continue
        findings.append(Finding(path, data[:match.start()].count(b'\n') + 1, 'credential-token'))
    for rule, pattern in RULES.items():
        for match in pattern.finditer(data):
            if rule == 'private-notion-url' and synthetic(match[1]):
                continue
            findings.append(Finding(path, data[:match.start()].count(b'\n') + 1, rule))
    for value in local_values:
        index = data.find(value)
        if index >= 0:
            findings.append(Finding(path, data[:index].count(b'\n') + 1, 'local-sensitive-value'))
    return findings


def prohibited_path(path: str) -> bool:
    item = Path(path)
    if any(part.startswith(('.venv', '.local')) or part in ('node_modules', '__pycache__', 'secrets', 'private') for part in item.parts):
        return True
    if item.name.startswith('.env') and item.name != '.env.example':
        return True
    return bool(re.search(r'\.(?:db|sqlite|sqlite3)(?:-.*)?$|\.(?:pem|key|p12|pfx|log)$', path))


def local_secrets() -> tuple[bytes, ...]:
    values = []
    for path in (ROOT / '.env', ROOT / 'backend/.env', ROOT / 'frontend/.env'):
        if not path.is_file():
            continue
        for line in path.read_text(encoding='utf-8').splitlines():
            match = re.match(r'([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(.*?)\s*$', line)
            if not match:
                continue
            name, value = match.groups()
            value = value.strip('\"\'')
            if (any(word in name.upper() for word in ('TOKEN', 'API_KEY', 'PASSWORD', 'SECRET', 'DATABASE_ID'))
                    and len(value) >= 12 and not re.search(r'your_|example|placeholder|test_', value, re.I)):
                values.append(value.encode())
    return tuple(values)


def inspect_candidates(values: tuple[bytes, ...]) -> tuple[int, list[Finding]]:
    paths = set(git('ls-files', '-z', '--cached', '--others', '--exclude-standard').split(b'\0')) - {b''}
    findings = []
    count = 0
    for raw in sorted(paths):
        relative = raw.decode('utf-8')
        path = ROOT / relative
        if not path.exists() and not path.is_symlink():
            continue  # Working-tree removals must not be resurrected from the index.
        count += 1
        if prohibited_path(relative):
            findings.append(Finding(relative, 0, 'private-or-generated-file'))
        if path.is_symlink():
            if not path.resolve().is_relative_to(ROOT):
                findings.append(Finding(relative, 0, 'symlink-outside-repository'))
            continue
        data = path.read_bytes()
        if b'\0' not in data[:8000]:
            findings.extend(inspect_text(relative, data, values))
    return count, findings


def inspect_history(values: tuple[bytes, ...]) -> tuple[int, list[Finding]]:
    findings = []
    count = 0
    for entry in git('rev-list', '--objects', '--all').decode().splitlines():
        parts = entry.split(' ', 1)
        if len(parts) != 2 or git('cat-file', '-t', parts[0]).strip() != b'blob':
            continue
        count += 1
        findings.extend(inspect_text(parts[1], git('cat-file', 'blob', parts[0]), values))
    return count, findings


def inspect_staged(values: tuple[bytes, ...]) -> tuple[int, list[Finding]]:
    """A staged secret must not be hidden by a later clean working-tree edit."""
    paths = git('diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z').split(b'\0')
    findings = []
    count = 0
    for raw in paths:
        if not raw:
            continue
        relative = raw.decode('utf-8')
        count += 1
        label = relative + ' (staged)'
        if prohibited_path(relative):
            findings.append(Finding(label, 0, 'private-or-generated-file'))
        findings.extend(inspect_text(label, git('show', ':' + relative), values))
    return count, findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', action='store_true', help='Also inspect reachable historical blobs without rewriting them')
    args = parser.parse_args()
    values = local_secrets()
    count, findings = inspect_candidates(values)
    print(f'Git candidates: {count}; findings: {len(findings)}')
    staged_count, staged_findings = inspect_staged(values)
    print(f'Staged changed files: {staged_count}; findings: {len(staged_findings)}')
    findings.extend(staged_findings)
    for item in sorted(set(findings), key=lambda item: (item.path, item.line, item.rule)):
        print(f'BLOCK {item.path}:{item.line} [{item.rule}]')
    historical = []
    if args.history:
        blobs, historical = inspect_history(values)
        print(f'Historical blobs: {blobs}; findings: {len(historical)}')
        for item in sorted(set(historical), key=lambda item: (item.path, item.line, item.rule)):
            print(f'HISTORY {item.path}:{item.line} [{item.rule}]')
    history_credentials = any(item.rule != 'private-notion-url' for item in historical)
    if historical:
        print('Historical findings require separate review; removing a current file does not erase history.')
    print('Dependency advisories and unreachable Git objects are outside this check.')
    return 1 if findings or history_credentials else 0


if __name__ == '__main__':
    raise SystemExit(main())
