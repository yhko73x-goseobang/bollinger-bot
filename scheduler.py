import pandas as pd
import yfinance as yf
import requests

# 기본 내장된 텔레그램 정보
TOKEN = "8345013135:AAExhqYJmc2_zX1QRyGAmNoLgox7oPPU0hI"
CHAT_ID = "6287856148"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": msg})
    except Exception as e:
        print(f"텔레그램 전송 에러: {e}")

def format_ticker(raw_ticker):
    t = raw_ticker.strip().upper()
    if not t:
        return ""
    if t in ["US100", "NDX"]:
        return "^NDX"
    if t == "KOSPI":
        return "^KS11"
    if t == "KOSPI200":
        return "^KS200"
    if t.isdigit() and len(t) == 6:
        return f"{t}.KS"
    return t

# 자동 검사할 전체 종목 리스트
tickers_to_check = [
    "US100", "KOSPI", "KOSPI200",
    "091160", "395270", "396500", "471760", "476260", "069500", "102110", "148020", "114800", "139230", 
    "465580", "487240", "139270", "139240", "117460", "139250", "229200", "266390", "266420", "453640", 
    "227560", "266410", "453630", "453660", "139290", "252670",
    "133690", "379810", "360750", "379800", "314250", "381180", "487230", "203780", "494840",
    "446720", "458730", "476550", "0238P0", "373590", "485230", "484120", "483320"
]

print("볼린저밴드 자동 스케줄러 실행 중...")
touched_list = []

for raw_t in tickers_to_check:
    ticker = format_ticker(raw_t)
    try:
        df = yf.download(ticker, period="5d", interval="30m", progress=False)
        if df.empty or len(df) < 20:
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)

        df['MA20'] = df['Close'].rolling(window=20).mean()
        df['Std'] = df['Close'].rolling(window=20).std()
        df['Lower'] = df['MA20'] - (2 * df['Std'])

        latest = df.iloc[-2]
        close_p = float(latest['Close'])
        lower_b = float(latest['Lower'])
        t_stamp = str(df.index[-2])

        if close_p <= lower_b:
            touched_list.append(f"- 종목: {raw_t} (종가: {close_p:.2f} / 하단: {lower_b:.2f})")
    except Exception as e:
        print(f"Error {raw_t}: {e}")

# 터치한 종목이 있다면 텔레그램으로 일괄 알림 전송
if touched_list:
    alert_msg = "🚨 [자동 알림] 30분봉 볼린저밴드 하단 터치 종목 발생!\n" + "\n".join(touched_list)
    send_telegram(alert_msg)
    print("알림 전송 완료")
else:
    print("조건 만족 종목 없음")
