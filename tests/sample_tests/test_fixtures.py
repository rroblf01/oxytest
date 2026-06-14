import oxytest as pytest


class TestWithFixtures:
    def test_tmp_path(self, tmp_path):
        import pathlib
        assert isinstance(tmp_path, pathlib.Path)
        assert tmp_path.exists()
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")
        assert test_file.read_text() == "hello"

    def test_multiple_tmp_paths(self, tmp_path):
        d = tmp_path / "subdir"
        d.mkdir()
        assert d.exists()

    def test_capsys(self, capsys):
        print("captured output")
        out, err = capsys.readouterr()
        assert "captured output" in out


def test_with_tmp_path(tmp_path):
    d = tmp_path / "data"
    d.mkdir()
    f = d / "file.txt"
    f.write_text("content")
    assert f.read_text() == "content"


def test_with_capsys(capsys):
    import sys
    print("stdout message")
    sys.stderr.write("stderr message\n")
    out, err = capsys.readouterr()
    assert "stdout message" in out
