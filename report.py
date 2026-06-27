"""지표 집계 + 최종 '가능/불가능' 판정.

측정 지표(요구사항 전부):
  - 시뮬 손익: 실현(정산) + 미실현(미해소 포지션 stake)
  - 캘리브레이션: 매수가격 버킷별 실제 적중률 vs 가격 + Brier(추정확률 vs 가격)
  - 실현 엣지: stake가중 (실제 적중률 − 평균 매수가격), 마찰 대비
  - 조건충족 기회 수 N(=정산 건수)
  - 마찰 돌파: 실현엣지 > 평균 friction 이고 누적 실현손익 > 0 인가
  - 판정: 표본 충분 + 실현엣지>마찰 + 추정확률이 가격보다 정확(Brier) → '가능'
"""
import config
import ledger


def _weighted(pairs):
    """[(value, weight)] → 가중평균(가중합 0이면 0)."""
    tw = sum(w for _, w in pairs)
    if tw <= 0:
        return 0.0
    return sum(v * w for v, w in pairs) / tw


def _brier(prob_outcome_pairs):
    """mean((prob − outcome)^2). 낮을수록 정확."""
    if not prob_outcome_pairs:
        return None
    return sum((p - o) ** 2 for p, o in prob_outcome_pairs) / len(prob_outcome_pairs)


def build() -> dict:
    settled = ledger.load(config.SETTLED_FILE)
    open_pos = ledger.open_positions()

    n = len(settled)
    realized_pnl = sum(s["realized_pnl"] for s in settled)
    total_stake = sum(s["stake_usdc"] for s in settled)
    roi = realized_pnl / total_stake if total_stake > 0 else 0.0

    # 실현 엣지(가격 단위): stake가중 (실제 적중률 − 평균 매수가격)
    win_rate = _weighted([(1.0 if s["win"] else 0.0, s["stake_usdc"]) for s in settled])
    avg_buy = _weighted([(s["buy_price"], s["stake_usdc"]) for s in settled])
    realized_edge = win_rate - avg_buy
    avg_friction = (sum(s["friction"] for s in settled) / n) if n else 0.0

    # Brier: 추정확률 vs 시장가격(=매수가격) — outcome=우리 쪽이 적중하면 1
    outcomes = [(s, 1.0 if s["win"] else 0.0) for s in settled]
    brier_est = _brier([(s["est_prob"], o) for s, o in outcomes])
    brier_price = _brier([(s["buy_price"], o) for s, o in outcomes])

    # 캘리브레이션 버킷(매수가격 0.1 단위)
    buckets = {}
    for s in settled:
        b = min(9, int(s["buy_price"] * 10))
        d = buckets.setdefault(b, {"n": 0, "wins": 0, "price_sum": 0.0})
        d["n"] += 1
        d["wins"] += 1 if s["win"] else 0
        d["price_sum"] += s["buy_price"]
    calibration = []
    for b in sorted(buckets):
        d = buckets[b]
        calibration.append({
            "bucket": f"{b/10:.1f}-{(b+1)/10:.1f}",
            "n": d["n"],
            "avg_price": d["price_sum"] / d["n"],
            "actual_win_rate": d["wins"] / d["n"],
        })

    # 미실현(미해소): 단순히 투입 stake 합으로 노출 표기(마크는 운영 중 변동)
    unrealized_stake = sum(p["stake_usdc"] for p in open_pos)

    # 마찰 돌파 & 판정
    beats_friction = (realized_edge > avg_friction) and (realized_pnl > 0)
    est_more_accurate = (
        brier_est is not None and brier_price is not None and brier_est < brier_price
    )
    if n < config.N_MIN_FOR_VERDICT:
        verdict = "표본 불충분 — 운영 지속"
    elif beats_friction and est_more_accurate:
        verdict = "가능 (엣지가 마찰을 넘음)"
    else:
        verdict = "불가능 (마찰 미돌파 또는 추정확률이 가격보다 정확하지 않음)"

    return {
        "n_settled": n,
        "n_open": len(open_pos),
        "realized_pnl": realized_pnl,
        "total_stake": total_stake,
        "roi": roi,
        "unrealized_stake": unrealized_stake,
        "win_rate": win_rate,
        "avg_buy_price": avg_buy,
        "realized_edge": realized_edge,
        "avg_friction": avg_friction,
        "brier_est": brier_est,
        "brier_price": brier_price,
        "beats_friction": beats_friction,
        "est_more_accurate": est_more_accurate,
        "calibration": calibration,
        "verdict": verdict,
    }


def render(rep: dict) -> str:
    L = []
    L.append("=" * 60)
    L.append("폴리마켓 드라이런 — 가능성 리포트")
    L.append("=" * 60)
    L.append(f"정산 건수 N        : {rep['n_settled']}  (미해소 {rep['n_open']})")
    L.append(f"실현 손익          : {rep['realized_pnl']:+.2f} USDC  "
             f"(투입 {rep['total_stake']:.2f}, ROI {rep['roi']*100:+.2f}%)")
    L.append(f"미실현 노출        : {rep['unrealized_stake']:.2f} USDC")
    L.append(f"가중 실제 적중률   : {rep['win_rate']*100:.2f}%")
    L.append(f"가중 평균 매수가   : {rep['avg_buy_price']*100:.2f}%")
    L.append(f"실현 엣지          : {rep['realized_edge']*100:+.2f}%p  "
             f"(마찰 평균 {rep['avg_friction']*100:.2f}%p)")
    be = rep["brier_est"]; bp = rep["brier_price"]
    L.append(f"Brier(추정확률)    : {be:.4f}" if be is not None else "Brier(추정확률)    : -")
    L.append(f"Brier(시장가격)    : {bp:.4f}" if bp is not None else "Brier(시장가격)    : -")
    L.append("-" * 60)
    L.append("캘리브레이션 (매수가격 버킷별 실제 적중률):")
    L.append(f"  {'버킷':>9} {'n':>4} {'평균가':>8} {'실제적중률':>10}")
    for c in rep["calibration"]:
        L.append(f"  {c['bucket']:>9} {c['n']:>4} {c['avg_price']*100:>7.1f}% "
                 f"{c['actual_win_rate']*100:>9.1f}%")
    L.append("-" * 60)
    L.append(f"마찰 돌파          : {'예' if rep['beats_friction'] else '아니오'}")
    L.append(f"추정>가격 정확도   : {'예' if rep['est_more_accurate'] else '아니오'}")
    L.append(f"판정               : {rep['verdict']}")
    L.append("=" * 60)
    return "\n".join(L)
