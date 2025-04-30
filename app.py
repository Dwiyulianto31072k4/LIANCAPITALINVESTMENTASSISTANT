import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import re
import json

# -------- KONFIGURASI GOOGLE SHEET --------
SPREADSHEET_ID = "1g3XL1EllHoWV3jhmi7gT3at6MtCNTJBo8DQ1WyWhMEo"
SHEET_NAME = "Sheet1"  # atau nama sheet yang kamu pakai

# -------- KONEKSI GOOGLE SHEETS --------
@st.cache_resource
def connect_to_gsheet():
    # Hard-coded credentials untuk debugging
    service_account_info = {
        "type": "service_account",
        "project_id": "lian-408711",
        "private_key_id": "18cb4e8340e259d229873881d600e54447d8f76c",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC0pQ1Zu4hOHSIU\npR7kq63nfQGmO1kexzjEOuSXNPZ3/cSZzXKLX3F+YsHSnZOUErD/5PnKBDsUKvnH\nPInydGEtKLawZ6ipQ43eyIrYfmlEk1XowQqydyGlcnEHqWyWpvJWtcqfyoii6eSR\nV64Rs5kq6RZ1+ep4MseEZ5qu0f8QKrPfZYbt7WL+JxnN2IMETiao++5hceCazNEF\nxX7yk8lC1QwWTbJ54NgkCoQqsKGNHJLbH1EPl/Sb2QcnTDi5snC/FXA/GRFa0Xn+\nl+v0fJvBW0vTqRyWE0sWtDDjCpo6oYXl2sksuIMe0165od2bceUnc4NPAEQVwPzz\n480ctK4DAgMBAAECggEARa4K5cuEKtlq/Xqp3Xvpg0sBWV04JbqkB3FOHpND5QoC\njW8lmWQx85XlfLfiprHFC5gH0Chsn31qRrNv5JGGsHQtcAM0GEJiFYbWo+ay9Uw9\nzZ+04B064cYwmkt8guoXvWG3LIbjyK+exn+DOfnEgbxSOSSzEDVKJ6UNEhUXpWSj\naGfGJu9xMPc6eSiJviJ8NjIbOVV2JKN+J/AEtCssY6XrNXDqG1BKPERYIMjyD4bS\neUWPGGhKYyTE9kqsoZmciEoGFGFNYMs4T13z+x5e5aZ1Ro5f/8tSaAenwkEG71aq\n1RN549Yjlq/KOO3IA+cyOvHYkvgK0Dw6WUM5XW+k+QKBgQD8E52kZMpnt8w3OMGk\nuwHSmBklYRdCJBBXSNsEjQ1fZse4lvU0W7Y1GTUddZrCbXUX17dl3dwu2ynxjxDC\ngGKXI/wZ2I602lSIq49GM/A9BBSFQz9DUjph4X0WD5yaXK6bKIrMvHGFEpGnv424\nDwBZNzN/5mUa9Uq93cZYQ2CvaQKBgQC3dNH9qHz7Zv/gVduKoykx79bGjm5M9mNU\n4I4tFjqAqCJM2HcVzfqKCzUdlJ+P20Y5D8poeRkbqKlfLNyW/xXkooqlvBe9HZGT\nL1WOjldbMJD4Y0L93deP5CJxd2zK3/kkqDxI5xrMwzk8B8uehXLoRzKlUUciyN1k\nVTGtp0vwiwKBgQCgay9YjlgNF3fb8L+zQNuRFQBzvE0b522Kzq+rPsSy4OrbOx6D\nGpZjRk56F/zMHPJ2oO5y4nUcUJdpxd0pmqCjhOAL5rgyufswGtYMHEOX4P/aKwiY\npDzJS8HaB0dnKPJphayHTKmFwWJ2eb4L02gqXqnkjE/tjwrot7lhNEfUeQKBgHzs\nZK4ZFHpRCf5mGKhQMJYbnqH4jS2FPeCnRMl48H95flnbsUO8zlVACnxJH1pjU285\nzHfVtn46HJN9xfxgWTUmZckzyupxfxa9zcHUNbIX4S/yz8R1UvtduwKO8xs25r3K\nfbqa/IngilHRcRtR/gwjp14heZI7O16+EKUSXci/AoGBAKvnYSQItiH7+BCplEKS\nS6Pzh6aiV5pQbzGDcbIjhLqbueJ4OQAyOa+2clHBrGhJEnMjH/QfRiOVQ5pCaa4x\nWxJghzZCDVRLZaFJSrZVa0KVB9GYdupw1ycDIafvWEdOjmK//E+Oc4/fojtZJibU\noLjKPfRJ+rEtJO3xHqjfN12x\n-----END PRIVATE KEY-----\n",
        "client_email": "streamlit-writer-capitalinvest@lian-408711.iam.gserviceaccount.com",
        "client_id": "118403340754283074580",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/streamlit-writer-capitalinvest%40lian-408711.iam.gserviceaccount.com",
        "universe_domain": "googleapis.com"
    }
    
    credentials = Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    
    client = gspread.authorize(credentials)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    return sheet

# -------- PARSING FUNGSI DARI TEKS --------
def parse_trading_summary(text):
    date_match = re.search(r"📅\s*(.+?)\s+Daily", text)
    date = date_match.group(1) if date_match else "Unknown"

    total_signals = int(re.search(r"Total Signals:\s*(\d+)", text).group(1))
    tp = int(re.search(r"Take-Profits:\s*(\d+)", text).group(1))
    sl = int(re.search(r"Stop-Losses:\s*(\d+)", text).group(1))
    finished = tp + sl
    winrate = round((tp / finished) * 100, 2) if finished > 0 else 0

    return {
        "Date": date,
        "Total_Signal": total_signals,
        "Finished": finished,
        "TP": tp,
        "SL": sl,
        "Winrate_pct": winrate,
    }

# -------- STREAMLIT UI --------
st.title("📊 Rekapan Hasil Trading Harian")

input_text = st.text_area("Masukkan teks rekap sinyal trading:", height=300)

if input_text and st.button("🔍 Proses dan Hitung"):
    try:
        result = parse_trading_summary(input_text)
        comment = st.text_input("Comment (opsional):", placeholder="Contoh: Good momentum, banyak TP")
        result["Comment"] = comment

        st.subheader("📋 Hasil Parsing:")
        st.write(result)

        if st.button("📤 Upload ke Google Sheets"):
            try:
                sheet = connect_to_gsheet()
                sheet.append_row([
                    result["Date"],
                    result["Total_Signal"],
                    result["Finished"]
                    result["TP"],
                    result["SL"],
                    f"{result['Winrate_pct']}%",
                    result["Comment"]
                ])
                st.success("✅ Data berhasil ditambahkan ke Google Sheets!")
            except Exception as e:
                st.error(f"❌ Error saat mengupload ke Google Sheets: {str(e)}")
                st.info("Pastikan service account memiliki akses ke spreadsheet dan ID spreadsheet sudah benar.")
    except Exception as e:
        st.error(f"❌ Error saat memproses teks: {str(e)}")
        st.info("Pastikan format teks sesuai dengan yang diharapkan.")

# Tampilkan contoh format input
with st.expander("ℹ️ Contoh Format Input"):
    st.markdown("""
    ```
    📅 18 April 2025 Daily Trading Report
    
    Total Signals: 15
    Take-Profits: 10
    Stop-Losses: 3
    ```
    """)

# Menambahkan footer
st.markdown("---")
st.markdown("Made with ❤️ by Lian Capital")
