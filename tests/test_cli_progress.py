from metatool.cli.app import _should_show_progress


def test_progress_is_limited_to_interactive_directory_table_output() -> None:
    assert _should_show_progress("table", True, False, True)
    assert not _should_show_progress("json", True, False, True)
    assert not _should_show_progress("table", True, True, True)
    assert not _should_show_progress("table", False, False, True)
    assert not _should_show_progress("table", True, False, False)
