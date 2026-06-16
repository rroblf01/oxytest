from oxytest._cov import (
    is_available,
    OxytestCoverPlugin,
    _COV_SOURCE,
    _COV_REPORT,
    _COV_CONFIG,
    _COV_BRANCH,
    _COV_FAIL_UNDER,
)


def test_is_available():
    result = is_available()
    assert isinstance(result, bool)


def test_plugin_init_defaults():
    plugin = OxytestCoverPlugin()
    assert plugin.source is None
    assert plugin.report == "term"
    assert plugin.config_file is None
    assert plugin.branch is False
    assert plugin.fail_under is None
    assert plugin.append is False
    assert plugin.cov is None


def test_plugin_init_custom():
    plugin = OxytestCoverPlugin(
        source="src/",
        report="html",
        config_file=".coveragerc",
        branch=True,
        fail_under=80.0,
        append=True,
    )
    assert plugin.source == "src/"
    assert plugin.report == "html"
    assert plugin.config_file == ".coveragerc"
    assert plugin.branch is True
    assert plugin.fail_under == 80.0
    assert plugin.append is True


def test_plugin_start_no_coverage(monkeypatch):
    import oxytest._cov as cov_mod
    monkeypatch.setattr(cov_mod, "coverage", None)
    plugin = OxytestCoverPlugin(source="src/")
    plugin.start()
    assert plugin.cov is None


def test_plugin_stop_no_coverage(monkeypatch):
    import oxytest._cov as cov_mod
    monkeypatch.setattr(cov_mod, "coverage", None)
    plugin = OxytestCoverPlugin()
    plugin.start()
    plugin.stop_and_save()
    assert plugin.cov is None


def test_plugin_generate_reports_no_coverage(monkeypatch):
    import oxytest._cov as cov_mod
    monkeypatch.setattr(cov_mod, "coverage", None)
    plugin = OxytestCoverPlugin()
    plugin.generate_reports()


def test_plugin_generate_reports_no_cov():
    plugin = OxytestCoverPlugin()
    plugin.cov = None
    plugin.generate_reports()


def test_plugin_stop_and_save():
    class FakeCov:
        def __init__(self):
            self.stopped = False
            self.saved = False
        def stop(self):
            self.stopped = True
        def save(self):
            self.saved = True
    plugin = OxytestCoverPlugin()
    plugin.cov = FakeCov()
    plugin.stop_and_save()
    assert plugin.cov.stopped
    assert plugin.cov.saved


def test_plugin_generate_term_report():
    class FakeCov:
        def report(self, **kwargs):
            self.report_kwargs = kwargs
            return 0.0
    plugin = OxytestCoverPlugin(report="term")
    plugin.cov = FakeCov()
    plugin.generate_reports()
    assert plugin.cov.report_kwargs is not None


def test_plugin_generate_html_report():
    class FakeCov:
        def report(self, **kwargs):
            self.report_kwargs = kwargs
            return 0.0
        def html_report(self, **kwargs):
            self.html_kwargs = kwargs
    plugin = OxytestCoverPlugin(report="html")
    plugin.cov = FakeCov()
    plugin.generate_reports()
    assert hasattr(plugin.cov, "html_kwargs")


def test_plugin_generate_xml_report():
    class FakeCov:
        def report(self, **kwargs):
            self.report_kwargs = kwargs
            return 0.0
        def xml_report(self, **kwargs):
            self.xml_kwargs = kwargs
    plugin = OxytestCoverPlugin(report="xml")
    plugin.cov = FakeCov()
    plugin.generate_reports()
    assert hasattr(plugin.cov, "xml_kwargs")


def test_plugin_fail_under_below():
    class FakeCov:
        def report(self, **kwargs):
            self.report_kwargs = kwargs
            return 50.0
    plugin = OxytestCoverPlugin(fail_under=80.0)
    plugin.cov = FakeCov()
    try:
        plugin.generate_reports()
        assert False, "Should have raised SystemExit"
    except SystemExit as e:
        assert e.code == 2


def test_plugin_fail_under_above():
    class FakeCov:
        def report(self, **kwargs):
            self.report_kwargs = kwargs
            return 90.0
    plugin = OxytestCoverPlugin(fail_under=80.0)
    plugin.cov = FakeCov()
    plugin.generate_reports()
    assert plugin.cov.report_kwargs is not None


def test_plugin_start_source_string_to_list(monkeypatch):
    import oxytest._cov as cov_mod
    captured_kwargs = {}
    def fake_coverage_cls(*args, **kwargs):
        captured_kwargs.update(kwargs)
        class FakeCovInstance:
            def erase(self):
                pass
            def start(self):
                pass
        return FakeCovInstance()
    fake_mod = type("fake_coverage", (), {"Coverage": fake_coverage_cls})()
    monkeypatch.setattr(cov_mod, "coverage", fake_mod)
    plugin = OxytestCoverPlugin(source="src/,lib/")
    plugin.start()
    assert plugin.cov is not None


def test_module_constants_exist():
    assert _COV_SOURCE is None
    assert _COV_REPORT is None
    assert _COV_CONFIG is None
    assert _COV_BRANCH is False
    assert _COV_FAIL_UNDER is None
