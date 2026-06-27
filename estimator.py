"""추정확률 estimator — 전략①(신규/저거래량 미스프라이싱) 베이스라인.

★ 여기가 "엣지 신호를 어디서 얻는가"의 핵심이자 교체 가능 지점이다. ★

베이스라인 가설(누설 없음, 신호시점 정보만 사용):
    저거래량 마켓의 현재 실행가는 과거가격 평균에서 크게 벗어나 있을 때
    '오버슈트'일 가능성이 있고, 평균(fair)으로 수렴한다고 본다.
    → 추정확률 = 과거가격 시간평균(hist_mean).
    → 현재 실행가가 평균보다 REVERSION_BAND 이상 '싸면' 매수 신호(상방 수렴 기대).

이 가설이 맞는지(=가격 대비 더 정확한지)는 드라이런이 캘리브레이션으로 측정한다.
엣지가 없으면 이 함수만 다른 신호로 교체하면 된다. 대안 후보:
    - 멀티아웃컴(네거티브리스크) 정규화: 한 이벤트 내 YES 합이 1에서 벗어나면 미스프라이싱
    - 뉴스 반영 시차 / 카테고리 전문성 (별도 입력 필요)

ctx(dict) 필드: ask, mid, last_trade_price, hist_mean, volume, category, outcome_label
반환: 추정확률 float(0~1) 또는 None(신호 없음 → 스킵).
"""
import config


def estimate_prob(ctx: dict) -> float | None:
    hist_mean = ctx.get("hist_mean")
    ask = ctx.get("ask")
    if hist_mean is None or ask is None:
        return None  # 과거가격 표본 부족 등 → 판단 보류

    # 현재 실행가가 과거평균보다 충분히 싼 경우에만 상방 수렴을 가설.
    # (반대로 비싸면 하방 신호지만, 매수 전략이므로 본 베이스라인은 상방만 취함.)
    if (hist_mean - ask) < config.REVERSION_BAND:
        return None

    fair = hist_mean
    # 극단값 방어용 클램프
    return min(0.99, max(0.01, fair))
