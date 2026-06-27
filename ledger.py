"""가상 원장 — 실제 주문 전송 없이 '의도 + 시뮬 체결'을 JSONL로 적립.

파일(logs/):
  orders.jsonl  : 엣지 조건을 만족해 생성된 '주문 의도'(평가 스냅샷 포함)
  fills.jsonl   : 시뮬 체결 = 미해소 포지션 (resolve가 이걸 읽어 정산)
  settled.jsonl : 해소·정산 결과 (resolve가 append, report가 읽음)

시뮬 체결 가정: 테이커 즉시 전량 체결 @ best_ask, 부분체결/시장충격 없음(낙관적).
비용은 진입가에 녹이지 않고 손익 계산 시 friction으로 차감(costs.net_edge와 일관).
"""
import json
import os
from datetime import datetime, timezone

import config


def _path(filename: str) -> str:
    os.makedirs(config.LOG_DIR, exist_ok=True)
    return os.path.join(config.LOG_DIR, filename)


def _append(filename: str, record: dict) -> None:
    with open(_path(filename), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def load(filename: str) -> list[dict]:
    path = _path(filename)
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_order(intent: dict) -> None:
    """주문 의도 적립(감사·디버그용)."""
    _append(config.ORDERS_FILE, intent)


def record_fill(fill: dict) -> None:
    """시뮬 체결(미해소 포지션) 적립."""
    _append(config.FILLS_FILE, fill)


def record_settlement(settled: dict) -> None:
    """정산 결과 적립."""
    _append(config.SETTLED_FILE, settled)


def open_positions() -> list[dict]:
    """아직 정산되지 않은 시뮬 체결 목록.

    fills 중 settled에 fill_id가 없는 것만. (resolve가 멱등적으로 재실행되도록)
    """
    settled_ids = {s.get("fill_id") for s in load(config.SETTLED_FILE)}
    return [f for f in load(config.FILLS_FILE) if f.get("fill_id") not in settled_ids]
