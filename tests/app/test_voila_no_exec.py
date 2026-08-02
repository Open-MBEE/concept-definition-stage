"""REQ-K3.1 — the Voila app exposes no code/execute surface. (P5)"""
import pytest


@pytest.mark.xfail(reason="P5: Voila app not built yet", strict=False)
def test_voila_execute_disabled():
    from cds.app import notebook_config

    assert notebook_config.execute_disabled() is True
