"""costs.py 순수함수 검증 — config 상수 기준으로 산술을 대조한다."""
import pytest

import config
import costs


def test_taker_fee_known_category():
    assert costs.taker_fee("politics") == config.TAKER_FEE_BY_CATEGORY["politics"]
    assert costs.taker_fee("CRYPTO") == config.TAKER_FEE_BY_CATEGORY["crypto"]  # 대소문자 무시


def test_taker_fee_unknown_or_none():
    assert costs.taker_fee("sports") == config.TAKER_FEE_DEFAULT
    assert costs.taker_fee(None) == config.TAKER_FEE_DEFAULT


def test_friction_sum():
    expected = config.FX_ROUNDTRIP + config.TAKER_FEE_BY_CATEGORY["crypto"] + config.SLIPPAGE_BUFFER
    assert costs.friction("crypto") == pytest.approx(expected)


def test_gross_and_net_edge():
    assert costs.gross_edge(0.6, 0.5) == pytest.approx(0.1)
    expected_net = 0.1 - costs.friction(None)
    assert costs.net_edge(0.6, 0.5, None) == pytest.approx(expected_net)
