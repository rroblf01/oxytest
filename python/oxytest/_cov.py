import sys
import typing


try:
    import coverage
except ImportError:
    if typing.TYPE_CHECKING:
        coverage = typing.cast(typing.Any, None)
    else:
        coverage = None


_COV_SOURCE = None
_COV_REPORT = None
_COV_CONFIG = None
_COV_BRANCH = False
_COV_FAIL_UNDER = None


def is_available() -> bool:
    return coverage is not None


class OxytestCoverPlugin:
    def __init__(
        self,
        source=None,
        report="term",
        config_file=None,
        branch=False,
        fail_under=None,
        append=False,
    ):
        self.source = source
        self.report = report
        self.config_file = config_file
        self.branch = branch
        self.fail_under = fail_under
        self.append = append
        self.cov = None

    def start(self):
        if coverage is None:
            return
        cov_source = self.source
        if cov_source and isinstance(cov_source, str):
            cov_source = [s.strip() for s in cov_source.split(",")]
        self.cov = coverage.Coverage(
            source=cov_source,
            branch=self.branch,
            config_file=self.config_file if self.config_file else True,
            data_suffix=True,
        )
        if not self.append:
            self.cov.erase()
        self.cov.start()

    def stop_and_save(self):
        if self.cov is not None:
            self.cov.stop()
            self.cov.save()

    def generate_reports(self):
        if self.cov is None:
            return
        if self.report in ("term", "term-missing"):
            omit_missing = self.report == "term-missing"
            self.cov.report(show_missing=omit_missing, file=sys.stderr)
        if self.report == "html":
            self.cov.html_report(directory="htmlcov")
        if self.report == "xml":
            self.cov.xml_report(outfile="coverage.xml")
        if self.fail_under is not None:
            total = self.cov.report(file=None)
            if total < self.fail_under:
                print(
                    f"FAIL: coverage {total:.2f}% below threshold {self.fail_under}%",
                    file=sys.stderr,
                )
                raise SystemExit(2)
