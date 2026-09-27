import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import requests

# ==========================================
# 페이지 설정 및 기본값
# ==========================================
st.set_page_config(page_title="볼린저 밴드 하단 알리미", layout="wide")

st.title("📊 다중 타임프레임 볼린저 밴드 하단 알리미")
st.markdown("설정된 종목과 타임프레임을 검사하여 텔레그램으로 실시간 알림을 보냅니다.")

# 사이드바 설정 (토큰 및 채팅 ID)
st.sidebar.header("🔑 텔레그램 설정")
bot_token = st.sidebar.text_input("Bot Token", value="8345013135:AAExhqYJmc2_zX1QRyGAmNoLgox7oPPU0hI")
chat_id = st.sidebar.text_input("Chat ID", value="6287856148")

# ==========================================
# 타임프레임 및 종목 정의
# ==========================================
st.sidebar.header("⏱️ 타임프레임 선택")
all_intervals = {
    '5분봉 (5m)': '5m',
    '15분봉 (15m)': '15m',
    '30분봉 (30m)': '30m',
    '1시간봉 (1h)': '1h',
    '4시간/일봉 (1d)': '1d'
}

selected_interval_labels = st.sidebar.multiselect(
    "검사할 시간대를 여러 개 선택하세요:",
    options=list(all_intervals.keys()),
    default=['5분봉 (5m)', '15분봉 (15m)', '30분봉 (30m)', '1시간봉 (1h)', '4시간/일봉 (1d)']
)
selected_intervals = [all_intervals[label] for label in selected_interval_labels]

# 요청하신 100개 기업 + 빈칸 20개 (총 120개 슬롯)
default_tickers = [
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
] + [""] * 20

st.subheader("📋 검사 대상 종목 리스트 (수정 가능)")
tickers_input = st.text_area(
    "종목 코드를 쉼표(,) 또는 줄바꿈으로 구분하여 입력하세요.",
    value=", ".join(default_tickers),
    height=150
)

# 입력받은 종목 정리 (빈칸 제거)
tickers = [t.strip().upper() for t in tickers_input.replace("\n", ",").split(",") if t.strip()]

# ==========================================
# 텔레그램 전송 함수
# ==========================================
def send_telegram_message(token, chat, message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        return {"ok": False, "description": str(e)}

# ==========================================
# 실행 버튼
# ==========================================
if st.button("🚀 볼린저 밴드 하단 검사 및 텔레그램 전송 실행", type="primary"):
    if not bot_token or not chat_id:
        st.error("텔레그램 Bot Token과 Chat ID를 입력해주세요.")
    elif not selected_intervals:
        st.error("최소 하나 이상의 타임프레임을 선택해주세요.")
    elif not tickers:
        st.error("검사할 종목이 없습니다.")
    else:
        with st.spinner("종목 데이터를 수집하고 볼린저 밴드를 계산 중입니다... 잠시만 기다려주세요."):
            period_map = {
                '5m': '5d',
                '15m': '5d',
                '30m': '7d',
                '1h': '60d',
                '1d': '1y'
            }

            report_messages = ["🚨 *다중 타임프레임 볼린저 밴드 하단 터치 알림* 🚨\n"]
            detected_count = 0
            progress_bar = st.progress(0)
            total_tasks = len(tickers) * len(selected_intervals)
            current_task = 0

            for ticker in tickers:
                for interval in selected_intervals:
                    current_task += 1
                    progress_bar.progress(current_task / total_tasks)
                    try:
                        period = period_map.get(interval, '1mo')
                        df = yf.download(ticker, period=period, interval=interval, progress=False)
                        
                        if df.empty or len(df) < 25:
                            continue
                        
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = df.columns.get_level_values(0)

                        # 볼린저 밴드 계산 (20일 기준, 2 표준편차)
                        df['MA20'] = df['Close'].rolling(window=20).mean()
                        df['STD'] = df['Close'].rolling(window=20).std()
                        df['Lower'] = df['MA20'] - (df['STD'] * 2)

                        latest = df.iloc[-1]
                        close_price = float(latest['Close'])
                        lower_band = float(latest['Lower'])

                        if close_price <= lower_band:
                            detected_count += 1
                            msg = f"• *{ticker}* ({interval}): 종가 `${close_price:.2f}` (하단: `${lower_band:.2f}`)"
                            report_messages.append(msg)
                    except Exception:
                        continue
            
            progress_bar.empty()

            if detected_count > 0:
                final_message = "\n".join(report_messages)
            else:
                final_message = f"📊 *볼린저 밴드 검사 완료* ({datetime.now().strftime('%m-%d %H:%M')})\n- 설정된 종목 중 조건에 부합하는 하단 터치 종목이 없습니다."

            # 텔레그램 전송
            res = send_telegram_message(bot_token, chat_id, final_message)
            
            if res.get("ok"):
                st.success(f"검사 완료! 조건에 맞는 종목 {detected_count}개를 텔레그램으로 성공적으로 전송했습니다.")
                st.markdown(final_message)
            else:
                st.error(f"텔레그램 전송 실패: {res.get('description')}")
