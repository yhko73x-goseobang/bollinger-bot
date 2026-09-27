import streamlit as st
import pandas as pd
import yfinance as yf
import requests

# --- 페이지 설정 ---
st.set_page_config(page_title="30분봉 볼린저밴드 알리미", layout="centered")

st.title("📈 30분봉 볼린저밴드 하단 알리미")
st.markdown("지정된 대량의 관심 종목을 관리하고, 볼린저밴드 하단 터치 시 텔레그램으로 알림을 받아보세요.")

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
        return False

# --- 티커 변환 헬퍼 함수 (국내 주식 및 지수 대응) ---
def format_ticker(raw_ticker):
    t = raw_ticker.strip().upper()
    if not t:
        return ""
    # 해외 지수 및 미국 주식
    if t in ["US100", "NDX"]:
        return "^NDX"
    if t == "KOSPI":
        return "^KS11"
    if t == "KOSPI200":
        return "^KS200"
    # 국내 종목 코드 (6자리 숫자)
    if t.isdigit() and len(t) == 6:
        # 주요 코스피/코스닥 구분 (편의상 기본 .KS 적용, 필요시 .KQ 자동 매칭 가능)
        return f"{t}.KS"
    return t

# --- 메인 화면: 종목 관리 ---
st.header("🎯 관심 종목 설정 (기본 종목 + 빈칸 추가)")

# 요청하신 전체 기본 종목 리스트 (중복 제거 및 정리)
raw_default_tickers = [
    "US100", "KOSPI", "KOSPI200",
    "091160", "395270", "396500", "471760", "476260", "069500", "102110", "148020", "114800", "139230", 
    "465580", "487240", "139270", "139240", "117460", "139250", "229200", "266390", "266420", "453640", 
    "227560", "266410", "453630", "453660", "139290", "252670",
    "133690", "379810", "360750", "379800", "314250", "381180", "487230", "203780", "494840",
    "446720", "458730", "476550", "0238P0", "373590", "485230", "484120", "483320"
]

# 중복 제거
default_tickers = []
for t in raw_default_tickers:
    if t not in default_tickers:
        default_tickers.append(t)

# 파일 업로드로 종목 불러오기 (TXT)
uploaded_file = st.file_uploader("📂 저장해둔 종목 TXT 파일 업로드하기", type=["txt"])
if uploaded_file is not None:
    try:
        content = uploaded_file.read().decode("utf-8")
        loaded_tickers = [line.strip().upper() for line in content.splitlines() if line.strip()]
        if loaded_tickers:
            default_tickers = loaded_tickers
            st.success("TXT 파일에서 종목 리스트를 불러왔습니다!")
    except Exception as e:
        st.error(f"파일 읽기 실패: {e}")

# 기본 종목들 + 추가 10개의 빈칸을 합쳐서 총 리스트 구성
total_slots = len(default_tickers) + 10
extended_defaults = default_tickers + [""] * 10

st.info(f"총 {len(default_tickers)}개의 기본 종목과 여유분 빈칸 10개가 준비되어 있습니다. 아래에서 자유롭게 수정·추가하실 수 있습니다.")

user_tickers = []
col1, col2 = st.columns(2)

for i in range(1, total_slots + 1):
    with (col1 if i % 2 != 0 else col2):
        curr_val = extended_defaults[i-1]
        t_input = st.text_input(f"종목 {i}", value=curr_val, key=f"t_{i}")
        if t_input.strip():
            user_tickers.append(t_input.strip().upper())

# 현재 등록된 종목 리스트를 TXT 파일로 다운로드 버튼 제공
if user_tickers:
    txt_data = "\n".join(user_tickers)
    st.download_button(
        label="💾 현재 종목 리스트 TXT로 저장",
        data=txt_data,
        file_name="my_bollinger_tickers.txt",
        mime="text/plain"
    )

st.divider()

# --- 분석 및 알림 실행 로직 ---
if st.button("🚀 볼린저밴드 상태 검사 및 알림 보내기", type="primary"):
    if not user_tickers:
        st.warning("종목을 최소 1개 이상 입력해주세요.")
    else:
        results = []
        with st.spinner("30분봉 데이터를 수집하고 볼린저밴드를 계산 중입니다 (종목이 많아 수 초 소요될 수 있습니다)..."):
            for raw_t in user_tickers:
                ticker = format_ticker(raw_t)
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
                        "종목": raw_t,
                        "시간": t_stamp,
                        "종가": round(close_p, 2),
                        "하단밴드": round(lower_b, 2),
                        "상태": "🚨 하단 터치!" if is_touch else "정상"
                    })

                    # 터치한 경우 텔레그램으로 즉시 전송
                    if is_touch:
                        msg = f"[볼린저밴드 하단 터치 알림]\n- 종목: {raw_t}\n- 시간: {t_stamp}\n- 종가: {close_p:.2f}\n- 하단밴드: {lower_b:.2f}"
                        send_telegram(msg, token, chat_id)

                except Exception as e:
                    print(f"Error {raw_t}: {e}")

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
            st.warning("데이터를 가져오지 못했습니다. 종목 코드를 다시 확인해주세요.")
