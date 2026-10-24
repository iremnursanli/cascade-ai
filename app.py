import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px
import requests
from datetime import datetime, date, timedelta
import numpy as np

# --- 1. ARAYÜZ YAPILANDIRMASI VE SABİTLER ---
st.set_page_config(page_title="Cascade AI | Enterprise DSS", layout="wide", page_icon="🌱")

PORSIYON_MALIYET_TL = 35 # Öğrenci satış fiyatı bazlı konservatif birim tasarruf (TL)

menu_kategorileri = {
    "Tavuk Dünyası": "Tavuk", "Fırın Baget": "Tavuk", "Tavuk Sote": "Tavuk", "Fırın Tavuk": "Tavuk",
    "Çiftlik Köfte": "Köfte", "İzmir Köfte": "Köfte", "İnegöl Köfte": "Köfte", "Kadınbudu Köfte": "Köfte",
    "Orman Kebabı": "Sulu Et", "Etli Mevsim Türlüsü": "Sulu Et", "Karnıyarık": "Sulu Et", "Tas Kebabı": "Sulu Et",
    "Etli Kuru Fasulye": "Bakliyat", "Etli Nohut": "Bakliyat", "Yeşil Mercimek": "Bakliyat", "Zeytinyağlı Barbunya": "Bakliyat",
    "Pırasa Yemeği": "Sebze", "Ispanak": "Sebze", "Zeytinyağlı Kapuska": "Sebze", "Kereviz Yemeği": "Sebze", "Zeytinyağlı Brokoli": "Sebze"
}

@st.cache_data(ttl=600)
def veri_getir():
    try:
        # st.secrets ile güvenli bulut bağlantısı eklendi
        db = mysql.connector.connect(
            host=st.secrets["DB_HOST"],
            port=st.secrets["DB_PORT"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASS"],
            database="yemekhane_projesi"
        )
        return pd.read_sql("SELECT * FROM esogu_gercek_veriler", con=db)
    except Exception as e:
        st.error(f"Veritabanı bağlantı hatası: {e}. Lütfen 'Advanced settings -> Secrets' ayarlarını kontrol edin.")
        return pd.DataFrame()

def wmo_cevir(w):
    if w in [0, 1]: return "Güneşli"
    elif w in [2, 3]: return "Parçalı Bulutlu"
    elif w in [45, 48]: return "Kapalı"
    elif w in [51, 53, 55, 61, 63, 65, 80, 81, 82]: return "Yağmurlu"
    elif w in [71, 73, 75, 77, 85, 86]: return "Kar Yağışlı"
    return "Bulutlu"

def beklenen_talep_orani_hesapla(olay, takvim, kategori):
    """Uzman Sistem (Expert System) Temel Talep Katsayı Motoru"""
    oran = 1.0
    if olay == "Kar Yağışlı": oran *= 0.72
    elif olay == "Yağmurlu": oran *= 0.85
    elif olay == "Kapalı": oran *= 0.92
    elif olay in ["Bulutlu", "Parçalı Bulutlu"]: oran *= 0.96
    
    if takvim == "Ramazan Ayı": oran *= 0.82
    elif takvim in ["Ara Sınav (Vize) Haftası", "Final Haftası"]: oran *= 0.78
    
    if kategori in ["Tavuk", "Köfte"]: oran *= 1.06
    elif kategori == "Sulu Et": oran *= 0.96
    elif kategori == "Bakliyat": oran *= 0.92
    elif kategori == "Sebze": oran *= 0.76
    
    return min(0.98, oran)

# --- 2. CANLI 7 GÜNLÜK HAVA TAHMİNİ ---
@st.cache_data(ttl=1800) 
def canli_7gun_tahmin_cek():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=39.77&longitude=30.52&daily=temperature_2m_max,weathercode&timezone=auto&forecast_days=7"
        res = requests.get(url, timeout=5).json()
        tahmin_sozluk = {}
        for i, t_str in enumerate(res['daily']['time']):
            t_dt = pd.to_datetime(t_str).date()
            if res['daily']['temperature_2m_max'][i] is not None:
                tahmin_sozluk[t_dt] = (int(res['daily']['temperature_2m_max'][i]), wmo_cevir(res['daily']['weathercode'][i]))
        return tahmin_sozluk
    except:
        return {}

df = veri_getir()
canli_tahminler = canli_7gun_tahmin_cek()

# --- 3. VERİ MÜHENDİSLİĞİ & KARAR MOTORU ---
if not df.empty:
    df['tarih_dt'] = pd.to_datetime(df['tarih']).dt.date
    df = df.sort_values('tarih_dt').reset_index(drop=True)
    df['kategori'] = df['menu_tipi'].map(menu_kategorileri)
    
    gercek_bugun = date.today()
    
    # Canlı 7 günlük API tahminlerini ana DataFrame'e işle
    for idx, row in df.iterrows():
        t_dt = row['tarih_dt']
        if t_dt in canli_tahminler:
            yeni_sicaklik, yeni_olay = canli_tahminler[t_dt]
            df.at[idx, 'hava_durumu_c'] = yeni_sicaklik
            df.at[idx, 'hava_olayi'] = yeni_olay

    # Sonraki operasyon günü, menüsü ve kategorisi (Çapraz uyum kontrolü için)
    df['sonraki_tarih'] = df['tarih_dt'].shift(-1).fillna(date(2027, 9, 15))
    df['gun_farki'] = (pd.to_datetime(df['sonraki_tarih']) - pd.to_datetime(df['tarih_dt'])).dt.days.fillna(75).astype(int)
    df['yarinki_menu'] = df['menu_tipi'].shift(-1).fillna("Yeni Akademik Yıl Açılış Menüsü")
    df['yarinki_kategori'] = df['kategori'].shift(-1).fillna("Standart")
    
    gun_isimleri = {0: "Pazartesi", 1: "Salı", 2: "Çarşamba", 3: "Perşembe", 4: "Cuma", 5: "Cumartesi", 6: "Pazar"}
    df['sonraki_is_gunu_no'] = pd.to_datetime(df['sonraki_tarih']).dt.weekday.fillna(0).astype(int)
    df['sonraki_is_gunu_adi'] = df['sonraki_is_gunu_no'].map(gun_isimleri)

    aktif_tarih = gercek_bugun
    while aktif_tarih not in df['tarih_dt'].values and aktif_tarih <= df['tarih_dt'].max():
        aktif_tarih += timedelta(days=1)

    # --- YAN MENÜ ---
    st.sidebar.markdown("## 🌍 Cascade AI Core")
    st.sidebar.selectbox("📍 Kurum Seçimi", ["ESOGÜ (Pilot Bölge - Aktif)", "ESTÜ (Entegrasyon Aşamasında)"])
    st.sidebar.markdown("---")
    st.sidebar.success("🟢 SKS Web Scraping: Aktif")
    st.sidebar.info("☁️ Open-Meteo API: Senkronize")
    st.sidebar.info("🧠 AI Motoru: Expert System (Faz 1)")
    st.sidebar.warning("🔄 ERP ETL İş Akışı: Logo Tiger Beklemede")
    st.sidebar.markdown("---")
    
    gecerli_tarihler = df['tarih_dt'].tolist()
    secilen_gun = st.sidebar.date_input("Operasyon Tarihini Seçin:", aktif_tarih, min_value=df['tarih_dt'].min(), max_value=df['tarih_dt'].max())

    # Bilimsel Dinamik Karbon & Su Ayak İzi (Biyolojik İçeriğe Göre)
    def cevresel_etki(row):
        m = row['menu_tipi']
        kat = row['kategori']
        if kat in ["Köfte", "Sulu Et"]:
            return 5.5, 350 # Kırmızı Et Grubu
        elif kat == "Tavuk":
            return 2.2, 120 # Beyaz Et Grubu
        elif "Etli" in m:
            return 1.8, 110 # Parça Et İçeren Bakliyatlar (Etli Kuru Fasulye, Etli Nohut)
        else:
            return 0.8, 40  # %100 Bitkisel Sebze ve Bakliyatlar

    df[['porsiyon_karbon_kg', 'porsiyon_su_litre']] = df.apply(lambda r: pd.Series(cevresel_etki(r)), axis=1)

    # Uzman Sistem Karar Motoru (Beklenen Talep & %3.5 Safety Stock Dahil Optimal Üretim)
    def karar_motoru(row):
        baz = float(row['kapasite'])
        beklenen_oran = beklenen_talep_orani_hesapla(row['hava_olayi'], row['akademik_takvim'], row['kategori'])
        beklenen_talep = int(round(baz * beklenen_oran))
        onerilen_uretim = min(int(row['kapasite']), int(round(beklenen_talep * 1.035))) # +%3.5 Güvenlik Stoku
        return beklenen_talep, onerilen_uretim

    df[['beklenen_model_talebi', 'onerilen_uretim']] = df.apply(lambda r: pd.Series(karar_motoru(r)), axis=1)

    # 🌟 VERİ BİLİMİ ETİĞİ (STRICT TEMPORAL FIREWALL - DATA LEAKAGE KORUMASI) 🌟
    df['analiz_talebi'] = np.where(df['tarih_dt'] < gercek_bugun, df['gercek_talep'], df['beklenen_model_talebi'])

    # Spesifik Sebze Reçetesi Üretici (Hem Hafta İçi Hem Cuma İçin Ortak Kullanılır)
    def spesifik_sebze_recetesi(m, zaman_etiketi, ym, kisa_tatil_mi=False):
        on_hazirlik = "Yıkanmadan ve doğranmadan +4°C nem kontrollü kasalarda korunan" if kisa_tatil_mi else "İşlemden çekilen taze"
        if "Ispanak" in m:
            return f"➡️ **Spesifik Sebze Upcycle (Ispanak):** {on_hazirlik} çiğ ıspanak yapraklarını {zaman_etiketi} '{ym}' menüsünün yanında yardımcı 'Ispanaklı Gül Böreği' harcı veya taze salata barı olarak değerlendirin. Kök kısımlarını ESOGÜ Ziraat Fakültesi kompostuna ayırın.\n"
        elif "Pırasa" in m:
            return f"➡️ **Spesifik Sebze Upcycle (Pırasa):** {on_hazirlik} pırasaları {zaman_etiketi} '{ym}' menüsünün başlangıç çorbasında (Sebzeli Çorba) veya yardımcı fırın mücver/börek harcında değerlendirin.\n"
        elif "Kereviz" in m:
            return f"➡️ **Spesifik Sebze Upcycle (Kereviz):** {on_hazirlik} kerevizleri {zaman_etiketi} '{ym}' menüsünde yoğurtlu 'Kereviz Tarator' (meze) olarak işleyip salata barına ek değer olarak sunun.\n"
        elif "Brokoli" in m:
            return f"➡️ **Spesifik Sebze Upcycle (Brokoli):** {on_hazirlik} brokolileri {zaman_etiketi} '{ym}' menüsünde buharda şoklayarak vegan/diyet alternatif veya soğuk zeytinyağlı salata barı olarak değerlendirin.\n"
        else: # Kapuska / Lahana
            return f"➡️ **Spesifik Sebze Upcycle (Lahana):** {on_hazirlik} beyaz lahanaları {zaman_etiketi} '{ym}' menüsünün salata barında ince kıyım 'Coleslaw (Lahana Salatası)' veya kışlık turşu olarak değerlendirin.\n"

    # 🌟 ÇAPRAZ MENÜ UYUMLU, 3 KADEMELİ HACCP VE ZAMAN BİLİNÇLİ CASCADE ALGORİTMASI 🌟
    def cascade_talimati(row):
        cig = max(0, row['kapasite'] - row['onerilen_uretim'])
        pismis = max(0, row['onerilen_uretim'] - row['analiz_talebi']) 
        m = row['menu_tipi']
        kat = row['kategori']
        ym = row['yarinki_menu']
        y_kat = row['yarinki_kategori']
        gun_farki = int(row['gun_farki'])
        s_gun = row['sonraki_is_gunu_adi']
        s_tarih = row['sonraki_tarih']
        zaman_etiketi = f"{s_gun} günkü"
        
        is_gecmis_gun = row['tarih_dt'] < gercek_bugun

        if cig <= 0 and (not is_gecmis_gun or pismis <= 0):
            if is_gecmis_gun:
                return "✅ Operasyon Mükemmeliyeti: Beklenen talep tam kapasitede gerçekleşti, sıfır atık sağlandı."
            else:
                return f"✅ Tam Kapasite Üretim: Yüksek tercihli menü ({m}) ve mevcut koşullar ({row['hava_olayi']}) doğrultusunda %100 kapasite üretimi önerilmektedir. Kaynakta kesinti (Upstream) gerekmez.\n\n🟧 **DOWNSTREAM (GÜN SONU SOP):** *Olası tezgah fazlası oluşursa akşam vardiyasında yurtlara/barınaklara yönlendirilecektir.*"

        t = ""
        
        # --- 1. UPSTREAM: ÜRETİME GİRMEYEN ÇİĞ MALZEME YÖNETİMİ ---
        if cig > 0:
            t += f"🟩 **KAYNAKTA KORUMA (ÇİĞ STOK - UPSTREAM):** Beklenen talep düşüşü nedeniyle **{int(cig)} porsiyonluk** ham maddeyi işlemden çekin!\n\n"
            
            if gun_farki >= 4:
                t += f"🛑 **HACCP (UZUN TATİL / DÖNEM SONU PROTOKOLÜ):** Dikkat! Bir sonraki operasyon gününe ({s_tarih} {s_gun}) **{gun_farki} gün** var! Mutfak uzun süreli kapanacağı için **hiçbir taze sebze veya çiğ et +4°C'de bırakılamaz (bakteriyel bozulma riski)!**\n"
                if kat == "Bakliyat":
                    ek_et = " Eser miktardaki parça etleri vakumlayıp -18°C'ye kaldırın." if "Etli" in m else ""
                    t += f"➡️ **Uzun Dönem Aksiyonu ({m}):** Kuru bakliyatları ıslatmayın, kuru erzak deposunda yeni döneme kadar muhafaza edin.{ek_et}\n"
                elif kat in ["Tavuk", "Köfte", "Sulu Et"]:
                    t += "➡️ **Uzun Dönem Aksiyonu:** Tüm çiğ et, kıyma ve tavuk stoklarını vakumlayarak **-18°C'de şoklayın**. Eşlikçi taze sebzeleri ise bekletmeden bugün SKS kantinlerine veya yerel aşevlerine/gıda bankalarına bağışlayın.\n"
                else: 
                    t += f"➡️ **Uzun Dönem Aksiyonu ({m}):** Taze sebzeler {gun_farki} gün soğuk odada bekleyemez. Çiğ sebzeleri bugün ön haşlama (blanching) yapıp **-18°C'de dondurun** veya soğuk zincirle doğrudan aşevlerine bağışlayın.\n"
            
            elif gun_farki in [2, 3]:
                t += f"⚠️ **HACCP (HAFTA SONU / KISA TATİL PROTOKOLÜ):** Sonraki operasyon gününe ({s_gun}) **{gun_farki} gün** var! Çiğ et, kıyma ve tavuk ürünlerini +4°C'de bekletmeyin; derhal vakumlayıp **-18°C'de şoklayın**. Taze sebzeleri ise soyma/doğrama işlemine almadan, bütün halde **+4°C nem kontrollü** depoda muhafaza edin.\n\n"
                if kat == "Tavuk":
                    t += f"➡️ **Çiğ Beyaz Et Aksiyonu ({m}):** Pişirilmeyen tavuk etlerini vakumlayarak -18°C soğuk zincire alın; gelecek haftanın tavuk döngüsünde kullanın.\n"
                elif kat == "Köfte":
                    t += f"➡️ **Çiğ Kıyma Aksiyonu ({m}):** Köfte harcını porsiyonlayıp vakumlayarak -18°C'de dondurun; gelecek haftanın köfte gününe saklayın.\n"
                elif kat == "Bakliyat":
                    ek_et
