"""Core rules must not acquire HTTP or infrastructure imports via refactoring."""
import ast
from pathlib import Path

import pytest


@pytest.mark.parametrize('layer', ['domain', 'application'])
def test_business_layers_do_not_import_framework_or_outer_adapters(layer):
    root = Path(__file__).resolve().parents[2]
    forbidden = {'api', 'infrastructure', 'fastapi', 'httpx', 'bs4', 'sqlite3', 'core.exceptions'}
    if layer == 'domain':
        forbidden.add('application')
    violations = []
    for path in (root / layer).rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            names = [node.module or ''] if isinstance(node, ast.ImportFrom) else (
                [alias.name for alias in node.names] if isinstance(node, ast.Import) else [])
            for name in names:
                if any(name == prefix or name.startswith(prefix + '.') for prefix in forbidden):
                    violations.append(f'{path.relative_to(root)}:{node.lineno}: {name}')
    assert violations == []
