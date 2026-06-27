"""공식 py-sdk(PublicClient) 얇은 래퍼 — 읽기 전용.

py-sdk(PyPI: polymarket-client)의 PublicClient 하나로 Gamma 탐색 / CLOB 호가 /
과거가격 / Data 체결을 모두 읽는다(무인증). 새 추상화는 만들지 않고, 시뮬에
필요한 값만 float로 뽑아 주는 헬퍼들만 둔다.

주의: 이 환경(에이전트 샌드박스)은 polymarket.com 도메인 egress가 막혀 있어
라이브 호출이 안 될 수 있다. 실제 검증은 사용자의 Windows에서 `py polyclient.py`.
"""
from datetime import datetime, timezone
import statistics

import polymarket as pm

import config


def get_client() -> pm.PublicClient:
    """프로덕션 PublicClient. 읽기 전용이라 지갑/키 불필요."""
    return pm.PublicClient()


def _f(x) -> float | None:
    """Decimal/None → float 안전 변환."""
    return None if x is None else float(x)


def iter_candidate_markets(client: pm.PublicClient, limit: int = 200):
    """유동성 밴드에 드는 활성·미해소 마켓을 거래량 오름차순으로 순회.

    저거래량 우선(ascending=True) — 전략①이 노리는 '얇은' 마켓부터 본다.
    """
    paginator = client.list_markets(
        closed=False,
        order="volumeNum",
        ascending=True,
        volume_num_min=config.MIN_VOLUME,
        volume_num_max=config.MAX_VOLUME,
        page_size=50,
    )
    count = 0
    for market in paginator.iter_items():
        yield market
        count += 1
        if count >= limit:
            return


def hours_to_resolve(market) -> float | None:
    """해소 예정까지 남은 시간(시간). end_date 없으면 None."""
    end = market.state.end_date
    if end is None:
        return None
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return (end - datetime.now(timezone.utc)).total_seconds() / 3600.0


def book_snapshot(client: pm.PublicClient, token_id: str) -> dict | None:
    """호가 스냅샷: best_bid / best_ask / mid / spread / last_trade_price (float).

    실행가(테이커 매수가) = best_ask. 양측 호가가 모두 있어야 유효.
    """
    ob = client.get_order_book(token_id=token_id)
    if not ob.bids or not ob.asks:
        return None
    best_bid = max(_f(lvl.price) for lvl in ob.bids)
    best_ask = min(_f(lvl.price) for lvl in ob.asks)
    if best_bid is None or best_ask is None or best_ask <= best_bid:
        return None
    return {
        "best_bid": best_bid,
        "best_ask": best_ask,
        "mid": (best_bid + best_ask) / 2.0,
        "spread": best_ask - best_bid,
        "last_trade_price": _f(ob.last_trade_price),
    }


def price_history_mean(client: pm.PublicClient, token_id: str) -> float | None:
    """과거가격 시간평균(estimator 입력). 표본이 HIST_MIN_POINTS 미만이면 None."""
    points = client.get_price_history(token_id=token_id, interval=config.HIST_INTERVAL)
    prices = [_f(pt.p) for pt in points if pt.p is not None]
    if len(prices) < config.HIST_MIN_POINTS:
        return None
    return statistics.fmean(prices)


def resolution(market):
    """해소 상태 → (is_resolved: bool, winner_label: 'yes'|'no'|None).

    closed 이고 uma_status∈{resolved,settled} 이며 한쪽 outcome price가 ~1.0 이면 확정.
    """
    state = market.state
    status = market.resolution.uma_resolution_status
    status_val = getattr(status, "value", status)
    if not state.closed or status_val not in ("resolved", "settled"):
        return False, None
    yes_p = _f(market.outcomes.yes.price)
    no_p = _f(market.outcomes.no.price)
    if yes_p is not None and yes_p >= 0.99:
        return True, "yes"
    if no_p is not None and no_p >= 0.99:
        return True, "no"
    return False, None


# ── 스모크 테스트: 사용자 머신에서 `py polyclient.py` ────────────────
if __name__ == "__main__":
    print("[스모크] PublicClient 생성 및 마켓 1개 호가 조회 시도...")
    try:
        client = get_client()
        for market in iter_candidate_markets(client, limit=1):
            yes = market.outcomes.yes
            print(f"  question : {market.question}")
            print(f"  category : {market.category}  volume_num={market.metrics.volume_num}")
            print(f"  YES token: {yes.token_id}")
            snap = book_snapshot(client, str(yes.token_id))
            print(f"  book     : {snap}")
            hm = price_history_mean(client, str(yes.token_id))
            print(f"  hist_mean: {hm}")
            break
        else:
            print("  (조건에 맞는 마켓 없음 — 유동성 밴드/필터를 조정해 보세요)")
        print("[스모크] OK — 읽기 경로 정상.")
    except Exception as exc:  # 네트워크 차단/SDK 변경 등을 사람이 읽을 수 있게
        print(f"[스모크] 실패: {type(exc).__name__}: {exc}")
        print("  → polymarket.com egress가 막힌 환경이거나 SDK API 변경일 수 있습니다.")
