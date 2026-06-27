"""해소·정산: 미해소 시뮬 포지션의 마켓을 조회해 승패를 확정하고 실현손익을 기록.

실현손익(net) = gross_pnl − friction×stake
  적중: gross_pnl = stake × (1−buy_price)/buy_price   (share가 1.0로 상환)
  실패: gross_pnl = −stake
friction은 환전왕복+수수료+슬리피지(costs.friction)로, 원금(stake)에 부과.
멱등적: 이미 settled된 fill_id는 ledger.open_positions가 제외.
"""
import costs
import ledger


def _realized_pnl(buy_price: float, stake: float, friction: float, win: bool) -> float:
    if win:
        gross = stake * (1.0 - buy_price) / buy_price
    else:
        gross = -stake
    return gross - friction * stake


def settle_open(client, polyclient) -> int:
    """해소된 포지션을 정산해 settled.jsonl에 적립. 반환: 신규 정산 건수."""
    settled_count = 0
    # market_id별로 한 번만 조회(여러 포지션이 같은 마켓일 수 있음)
    cache: dict[str, object] = {}
    for pos in ledger.open_positions():
        mid = pos["market_id"]
        try:
            market = cache.get(mid) or client.get_market(id=mid)
            cache[mid] = market
        except Exception as exc:
            print(f"  [skip] market {mid} 조회 실패: {type(exc).__name__}: {exc}")
            continue

        is_resolved, winner = polyclient.resolution(market)
        if not is_resolved:
            continue  # 아직 미해소 → 다음 기회에

        win = (winner == pos["outcome"])
        friction = pos.get("friction") or costs.friction(pos.get("category"))
        pnl = _realized_pnl(pos["buy_price"], pos["stake_usdc"], friction, win)
        rec = {
            "fill_id": pos["fill_id"],
            "settled_ts": ledger.now_iso(),
            "market_id": mid,
            "question": pos["question"],
            "category": pos["category"],
            "outcome": pos["outcome"],
            "winner": winner,
            "win": win,
            "buy_price": pos["buy_price"],
            "est_prob": pos["est_prob"],
            "stake_usdc": pos["stake_usdc"],
            "friction": friction,
            "realized_pnl": pnl,
        }
        ledger.record_settlement(rec)
        settled_count += 1
        print(f"  [SETTLE] {'WIN ' if win else 'LOSS'} {pos['outcome'].upper()} "
              f"{pos['question'][:45]!r} buy={pos['buy_price']:.3f} pnl={pnl:+.2f}")
    return settled_count
