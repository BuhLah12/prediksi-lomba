import streamlit as st
import psycopg2
import pandas as pd

# ==========================================
# 1. KONFIGURASI DATABASE
# ==========================================
DB_HOST = "aws-0-ap-southeast-1.pooler.supabase.com" # <-- GANTI DENGAN HOST ANDA
DB_NAME = "postgres"
DB_USER = "postgres.BuhLah12" # <-- GANTI DENGAN USERNAME ANDA
DB_PASS = "Luthfi*1213" # <-- GANTI DENGAN PASSWORD ANDA
DB_PORT = "6543"

@st.cache_resource
def init_connection():
    return psycopg2.connect(
        host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=DB_PORT
    )

try:
    conn = init_connection()
except Exception as e:
    st.error(f"Gagal koneksi ke PostgreSQL: {e}")
    st.stop()

# Ambil Semua Data ke dalam Pandas DataFrame sekaligus
df_match = pd.DataFrame()
df_pemain_all = pd.DataFrame()
try:
    df_match = pd.read_sql("SELECT * FROM data_futsal", conn)
    df_pemain_all = pd.read_sql("SELECT * FROM statistik_pemain", conn)
except Exception as e:
    conn.rollback()

# ==========================================
# UI UTAMA APLIKASI
# ==========================================
st.title("⚽ Sistem Analitik & Input Data Lomba")

# --- FITUR 1: INPUT SKOR MATCH ---
st.header("📋 Input Hasil Pertandingan")
with st.form("form_input_futsal"):
    col1, col2 = st.columns(2)
    with col1:
        team_a = st.text_input("Nama Tim A")
        score_a = st.number_input("Gol Tim A", min_value=0, step=1)
    with col2:
        team_b = st.text_input("Nama Tim B")
        score_b = st.number_input("Gol Tim B", min_value=0, step=1)
    submit_button = st.form_submit_button("Simpan Pertandingan")

if submit_button and team_a and team_b:
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO data_futsal (tim_a, tim_b, gol_a, gol_b) VALUES (%s, %s, %s, %s)",
            (team_a, team_b, score_a, score_b)
        )
        conn.commit()
        cur.close()
        st.success(f"Pertandingan {team_a} vs {team_b} berhasil disimpan!")
        st.rerun()
    except Exception as e:
        conn.rollback()
        st.error(f"Gagal menyimpan pertandingan: {e}")

# --- FITUR 2: ANALISIS & PREDIKSI AI (GABUNGAN) ---
st.markdown("---")
st.header("🤖 Mesin Prediksi AI (Logika Gabungan)")
st.write("AI sekarang memprediksi kemenangan tidak hanya dari skor tim lalu, tetapi juga dari kontribusi statistik tiap pemain (Gol & Assist).")

tim_unik = pd.concat([df_match['tim_a'], df_match['tim_b']]).unique().tolist() if not df_match.empty else []

if len(tim_unik) >= 2:
    col_pred1, col_pred2 = st.columns(2)
    with col_pred1:
        tim_prediksi_a = st.selectbox("Pilih Tim A", tim_unik, key="pred_a")
    with col_pred2:
        tim_prediksi_b = st.selectbox("Pilih Tim B", tim_unik, key="pred_b")
        
    if st.button("Mulai Prediksi AI"):
        if tim_prediksi_a == tim_prediksi_b:
            st.error("Pilih dua tim yang berbeda.")
        else:
            # Fungsi Logika Gabungan
            def hitung_kekuatan_gabungan(nama_tim):
                # 1. Hitung Kekuatan Dasar (Riwayat Tim)
                main_sbg_a = df_match[df_match['tim_a'] == nama_tim]
                main_sbg_b = df_match[df_match['tim_b'] == nama_tim]
                total_main = len(main_sbg_a) + len(main_sbg_b)
                
                rata_gol_tim = 0
                if total_main > 0:
                    total_gol = main_sbg_a['gol_a'].sum() + main_sbg_b['gol_b'].sum()
                    rata_gol_tim = total_gol / total_main
                
                # 2. Hitung Kekuatan Tambahan (Kualitas Pemain Individu)
                bonus_pemain = 0
                total_gol_pemain = 0
                total_assist_pemain = 0
                
                if not df_pemain_all.empty:
                    pemain_tim = df_pemain_all[df_pemain_all['asal_tim'] == nama_tim]
                    if not pemain_tim.empty:
                        total_gol_pemain = pemain_tim['gol'].sum()
                        total_assist_pemain = pemain_tim['assist'].sum()
                        # Rumus Bobot Sains Data: Gol * 0.5, Assist * 0.3
                        bonus_pemain = (total_gol_pemain * 0.5) + (total_assist_pemain * 0.3)
                
                total_kekuatan = rata_gol_tim + bonus_pemain
                return total_kekuatan, rata_gol_tim, bonus_pemain, total_gol_pemain, total_assist_pemain

            # Eksekusi AI untuk kedua tim
            power_a, base_a, bonus_a, g_pemain_a, a_pemain_a = hitung_kekuatan_gabungan(tim_prediksi_a)
            power_b, base_b, bonus_b, g_pemain_b, a_pemain_b = hitung_kekuatan_gabungan(tim_prediksi_b)
            
            total_power = power_a + power_b
            
            # Perhitungan Probabilitas Akhir
            prob_a = (power_a / total_power) * 100 if total_power > 0 else 50.0
            prob_b = (power_b / total_power) * 100 if total_power > 0 else 50.0
            
            # Tampilkan Hasil Utama
            st.subheader("📊 Hasil Prediksi Gabungan")
            st.write(f"**{tim_prediksi_a}** ({prob_a:.1f}%) vs **{tim_prediksi_b}** ({prob_b:.1f}%)")
            st.progress(max(0, min(100, int(prob_a))))
            
            if prob_a > prob_b:
                st.success(f"Prediksi: {tim_prediksi_a} lebih diunggulkan!")
            elif prob_b > prob_a:
                st.success(f"Prediksi: {tim_prediksi_b} lebih diunggulkan!")
            else:
                st.info("Kekuatan kedua tim sangat seimbang!")

            # Rincian Analisis (Transparansi untuk Panitia/Pengguna)
            with st.expander("Lihat Rincian Analisis AI (Mengapa AI memprediksi demikian?)"):
                col_rinci1, col_rinci2 = st.columns(2)
                with col_rinci1:
                    st.write(f"**Analisis {tim_prediksi_a}:**")
                    st.write(f"- Performa Riwayat Tim: {base_a:.2f} poin")
                    st.write(f"- Kontribusi Individu Pemain: {bonus_a:.2f} poin")
                    st.caption(f"(Total dari {g_pemain_a} Gol Pemain & {a_pemain_a} Assist Pemain)")
                with col_rinci2:
                    st.write(f"**Analisis {tim_prediksi_b}:**")
                    st.write(f"- Performa Riwayat Tim: {base_b:.2f} poin")
                    st.write(f"- Kontribusi Individu Pemain: {bonus_b:.2f} poin")
                    st.caption(f"(Total dari {g_pemain_b} Gol Pemain & {a_pemain_b} Assist Pemain)")
else:
    st.info("Masukkan minimal 2 pertandingan dengan tim berbeda untuk mengaktifkan AI Prediksi.")

# --- FITUR 3: STATISTIK INDIVIDU & LEADERBOARD ---
st.markdown("---")
st.header("🏃‍♂️ Statistik Individu Pemain")
with st.form("form_input_pemain"):
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        nama_pemain = st.text_input("Nama Pemain")
        tim_pemain = st.selectbox("Asal Tim", tim_unik if len(tim_unik)>0 else ["Belum ada tim"])
    with col_p2:
        gol_pemain = st.number_input("Jumlah Gol Cetakan", min_value=0, step=1)
        assist_pemain = st.number_input("Jumlah Assist", min_value=0, step=1)
    submit_pemain = st.form_submit_button("Simpan Data Pemain")

if submit_pemain and nama_pemain and tim_pemain != "Belum ada tim":
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO statistik_pemain (nama_pemain, asal_tim, gol, assist) VALUES (%s, %s, %s, %s)",
            (nama_pemain, tim_pemain, gol_pemain, assist_pemain)
        )
        conn.commit()
        cur.close()
        st.success(f"Statistik {nama_pemain} berhasil disimpan!")
        st.rerun()
    except Exception as e:
        conn.rollback()
        st.error(f"Gagal menyimpan: {e}")

st.subheader("🏆 Papan Peringkat (Top Players)")
if not df_pemain_all.empty:
    # Agregasi data langsung menggunakan Pandas agar lebih ringan
    leaderboard = df_pemain_all.groupby(['nama_pemain', 'asal_tim']).sum(numeric_only=True).reset_index()
    leaderboard = leaderboard[['nama_pemain', 'asal_tim', 'gol', 'assist']]
    leaderboard = leaderboard.sort_values(by=['gol', 'assist'], ascending=[False, False])
    st.dataframe(leaderboard, use_container_width=True)
else:
    st.info("Belum ada data statistik pemain.")
