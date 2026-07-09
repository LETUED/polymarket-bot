"""strategy.passes_liquidity 필터 경계 검증 (market 인자는 필터 내부 미사용 — None 전달)."""
import config
import strategy


def snap(best_ask=0.5, spread=0.01):
    return {"best_ask": best_ask, "spread": spread, "mid": best_ask, "last_trade_price": best_ask}


def test_none_snapshot_rejected():
    assert strategy.passes_liquidity(None, None, 100) is False


def test_wide_spread_rejected():
    assert strategy.passes_liquidity(None, snap(spread=config.MAX_SPREAD + 0.01), 100) is False


def test_extreme_price_rejected():
    assert strategy.passes_liquidity(None, snap(best_ask=config.PRICE_MIN - 0.01), 100) is False
    assert strategy.passes_liquidity(None, snap(best_ask=config.PRICE_MAX + 0.01), 100) is False


def test_near_resolution_rejected():
    assert strategy.passes_liquidity(None, snap(), config.MIN_HOURS_TO_RESOLVE - 1) is False


def test_good_market_passes():
    assert strategy.passes_liquidity(None, snap(), config.MIN_HOURS_TO_RESOLVE + 1) is True
    assert strategy.passes_liquidity(None, snap(), None) is True  # 마감정보 없음 허용
