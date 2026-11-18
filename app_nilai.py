import io
import json
import re
import google.generativeai as genai
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

# Konfigurasi API Key Gemini
GEMINI_API_KEY = "MASUKKAN_API_KEY_KAMU_DI_SINI"
genai.configure(api_key=GEMINI_API_KEY)

st.title("Analisis Nilai Mahasiswa Menggunakan Gemini AI (JSON Version)")

# Widget untuk mengunggah file CSV
uploaded_file = st.file_uploader(
    "Upload file CSV data nilai mahasiswa", type=["csv"]
)

if uploaded_file is not None:
  # 1. Membaca data CSV dengan pandas
  df = pd.read_csv(uploaded_file)
  st.write("Data Nilai Mahasiswa:")
  st.dataframe(df.head())

  # 2. Simpan file sementara agar bisa diunggah ke Gemini
  temp_path = "uploaded.csv"
  df.to_csv(temp_path, index=False)

  # 3. Upload file ke sistem Gemini dengan MIME type text/csv
  uploaded_to_gemini = genai.upload_file(temp_path, mime_type="text/csv")

  # 4. Menyiapkan Prompt terstruktur
  prompt = """
    Analisis data nilai mahasiswa yang telah diupload.
    1. Hitung nilai maksimum, minimum, dan rata-rata.
    2. Temukan pola menarik dari distribusi nilai.
    3. Berikan observasi tentang performa kelas.
    4. Berikan rekomendasi untuk meningkatkan performa kelas.
    5. Kirimkan hasil analisis dalam format JSON valid.
    6. Jangan berikan teks atau penjelasan tambahan di luar JSON.
    
    Contoh format output:
    {
      "maksimum": 95,
      "minimum": 45,
      "rata_rata": 72.5,
      "pola": "Sebagian besar nilai berada di kisaran 60-80",
      "observasi": "Performa kelas cukup baik dengan beberapa siswa berprestasi tinggi",
      "rekomendasi": "Fokus pada siswa dengan nilai di bawah rata-rata untuk peningkatan"
    }
    """

  # 5. Mengirim data dan prompt ke Gemini AI
  with st.spinner(
      "Sedang mengirim data ke Gemini dan menunggu hasil analisis..."
  ):
    # Menggunakan model flash terbaru
    model = genai.GenerativeModel("models/gemini-3.8-flash")
    response = model.generate_content([prompt, uploaded_to_gemini])

  # 6. Membersihkan respons agar hanya mengambil bagian JSON dengan regex
  raw_text = response.text.strip()
  json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
  json_text = json_match.group(0) if json_match else raw_text

  try:
    # Parsing teks JSON menjadi Dictionary Python
    hasil = json.loads(json_text)

    st.subheader("Hasil Analisis Nilai Mahasiswa")
    col1, col2, col3 = st.columns(3)
    with col1:
      st.metric("Nilai Maksimum", hasil["maksimum"])
    with col2:
      st.metric("Nilai Minimum", hasil["minimum"])
    with col3:
      st.metric("Nilai Rata-rata", hasil["rata_rata"])

    st.write(f"**Pola:** {hasil['pola']}")
    st.write(f"**Observasi:** {hasil['observasi']}")
    st.write(f"**Rekomendasi:** {hasil['rekomendasi']}")

    # 7. Membuat Grafik Distribusi Nilai (Histogram)
    st.subheader("Grafik Distribusi Nilai Mahasiswa")
    fig, ax = plt.subplots()
    ax.hist(df["Nilai"], bins=10, edgecolor="black")
    ax.set_xlabel("Rentang Nilai")
    ax.set_ylabel("Jumlah Mahasiswa")
    ax.set_title("Distribusi Nilai Mahasiswa")
    st.pyplot(fig)

  except json.JSONDecodeError:
    st.error("Gagal membaca hasil JSON dari Gemini. Format tidak valid.")
    st.write("Respons mentah dari AI:", raw_text)
  except Exception as e:
    st.error(f"Terjadi kesalahan: {e}")

else:
  st.info("Silakan unggah file CSV terlebih dahulu.")