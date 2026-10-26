from pathlib import Path

from ingest.collect import collect

FIXTURE = Path(__file__).parent / "fixtures" / "mini_harborrag"


def test_collect_returns_expected_sorted_paths_for_fixture():
    expected: list[Path] = [
        Path("CHANGELOG.md"),
        Path("CONTRIBUTING.md"),
        Path("README.md"),
        Path("SECURITY.md"),
        Path("docs/getting-started/README.md"),
        Path("docs/users/guide.md"),
        Path("packages/demo/README.md"),
        Path("packages/demo/pyproject.toml"),
    ]

    assert collect(FIXTURE) == expected


def test_collect_is_deterministic():
    first_result = collect(FIXTURE)
    second_result = collect(FIXTURE)

    assert first_result == second_result
    assert first_result == sorted(first_result, key=Path.as_posix)


def test_collect_returns_relative_paths():
    result = collect(FIXTURE)
    assert result != []
    for p in result:
        assert not p.is_absolute()
        assert (FIXTURE / p).is_file()
