"""REQ-K3.1 — the Voila app exposes no code/execute surface. (P5)"""


def test_voila_execute_disabled() -> None:
    from cds.app import notebook_config

    assert notebook_config.execute_disabled() is True


def test_voila_config_is_hardened() -> None:
    from cds.app import notebook_config

    cfg = notebook_config.voila_settings()
    assert cfg["VoilaConfiguration"]["show_tracebacks"] is False
    assert cfg["VoilaConfiguration"]["allow_frontend_execute"] is False
    assert cfg["VoilaConfiguration"]["strip_sources"] is True
