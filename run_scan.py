"""엔트리: 1회 스캔. 스케줄러/수동으로 주기 실행한다.

    py run_scan.py            # 라이브 호가로 1회 스캔
    py run_scan.py --limit 50 # 순회 마켓 수 제한

실제 주문은 전송하지 않는다(드라이런). 결과는 logs/orders.jsonl, logs/fills.jsonl.
"""
import sys

import polyclient
import strategy


def main() -> int:
    limit = 200
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    print(f"[scan] PublicClient 생성, 후보 최대 {limit}개 순회...")
    try:
        client = polyclient.get_client()
    except Exception as exc:
        print(f"[scan] 클라이언트 생성 실패: {type(exc).__name__}: {exc}")
        return 1

    try:
        entries = strategy.scan_once(client, polyclient, limit=limit)
    except Exception as exc:
        print(f"[scan] 스캔 실패: {type(exc).__name__}: {exc}")
        print("  → polymarket.com egress 차단 환경이거나 SDK API 변경일 수 있습니다.")
        return 1

    print(f"[scan] 완료 — 신규 진입 {entries}건 적립.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
