# polymarket-bot

> 폴리마켓 엣지 전략의 수익 가능성을 실주문 없이 검증하는 드라이런(시뮬) 봇. 공개 API 라이브 데이터로 "전략이 마찰비용을 넘는 엣지를 내는가"를 측정한다.

## 무엇인가

엣지 = (내 추정확률 − 시장가격) 이 마찰비용을 넘는지를, 실제 돈·주문 없이 "의도한 주문 + 시뮬 체결"로 로깅해 판정하는 프레임워크다. 최종 산출물은 시뮬 손익 + 의사결정 로그 + "가능/불가능" 판정 리포트.

**비용 모델 (사전 조사로 확정)**
- 거래 수수료: 메이커 0% / 테이커 정치 1%·크립토 1.8% / 지정학 0%
- 환전 왕복 ≈ 3% (거래소 경유, 원금에 부과)
- 한 판 본전 차익 허들 ≈ +3~5% → 엣지 = (추정확률 − 가격)
- 세금(참고): 2026년 가상자산 비과세(유예), 2027년~ 연 250만원 초과분 22% 분리과세

## 구성

읽기 전용 SDK만 사용한다 (지갑·API키 불필요). 공식 Polymarket `py-sdk`의 PublicClient로 Gamma(마켓 탐색)/Data(과거)/CLOB(호가)를 REST 조회 — WebSocket 실시간 스트림은 미구현. 각 모듈은 리포 루트의 작은 순수함수:

| 파일 | 역할 |
|---|---|
| `config.py` | 임계값·비용상수·필터·켈리·뱅크롤 등 모든 설정 |
| `polyclient.py` | `py-sdk`(PublicClient) 얇은 래퍼: 마켓 탐색/호가/과거가격/해소 |
| `costs.py` | 비용·엣지 모델 (friction, gross/net edge) |
| `sizing.py` | 프랙셔널 켈리(¼) + 1회 베팅 상한 |
| `estimator.py` | 추정확률 산출 (전략①, 교체 가능 지점) |
| `strategy.py` | 유동성 필터 → 엣지 판정 → 주문의도 + 시뮬 체결 |
| `ledger.py` / `resolve.py` | 가상 원장(JSONL) / 해소 정산 → 실현손익 |
| `report.py` | 지표 집계 + "가능/불가능" 판정 |
| `run_scan.py` / `run_report.py` | 엔트리포인트 |

**1차 전략** = 신규/저거래량 미스프라이싱. `estimator.py` 베이스라인 = 과거가격 평균 대비 현재가 괴리 → 평균 수렴 가설(이 가설 자체를 캘리브레이션으로 검증). "불가능"이면 `estimate_prob`만 다른 신호로 교체해 재측정.

## 실행

Windows, Python 3.13 (`py`). 실주문은 전송하지 않으며 모든 결과는 `logs\*.jsonl`.

```cmd
py -m pip install -r requirements.txt           :: 공식 py-sdk (버전 핀)
py polyclient.py                              :: 스모크: 마켓 1개 호가/과거가격
py run_scan.py                                :: 1회 스캔 → logs\orders.jsonl, fills.jsonl
py run_report.py                              :: 정산 + 가능성 리포트
py run_report.py --no-settle                  :: 오프라인(쌓인 settled만 집계)
```

**운영 루프** — 신호→해소까지 시간이 걸려 며칠~수주 누적해야 판정이 선다. `run_scan.py`를 주기 실행(30~60분)하고 하루 1회 `run_report.py`로 정산. 정산 `N ≥ N_MIN_FOR_VERDICT(기본 50)`가 되면 판정: 실현 엣지 > 평균 마찰 **그리고** 누적 실현손익 > 0, **그리고** Brier(추정확률) < Brier(시장가격).

> 일부 사내/클라우드 환경은 `polymarket.com` egress가 막혀 라이브 호출이 403일 수 있다 — 개인 PC에서 실행할 것. 설계 프롬프트는 `docs/ultraplan-prompt.md`.

## 결과

2026-07-09 라이브 1회 스캔(후보 최대 100개 순회) → 신규 진입 1건, 정산·리포트 실행 — 전체 출력은 [docs/실행증거_2026-07-09.md](docs/실행증거_2026-07-09.md).
핵심 계산 모듈(costs·sizing·strategy)은 pytest 14개로 검증: `py -m pytest tests/ -q`.

## 상태

측정 프레임워크(스캔→시뮬 체결→정산→판정)까지 완성. 판정에 필요한 정산 표본(N ≥ 50)을 쌓는 포워드 러닝은 아직 진행 중이라 가능/불가능 결론은 미확정.
2026-07 정비: SDK 버전 핀(0.1.0b10)·pytest·실행 증거 추가. 판정은 여전히 포워드 러닝 누적 대기.
