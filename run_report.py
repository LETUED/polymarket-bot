"""엔트리: 미해소 포지션 정산 → 지표 집계 → 가능/불가능 판정 출력.

    py run_report.py            # 정산 후 리포트
    py run_report.py --no-settle  # 정산 건너뛰고 현재 원장만 집계(오프라인)

정산에는 라이브 마켓 조회가 필요하다(egress 필요). --no-settle은 네트워크 없이
이미 쌓인 settled.jsonl만으로 리포트한다.
"""
import sys

import polyclient
import report
import resolve


def main() -> int:
    polyclient.use_utf8_stdout()
    do_settle = "--no-settle" not in sys.argv

    if do_settle:
        print("[report] 미해소 포지션 정산 시도...")
        try:
            client = polyclient.get_client()
            n = resolve.settle_open(client, polyclient)
            print(f"[report] 신규 정산 {n}건.")
        except Exception as exc:
            print(f"[report] 정산 실패(리포트는 계속): {type(exc).__name__}: {exc}")

    rep = report.build()
    print(report.render(rep))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
