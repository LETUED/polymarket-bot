"""비용·엣지 모델 (순수함수).

엣지     = (내 추정확률 − 실행가)              … gross_edge
마찰비용 = 환전왕복 + 테이커수수료 + 슬리피지   … friction
순엣지   = gross_edge − friction              … net_edge   ← 진입 판정 기준

폴리마켓 share를 가격 p에 사면, 적중 시 +(1−p) / 실패 시 −p 가 (수수료 전) 손익.
본전 승률 = 매수가격 그 자체이므로, 추정확률이 가격을 friction 이상 초과해야
기대값이 양(+)이 된다.
"""
import config


def taker_fee(category: str | None) -> float:
    """카테고리별 테이커 수수료율. 메이커는 0이지만 본 시뮬은 즉시체결(테이커) 가정."""
    if category is None:
        return config.TAKER_FEE_DEFAULT
    return config.TAKER_FEE_BY_CATEGORY.get(category.lower(), config.TAKER_FEE_DEFAULT)


def friction(category: str | None) -> float:
    """한 판당 왕복 마찰비용(가격 단위, 0~1). 환전 왕복 + 수수료 + 슬리피지 여유."""
    return config.FX_ROUNDTRIP + taker_fee(category) + config.SLIPPAGE_BUFFER


def gross_edge(est_prob: float, buy_price: float) -> float:
    """원시 엣지 = 추정확률 − 실행가."""
    return est_prob - buy_price


def net_edge(est_prob: float, buy_price: float, category: str | None) -> float:
    """마찰 차감 후 순엣지. 이 값이 EDGE_THRESHOLD를 넘어야 가상 매수."""
    return gross_edge(est_prob, buy_price) - friction(category)
