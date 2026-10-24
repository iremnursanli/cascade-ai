import streamlit as st
import pandas as pd
import plotly.express as px
import mysql.connector
from datetime import datetime

# ==========================================
# 1. SAYFA AYARLARI VE TEMA
# ==========================================
st.set_page_config(page_title="Cascade AI | DSS", page_icon="🍃", layout="wide")

# CSS - Dark/Light Modlarla %100 Uyumlu Tasarım
st.markdown("""
    <style>
    div[data-testid="metric-container"] {
        border-left: 5px solid #10B981; 
        padding-left: 15px;
    }
    .cascade-box {
        background-color: rgba(46, 125, 50, 0.15);
        border-left: 5px solid #2E7D32;
        padding: 20px;
        border-radius: 5px;
        font-size: 16px;
        margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 18px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. VERİTABANI BAĞLANTISI (AIVEN CLOUD)
# ==========================================
@st.cache_data(ttl=600)
def veri_getir():
    try:
        db = mysql.connector.connect(
            host=st.secrets["DB_HOST"],
            port=st.secrets["DB_PORT"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASS"],
            database="yemekhane_projesi"
        )
        return pd.read_sql("SELECT * FROM esogu_gercek_veriler", con=db)
    except Exception as e:
        tarihler = pd.date_range(start="2026-10-01", periods=14)
        return pd.DataFrame({
            'Tarih': tarihler,
            'Beklenen_Talep': [4500, 4600, 4200, 4800, 5000, 2000, 1500, 4700, 4800, 4900, 5100, 5000, 1800, 1600],
            'Uretim_Onerisi': [4500, 4600, 4100, 4800, 5000, 2000, 1500, 4650, 4800, 4900, 5050, 5000, 1800, 1600],
            'Kurtarilan_Gida_Kg': [0, 0, 100, 0, 0, 0, 0, 50, 0, 0, 50, 0, 0, 0],
            'Hava_Durumu': ['Güneşli', 'Bulutlu', 'Yağmurlu', 'Güneşli', 'Güneşli', 'Güneşli', 'Güneşli', 'Yağmurlu', 'Bulutlu', 'Güneşli', 'Güneşli', 'Güneşli', 'Güneşli', 'Bulutlu']
        })

df = veri_getir()

# ==========================================
# 3. YAN MENÜ (SIDEBAR) - ORİJİNAL KONTROLLER
# ==========================================
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/8064/8064808.png", width=80) 
st.sidebar.title("Cascade AI Parametreleri")
st.sidebar.markdown("---")

secilen_tarih = st.sidebar.date_input("📅 Tarih Seçimi", datetime.today())
hava_durumu = st.sidebar.selectbox("🌤️ Hava Durumu (Open-Meteo)", ["Güneşli", "Bulutlu", "Yağmurlu", "Karlı"])

st.sidebar.markdown("**📚 Akademik Takvim**")
is_ramazan = st.sidebar.checkbox("🌙 Ramazan Ayı")
is_sinav = st.sidebar.checkbox("📝 Sınav Haftası")
is_haftasonu = st.sidebar.checkbox("🏖️ Hafta Sonu / Tatil")

st.sidebar.markdown("---")
st.sidebar.info("Modül Entegrasyonları:\n\n✅ SKS Web Scraping\n\n⏳ Logo Tiger ERP (Faz 2)")

# --- DİNAMİK HESAPLAMA MOTORU (Jüri Demosu İçin) ---
baz_talep = 5000
if is_haftasonu:
    baz_talep = 1500
if is_ramazan:
    baz_talep = int(baz_talep * 0.4)
if is_sinav and not is_haftasonu:
    baz_talep = int(baz_talep * 1.1)
if hava_durumu == "Yağmurlu":
    baz_talep = int(baz_talep * 0.88)
elif hava_durumu == "Karlı":
    baz_talep = int(baz_talep * 0.75)

uretim_hedefi = int(baz_talep * 1.035) # %3.5 Güvenlik Stoku
fark = 5000 - baz_talep
kurtarilan_kg = int(fark * 0.25) if fark > 0 else 0

# ==========================================
# 4. ANA EKRAN VE SEKMELER
# ==========================================
st.title("🍃 Cascade AI: Kurumsal Karar Destek Sistemi")
st.markdown("Akıllı Üretim Planlama ve Gıda İleri Dönüşüm (Upcycle) Platformu")

tab1, tab2, tab3 = st.tabs(["👩‍🍳 Mutfak Operasyon (Şef)", "📊 SKS Yönetim (Finans & Karbon)", "🛒 Satın Alma (Erken Uyarı)"])

with tab1:
    st.header("Günlük Üretim ve Cascade Yönergeleri")
    
    col1, col2, col3 = st.columns(3)
    col1.metric(label="Anlık Talep Beklentisi", value=f"{baz_talep:,} Porsiyon", delta=f"{hava_durumu} / Seçili Takvim")
    col2.metric(label="Optimum Üretim Hedefi", value=f"{uretim_hedefi:,} Porsiyon", delta="%3.5 Güvenlik Stoku Dahil", delta_color="normal")
    col3.metric(label="Önlenen İsraf (Çiğ)", value=f"{kurtarilan_kg} Kg", delta="Döngüye Alındı", delta_color="normal")

    st.markdown("### 🔄 Cascade (İleri Dönüşüm) Yönergeleri")
    
    # Dinamik Yönerge Metni
    yönerge_metni = f"1. <b>Üretim Ayarlaması:</b> Bugün hedeflenen üretim {uretim_hedefi:,} porsiyondur.<br>"
    if is_ramazan:
        yönerge_metni += "2. <b>Ramazan Ayı Protokolü:</b> Talep %60 düştü. Üretime girmeyen etleri -18°C'de şoklayın. İftar menüsü hazırlıklarına ağırlık verin.<br>"
    elif is_haftasonu:
        yönerge_metni += "2. <b>Hafta Sonu Protokolü:</b> Sadece nöbetçi yurt öğrencileri için asgari üretim yapın. Taze sebze alımlarını pazartesiye erteleyin.<br>"
    elif hava_durumu in ["Yağmurlu", "Karlı"]:
        yönerge_metni += f"2. <b>Hava Muhalefeti:</b> {hava_durumu} sebebiyle kampüs nüfusu düşüyor. {kurtarilan_kg} kg çiğ gıdayı +4°C'de yarına saklayın.<br>"
    else:
        yönerge_metni += "2. <b>Standart Operasyon:</b> Talep normal seviyede. Tezgahta kalan pişmiş yemek olursa akşam 19:00'da indirimli satışa (Too Good To Go) açın.<br>"

    st.markdown(f"""
    <div class="cascade-box">
        <b>🚨 HACCP Aksiyon Reçetesi (Tarih: {secilen_tarih}):</b><br><br>
        {yönerge_metni}
    </div>
    """, unsafe_allow_html=True)

    st.subheader("Haftalık Operasyon Projeksiyonu")
    st.dataframe(df[['Tarih', 'Beklenen_Talep', 'Uretim_Onerisi', 'Hava_Durumu']], use_container_width=True)

with tab2:
    st.header("Sürdürülebilirlik ve Finansal Performans")
    
    c1, c2, c3 = st.columns(3)
    c1.metric(label="💰 Haftalık Net Tasarruf", value="₺18,500", delta="+₺3.200 (Geçen Haftaya Göre)")
    c2.metric(label="💧 Korunan Su Kaynağı", value="4,200 Litre", delta="Tarımsal Su Ayak İzi")
    c3.metric(label="🌍 Engellenen Karbon (CO2e)", value="850 Kg", delta="Metan Gazı Önleme")

    st.markdown("---")
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        fig1 = px.line(df, x='Tarih', y=['Beklenen_Talep', 'Uretim_Onerisi'], 
                       labels={'value': 'Porsiyon', 'variable': 'Metrik'},
                       color_discrete_sequence=["#3b82f6", "#10b981"],
                       title="Talep ve Optimum Üretim Karşılaştırması")
        fig1.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig1, use_container_width=True)

    with col_chart2:
        fig2 = px.bar(df, x='Tarih', y='Kurtarilan_Gida_Kg', 
                      title="Günlük Kurtarılan Gıda Miktarı (Kg)",
                      color_discrete_sequence=["#10b981"])
        fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)

with tab3:
    st.header("Tedarik ve Risk Yönetimi")
    st.info("💡 **Akıllı Analiz:** Bu sekme ERP sistemine (Faz 2) entegre edildiğinde satın alma emirlerini otomatik oluşturacaktır.")
    
    alert_data = pd.DataFrame({
        "Hammadde": ["Kırmızı Et", "Domates", "Un", "Mevsim Yeşillikleri"],
        "Durum": ["Stok Fazlası (Şoklandı)", "Kritik Stok", "Normal", "Hızlı Bozulma Riski"],
        "Önerilen Aksiyon": ["Cuma günkü alımı iptal et", "Tedarikçiden acil sipariş geç", "Aksiyon Gerekmiyor", "Tatil öncesi alımı %40 azalt"],
        "Öncelik": ["Yüksek", "Yüksek", "Düşük", "Orta"]
    })
    
    st.dataframe(alert_data.style.apply(
        lambda x: ['background-color: rgba(239, 68, 68, 0.2)' if v == 'Yüksek' 
                   else 'background-color: rgba(245, 158, 11, 0.2)' if v == 'Orta' 
                   else '' for v in x], subset=['Öncelik']
    ), use_container_width=True)

st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>Cascade AI © 2026 | Siemens Climathon PDR Sürümü</p>", unsafe_allow_html=True)
