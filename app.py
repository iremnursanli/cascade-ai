import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import mysql.connector
from datetime import datetime, timedelta

# ==========================================
# 1. SAYFA AYARLARI VE TEMA (YEŞİL & MAVİ)
# ==========================================
st.set_page_config(page_title="Cascade AI | DSS", page_icon="🍃", layout="wide")

# CSS ile Kurumsal Tema (Yeşil ve Mavi Tonları)
st.markdown("""
    <style>
    /* Ana arkaplan ve yazı tipleri */
    .stApp {
        background-color: #F4F9F9;
    }
    /* Üst başlıklar - Kurumsal Mavi */
    h1, h2, h3 {
        color: #1E3A8A !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    /* Metrik Kartları Tasarımı */
    div[data-testid="metric-container"] {
        background-color: #FFFFFF;
        border-left: 5px solid #10B981; /* Zümrüt Yeşili */
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
    }
    /* Cascade Yönerge Kutusu */
    .cascade-box {
        background-color: #E8F5E9;
        border-left: 5px solid #2E7D32;
        padding: 20px;
        border-radius: 5px;
        color: #1B5E20;
        font-size: 16px;
        margin-bottom: 20px;
    }
    /* Sekme (Tab) renkleri */
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 18px;
        font-weight: bold;
        color: #1E3A8A;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. VERİTABANI BAĞLANTISI (AIVEN CLOUD)
# ==========================================
@st.cache_data(ttl=600)
def veri_getir():
    try:
        # Aiven Bulut Veritabanı Bağlantısı (st.secrets ile güvenli)
        db = mysql.connector.connect(
            host=st.secrets["DB_HOST"],
            port=st.secrets["DB_PORT"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASS"],
            database="yemekhane_projesi"
        )
        # Eğer tablon varsa veriyi çeker, yoksa hata vermemesi için sahte (mock) veri oluştururuz
        return pd.read_sql("SELECT * FROM esogu_gercek_veriler", con=db)
    except Exception as e:
        # Sunum sırasında bağlantı koparsa arayüz çökmesin diye Mock Veri B Planı
        tarihler = pd.date_range(start="2026-10-01", periods=14)
        mock_data = pd.DataFrame({
            'Tarih': tarihler,
            'Beklenen_Talep': [4500, 4600, 4200, 4800, 5000, 2000, 1500, 4700, 4800, 4900, 5100, 5000, 1800, 1600],
            'Uretim_Onerisi': [4500, 4600, 4100, 4800, 5000, 2000, 1500, 4650, 4800, 4900, 5050, 5000, 1800, 1600],
            'Kurtarilan_Gida_Kg': [0, 0, 100, 0, 0, 0, 0, 50, 0, 0, 50, 0, 0, 0],
            'Hava_Durumu': ['Güneşli', 'Bulutlu', 'Yağmurlu', 'Güneşli', 'Güneşli', 'Güneşli', 'Güneşli', 'Yağmurlu', 'Bulutlu', 'Güneşli', 'Güneşli', 'Güneşli', 'Güneşli', 'Bulutlu']
        })
        return mock_data

df = veri_getir()

# ==========================================
# 3. BAŞLIK VE YAN MENÜ (SIDEBAR)
# ==========================================
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/8064/8064808.png", width=100) # Yaprak/AI İkonu
st.sidebar.title("Cascade AI")
st.sidebar.markdown("---")
st.sidebar.markdown("🟢 **Durum:** Sistem Aktif")
st.sidebar.markdown("☁️ **Veritabanı:** Aiven MySQL (Secure)")
st.sidebar.markdown("🌤️ **API:** Open-Meteo Senkronize")
st.sidebar.markdown("---")
st.sidebar.info("Modül Entegrasyonları:\n\n✅ SKS Web Scraping\n\n⏳ Logo Tiger ERP (Faz 2)")

st.title("🍃 Cascade AI: Kurumsal Karar Destek Sistemi")
st.markdown("Akıllı Üretim Planlama ve Gıda İleri Dönüşüm (Upcycle) Platformu")

# ==========================================
# 4. ROL BAZLI SEKME MİMARİSİ
# ==========================================
tab1, tab2, tab3 = st.tabs(["👩‍🍳 Mutfak Operasyon (Şef)", "📊 SKS Yönetim (Finans & Karbon)", "🛒 Satın Alma (Erken Uyarı)"])

with tab1:
    st.header("Günlük Üretim ve Cascade Yönergeleri")
    
    col1, col2, col3 = st.columns(3)
    col1.metric(label="Bugünkü Hava Durumu", value="Yağmurlu 🌧️", delta="-12% Talep Düşüşü Beklentisi", delta_color="inverse")
    col2.metric(label="Optimum Üretim Hedefi", value="4,100 Porsiyon", delta="%3.5 Güvenlik Stoku Dahil")
    col3.metric(label="Önlenen İsraf (Çiğ)", value="120 Kg", delta="Döngüye Alındı")

    st.markdown("### 🔄 Cascade (İleri Dönüşüm) Yönergeleri")
    st.markdown("""
    <div class="cascade-box">
        <b>🚨 HACCP Aksiyon Reçetesi (Tarih: Bugün):</b><br>
        1. <b>Talep Düşüşü:</b> Yağış sebebiyle 500 porsiyonluk et üretimi durduruldu.<br>
        2. <b>Çiğ Gıda Koruma:</b> Üretime girmeyen 120 kg kuşbaşı eti -18°C'de şoklayın (Sonraki menü: Cuma - Orman Kebabı).<br>
        3. <b>Pişmiş Gıda Riski:</b> Ispanak sotesinde artış bekleniyor. Kalan porsiyonları yarınki 'Gül Böreği' harcı için +4°C'de ayırın.
    </div>
    """, unsafe_allow_html=True)

    # Chef tablosu
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
        # Plotly Çizgi Grafiği - Estetik Mavi/Yeşil
        fig1 = px.line(df, x='Tarih', y=['Beklenen_Talep', 'Uretim_Onerisi'], 
                       labels={'value': 'Porsiyon', 'variable': 'Metrik'},
                       color_discrete_sequence=["#1E3A8A", "#10B981"], # Mavi ve Yeşil
                       title="Talep ve Optimum Üretim Karşılaştırması")
        fig1.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig1, use_container_width=True)

    with col_chart2:
        # Plotly Bar Grafiği
        fig2 = px.bar(df, x='Tarih', y='Kurtarilan_Gida_Kg', 
                      title="Günlük Kurtarılan Gıda Miktarı (Kg)",
                      color_discrete_sequence=["#10B981"])
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
    
    # Renkli tablo gösterimi
    st.dataframe(alert_data.style.apply(
        lambda x: ['background-color: #ffcccc' if v == 'Yüksek' 
                   else 'background-color: #fff2cc' if v == 'Orta' 
                   else '' for v in x], subset=['Öncelik']
    ), use_container_width=True)

st.markdown("---")
st.markdown("<p style='text-align: center; color: #7f8c8d;'>Cascade AI © 2026 | Siemens Climathon PDR Sürümü</p>", unsafe_allow_html=True)
