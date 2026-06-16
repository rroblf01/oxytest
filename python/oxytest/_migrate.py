import os
import sys


def _migrate_text(text: str, reverse: bool = False) -> str:
    """Migrate imports in a Python source string.

    Forward (pytest → oxytest):
      import pytest          → import oxytest as pytest
      import pytest as X     → import oxytest as X
      from pytest import ... → from oxytest import ...

    Reverse (oxytest → pytest):
      import oxytest as pytest → import pytest
      import oxytest as X      → import pytest as X
      import oxytest           → import pytest
      from oxytest import ...  → from pytest import ...
    """
    lines = text.splitlines(keepends=True)
    result = []

    for line in lines:
        line_end = ''
        if line.endswith('\r\n'):
            line_end = '\r\n'
        elif line.endswith('\n'):
            line_end = '\n'

        stripped = line.rstrip('\r\n')
        stripped_body = stripped.lstrip()
        indent = stripped[:len(stripped) - len(stripped_body)]

        if stripped_body.startswith('#'):
            result.append(line)
            continue

        if reverse:
            new_body = _reverse_line(stripped_body)
        else:
            new_body = _forward_line(stripped_body)

        result.append(indent + new_body + line_end)

    return ''.join(result)


def _forward_line(stripped_body: str) -> str:
    """Apply forward migration to a single line (no indent, no line ending)."""
    if stripped_body.startswith('from pytest '):
        return 'from oxytest ' + stripped_body[len('from pytest '):]

    if stripped_body.startswith('from pytest.'):
        return 'from oxytest.' + stripped_body[len('from pytest.'):]

    if stripped_body.startswith('import '):
        return _forward_import(stripped_body)

    return stripped_body


def _forward_import(stmt: str) -> str:
    """Process an ``import`` statement for forward migration."""
    stmt = stmt.rstrip()
    # import pytest as X → import oxytest as X
    if stmt.startswith('import pytest as '):
        return 'import oxytest as ' + stmt[len('import pytest as '):]

    # Replace bare `pytest` tokens in the import module list
    modules = stmt[len('import '):]
    parts = _split_import_modules(modules)
    changed = False
    for i, (name, alias) in enumerate(parts):
        if name == 'pytest':
            if alias:
                parts[i] = ('oxytest', alias)
            else:
                parts[i] = ('oxytest', 'pytest')
            changed = True

    if not changed:
        return stmt

    new_modules = ', '.join(
        f'{name} as {alias}' if alias else name
        for name, alias in parts
    )
    return f'import {new_modules}'


def _reverse_line(stripped_body: str) -> str:
    """Apply reverse migration to a single line (no indent, no line ending)."""
    if stripped_body.startswith('from oxytest '):
        return 'from pytest ' + stripped_body[len('from oxytest '):]

    if stripped_body.startswith('from oxytest.'):
        return 'from pytest.' + stripped_body[len('from oxytest.'):]

    if stripped_body.startswith('import '):
        return _reverse_import(stripped_body)

    return stripped_body


def _reverse_import(stmt: str) -> str:
    """Process an ``import`` statement for reverse migration."""
    stmt = stmt.rstrip()
    modules = stmt[len('import '):]

    # import oxytest as pytest → import pytest
    if modules == 'oxytest as pytest':
        return 'import pytest'

    # import oxytest as X → import pytest as X
    if modules.startswith('oxytest as '):
        return 'import pytest as ' + modules[len('oxytest as '):]

    parts = _split_import_modules(modules)
    changed = False
    for i, (name, alias) in enumerate(parts):
        if name == 'oxytest':
            parts[i] = ('pytest', alias if alias and alias != 'pytest' else None)
            changed = True

    if not changed:
        return stmt

    new_modules = ', '.join(
        f'{name} as {alias}' if alias else name
        for name, alias in parts
    )
    return f'import {new_modules}'


def _split_import_modules(modules: str) -> list[tuple[str, str | None]]:
    """Split ``import X, Y as Z, ...`` into [(name, alias), ...]."""
    parts: list[tuple[str, str | None]] = []
    for part in modules.split(','):
        part = part.strip()
        if not part:
            continue
        if ' as ' in part:
            name, alias = part.split(' as ', 1)
            parts.append((name.strip(), alias.strip()))
        else:
            parts.append((part.strip(), None))
    return parts


def _migrate_file(filepath: str, reverse: bool = False, dry_run: bool = False) -> bool:
    """Migrate a single file. Returns True if the file was changed."""
    with open(filepath, encoding='utf-8') as f:
        original = f.read()

    migrated = _migrate_text(original, reverse=reverse)
    if migrated == original:
        return False

    if dry_run:
        print(f"  Would modify: {filepath}")
    else:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(migrated)
        print(f"  Modified: {filepath}")
    return True


def migrate(
    root: str = '.',
    *,
    reverse: bool = False,
    dry_run: bool = False,
    check: bool = False,
) -> int:
    """Recursively migrate all Python files under *root*.

    Returns exit code (0 = no changes, 1 = changes made or needed).
    """
    if dry_run:
        print("Dry-run mode – no files will be modified")
        print()

    changed = 0
    total = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith('.py'):
                total += 1
                filepath = os.path.join(dirpath, fn)
                if _migrate_file(filepath, reverse=reverse, dry_run=dry_run or check):
                    changed += 1

    direction = "reverse" if reverse else "forward"
    print()
    if changed:
        print(f"Migration ({direction}): {changed}/{total} files modified")
    else:
        print(f"Migration ({direction}): all {total} files already up to date")

    if changed:
        return 1
    return 0


def migrate_main(argv: list[str]) -> int:
    """Entry point for ``oxytest migrate [options] [path]``."""
    import argparse
    parser = argparse.ArgumentParser(
        prog='oxytest migrate',
        description='Automatically migrate imports between pytest and oxytest.',
    )
    parser.add_argument(
        'path', nargs='?', default='.',
        help='Root directory to scan (default: current directory)',
    )
    parser.add_argument(
        '--reverse', action='store_true',
        help='Reverse migration (oxytest → pytest)',
    )
    parser.add_argument(
        '-n', '--dry-run', action='store_true',
        help='Show what would be changed without modifying files',
    )
    parser.add_argument(
        '--check', action='store_true',
        help='Exit with code 1 if any file would be changed (for CI)',
    )
    parsed = parser.parse_args(argv)

    if parsed.dry_run and parsed.check:
        print("error: --dry-run and --check are mutually exclusive", file=sys.stderr)
        return 2

    return migrate(
        parsed.path,
        reverse=parsed.reverse,
        dry_run=parsed.dry_run,
        check=parsed.check,
    )
