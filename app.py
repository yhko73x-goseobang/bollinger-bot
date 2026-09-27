import time
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
import schedule # pip install schedule

# ==========================================
# 1. 텔레그램 설정 및 종목/타임프레임 정의
# ==========================================
BOT_TOKEN = "8345013135:AAExhqYJmc2_zX1QRyGAmNoLgox7oPPU0hI"
CHAT_ID = "6287856148"

# 기본 검색 시간대 (5분, 15분, 30분, 1시간, 4시간, 일봉)
# yfinance interval 형식: '5m', '15m', '30m', '1h', '4h'(yfinance는 4h 직접 지원 안될 수 있어 1h 데이터 리샘플링 또는 1h/1d 조합 사용, 여기서는 표준 인터벌 사용)
INTERVALS = ['5m', '15m', '30m', '1h', '1d'] 

# 요청하신 100개 기업 + 빈칸 20개 (총 120개 슬롯)
TICKERS = [
    # 지정해주신 100개 기업
    "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "GOOG", "META", "AVGO", "TSLA", "MU",
    "LLY", "JPM", "WMT", "AMD", "BRK-B", "V", "XOM", "JNJ", "INTC", "MA",
    "ABBV", "CSCO", "ORCL", "CVX", "PLTR", "BAC", "COST", "KO", "CAT", "DELL",
    "MRK", "PG", "LRCX", "UNH", "AMAT", "GE", "MS", "NFLX", "PANW", "HD",
    "PM", "GS", "WFC", "RTX", "ANET", "CRWD", "GEV", "TXN", "TMO", "IBM",
    "C", "SNDK", "KLAC", "AXP", "VZ", "MRVL", "CRM", "AMGN", "QCOM", "APH",
    "PEP", "PFE", "ABT", "MCD", "DIS", "INTU", "NOW", "CMCSA", "TMUS", "BKNG",
    "SBUX", "GILD", "NKE", "BLK", "CCEP", "UNP", "LOW", "COP", "VRTX", "ADBE",
    "SHOP", "PYPL", "DDOG", "ABNB", "DASH", "APP", "CEG", "LIN", "ADI", "HON",
    "WDC", "STX", "MDT", "SNOW", "WDAY", "SNPS", "CDNS", "REGN", "MDLZ", "ISRG", "MCHP",
    # 추가 빈칸 20개 슬롯 (필요시 종목명을 입력하여 사용하세요)
    "", "", "", "", "", "", "", "", "", "",
    "", "", "", "", "", "", "", "", "", ""
]

# ==========================================
# 2. 텔레그램 메시지 전송 함수
# ==========================================
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"텔레그램 전송 에러: {e}")

# ==========================================
# 3. 볼린저 밴드 계산 및 조건 검사 로직
# ==========================================
def check_bollinger_bands():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S]')} 볼린저 밴드 하단 검사 시작...")
    
    # yfinance 주기 설정 (짧은 분봉은 최근 데이터만 조회 가능)
    period_map = {
        '5m': '5d',
        '15m': '5d',
        '30m': '7d',
        '1h': '60d',
        '1d': '1y'
    }

    report_messages = ["🚨 *다중 타임프레임 볼린저 밴드 하단 터치 알림* 🚨\n"]
    detected_count = 0

    for ticker in TICKERS:
        if not ticker.strip(): # 빈칸 슬롯 무시
            continue
            
        for interval in INTERVALS:
            try:
                period = period_map.get(interval, '1mo')
                df = yf.download(ticker, period=period, interval=interval, progress=False)
                
                if df.empty or len(df) < 25:
                    continue
                
                # MultiIndex 컬럼 처리 (yfinance 최신 버전 대응)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)

                # 볼린저 밴드 계산 (20일 기준, 2 표준편차)
                df['MA20'] = df['Close'].rolling(window=20).mean()
                df['STD'] = df['Close'].rolling(window=20).std()
                df['Upper'] = df['MA20'] + (df['STD'] * 2)
                df['Lower'] = df['MA20'] - (df['STD'] * 2)

                # 최신 봉 기준 하단 터치 또는 이탈 여부 확인
                latest = df.iloc[-1]
                close_price = float(latest['Close'])
                lower_band = float(latest['Lower'])

                if close_price <= lower_band:
                    detected_count += 1
                    msg = f"• *{ticker}* ({interval}): 종가 `${close_price:.2f}` (하단 밴드: `${lower_band:.2f}`)"
                    report_messages.append(msg)
            
            except Exception as e:
                # API 호출 제한이나 일시적 오류 패스
                continue
                
    if detected_count > 0:
        final_message = "\n".join(report_messages)
    else:
        final_message = f"📊 *볼린저 밴드 검사 완료* ({datetime.now().strftime('%m-%d %H:%M')})\n- 설정된 종목 중 조건에 부합하는 하단 터치 종목이 없습니다."

    send_telegram_message(final_message)
    print("검사 및 알림 전송 완료.")

# ==========================================
# 4. 스케줄러 구동 (한국 시간 기준 매일 오전 8시, 저녁 8시)
# ==========================================
def run_scheduler():
    # 한국 시간(KST) 매일 08:00, 20:00 지정
    schedule.every().day.at("08:00").do(check_bollinger_bands)
    schedule.every().day.at("20:00").do(check_bollinger_bands)

    print("🤖 볼린저 밴드 알람 봇 스케줄러가 시작되었습니다.")
    print("⏰ 실행 시간: 매일 오전 8:00, 저녁 8:00 (한국 시간)")
    
    # 테스트를 위해 실행 즉시 한번 검사하고 싶다면 아래 주석을 해제하세요.
    # check_bollinger_bands()

    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    run_scheduler()
