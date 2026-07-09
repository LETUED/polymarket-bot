"""sizing.py 켈리 계산·상한 검증."""
import pytest

import config
import sizing


def test_kelly_fraction_known_value():
    # p=0.6, b=0.5 → odds=1 → f* = (0.6·1 − 0.4)/1 = 0.2
    assert sizing.kelly_fraction(0.6, 0.5) == pytest.approx(0.2)


def test_kelly_fraction_no_edge_is_zero():
    assert sizing.kelly_fraction(0.5, 0.5) == 0.0
    assert sizing.kelly_fraction(0.3, 0.5) == 0.0  # 음수 켈리 → 0


def test_kelly_fraction_degenerate_price():
    assert sizing.kelly_fraction(0.9, 0.0) == 0.0
    assert sizing.kelly_fraction(0.9, 1.0) == 0.0


def test_bet_size_fraction_cap():
    # f* = 0.2 → ¼켈리 0.05 → MAX_BET_FRACTION으로 캡 → 뱅크롤 비례
    assert sizing.bet_size(0.6, 0.5, bankroll=1000.0) == pytest.approx(
        min(config.MAX_BET_FRACTION * 1000.0, config.MAX_BET_ABS)
    )


def test_bet_size_abs_cap():
    # 큰 뱅크롤에서는 절대 상한(MAX_BET_ABS)이 걸린다
    assert sizing.bet_size(0.6, 0.5, bankroll=1_000_000.0) == config.MAX_BET_ABS
