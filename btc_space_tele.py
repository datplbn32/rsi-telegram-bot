import requests
import pandas as pd
import ta
import time
from datetime import datetime

# === TELEGRAM CONFIG ===
TELEGRAM_TOKEN = '7793755516:AAEHGwFWd78LJtNDbJ2LE6_VZil3vsaegtk'
CHAT_ID = '-4619634301'

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': text}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"[LỖI GỬI TELEGRAM] {e}")

def fetch_ohlc(instId, interval, limit=100):
    url = 'https://www.okx.com/api/v5/market/candles'
    params = {'instId': instId, 'bar': interval, 'limit': limit}
    response = requests.get(url, params=params)
    data = response.json()
    if data['code'] != '0':
        raise Exception("Lỗi khi lấy dữ liệu nến từ OKX")

    df = pd.DataFrame(data['data'], columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'volCcy', 'volCcyQuote', 'confirm'
    ])
    df = df.iloc[::-1]
    df['close'] = df['close'].astype(float)
    return df

def calculate_rsi(df, period):
    return ta.momentum.RSIIndicator(df['close'], window=period).rsi()

def check_signals():
    try:
        # Dữ liệu đa khung
        df_5m = fetch_ohlc('BTC-USDT', '5m', 50)
        df_15m = fetch_ohlc('BTC-USDT', '15m', 50)
        df_1h = fetch_ohlc('BTC-USDT', '1H', 50)

        # Tính RSI các khung
        rsi6_5m = calculate_rsi(df_5m, 6)
        rsi12_5m = calculate_rsi(df_5m, 12)
        rsi6_15m = calculate_rsi(df_15m, 6)
        rsi12_15m = calculate_rsi(df_15m, 12)
        rsi1h = calculate_rsi(df_1h, 14).iloc[-1]

        # Lấy giá trị cuối cùng
        rsi6_5 = rsi6_5m.iloc[-1]
        rsi12_5 = rsi12_5m.iloc[-1]
        rsi6_15 = rsi6_15m.iloc[-1]
        rsi12_15_curr = rsi12_15m.iloc[-1]
        rsi12_15_prev = rsi12_15m.iloc[-2]

        # In log
        now = datetime.now().strftime('%H:%M:%S')
        print(f"[{now}] Kiểm tra tín hiệu...")
        print(f"RSI 1H: {rsi1h:.2f}")
        print(f"RSI 5m: 6={rsi6_5:.2f}, 12={rsi12_5:.2f}")
        print(f"RSI 15m: 6={rsi6_15:.2f}, 12={rsi12_15_curr:.2f} (trước: {rsi12_15_prev:.2f})")

        # === LONG ===
        cond_long_5m = rsi6_5 > rsi12_5 and rsi12_5 < 60
        cond_long_15m = (
            rsi12_15_curr < 40 and
            (rsi12_15_curr - rsi6_15 <= 10) and
            rsi12_15_curr > rsi12_15_prev
        )
        cond_long_trend = rsi1h > 50

        # === SHORT ===
        cond_short_5m = rsi6_5 < rsi12_5 and rsi12_5 > 40
        cond_short_15m = (
            rsi12_15_curr > 60 and
            (rsi6_15 - rsi12_15_curr <= 10) and
            rsi12_15_curr < rsi12_15_prev
        )
        cond_short_trend = rsi1h < 50

        # Gửi tín hiệu
        if cond_long_5m and cond_long_15m and cond_long_trend:
            msg = (
                f"📈 GỢI Ý LỆNH LONG:\n"
                f"RSI 5m: 6={rsi6_5:.2f}, 12={rsi12_5:.2f}\n"
                f"RSI 15m: 6={rsi6_15:.2f}, 12={rsi12_15_curr:.2f} (trước: {rsi12_15_prev:.2f})\n"
                f"RSI 1H: {rsi1h:.2f}"
            )
            send_telegram_message(msg)
            print("🚀 Đã gửi tín hiệu LONG.")

        elif cond_short_5m and cond_short_15m and cond_short_trend:
            msg = (
                f"📉 GỢI Ý LỆNH SHORT:\n"
                f"RSI 5m: 6={rsi6_5:.2f}, 12={rsi12_5:.2f}\n"
                f"RSI 15m: 6={rsi6_15:.2f}, 12={rsi12_15_curr:.2f} (trước: {rsi12_15_prev:.2f})\n"
                f"RSI 1H: {rsi1h:.2f}"
            )
            send_telegram_message(msg)
            print("📤 Đã gửi tín hiệu SHORT.")
        else:
            print("⛔ Không đủ điều kiện LONG hoặc SHORT.")

    except Exception as e:
        print(f"[LỖI] {e}")
        send_telegram_message(f"⚠️ LỖI XẢY RA: {e}")

def wait_until_next_15m():
    while True:
        now = datetime.now()
        if now.minute % 15 == 0 and now.second < 5:
            return
        time.sleep(1)

if __name__ == '__main__':
    print("🚀 Bot bắt đầu chạy — kiểm tra tín hiệu mỗi 15 phút.")
    while True:
        try:
            wait_until_next_15m()
            check_signals()
            time.sleep(60)
        except Exception as e:
            print(f"[LỖI CHÍNH] {e}")
            send_telegram_message(f"❌ LỖI HỆ THỐNG: {e}")
            time.sleep(60)
