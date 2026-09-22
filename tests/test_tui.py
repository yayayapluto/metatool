from metatool.tui.app import MetaToolApp


def test_tui_exposes_textual_application() -> None:
    application = MetaToolApp()

    assert application.TITLE == "MetaTool"
