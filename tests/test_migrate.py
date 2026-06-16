import os
import tempfile
import textwrap

from oxytest._migrate import (
    _migrate_text,
    _forward_line,
    _forward_import,
    _reverse_line,
    _reverse_import,
    _split_import_modules,
    _migrate_file,
    migrate,
    migrate_main,
)


def test_split_import_modules_single():
    assert _split_import_modules("pytest") == [("pytest", None)]


def test_split_import_modules_alias():
    assert _split_import_modules("pytest as pt") == [("pytest", "pt")]


def test_split_import_modules_multi():
    result = _split_import_modules("os, sys as sys2")
    assert result == [("os", None), ("sys", "sys2")]


def test_split_import_modules_empty_part():
    result = _split_import_modules("a, , b")
    assert result == [("a", None), ("b", None)]


# Forward tests


def test_forward_line_from_pytest():
    assert _forward_line("from pytest import main") == "from oxytest import main"


def test_forward_line_from_pytest_dot():
    assert _forward_line("from pytest._compat import main") == "from oxytest._compat import main"


def test_forward_line_import_pytest():
    assert _forward_line("import pytest") == "import oxytest as pytest"


def test_forward_line_import_pytest_as():
    assert _forward_line("import pytest as pt") == "import oxytest as pt"


def test_forward_line_import_multi():
    assert _forward_line("import os, pytest, sys") == "import os, oxytest as pytest, sys"


def test_forward_line_other():
    assert _forward_line("print('hello')") == "print('hello')"


def test_forward_line_comment():
    assert _forward_line("# import pytest") == "# import pytest"


def test_forward_import_pytest_as():
    assert _forward_import("import pytest as XYZ") == "import oxytest as XYZ"


# Reverse tests


def test_reverse_line_from_oxytest():
    assert _reverse_line("from oxytest import main") == "from pytest import main"


def test_reverse_line_from_oxytest_dot():
    assert _reverse_line("from oxytest._compat import main") == "from pytest._compat import main"


def test_reverse_line_import_oxytest_as_pytest():
    assert _reverse_line("import oxytest as pytest") == "import pytest"


def test_reverse_line_import_oxytest_as_other():
    assert _reverse_line("import oxytest as pt") == "import pytest as pt"


def test_reverse_line_import_oxytest_bare():
    assert _reverse_line("import oxytest") == "import pytest"


def test_reverse_line_import_multi():
    result = _reverse_line("import os, oxytest as pytest, sys")
    assert result == "import os, pytest, sys"


def test_reverse_line_other():
    assert _reverse_line("x = 1") == "x = 1"


def test_reverse_line_comment():
    assert _reverse_line("# import oxytest") == "# import oxytest"


def test_reverse_import_oxytest_as_pytest():
    assert _reverse_import("import oxytest as pytest") == "import pytest"


def test_reverse_import_oxytest_as_alias():
    assert _reverse_import("import oxytest as my") == "import pytest as my"


# Full text migration


def test_migrate_text_forward():
    text = textwrap.dedent("""\
        import pytest
        from pytest import raises
        from pytest._compat import main

        pytest.main()
    """)
    result = _migrate_text(text)
    assert "import oxytest as pytest" in result
    assert "from oxytest import raises" in result
    assert "from oxytest._compat import main" in result


def test_migrate_text_reverse():
    text = textwrap.dedent("""\
        import oxytest as pytest
        from oxytest import raises
    """)
    result = _migrate_text(text, reverse=True)
    assert "import pytest" in result
    assert "from pytest import raises" in result


def test_migrate_text_preserves_whitespace():
    text = "  import pytest\n"
    result = _migrate_text(text)
    assert result == "  import oxytest as pytest\n"


def test_migrate_text_preserves_crlf():
    text = "import pytest\r\n"
    result = _migrate_text(text)
    assert result == "import oxytest as pytest\r\n"


def test_migrate_text_no_change():
    text = "x = 1\ny = 2\n"
    result = _migrate_text(text)
    assert result == text


def test_migrate_text_comment_line():
    text = "# import pytest\nimport pytest\n"
    result = _migrate_text(text)
    assert "# import pytest" in result
    assert "import oxytest as pytest" in result


# File migration


def test_migrate_file_unchanged():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("x = 1\n")
        f.flush()
        path = f.name
    try:
        changed = _migrate_file(path, dry_run=True)
        assert not changed
        with open(path) as f2:
            assert f2.read() == "x = 1\n"
    finally:
        os.unlink(path)


def test_migrate_file_dry_run():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("import pytest\n")
        f.flush()
        path = f.name
    try:
        changed = _migrate_file(path, dry_run=True)
        assert changed
        with open(path) as f2:
            assert f2.read() == "import pytest\n"
    finally:
        os.unlink(path)


def test_migrate_file_actual():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("import pytest\n")
        f.flush()
        path = f.name
    try:
        changed = _migrate_file(path, dry_run=False)
        assert changed
        with open(path) as f2:
            assert f2.read() == "import oxytest as pytest\n"
    finally:
        os.unlink(path)


# migrate() function


def test_migrate_empty_directory(tmp_path):
    exit_code = migrate(str(tmp_path), dry_run=True)
    assert exit_code == 0


def test_migrate_with_py_file(tmp_path):
    pyfile = tmp_path / "test_foo.py"
    pyfile.write_text("import pytest\n")
    exit_code = migrate(str(tmp_path), dry_run=True)
    assert exit_code == 1


def test_migrate_reverse(tmp_path):
    pyfile = tmp_path / "test_foo.py"
    pyfile.write_text("import oxytest as pytest\n")
    exit_code = migrate(str(tmp_path), reverse=True, dry_run=True)
    assert exit_code == 1


def test_migrate_check_passes(tmp_path):
    pyfile = tmp_path / "test_foo.py"
    pyfile.write_text("x = 1\n")
    exit_code = migrate(str(tmp_path), check=True)
    assert exit_code == 0


def test_migrate_check_fails(tmp_path):
    pyfile = tmp_path / "test_foo.py"
    pyfile.write_text("import pytest\n")
    exit_code = migrate(str(tmp_path), check=True)
    assert exit_code == 1


# migrate_main()


def test_migrate_main_defaults(tmp_path):
    pyfile = tmp_path / "test_foo.py"
    pyfile.write_text("import pytest\n")
    exit_code = migrate_main([str(tmp_path)])
    assert exit_code == 1


def test_migrate_main_reverse(tmp_path):
    pyfile = tmp_path / "test_foo.py"
    pyfile.write_text("import oxytest as pytest\n")
    exit_code = migrate_main([str(tmp_path), "--reverse", "--dry-run"])
    assert exit_code == 1


def test_migrate_main_check(tmp_path):
    pyfile = tmp_path / "test_foo.py"
    pyfile.write_text("x = 1\n")
    exit_code = migrate_main([str(tmp_path), "--check"])
    assert exit_code == 0


def test_migrate_main_dry_run_and_check_mutually_exclusive():
    exit_code = migrate_main([".", "--dry-run", "--check"])
    assert exit_code == 2


def test_migrate_main_no_args(tmp_path):
    exit_code = migrate_main([str(tmp_path)])
    assert exit_code == 0
