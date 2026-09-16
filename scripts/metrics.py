"""Release metrics: a snapshot of the project at one version.

Collects seven metrics, writes them to ``docs/metrics/<version>.json`` and
regenerates the summary table ``docs/metrics/README.md`` from every snapshot
in that directory.

    M1  linter findings and suppressions    ruff
    M2  cyclomatic complexity               radon
    M3  line and branch coverage            pytest-cov
    M4  test results and run time           pytest, JUnit XML
    M5  commits since the previous version  git log
    M6  CI pipeline runs and duration       GitHub Actions API
    M7  project size                        git ls-files

Run it through ``just metrics <version>``. CI runs the same recipe on every
tag, see ``.github/workflows/metrics.yml``.

Dates are deliberately absent from the output: commits are reduced to counts
and averages, never laid out on a timeline.
"""

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, cast
import urllib.error
import urllib.request
from xml.etree.ElementTree import Element, parse


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = ROOT / "docs" / "metrics"

# The aggregate CI workflow whose runs M6 describes.
CI_WORKFLOW = "ci.yml"

# Directories whose Python files count as the project's own code.
PYTHON_AREAS = ("src", "tests", "scripts")

# Functions above this cyclomatic complexity are counted separately; it is the
# usual boundary between "simple" and "needs attention" (radon rank B and up).
COMPLEXITY_LIMIT = 10

TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")

LANGUAGES = {
    ".py": "Python",
    ".toml": "TOML",
    ".ini": "INI",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".md": "Markdown",
    ".json": "JSON",
}
COMMENT_PREFIXES = {"Python": "#", "TOML": "#", "INI": "#", "YAML": "#"}


# --- Helpers -----------------------------------------------------------------


def _run(*args: str, check: bool = True) -> str:
    """Run a command in the repository root and return its standard output."""
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=False)
    if check and result.returncode != 0:
        command = " ".join(args)
        raise RuntimeError(f"{command} exited with {result.returncode}:\n{result.stderr}")
    return result.stdout


def _tracked_files() -> list[Path]:
    """Files under version control, without the metrics snapshots themselves."""
    return [
        ROOT / name
        for name in _run("git", "ls-files").splitlines()
        if not name.startswith("docs/metrics/")
    ]


def _python_files() -> list[Path]:
    return [
        path
        for path in _tracked_files()
        if path.suffix == ".py" and path.relative_to(ROOT).parts[0] in PYTHON_AREAS
    ]


def _attribute(element: Element, name: str) -> str:
    value = element.get(name)
    if value is None:
        raise RuntimeError(f"<{element.tag}> has no attribute {name!r}")
    return value


def _ratio(part: int, whole: int, digits: int = 4) -> float | None:
    return round(part / whole, digits) if whole else None


# --- M1: linter --------------------------------------------------------------


def lint_metrics() -> dict[str, Any]:
    """Ruff findings by rule, plus the suppressions that hide findings."""
    output = _run("ruff", "check", "--exit-zero", "--statistics", "--output-format", "json", ".")
    statistics = cast("list[dict[str, Any]]", json.loads(output or "[]"))
    by_rule = {str(item["code"]): int(item["count"]) for item in statistics}

    noqa = type_ignores = 0
    for path in _python_files():
        text = path.read_text(encoding="utf-8")
        noqa += len(re.findall(r"#\s*noqa\b", text))
        type_ignores += len(re.findall(r"#\s*type:\s*ignore\b", text))

    return {
        "findings": sum(by_rule.values()),
        "by_rule": by_rule,
        "noqa": noqa,
        "type_ignores": type_ignores,
    }


# --- M2: complexity ----------------------------------------------------------


def complexity_metrics() -> dict[str, Any]:
    """Cyclomatic complexity of every function and method in src/.

    Class entries are skipped: radon reports a class as the sum of its methods
    and lists those methods separately as well.
    """
    report = cast("dict[str, Any]", json.loads(_run("radon", "cc", "--json", "src")))
    scores = [
        int(block["complexity"])
        for blocks in report.values()
        if isinstance(blocks, list)
        for block in blocks
        if block["type"] in {"function", "method"}
    ]
    above = sum(score > COMPLEXITY_LIMIT for score in scores)
    return {
        "functions": len(scores),
        "average": round(sum(scores) / len(scores), 2) if scores else None,
        "max": max(scores, default=None),
        "above_limit": above,
        "above_limit_share": _ratio(above, len(scores)),
    }


# --- M3, M4: tests and coverage ----------------------------------------------


def test_metrics() -> tuple[dict[str, Any], dict[str, Any]]:
    """Run the suite once and read both coverage (M3) and results (M4).

    The threshold from .coveragerc is switched off here: a snapshot records
    what the coverage is, it does not judge it. Random ordering is off so that
    two snapshots of the same code measure the same run.
    """
    with tempfile.TemporaryDirectory() as directory:
        coverage_xml = Path(directory) / "coverage.xml"
        junit_xml = Path(directory) / "junit.xml"
        _run(
            sys.executable,
            "-m",
            "pytest",
            "--cov",
            f"--cov-report=xml:{coverage_xml}",
            "--cov-fail-under=0",
            f"--junitxml={junit_xml}",
            "-p",
            "no:randomly",
            "-q",
            check=False,
        )
        if not junit_xml.exists():
            raise RuntimeError("pytest produced no JUnit report; run `just test` to see why")

        # Both reports were written a moment ago by our own test run.
        coverage = parse(coverage_xml).getroot()  # noqa: S314
        junit = parse(junit_xml).getroot()  # noqa: S314

    suite = junit if junit.tag == "testsuite" else junit.find("testsuite")
    if suite is None:
        raise RuntimeError("the JUnit report contains no <testsuite>")

    total = int(_attribute(suite, "tests"))
    failed = int(_attribute(suite, "failures"))
    errors = int(_attribute(suite, "errors"))
    skipped = int(_attribute(suite, "skipped"))

    return (
        {
            "lines": round(float(_attribute(coverage, "line-rate")) * 100, 2),
            "branches": round(float(_attribute(coverage, "branch-rate")) * 100, 2),
            "lines_valid": int(_attribute(coverage, "lines-valid")),
            "lines_covered": int(_attribute(coverage, "lines-covered")),
            "branches_valid": int(_attribute(coverage, "branches-valid")),
            "branches_covered": int(_attribute(coverage, "branches-covered")),
        },
        {
            "total": total,
            "passed": total - failed - errors - skipped,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "duration_s": round(float(_attribute(suite, "time")), 2),
        },
    )


# --- M5: commits -------------------------------------------------------------


def commit_metrics(previous: str | None) -> dict[str, Any]:
    """Commits since the previous version: count, size and frequency.

    Frequency is expressed per active week (a week with at least one commit),
    which describes the rhythm of work without tying it to calendar dates.
    """
    revisions = f"{previous}..HEAD" if previous else "HEAD"
    log = _run("git", "log", "--numstat", "--format=%x1e%aI", revisions)

    weeks: set[tuple[int, int]] = set()
    insertions = deletions = 0
    commits = log.split("\x1e")[1:]
    for entry in commits:
        header, _, body = entry.partition("\n")
        year, week, _ = datetime.fromisoformat(header.strip()).isocalendar()
        weeks.add((year, week))
        for line in body.splitlines():
            added, removed, *_ = [*line.split("\t"), "", ""]
            # Binary files report "-" instead of a line count.
            if added.isdigit() and removed.isdigit():
                insertions += int(added)
                deletions += int(removed)

    count = len(commits)
    return {
        "count": count,
        "insertions": insertions,
        "deletions": deletions,
        "average_size": round((insertions + deletions) / count, 1) if count else None,
        "active_weeks": len(weeks),
        "per_active_week": round(count / len(weeks), 2) if weeks else None,
    }


# --- M6: pipeline ------------------------------------------------------------


def _github_token() -> str | None:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    try:
        return _run("gh", "auth", "token").strip() or None
    except (OSError, RuntimeError):
        return None


def _github_repository() -> str | None:
    if repository := os.environ.get("GITHUB_REPOSITORY"):
        return repository
    match = re.search(
        r"github\.com[:/](.+?)(?:\.git)?$", _run("git", "remote", "get-url", "origin")
    )
    return match.group(1) if match else None


def _workflow_runs(repository: str, token: str) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    page = 1
    while True:
        request = urllib.request.Request(
            f"https://api.github.com/repos/{repository}/actions/workflows/{CI_WORKFLOW}"
            f"/runs?status=completed&per_page=100&page={page}",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        # A fixed https URL to the GitHub API; the scheme cannot be user-supplied.
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            batch = cast("list[dict[str, Any]]", json.load(response)["workflow_runs"])
        runs.extend(batch)
        if len(batch) < 100:
            return runs
        page += 1


def pipeline_metrics() -> dict[str, Any]:
    """Completed runs of the CI workflow up to the measured commit.

    Cancelled runs are counted but left out of the success rate and the
    duration: they were superseded by a newer push, not failed.
    """
    token, repository = _github_token(), _github_repository()
    if not token or not repository:
        return {"error": "no GitHub token or repository"}
    try:
        runs = _workflow_runs(repository, token)
    except urllib.error.HTTPError as error:
        return {"error": f"GitHub API answered HTTP {error.code}"}
    except urllib.error.URLError as error:
        return {"error": f"GitHub API is unreachable: {error.reason}"}

    until = datetime.fromisoformat(_run("git", "log", "-1", "--format=%cI", "HEAD").strip())
    runs = [run for run in runs if datetime.fromisoformat(run["created_at"]) <= until]
    finished = [run for run in runs if run["conclusion"] in {"success", "failure"}]
    successful = sum(run["conclusion"] == "success" for run in finished)
    durations = [
        (
            datetime.fromisoformat(run["updated_at"])
            - datetime.fromisoformat(run.get("run_started_at") or run["created_at"])
        ).total_seconds()
        for run in finished
    ]
    return {
        "runs": len(runs),
        "successful": successful,
        "failed": len(finished) - successful,
        "cancelled": len(runs) - len(finished),
        "success_rate": _ratio(successful, len(finished)),
        "average_duration_s": round(sum(durations) / len(durations), 1) if durations else None,
    }


# --- M7: size ----------------------------------------------------------------


def size_metrics() -> dict[str, Any]:
    """Files and lines under version control, by language and by code area.

    A code line is a non-blank line that is not a whole-line comment. uv.lock
    is left out: it is generated and would dwarf everything else.
    """
    by_language: dict[str, dict[str, int]] = {}
    python_areas = dict.fromkeys(PYTHON_AREAS, 0)

    for path in _tracked_files():
        if path.name == "uv.lock" or not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        language = LANGUAGES.get(path.suffix, "Other")
        prefix = COMMENT_PREFIXES.get(language)
        code = sum(
            bool(line.strip()) and not (prefix and line.lstrip().startswith(prefix))
            for line in lines
        )
        stats = by_language.setdefault(language, {"files": 0, "lines": 0, "code_lines": 0})
        stats["files"] += 1
        stats["lines"] += len(lines)
        stats["code_lines"] += code
        area = path.relative_to(ROOT).parts[0]
        if language == "Python" and area in python_areas:
            python_areas[area] += code

    return {
        "files": sum(stats["files"] for stats in by_language.values()),
        "lines": sum(stats["lines"] for stats in by_language.values()),
        "code_lines": sum(stats["code_lines"] for stats in by_language.values()),
        "python_code_lines": python_areas,
        "by_language": dict(sorted(by_language.items())),
    }


# --- Summary table -----------------------------------------------------------


def _version_key(path: Path) -> tuple[int, ...]:
    match = TAG.match(path.stem)
    return tuple(int(part) for part in match.groups()) if match else (sys.maxsize,)


def _cell(value: object, suffix: str = "") -> str:
    return "—" if value is None else f"{value}{suffix}"


def _row(snapshot: dict[str, Any]) -> str:
    metrics = snapshot["metrics"]
    lint, complexity = metrics["lint"], metrics["complexity"]
    coverage, tests = metrics["coverage"], metrics["tests"]
    commits, pipeline, size = metrics["commits"], metrics["pipeline"], metrics["size"]
    rate = pipeline.get("success_rate")
    cells = [
        f"`{snapshot['version']}`",
        _cell(lint["findings"]),
        f"{lint['noqa']} / {lint['type_ignores']}",
        f"{_cell(complexity['average'])} / {_cell(complexity['max'])}",
        _cell(complexity["above_limit"]),
        f"{coverage['lines']} / {coverage['branches']}",
        f"{tests['passed']} / {tests['total']}",
        _cell(tests["duration_s"]),
        _cell(commits["count"]),
        _cell(commits["average_size"]),
        _cell(round(rate * 100, 1) if rate is not None else None),
        _cell(pipeline.get("average_duration_s")),
        f"{size['python_code_lines']['src']} / {size['python_code_lines']['tests']}",
    ]
    return "| " + " | ".join(cells) + " |"


SUMMARY_HEADER = """\
# Метрики проекта

Срез снимается при выпуске каждой версии командой `just metrics <версия>`
(скрипт `scripts/metrics.py`); тот же рецепт по тегу запускает workflow
`.github/workflows/metrics.yml`. Файл сформирован автоматически; исходные
данные — JSON-файлы в этом каталоге.

| Метрика | Что измеряется | Инструмент |
| --- | --- | --- |
| M1 | Замечания линтера; подавления `noqa` и `type: ignore` | ruff |
| M2 | Цикломатическая сложность функций и методов `src/` | radon |
| M3 | Покрытие строк и ветвлений кода тестами | pytest-cov |
| M4 | Результаты тестов и время прогона | pytest |
| M5 | Число и средний размер коммитов с предыдущей версии | git |
| M6 | Запуски CI: доля успешных и среднее время | GitHub Actions API |
| M7 | Объём кода: строки кода Python в `src/` и `tests/` | git |

| Версия | M1: замечаний | M1: noqa / type: ignore | M2: сложность ср. / макс. \
| M2: функций со сложностью > 10 | M3: покрытие строк / ветвей, % | M4: тестов пройдено / всего \
| M4: время тестов, с | M5: коммитов | M5: строк на коммит | M6: успешных запусков, % \
| M6: время запуска, с | M7: строк кода src / tests |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
"""


def render_summary(directory: Path) -> str:
    """The Markdown summary of every snapshot in the directory, oldest first."""
    rows = [
        _row(cast("dict[str, Any]", json.loads(path.read_text(encoding="utf-8"))))
        for path in sorted(directory.glob("v*.json"), key=_version_key)
    ]
    return SUMMARY_HEADER + "\n".join(rows) + "\n"


# --- Entry point -------------------------------------------------------------


def _previous_version(version: str) -> str | None:
    tags = _run("git", "tag", "--merged", "HEAD", "--sort=-v:refname").split()
    return next((tag for tag in tags if tag != version and TAG.match(tag)), None)


def main(argv: list[str] | None = None) -> int:
    """Collect the snapshot for one version and refresh the summary table."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("version", help="version being measured, e.g. v0.2.0")
    parser.add_argument("--previous", help="previous version; the latest older tag by default")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args(argv)

    version: str = arguments.version
    if not TAG.match(version):
        parser.error(f"version must look like v1.2.3, got {version!r}")
    previous: str | None = arguments.previous or _previous_version(version)

    print(f"Measuring {version} (previous: {previous or 'none'})")
    coverage, tests = test_metrics()
    snapshot = {
        "version": version,
        "previous": previous,
        "commit": _run("git", "rev-parse", "--short", "HEAD").strip(),
        "metrics": {
            "lint": lint_metrics(),
            "complexity": complexity_metrics(),
            "coverage": coverage,
            "tests": tests,
            "commits": commit_metrics(previous),
            "pipeline": pipeline_metrics(),
            "size": size_metrics(),
        },
    }

    output: Path = arguments.output_dir
    output.mkdir(parents=True, exist_ok=True)
    target = output / f"{version}.json"
    target.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "README.md").write_text(render_summary(output), encoding="utf-8")
    print(f"Wrote {target} and {output / 'README.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
