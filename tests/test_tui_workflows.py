from metatool.tui.app import MetaToolApp


def test_tui_exposes_core_backed_sanitize_and_validate_workers() -> None:
    application = MetaToolApp()

    assert callable(application.sanitize_document_worker)
    assert callable(application.validate_document_worker)
