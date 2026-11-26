import json
import re
import google.generativeai as genai
import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st

GEMINI_API_KEY = "AQ.Ab8RN6L9zZi_PRY7_AdfKbZMKyv3p0C82qzN0Bs5PZ0evgIOwg"
USDA_API_KEY = "https://fdc.nal.usda.gov/api-guide](https://fdc.nal.usda.gov/api-guide"  # Ganti dengan API key data.gov kamu jika punya sendiri

LOKASI_KOORDINAT = {
    "Yogyakarta": (-7.7972, 110.3688),
    "Jakarta": (-6.2088, 106.8456),
    "Surabaya": (-7.2575, 112.7521),
    "Bandung": (-6.9175, 107.6191),
}

if "halaman_aktif" not in st.session_state:
  st.session_state["halaman_aktif"] = "Dashboard Utama"


#==========================================
# SIDEBAR UTAMA
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
