import json
import re
import google.generativeai as genai
import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st

# ==========================================
# KONFIGURASI AWAL & GEMINI API
# ==========================================
GEMINI_API_KEY = "AQ.Ab8RN6L9zZi_PRY7_AdfKbZMKyv3p0C82qzN0Bs5PZ0evgIOwg"
if GEMINI_API_KEY and GEMINI_API_KEY != "MASUKKAN_API_KEY_KAMU_DI_SINI":
  genai.configure(api_key=GEMINI_API_KEY)

st.set_page_config(page_title="SehatKu - Aplikasi Kesehatan", layout="wide")

DATA_AWAL = [
    {
        "Tanggal": "2026-11-17",
        "Berat_Kg": 62.2,
        "Tinggi_Cm": 170.0,
        "Tidur_Jam": 6.5,
        "Catatan": "Latihan fisik ringan",
        "Kondisi": "Cukup",
    },
    {
        "Tanggal": "2026-11-18",
        "Berat_Kg": 62.1,
        "Tinggi_Cm": 170.0,
        "Tidur_Jam": 7.0,
        "Catatan": "Tidur cukup dan terhidrasi",
        "Kondisi": "Baik",
    },
    {
        "Tanggal": "2026-11-19",
        "Berat_Kg": 62.3,
        "Tinggi_Cm": 170.0,
        "Tidur_Jam": 6.8,
        "Catatan": "Kuliah dan aktivitas padat",
        "Kondisi": "Cukup",
    },
    {
        "Tanggal": "2026-11-20",
        "Berat_Kg": 62.1,
        "Tinggi_Cm": 170.0,
        "Tidur_Jam": 7.0,
        "Catatan": "Olahraga ringan",
        "Kondisi": "Baik",
    },
    {
        "Tanggal": "2026-11-21",
        "Berat_Kg": 62.3,
        "Tinggi_Cm": 170.0,
        "Tidur_Jam": 6.0,
        "Catatan": "Sakit kepala ringan",
        "Kondisi": "Cukup",
    },
    {
        "Tanggal": "2026-11-22",
        "Berat_Kg": 62.0,
        "Tinggi_Cm": 170.0,
        "Tidur_Jam": 7.5,
        "Catatan": "Lari pagi 30 menit",
        "Kondisi": "Baik",
    },
    {
        "Tanggal": "2026-11-23",
        "Berat_Kg": 62.0,
        "Tinggi_Cm": 170.0,
        "Tidur_Jam": 7.5,
        "Catatan": "Pemulihan dan istirahat cukup",
        "Kondisi": "Baik",
    },
]

LOKASI_KOORDINAT = {
    "Yogyakarta": (-7.7972, 110.3688),
    "Jakarta": (-6.2088, 106.8456),
    "Surabaya": (-7.2575, 112.7521),
    "Bandung": (-6.9175, 107.6191),
}

# Inisialisasi state aplikasi (List of Dict sebagai Stack riwayat)
if "catatan_kesehatan" not in st.session_state:
  st.session_state["catatan_kesehatan"] = list(DATA_AWAL)

if "hasil_ai" not in st.session_state:
  st.session_state["hasil_ai"] = None

if "halaman_aktif" not in st.session_state:
  st.session_state["halaman_aktif"] = "Dashboard Utama"


# ==========================================
# FUNGSI BANTUAN, STRUKTUR DATA & ALGORITMA
# ==========================================
def ambil_cuaca_terkini(lat, lon):
  url = "https://api.open-meteo.com/v1/forecast"
  params = {
      "latitude": lat,
      "longitude": lon,
      "current": "temperature_2m",
      "timezone": "Asia/Jakarta",
  }
  resp = requests.get(url, params=params, timeout=10)
  resp.raise_for_status()
  return float(resp.json()["current"]["temperature_2m"])


def tentukan_kondisi_otomatis(tidur_jam, catatan_teks):
  teks_kecil = catatan_teks.lower()
  if "sakit" in teks_kecil or "pusing" in teks_kecil or "nyeri" in teks_kecil:
    return "Perlu Perhatian"
  if tidur_jam >= 7.0:
    return "Baik"
  if tidur_jam >= 5.5:
    return "Cukup"
  return "Buruk"


def cari_catatan(daftar_data, kata_kunci):
  """Algoritma linear search berdasarkan tanggal, catatan, atau kondisi."""
  kunci = kata_kunci.strip().lower()
  if not kunci:
    return list(daftar_data)

  hasil = []
  for item in daftar_data:
    cocok_tanggal = kunci in str(item.get("Tanggal", "")).lower()
    cocok_catatan = kunci in str(item.get("Catatan", "")).lower()
    cocok_kondisi = kunci in str(item.get("Kondisi", "")).lower()
    if cocok_tanggal or cocok_catatan or cocok_kondisi:
      hasil.append(item)
  return hasil


def urutkan_catatan(daftar_data, kriteria):
  """Algoritma sorting data catatan kesehatan sesuai pilihan pengguna."""
  salinan = list(daftar_data)
  if kriteria == "Tanggal Terbaru":
    salinan.sort(key=lambda x: str(x.get("Tanggal", "")), reverse=True)
  elif kriteria == "Tanggal Terlama":
    salinan.sort(key=lambda x: str(x.get("Tanggal", "")), reverse=False)
  elif kriteria == "Berat Badan Tertinggi":
    salinan.sort(key=lambda x: float(x.get("Berat_Kg", 0)), reverse=True)
  elif kriteria == "Berat Badan Terendah":
    salinan.sort(key=lambda x: float(x.get("Berat_Kg", 0)), reverse=False)
  elif kriteria == "Durasi Tidur Tertinggi":
    salinan.sort(key=lambda x: float(x.get("Tidur_Jam", 0)), reverse=True)
  elif kriteria == "Durasi Tidur Terendah":
    salinan.sort(key=lambda x: float(x.get("Tidur_Jam", 0)), reverse=False)
  return salinan


def analisis_kesehatan_gemini(df_rentang, kota_nama, suhu_info):
  if not GEMINI_API_KEY or GEMINI_API_KEY == "MASUKKAN_API_KEY_KAMU_DI_SINI":
    raise ValueError("API Key Gemini belum diisi pada variabel GEMINI_API_KEY.")

  ringkasan_teks = df_rentang.to_string(index=False)
  prompt = f"""
    Anda adalah asisten analisis kesehatan gaya hidup.
    Analisis data catatan kesehatan harian pengguna berikut:
    Lokasi pemantauan: {kota_nama} (Informasi suhu saat ini: {suhu_info})

    {ringkasan_teks}

    Berikan hasil analisis dalam format JSON valid saja (tanpa teks tambahan di luar JSON) dengan struktur:
    {{
      "status_singkat": "Stabil / Cukup Baik / Perlu Perhatian",
      "tren": "ringkasan 1-2 kalimat mengenai tren berat badan dan durasi tidur",
      "observasi": [
        "poin observasi 1 berdasarkan data dan cuaca",
        "poin observasi 2 berdasarkan data dan cuaca"
      ],
      "rekomendasi": [
        "rekomendasi gaya hidup praktis 1",
        "rekomendasi gaya hidup praktis 2",
        "rekomendasi gaya hidup praktis 3"
      ]
    }}
    """
  model = genai.GenerativeModel("models/gemini-3.8-flash")
  respons = model.generate_content(prompt)
  teks_mentah = respons.text.strip()
  pencocokan = re.search(r"\{.*\}", teks_mentah, re.DOTALL)
  teks_json = pencocokan.group(0) if pencocokan else teks_mentah
  return json.loads(teks_json)


# ==========================================
# SIDEBAR NAVIGASI
# ==========================================
st.sidebar.title("SehatKu")
daftar_halaman = [
    "Dashboard Utama",
    "Input & Riwayat Data",
    "Analisis AI & Laporan",
]
menu = st.sidebar.radio(
    "Navigasi",
    daftar_halaman,
    index=daftar_halaman.index(st.session_state["halaman_aktif"]),
)
st.session_state["halaman_aktif"] = menu

kota = st.sidebar.selectbox("Kota / lokasi cuaca", list(LOKASI_KOORDINAT.keys()))
lat, lon = LOKASI_KOORDINAT[kota]
try:
  suhu_sekarang = ambil_cuaca_terkini(lat, lon)
  label_suhu = f"{suhu_sekarang:.1f}°C"
except Exception:
  suhu_sekarang = 29.0
  label_suhu = "29.0°C"

df_utama = pd.DataFrame(st.session_state["catatan_kesehatan"])


# ==========================================
# HALAMAN 1: DASHBOARD UTAMA
# ==========================================
if menu == "Dashboard Utama":
  st.title("Dashboard Kesehatan Pribadi")
  st.caption(
      "Pantau berat badan, tidur, dan kondisi lingkungan Anda dalam satu"
      " tampilan."
  )

  if df_utama.empty:
    st.warning(
        "Belum ada catatan kesehatan tersimpan. Silakan tambahkan data di menu"
        " **Input & Riwayat Data**."
    )
  else:
    berat_terakhir = float(df_utama["Berat_Kg"].iloc[-1])
    tinggi_m = float(df_utama["Tinggi_Cm"].iloc[-1]) / 100.0
    imt = berat_terakhir / (tinggi_m**2) if tinggi_m > 0 else 0.0
    rata_tidur = float(df_utama["Tidur_Jam"].mean())
    total_catatan = len(df_utama)

    if imt < 18.5:
      status_imt = "Kurus"
    elif imt < 25.0:
      status_imt = "Normal"
    elif imt < 30.0:
      status_imt = "Gemuk"
    else:
      status_imt = "Obesitas"

    status_tidur = "Cukup" if rata_tidur >= 7.0 else "Kurang"

    c1, c2, c3, c4 = st.columns(4)
    with c1:
      st.metric("Indeks Massa Tubuh (IMT)", f"{imt:.1f}", status_imt)
    with c2:
      st.metric("Rata-rata Durasi Tidur", f"{rata_tidur:.1f} Jam", status_tidur)
    with c3:
      st.metric(
          "Total Catatan Tersimpan", f"{total_catatan} Hari", "Tersimpan"
      )
    with c4:
      st.metric("Suhu Lingkungan Saat Ini", label_suhu, kota)

    st.divider()

    g1, g2 = st.columns(2)

    with g1:
      st.subheader("Tren Berat Badan Harian")
      fig1, ax1 = plt.subplots()
      ax1.plot(
          df_utama["Tanggal"],
          df_utama["Berat_Kg"],
          marker="o",
          color="#0f766e",
      )
      ax1.set_xlabel("Tanggal")
      ax1.set_ylabel("Berat Badan (kg)")
      ax1.tick_params(axis="x", rotation=35)
      st.pyplot(fig1)

    with g2:
      st.subheader("Distribusi Kategori Kondisi Kesehatan")
      urutan_kondisi = ["Baik", "Cukup", "Perlu Perhatian", "Buruk"]
      jumlah_kondisi = [
          int((df_utama["Kondisi"] == k).sum()) for k in urutan_kondisi
      ]
      fig2, ax2 = plt.subplots()
      ax2.bar(urutan_kondisi, jumlah_kondisi, color="#0f766e")
      ax2.set_xlabel("Kategori Kondisi")
      ax2.set_ylabel("Jumlah Hari")
      st.pyplot(fig2)

    st.divider()
    col_info, col_btn = st.columns([4, 1])
    with col_info:
      ringkasan_ai = (
          st.session_state["hasil_ai"]["tren"]
          if st.session_state["hasil_ai"]
          else (
              f"Berat badan terkini {berat_terakhir:.1f} kg dan rata-rata"
              f" tidur {rata_tidur:.1f} jam/hari."
          )
      )
      st.success(f"**Status kesehatan terkini: Terpantau** — {ringkasan_ai}")
    with col_btn:
      if st.button("Lihat Analisis Lengkap", use_container_width=True):
        st.session_state["halaman_aktif"] = "Analisis AI & Laporan"
        st.rerun()


# ==========================================
# HALAMAN 2: INPUT & RIWAYAT DATA
# ==========================================
elif menu == "Input & Riwayat Data":
  st.title("Input & Riwayat Data")
  st.caption(
      "Tambahkan catatan baru, unggah berkas CSV, kelola stack riwayat, serta"
      " cari atau urutkan data."
  )

  # Kontrol Stack (LIFO) di sidebar
  st.sidebar.divider()
  st.sidebar.subheader("Riwayat (Stack)")
  st.sidebar.metric("Jumlah Item Stack", len(st.session_state["catatan_kesehatan"]))
  if st.sidebar.button(
      "Undo Catatan Terakhir (Stack Pop)", use_container_width=True
  ):
    if st.session_state["catatan_kesehatan"]:
      item_terhapus = st.session_state["catatan_kesehatan"].pop()
      st.sidebar.success(
          f"Dihapus (Pop): {item_terhapus.get('Tanggal', '-')} -"
          f" {item_terhapus.get('Catatan', '-')}"
      )
      st.rerun()
    else:
      st.sidebar.warning("Stack riwayat sudah kosong.")

  tab_manual, tab_csv = st.tabs(["Input Manual", "Unggah File CSV"])

  with tab_manual:
    with st.form("form_input_kesehatan", clear_on_submit=True):
      f1, f2, f3, f4 = st.columns(4)
      with f1:
        tgl_input = st.date_input("Tanggal", value=pd.to_datetime("2026-11-24"))
      with f2:
        berat_input = st.number_input(
            "Berat Badan (kg)",
            min_value=20.0,
            max_value=250.0,
            value=62.0,
            step=0.1,
        )
      with f3:
        tinggi_input = st.number_input(
            "Tinggi Badan (cm)",
            min_value=100.0,
            max_value=250.0,
            value=170.0,
            step=0.5,
        )
      with f4:
        tidur_input = st.number_input(
            "Durasi Tidur (jam)",
            min_value=0.0,
            max_value=24.0,
            value=7.0,
            step=0.5,
        )

      catatan_input = st.text_input(
          "Catatan Aktivitas / Keluhan", placeholder="Contoh: Lari pagi 30 menit"
      )
      simpan_btn = st.form_submit_button("Simpan Catatan", type="primary")

      if simpan_btn:
        teks_catatan = (
            catatan_input.strip() if catatan_input.strip() else "Catatan harian"
        )
        kondisi_otomatis = tentukan_kondisi_otomatis(tidur_input, teks_catatan)
        data_baru = {
            "Tanggal": str(tgl_input),
            "Berat_Kg": float(berat_input),
            "Tinggi_Cm": float(tinggi_input),
            "Tidur_Jam": float(tidur_input),
            "Catatan": teks_catatan,
            "Kondisi": kondisi_otomatis,
        }
        st.session_state["catatan_kesehatan"].append(data_baru)
        st.success("Catatan berhasil ditambahkan ke stack riwayat.")
        st.rerun()

  with tab_csv:
    st.write(
        "Unggah file `.csv` dengan kolom: `Tanggal`, `Berat_Kg`, `Tinggi_Cm`,"
        " `Tidur_Jam`, `Catatan`, dan `Kondisi` (opsional)."
    )
    file_csv = st.file_uploader("Pilih file CSV", type=["csv"])
    if file_csv is not None:
      df_upload = pd.read_csv(file_csv)
      st.dataframe(df_upload.head(), use_container_width=True)
      if st.button("Masukkan Data CSV ke Riwayat", type="primary"):
        kolom_wajib = {"Tanggal", "Berat_Kg", "Tinggi_Cm", "Tidur_Jam"}
        if not kolom_wajib.issubset(set(df_upload.columns)):
          st.error(
              "Kolom wajib belum lengkap. Pastikan ada: Tanggal, Berat_Kg,"
              " Tinggi_Cm, Tidur_Jam."
          )
        else:
          for _, row in df_upload.iterrows():
            cat_teks = (
                str(row["Catatan"])
                if "Catatan" in df_upload.columns and pd.notna(row["Catatan"])
                else "Impor CSV"
            )
            kond_teks = (
                str(row["Kondisi"])
                if "Kondisi" in df_upload.columns and pd.notna(row["Kondisi"])
                else tentukan_kondisi_otomatis(float(row["Tidur_Jam"]), cat_teks)
            )
            st.session_state["catatan_kesehatan"].append({
                "Tanggal": str(row["Tanggal"]),
                "Berat_Kg": float(row["Berat_Kg"]),
                "Tinggi_Cm": float(row["Tinggi_Cm"]),
                "Tidur_Jam": float(row["Tidur_Jam"]),
                "Catatan": cat_teks,
                "Kondisi": kond_teks,
            })
          st.success(f"{len(df_upload)} baris data CSV berhasil ditambahkan.")
          st.rerun()

  st.divider()
  st.subheader("Riwayat Catatan Kesehatan")

  # Pencarian (Searching) & Pengurutan (Sorting)
  s1, s2 = st.columns([2, 1])
  with s1:
    kata_cari = st.text_input(
        "Cari catatan berdasarkan tanggal atau kata kunci",
        placeholder="Ketik tanggal (2026-11-22), keluhan, atau kondisi...",
    )
  with s2:
    opsi_urut = st.selectbox(
        "Urutkan berdasarkan",
        [
            "Tanggal Terbaru",
            "Tanggal Terlama",
            "Berat Badan Tertinggi",
            "Berat Badan Terendah",
            "Durasi Tidur Tertinggi",
            "Durasi Tidur Terendah",
        ],
    )

  hasil_cari = cari_catatan(st.session_state["catatan_kesehatan"], kata_cari)
  hasil_akhir = urutkan_catatan(hasil_cari, opsi_urut)

  st.caption(f"Menampilkan {len(hasil_akhir)} catatan.")
  if hasil_akhir:
    st.dataframe(pd.DataFrame(hasil_akhir), use_container_width=True)
  else:
    st.info("Tidak ada catatan yang cocok dengan pencarian.")


# ==========================================
# HALAMAN 3: ANALISIS AI & LAPORAN
# ==========================================
else:
  st.title("Analisis AI & Laporan")
  st.caption(
      "Dapatkan ringkasan kondisi dan saran gaya hidup berbasis Gemini AI,"
      " lalu unduh laporan."
  )

  if df_utama.empty:
    st.warning(
        "Data riwayat masih kosong. Tambahkan data terlebih dahulu di halaman"
        " **Input & Riwayat Data**."
    )
  else:
    df_tgl = df_utama.copy()
    df_tgl["Tgl_Dt"] = pd.to_datetime(df_tgl["Tanggal"], errors="coerce")
    tgl_min = df_tgl["Tgl_Dt"].min().date()
    tgl_max = df_tgl["Tgl_Dt"].max().date()

    st.sidebar.divider()
    st.sidebar.subheader("Rentang tanggal analisis")
    tgl_awal = st.sidebar.date_input("Dari tanggal", value=tgl_min)
    tgl_akhir = st.sidebar.date_input("Sampai tanggal", value=tgl_max)

    mask = (df_tgl["Tgl_Dt"].dt.date >= tgl_awal) & (
        df_tgl["Tgl_Dt"].dt.date <= tgl_akhir
    )
    df_terfilter = df_tgl.loc[mask].drop(columns=["Tgl_Dt"])

    if df_terfilter.empty:
      df_terfilter = df_utama.copy()

    col_ket, col_aksi = st.columns([3, 1])
    with col_ket:
      st.write(
          f"Rentang data terpilih: **{len(df_terfilter)} catatan** di lokasi"
          f" **{kota}** ({label_suhu})."
      )
    with col_aksi:
      klik_analisis = st.button(
          "Analisis Kesehatan dengan Gemini AI",
          type="primary",
          use_container_width=True,
      )

    if klik_analisis:
      with st.spinner("Menganalisis data kesehatan dengan Gemini AI..."):
        try:
          hasil_ai = analisis_kesehatan_gemini(
              df_terfilter, kota, f"{label_suhu} ({kota})"
          )
          st.session_state["hasil_ai"] = hasil_ai
          st.success("Analisis AI selesai diperbarui.")
        except Exception as err:
          st.error(f"Gagal menjalankan analisis AI: {err}")

    if st.session_state["hasil_ai"]:
      ai_data = st.session_state["hasil_ai"]
      st.subheader("Status & Tren")
      st.info(
          f"**Status:** {ai_data.get('status_singkat', 'Terpantau')} —"
          f" {ai_data.get('tren', '')}"
      )

      o1, o2 = st.columns(2)
      with o1:
        st.subheader("Observasi")
        for poin in ai_data.get("observasi", []):
          st.markdown(f"* {poin}")
      with o2:
        st.subheader("Rekomendasi Gaya Hidup")
        for saran in ai_data.get("rekomendasi", []):
          st.markdown(f"* {saran}")

    st.divider()
    st.subheader("Unduh Laporan Kesehatan")

    paket_laporan = {
        "kota_pemantauan": kota,
        "suhu_lingkungan": label_suhu,
        "jumlah_catatan": len(df_terfilter),
        "data_kesehatan": df_terfilter.to_dict(orient="records"),
        "analisis_ai": st.session_state["hasil_ai"],
    }

    d1, d2 = st.columns(2)
    with d1:
      st.download_button(
          label="Download Laporan JSON",
          data=json.dumps(paket_laporan, indent=2, ensure_ascii=False),
          file_name="laporan_kesehatan_sehatku.json",
          mime="application/json",
          use_container_width=True,
      )
    with d2:
      st.download_button(
          label="Download Laporan CSV",
          data=df_terfilter.to_csv(index=False).encode("utf-8"),
          file_name="laporan_kesehatan_sehatku.csv",
          mime="text/csv",
          use_container_width=True,
      )