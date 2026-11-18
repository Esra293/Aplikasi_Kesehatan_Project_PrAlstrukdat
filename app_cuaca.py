import google.generativeai as genai
import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st

# Konfigurasi API Key Gemini
GEMINI_API_KEY = "AQ.Ab8RN6JA1qecb9xXn00G4kO9mJ-reFk17-XYd5ptxthhTK9MQw"
genai.configure(api_key=GEMINI_API_KEY)


# Fungsi untuk mengambil data cuaca dari API Open-Meteo
def get_weather_data(lat, lon, start_date, end_date):
  url = "https://archive-api.open-meteo.com/v1/era5"
  params = {
      "latitude": lat,
      "longitude": lon,
      "start_date": start_date,
      "end_date": end_date,
      "daily": "temperature_2m_max",
      "timezone": "Asia/Jakarta",
  }
  response = requests.get(url, params=params)
  data = response.json()

  df = pd.DataFrame({
      "Tanggal": data["daily"]["time"],
      "Suhu Maksimum (°C)": data["daily"]["temperature_2m_max"],
  })
  return df


# Fungsi untuk mengirim data DataFrame ke Gemini AI dan meminta analisis
def analyze_weather_with_gemini(df):
  # Ubah data tabel ke bentuk teks string agar bisa dibaca model AI
  text_data = df.to_string(index=False)

  prompt = f"""
    Berikut data suhu maksimum harian selama periode pengamatan:
    {text_data}
    
    Buat analisis tren suhu dan prediksi kondisi suhu 7 hari ke depan.
    Jawab dalam format JSON dengan field:
    - tren (naik/turun/stabil)
    - prediksi (ringkasan singkat)
    - alasan (penjelasan)
    """

  # Menggunakan model Gemini Flash
  model = genai.GenerativeModel("models/gemini-3.8-flash")
  response = model.generate_content(prompt)
  return response.text


# ==========================================
# ANTARMUKA STREAMLIT (UI)
# ==========================================
st.title("Prediksi Tren Cuaca dengan Gemini AI")
st.markdown(
    "Aplikasi ini mengambil data cuaca dari [Open-Meteo](https://open-meteo.com)"
    " dan mengirimkannya ke **Gemini AI** untuk mendapatkan analisis tren dan"
    " prediksi suhu."
)

# Input Parameter dari Pengguna
city = st.text_input("Kota", "Yogyakarta")
lat = st.number_input("Latitude", value=-7.7972, format="%.4f")
lon = st.number_input("Longitude", value=110.3688, format="%.4f")
start_date = st.date_input("Tanggal Mulai", pd.to_datetime("2025-09-24"))
end_date = st.date_input("Tanggal Akhir", pd.to_datetime("2025-10-24"))

if st.button("Ambil dan Analisis Data"):
  # 1. Ambil data cuaca
  with st.spinner("Mengambil data cuaca..."):
    df = get_weather_data(lat, lon, start_date, end_date)
    st.success("Data berhasil diambil!")
    st.dataframe(df)

  # 2. Visualisasi data dengan Matplotlib
  st.subheader("Grafik Suhu Harian")
  fig, ax = plt.subplots()
  ax.plot(df["Tanggal"], df["Suhu Maksimum (°C)"], marker="o")
  ax.set_xlabel("Tanggal")
  ax.set_ylabel("Suhu Maksimum (°C)")
  ax.set_title(f"Pergerakan Suhu Harian di {city}")
  plt.xticks(rotation=45)
  st.pyplot(fig)

  # 3. Kirim data ke Gemini AI untuk analisis
  with st.spinner("Mengirim data ke Gemini AI..."):
    result = analyze_weather_with_gemini(df)
    st.subheader("Hasil Analisis AI")
    st.write(result)