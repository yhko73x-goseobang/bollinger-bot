import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import json

# --- 페이지 설정 ---
st.set_page_config(page_title="30분봉 볼린저밴드 알리미", layout="centered")

st.title("📈 30분봉 볼린저밴드 하단 알리미")
st.markdown("관심 종목 10개를 관리하고, 볼린저밴드 하단 터치 시 텔레그램으로 알림을 받아보세요.")

# --- 사이드바: 텔레그램 설정 ---
st.sidebar.header("🔔 텔레그램 연동 설정")
token = st.sidebar.text_input("Bot Token", type="password")
chat_id = st.sidebar.text_input("Chat ID")

def send_telegram(msg, t, c):
    if not t or not c:
        return False
    url = f"https://api.telegram.org/bot{t}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": c, "text": msg})
        return res.ok
    except:
        return false

# --- 메인 화면: 종목 관리 (TXT 파일 입출력 및 직접 입력) ---
st.header("🎯 관심 종목 설정 (10개)")

# 기본 샘플 종목 10개
default_tickers = ["AAPL", "TSLA", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "NFLX", "AMD", "INTC"]

# 파일 업로드로 종목 불러오기 (TXT)
uploaded_file = st.file_uploader("📂 저장해둔 종목 TXT 파일 업로드하기", type=["txt"])
if uploaded_file is not None:
    try:
        content = uploaded_file.read().decode("utf-8")
        loaded_tickers = [line.strip().upper() for line in content.splitlines() if line.strip()]
        if loaded_tickers:
            default_tickers = loaded_tickers[:10]  # 최대 10개
            st.success("TXT 파일에서 종목을 불러왔습니다!")
    except Exception as e:
        st.error(f"파일 읽기 실패: {e}")

# 10개 입력창 구성
user_tickers = []
col1, col2 = st.columns(2)
for i in range(1, 11):
    with (col1 if i <= 5 else col2):
        curr_val = default_tickers[i-1] if i-1 < len(default_tickers) else ""
        t_input = st.text_input(f"종목 {i}", value=curr_val, key=f"t_{i}")
        if t_input.strip():
            user_tickers.append(t_input.strip().upper())

# 현재 종목을 TXT 파일로 다운로드 버튼 제공
if user_tickers:
    txt_data = "\n".join(user_tickers)
    st.download_button(
        label="💾 현재 종목 리스트 TXT로 저장",
        data=txt_data,
        file_name="my_tickers.txt",
        mime="text/plain"
    )

st.divider()

# --- 분석 및 알림 실행 로직 ---
if st.button("🚀 볼린저밴드 상태 검사 및 알림 보내기", type="primary"):
    if not user_tickers:
        st.warning("종목을 최소 1개 이상 입력해주세요.")
    else:
        results = []
        with st.spinner("30분봉 데이터를 수집하고 볼린저밴드를 계산 중입니다..."):
            for ticker in user_tickers:
                try:
                    df = yf.download(ticker, period="5d", interval="30m", progress=False)
                    if df.empty or len(df) < 20:
                        continue
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = df.columns.droplevel(1)

                    # 볼린저 밴드 계산 (20, 2)
                    df['MA20'] = df['Close'].rolling(window=20).mean()
                    df['Std'] = df['Close'].rolling(window=20).std()
                    df['Lower'] = df['MA20'] - (2 * df['Std'])

                    latest = df.iloc[-2]
                    close_p = float(latest['Close'])
                    lower_b = float(latest['Lower'])
                    t_stamp = str(df.index[-2])

                    is_touch = close_p <= lower_b

                    results.append({
                        "종목": ticker,
                        "시간": t_stamp,
                        "종가": round(close_p, 2),
                        "하단밴드": round(lower_b, 2),
                        "상태": "🚨 하단 터치!" if is_touch else "정상"
                    })

                    # 터치한 경우 텔레그램으로 즉시 전송
                    if is_touch:
                        msg = f"[볼린저밴드 하단 터치 알림]\n- 종목: {ticker}\n- 시간: {t_stamp}\n- 종가: {close_p:.2f}\n- 하단밴드: {lower_b:.2f}"
                        send_telegram(msg, token, chat_id)

                except Exception as e:
                    print(f"Error {ticker}: {e}")

        if results:
            res_df = pd.DataFrame(results)
            st.success("검사 완료!")
            st.dataframe(res_df, use_container_width=True)
            
            touched_count = len(res_df[res_df["상태"].str.contains("터치")])
            if touched_count > 0:
                st.error(f"⚠️ 총 {touched_count}개 종목이 하단에 닿아 텔레그램 전송을 완료했습니다!")
            else:
                st.info("현재 하단에 닿은 종목이 없습니다.")
        else:
            st.warning("데이터를 가져오지 못했습니다. 종목 티커를 확인해주세요.")
