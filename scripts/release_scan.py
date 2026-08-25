"""Offline release hygiene scanner.

Checks repository text files for credential-shaped values, forbidden environment
files, machine-specific absolute paths, and Docker COPY sources that do not
exist in the build context. It never prints matched secret values.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "artifacts",
    "logs",
}

BINARY_SUFFIXES = {
    ".7z",
    ".bin",
    ".dll",
    ".docx",
    ".exe",
    ".gif",
    ".gz",
    ".ico",
    ".jpeg",
    ".jpg",
    ".npy",
    ".pdf",
    ".png",
    ".pptx",
    ".pyc",
    ".rar",
    ".so",
    ".tar",
    ".xlsx",
    ".zip",
}

SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "openai_style_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "bearer_token": re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}\b", re.IGNORECASE),
    "assigned_api_key": re.compile(
        r"(?im)^\s*(?:OPENAI|OPENROUTER|DEEPSEEK|ANTHROPIC|GEMINI)_API_KEY\s*[:=]\s*['\"]?([^\s'\"#]{12,})"
    ),
}

ABSOLUTE_PATH_PATTERNS = {
    "unix_home_path": re.compile(r"(?<![A-Za-z0-9_])/(?:home|Users)/[^/\s]+/"),
    "windows_user_path": re.compile(r"(?i)\b[A-Z]:\\Users\\[^\\\s]+\\"),
}


@dataclass(frozen=True)
class Finding:
    code: str
    path: str
    line: int | None = None
    detail: str | None = None


def _iter_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        yield path


def _is_forbidden_env_file(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    name = path.name.lower()
    if name in {".env.example", ".env.sample", ".env.template"}:
        return False
    if name == ".env" or name.startswith(".env.") or ".env.backup" in name:
        return True
    return any(part.lower() == ".env" for part in rel.parts)


def _read_text(path: Path) -> str | None:
    if path.suffix.lower() in BINARY_SUFFIXES:
        return None
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data[:4096]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _scan_text(path: Path, root: Path, text: str) -> list[Finding]:
    findings: list[Finding] = []
    rel = path.relative_to(root).as_posix()
    for line_number, line in enumerate(text.splitlines(), start=1):
        if "release-scan: allow" in line:
            continue
        if "${" in line:
            # Compose/shell variable expansion names a key but does not contain it.
            continue
        for code, pattern in SECRET_PATTERNS.items():
            if pattern.search(line):
                findings.append(Finding(code=code, path=rel, line=line_number))
        for code, pattern in ABSOLUTE_PATH_PATTERNS.items():
            if pattern.search(line):
                findings.append(Finding(code=code, path=rel, line=line_number))
    return findings


def _docker_copy_sources(dockerfile: Path) -> Iterable[tuple[int, str]]:
    for line_number, raw in enumerate(dockerfile.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw.strip()
        if not stripped.upper().startswith("COPY "):
            continue
        tokens = shlex.split(stripped)
        if len(tokens) < 3 or any(token.startswith("--from=") for token in tokens[1:]):
            continue
        sources = [token for token in tokens[1:-1] if not token.startswith("--")]
        for source in sources:
            yield line_number, source


def _scan_docker(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for dockerfile in sorted(root.rglob("Dockerfile*")):
        if not dockerfile.is_file():
            continue
        for line_number, source in _docker_copy_sources(dockerfile):
            if any(char in source for char in "*?["):
                continue
            if not (root / source).exists():
                findings.append(
                    Finding(
                        code="docker_copy_source_missing",
                        path=dockerfile.relative_to(root).as_posix(),
                        line=line_number,
                        detail=source,
                    )
                )
    return findings


def scan(root: Path) -> list[Finding]:
    root = root.resolve()
    findings: list[Finding] = []
    for path in _iter_files(root):
        if _is_forbidden_env_file(path, root):
            findings.append(
                Finding(code="forbidden_env_file", path=path.relative_to(root).as_posix())
            )
            continue
        text = _read_text(path)
        if text is not None:
            findings.extend(_scan_text(path, root, text))
    findings.extend(_scan_docker(root))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan a release tree without network access.")
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    root = Path(args.root)
    findings = scan(root)
    if args.as_json:
        print(json.dumps([asdict(item) for item in findings], ensure_ascii=False, indent=2))
    else:
        if findings:
            for item in findings:
                location = item.path if item.line is None else f"{item.path}:{item.line}"
                suffix = f" ({item.detail})" if item.detail else ""
                print(f"FAIL {item.code} {location}{suffix}")
        else:
            print("PASS release scan: no findings")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
