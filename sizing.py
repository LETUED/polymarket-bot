"""포지션 사이징 (순수함수): 프랙셔널 켈리(¼) + 1회 베팅 상한."""
import config


def kelly_fraction(est_prob: float, buy_price: float) -> float:
    """이진 베팅 켈리 비율 f*.

    share를 가격 b(=buy_price)에 매수: 적중 시 순이익 (1−b)/b 배, 실패 시 −1배.
    켈리 f* = (p·odds − (1−p)) / odds,  odds = (1−b)/b.
    음수면 베팅 안 함(0).
    """
    b = buy_price
    if b <= 0.0 or b >= 1.0:
        return 0.0
    odds = (1.0 - b) / b              # 1달러 베팅 시 순이익 배수
    f = (est_prob * odds - (1.0 - est_prob)) / odds
    return max(0.0, f)


def bet_size(est_prob: float, buy_price: float, bankroll: float | None = None) -> float:
    """프랙셔널 켈리 적용 후 상한을 씌운 베팅액(USDC).

    f = clip(0, MAX_BET_FRACTION) of (KELLY_FRACTION × f*),
    베팅액 = min(f × bankroll, MAX_BET_ABS).
    """
    if bankroll is None:
        bankroll = config.BANKROLL
    f_star = kelly_fraction(est_prob, buy_price)
    f = config.KELLY_FRACTION * f_star
    f = min(f, config.MAX_BET_FRACTION)
    return min(f * bankroll, config.MAX_BET_ABS)
