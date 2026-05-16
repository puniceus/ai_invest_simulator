# AI Invest Simulator

종가 기준 가상 투자 시뮬레이터입니다. 시작 자본은 국장 1,000만원과 미장 10,000달러이며, 이후에는 각 시장의 시뮬레이션 결과로 변한 평가자산을 기준으로 계속 운용합니다.

## 기능

- 국장/미장 가격 데이터 수집
- 통합/국장/미장 수익률 분리 표시
- 3~20일 스윙형 후보 점수화
- 하루 신규 매수 최대 3종목
- 매도 제한 없음
- Gemini 기반 일일 성과 분석 및 전략 파라미터 자동 조정
- 매일 정적 HTML 리포트 생성

## 로컬 실행

```powershell
.\venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
.\venv\Scripts\python -m app.cli run --mock
```

실제 데이터와 Gemini를 사용하려면 `.env`에 `GEMINI_API_KEY`를 설정한 뒤 아래처럼 실행합니다.

```powershell
.\venv\Scripts\python -m app.cli run
```

생성 결과는 `reports/simulator.html`입니다.
