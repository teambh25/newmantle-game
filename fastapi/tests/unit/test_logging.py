import datetime

from app.cores.logging import cleanup_old_events

RETENTION_DAYS = 30


def _file(directory, days_ago, suffix):
    date = datetime.datetime.now(datetime.timezone.utc).date() - datetime.timedelta(
        days=days_ago
    )
    path = directory / f"{date.isoformat()}{suffix}"
    path.write_text("{}\n")
    return path


def test_removes_files_older_than_retention_of_any_pid(tmp_path):
    old_pid_a = _file(tmp_path, 31, ".111.jsonl")
    old_pid_b = _file(tmp_path, 31, ".222.jsonl")
    old_renamed = _file(tmp_path, 31, ".111.2026-10-01_14-31-39_123456.jsonl")
    boundary = _file(tmp_path, 30, ".111.jsonl")
    recent = _file(tmp_path, 1, ".333.jsonl")

    cleanup_old_events(tmp_path, RETENTION_DAYS)

    assert not old_pid_a.exists()
    assert not old_pid_b.exists()
    assert not old_renamed.exists()
    assert boundary.exists()
    assert recent.exists()


def test_keeps_non_jsonl_and_unparsable_files(tmp_path):
    old_zip = _file(tmp_path, 31, ".jsonl.zip")
    unparsable = tmp_path / "notes.jsonl"
    unparsable.write_text("{}\n")

    cleanup_old_events(tmp_path, RETENTION_DAYS)

    assert old_zip.exists()
    assert unparsable.exists()
