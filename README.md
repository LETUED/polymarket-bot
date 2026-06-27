# polymarket-bot

폴리마켓 엣지 전략의 **수익 가능성 검증용 드라이런(시뮬레이션) 봇**.
실제 돈·실제 주문 없이, 공개 API의 라이브 데이터로 "전략이 마찰비용을 넘는 엣지를 내는가"를 측정한다.

## 목표
- 엣지 = (내 추정확률 − 시장가격) 이 마찰비용을 넘는지 검증
- 실제 주문 없음 → "의도한 주문 + 시뮬 체결"로 로깅
- 최종 산출물: 시뮬 손익 + 의사결정 로그 + "가능/불가능" 판정 리포트

## 핵심 전제 (사전 조사로 확정된 비용 모델)
- 거래 수수료: 메이커 0% / 테이커 정치 1%·크립토 1.8% / 지정학 0%
- 환전 왕복 ≈ 3% (거래소 경유, 원금에 부과)
- 한 판 본전 차익 허들 ≈ +3~5% (메이커+거래소 환전 기준 약 +3%)
- 본전 승률 = 매수 가격 그 자체 → 엣지 = (추정확률 − 가격)
- 세금(참고): 2026년 가상자산 비과세(유예), 2027년~ 연 250만원 초과분 22% 분리과세

## 환경
- Windows 10, Python 3.13 (`py` 명령)
- 공식 SDK: Polymarket `py-sdk` (구버전 `py-clob-client`는 archived → 사용 금지)
- 읽기 전용: Gamma(마켓 탐색) / Data(과거) / CLOB(호가) + real-time-data-client(WebSocket)

## 구조 (모두 리포 루트의 작은 모듈)
| 파일 | 역할 |
|---|---|
| `config.py` | 임계값·비용상수·필터·켈리·뱅크롤 등 모든 설정 |
| `polyclient.py` | 공식 `py-sdk`(PublicClient) 얇은 래퍼: 마켓 탐색/호가/과거가격/해소 |
| `costs.py` | 비용·엣지 모델 (friction, gross/net edge) — 순수함수 |
| `sizing.py` | 프랙셔널 켈리(¼) + 1회 베팅 상한 — 순수함수 |
| `estimator.py` | **추정확률 산출(전략①, 교체 가능 지점)** — 순수함수 |
| `strategy.py` | 유동성 필터 → 엣지 판정 → 주문의도 + 시뮬 체결 |
| `ledger.py` | 가상 원장(JSONL): orders/fills/settled |
| `resolve.py` | 해소된 마켓 정산 → 실현손익 |
| `report.py` | 지표 집계 + "가능/불가능" 판정 |
| `run_scan.py` / `run_report.py` | 엔트리포인트 |

## 사용법 (Windows, `py`)
```cmd
py -m pip install --pre -r requirements.txt   :: 공식 py-sdk 설치
py polyclient.py                              :: 스모크: 마켓 1개 호가/과거가격 출력
py run_scan.py                                :: 1회 스캔 → logs\orders.jsonl, fills.jsonl
py run_report.py                              :: 정산 + 가능성 리포트
py run_report.py --no-settle                  :: 오프라인(이미 쌓인 settled만 집계)
```
실제 주문은 **전송하지 않는다**(드라이런). 모든 결과는 `logs\*.jsonl`.

## 운영 루프 (포워드 페이퍼트레이딩)
전략①은 신호→해소까지 시간이 걸리므로 **며칠~수주 누적**해야 판정이 선다.
1. `run_scan.py`를 주기 실행(예 30~60분). Windows 작업 스케줄러 또는:
   ```cmd
   :loop
   py run_scan.py
   timeout /t 3600 >nul
   goto loop
   ```
2. 하루 1회 `py run_report.py`로 해소분을 정산하고 지표 확인.
3. 정산 건수 `N ≥ config.N_MIN_FOR_VERDICT(기본 50)` 가 되면 리포트가
   **가능/불가능**을 판정한다. 판정 근거:
   - 실현 엣지(실제 적중률 − 평균 매수가) > 평균 마찰 **그리고** 누적 실현손익 > 0
   - Brier(추정확률) < Brier(시장가격)  ← 내 추정이 가격보다 정확한가
4. "불가능"이면 `estimator.py`의 `estimate_prob`만 다른 신호로 교체해 재측정.

## 1차 테스트 선택 (확정)
- **엣지 신호 = ① 신규/저거래량 미스프라이싱** (공개 데이터만으로 완전 자동·측정 가능)
- **추정확률 = 규칙 기반 자동**: `estimator.py` 베이스라인 = 과거가격 평균 대비
  현재 실행가 괴리 → 평균 수렴 가설. *이 가설의 유효성 자체를 캘리브레이션으로 검증.*
- **검증 = 포워드 페이퍼트레이딩** (라이브 가상매수 → 해소 후 채점)

## 주의
- 읽기 전용이라 **지갑/API키 불필요**. `.env`·`logs/`는 `.gitignore` 처리됨.
- `py-sdk`(PyPI `polymarket-client`)는 프리릴리스 → API 변경 가능. 읽기는 PublicClient에 의존.
- 일부 사내/클라우드 환경은 `polymarket.com` egress가 막혀 라이브 호출이 403일 수 있다.
  그 경우 개인 PC(또는 egress 허용 환경)에서 실행할 것.

## 계획 문서
원래 설계 프롬프트는 `docs/ultraplan-prompt.md`.
