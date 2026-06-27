"""1회 스캔 로직: 유동성 필터 → 엣지 판정 → 주문의도 + 시뮬 체결.

마켓의 두 outcome(YES/NO)을 각각 독립 매수 후보로 평가한다.
(NO 토큰 매수 = YES를 (1−price)에 파는 것과 대칭. 각 토큰은 자기 호가/과거가격을 가짐.)
"""
import config
import costs
import ledger
import sizing
from estimator import estimate_prob


def passes_liquidity(market, snap, hours_left) -> bool:
    """유동성/품질 필터. 미달이면 제외."""
    if snap is None:
        return False
    if snap["spread"] > config.MAX_SPREAD:
        return False
    ask = snap["best_ask"]
    if ask < config.PRICE_MIN or ask > config.PRICE_MAX:
        return False
    if hours_left is not None and hours_left < config.MIN_HOURS_TO_RESOLVE:
        return False
    return True


def evaluate_token(client, market, outcome_label, token_id, polyclient) -> dict | None:
    """단일 토큰(outcome) 평가 → 진입 시 (intent, fill) dict 반환, 아니면 None."""
    snap = polyclient.book_snapshot(client, token_id)
    hours_left = polyclient.hours_to_resolve(market)
    if not passes_liquidity(market, snap, hours_left):
        return None

    ask = snap["best_ask"]
    hist_mean = polyclient.price_history_mean(client, token_id)
    ctx = {
        "ask": ask,
        "mid": snap["mid"],
        "last_trade_price": snap["last_trade_price"],
        "hist_mean": hist_mean,
        "volume": float(market.metrics.volume_num or 0),
        "category": market.category,
        "outcome_label": outcome_label,
    }
    est = estimate_prob(ctx)
    if est is None:
        return None

    nedge = costs.net_edge(est, ask, market.category)
    if nedge <= config.EDGE_THRESHOLD:
        return None

    stake = sizing.bet_size(est, ask)
    if stake <= 0.0:
        return None
    shares = stake / ask

    ts = ledger.now_iso()
    fill_id = f"{market.id}:{outcome_label}:{ts}"
    common = {
        "fill_id": fill_id,
        "ts": ts,
        "market_id": str(market.id),
        "condition_id": str(market.condition_id),
        "question": market.question,
        "category": market.category,
        "outcome": outcome_label,          # 'yes' | 'no' — 우리가 산 쪽
        "token_id": str(token_id),
        "buy_price": ask,                  # 진입가(=실행 best_ask)
        "est_prob": est,
        "gross_edge": costs.gross_edge(est, ask),
        "net_edge": nedge,
        "friction": costs.friction(market.category),
        "stake_usdc": stake,
        "shares": shares,
        "hist_mean": hist_mean,
        "mid": snap["mid"],
        "spread": snap["spread"],
        "volume_num": float(market.metrics.volume_num or 0),
    }
    return common


def scan_once(client, polyclient, limit=200) -> int:
    """후보 마켓 순회 → 조건 충족분을 원장에 적립. 반환: 신규 진입 수."""
    entries = 0
    for market in polyclient.iter_candidate_markets(client, limit=limit):
        for label, outcome in (("yes", market.outcomes.yes), ("no", market.outcomes.no)):
            if outcome.token_id is None:
                continue
            try:
                rec = evaluate_token(client, market, label, str(outcome.token_id), polyclient)
            except Exception as exc:
                # 개별 토큰 조회 실패는 건너뛰고 계속(호가 없음/일시 오류 등)
                print(f"  [skip] {market.id}:{label} {type(exc).__name__}: {exc}")
                continue
            if rec is None:
                continue
            ledger.record_order(rec)
            ledger.record_fill(rec)
            entries += 1
            print(f"  [ENTER] {label.upper()} {market.question[:50]!r} "
                  f"@ {rec['buy_price']:.3f} est={rec['est_prob']:.3f} "
                  f"net_edge={rec['net_edge']:.3f} stake={rec['stake_usdc']:.2f}")
    return entries
