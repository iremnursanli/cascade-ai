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
@st.cache_data(ttl=600)
@st.cache_data(ttl=600)
def veri_getir():
    try:
        db = mysql.connector.connect(
            host="cascade-iremmur2407-e1c2.e.aivencloud.com",
            port=14752,
            user="avnadmin",
            password="AVNS_8e8lKtB-Ns2NWrsqNbP",
            database="yemekhane_projesi"
        )
        return pd.read_sql("SELECT * FROM esogu_gercek_veriler", con=db)
    except Exception as e:
        st.error(f"Veritabanı bağlantı hatası: {e}")
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
    # Geçmiş günlerde (tarih < gercek_bugun) gerçek turnike geçişi (gercek_talep) bilinir.
    # Bugün ve gelecek günlerde ise gerçek talep henüz yaşanmadığı için modelin beklenen talebi baz alınır!
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
            
            # DURUM A: UZUN TATİL / BAYRAM / SÖMESTR (4 Gün ve Üzeri Ara)
            if gun_farki >= 4:
                t += f"🛑 **HACCP (UZUN TATİL / DÖNEM SONU PROTOKOLÜ):** Dikkat! Bir sonraki operasyon gününe ({s_tarih} {s_gun}) **{gun_farki} gün** var! Mutfak uzun süreli kapanacağı için **hiçbir taze sebze veya çiğ et +4°C'de bırakılamaz (bakteriyel bozulma riski)!**\n"
                if kat == "Bakliyat":
                    ek_et = " Eser miktardaki parça etleri vakumlayıp -18°C'ye kaldırın." if "Etli" in m else ""
                    t += f"➡️ **Uzun Dönem Aksiyonu ({m}):** Kuru bakliyatları ıslatmayın, kuru erzak deposunda yeni döneme kadar muhafaza edin.{ek_et}\n"
                elif kat in ["Tavuk", "Köfte", "Sulu Et"]:
                    t += "➡️ **Uzun Dönem Aksiyonu:** Tüm çiğ et, kıyma ve tavuk stoklarını vakumlayarak **-18°C'de şoklayın**. Eşlikçi taze sebzeleri ise bekletmeden bugün SKS kantinlerine veya yerel aşevlerine/gıda bankalarına bağışlayın.\n"
                else: # Sebze
                    t += f"➡️ **Uzun Dönem Aksiyonu ({m}):** Taze sebzeler {gun_farki} gün soğuk odada bekleyemez. Çiğ sebzeleri bugün ön haşlama (blanching) yapıp **-18°C'de dondurun** veya soğuk zincirle doğrudan aşevlerine bağışlayın.\n"
            
            # DURUM B: HAFTA SONU VEYA KISA TATİL ARASI (2 - 3 Gün Ara)
            elif gun_farki in [2, 3]:
                t += f"⚠️ **HACCP (HAFTA SONU / KISA TATİL PROTOKOLÜ):** Sonraki operasyon gününe ({s_gun}) **{gun_farki} gün** var! Çiğ et, kıyma ve tavuk ürünlerini +4°C'de bekletmeyin; derhal vakumlayıp **-18°C'de şoklayın**. Taze sebzeleri ise soyma/doğrama işlemine almadan, bütün halde **+4°C nem kontrollü** depoda muhafaza edin.\n\n"
                if kat == "Tavuk":
                    t += f"➡️ **Çiğ Beyaz Et Aksiyonu ({m}):** Pişirilmeyen tavuk etlerini vakumlayarak -18°C soğuk zincire alın; gelecek haftanın tavuk döngüsünde kullanın.\n"
                elif kat == "Köfte":
                    t += f"➡️ **Çiğ Kıyma Aksiyonu ({m}):** Köfte harcını porsiyonlayıp vakumlayarak -18°C'de dondurun; gelecek haftanın köfte gününe saklayın.\n"
                elif kat == "Bakliyat":
                    ek_et = " Parça etleri vakumlayıp -18°C'de şoklayın." if "Etli" in m else ""
                    t += f"➡️ **Kuru Bakliyat Aksiyonu ({m}):** Talep fazlası bakliyatları ıslatmayın, kuru depoda tutun.{ek_et}\n"
                elif kat == "Sulu Et":
                    if "Karnıyarık" in m:
                        t += f"➡️ **Çiğ Harç & Sebze Aksiyonu (Karnıyarık):** İç harç kıymasını vakumlayıp -18°C'de şoklayın. Patlıcanları soymadan bütün halde +4°C nem kontrollü odada tutun; {zaman_etiketi} '{ym}' menüsünün yanında köz patlıcan salatası/meze olarak işleyin.\n"
                    else:
                        t += f"➡️ **Çiğ Parça Et & Sebze Aksiyonu ({m}):** Kuşbaşı etleri vakumlayıp -18°C'de şoklayın. Sebzeleri (patates/havuç) kesinlikle doğramayın; bütün halde +4°C nem kontrollü depoda tutarak {zaman_etiketi} '{ym}' menüsünün yan hazırlığında değerlendirin.\n"
                elif kat == "Sebze":
                    t += spesifik_sebze_recetesi(m, zaman_etiketi, ym, kisa_tatil_mi=True)
            
            # DURUM C: STANDART ARDIŞIK İŞ GÜNÜ (Yarın Açık - gun_farki == 1)
            else:
                if kat == "Tavuk":
                    t += f"➡️ **Çiğ Beyaz Et Aksiyonu:** İşlemden çekilen çiğ tavukları vakumlayıp -18°C'de bir sonraki tavuk döngüsüne şoklayın ({zaman_etiketi} ana yemek '{ym}' olarak planlanmıştır). Alternatif olarak haşlayıp {zaman_etiketi} menünün 'Tavuk Suyu Çorbası' bazında veya SKS kantin sandviçlerinde değerlendirin.\n"
                elif kat == "Köfte":
                    t += f"➡️ **Çiğ Kıyma Aksiyonu:** Hazırlanmış çiğ köfte harcını porsiyonlayarak vakumlayın ve -18°C'de bir sonraki köfte döngüsüne kadar dondurun ({zaman_etiketi} ana yemek '{ym}' olarak planlanmıştır).\n"
                elif kat == "Bakliyat":
                    if "Etli" in m:
                        t += f"➡️ **Kuru Bakliyat & Et Aksiyonu ({m}):** Talep fazlası kuru bakliyatları ıslatma işlemine almayın, kuru erzak deposunda muhafaza edin. Ayrılan kuşbaşı etleri vakumlayıp -18°C'ye kaldırın.\n"
                    else:
                        t += f"➡️ **Kuru Bakliyat Aksiyonu ({m}):** Talep fazlası bakliyatları ıslatma/haşlama işlemine almayın, doğrudan kuru erzak deposunda tutun. Doğranmamış soğan/havuç bazını {zaman_etiketi} '{ym}' menüsüne aktarın.\n"
                elif kat == "Sulu Et":
                    if "Karnıyarık" in m:
                        t += f"➡️ **Çiğ Harç & Sebze Aksiyonu:** Patlıcanları soymayın (+4°C'de tutun, {zaman_etiketi} '{ym}' yanında köz patlıcan salatası/meze yapın). İç harç için ayrılan çiğ kıymayı vakumlayıp -18°C'de şoklayın veya yardımcı makarna sosunda (Bolonez) değerlendirin.\n"
                    else:
                        uyum_notu = f"{zaman_etiketi} '{ym}' menüsünün yanına fırın/püre garnitür" if y_kat in ["Tavuk", "Köfte"] else f"{zaman_etiketi} '{ym}' menüsü öncesine sebze çorbası bazı"
                        t += f"➡️ **Çiğ Parça Et & Sebze Aksiyonu:** Kuşbaşı etleri pişirmeden vakumlayıp -18°C'de bir sonraki et döngüsüne saklayın. Doğranmış çiğ sebzeleri (patates, havuç) {uyum_notu} olarak aktarın.\n"
                elif kat == "Sebze":
                    t += spesifik_sebze_recetesi(m, zaman_etiketi, ym, kisa_tatil_mi=False)
            t += "\n"

        # --- 2. DOWNSTREAM: TEZGAHTA KALAN PİŞMİŞ YEMEK YÖNETİMİ ---
        if is_gecmis_gun:
            if pismis > 0:
                t += f"🟧 **TEZGAHTAN ARTAN (PİŞMİŞ - DOWNSTREAM):** Gün sonunda kazanlarda **{int(pismis)} porsiyon** pişmiş yemek kaldı! Uygulanan prosedür:\n"
                if kat == "Sebze":
                    t += "➡️ **Biyolojik Döngü (%100 Bitkisel Kompost):** Pişmiş sebze yemeklerinin tekrar ısıtılması (HACCP) uygun değildir. Hayvansal içerik barındırmadığı için süzülerek katı kısımları ESOGÜ Ziraat Fakültesi kompost alanına gönderildi.\n"
                elif kat in ["Tavuk", "Köfte"]:
                    t += "➡️ **İleri Dönüşüm & Barınak:** Hijyenik tezgah fazlası porsiyonlar SKS kafeteryasında sandviç/ekmek arası olarak değerlendirildi; kemik ve tabak atıkları kampüs hayvan besleme ünitelerine yönlendirildi.\n"
                else:
                    ek_not = "(Ramazan İftar Paketi)" if row['akademik_takvim'] == "Ramazan Ayı" else "(Too Good To Go Modeli)"
                    t += f"➡️ **Sosyal Satış {ek_not}:** Kazanlarda kalan sıcak ve güvenli yemekler, 18:00 - 19:30 arası öğrenci yurtlarına '%50 İndirimli Kurtarılmış Öğün' bildirimiyle satıldı ve aşevlerine bağışlandı.\n"
            else:
                t += "🟧 **DOWNSTREAM (PİŞMİŞ):** Tezgahta hiç pişmiş yemek artmadı (0 Pişmiş İsraf).\n"
        else:
            t += "🟧 **DOWNSTREAM (GÜN SONU ACİL DURUM PROSEDÜRÜ - SOP):** *Bu operasyon günü henüz tamamlanmadığı için tezgahta kalacak pişmiş yemek miktarı gün sonunda netleşecektir. Olası sapmalara karşı hazır tutulacak B Planı:*\n"
            if kat == "Sebze":
                t += "➡️ **SOP (Bitkisel Sebze Grubu):** Tezgahta pişmiş sebze artarsa süzülerek doğrudan ESOGÜ Ziraat Fakültesi kompost ünitesine ayrılacaktır.\n"
            elif kat in ["Tavuk", "Köfte"]:
                t += "➡️ **SOP (Protein Grubu):** Tezgahta pişmiş ürün kalırsa akşam vardiyasında kantin/yurt satışına veya kampüs hayvan barınaklarına yönlendirilecektir.\n"
            else:
                ek_not = "İftar saatinde" if row['akademik_takvim'] == "Ramazan Ayı" else "18:00 sonrasında"
                t += f"➡️ **SOP (Sulu Yemek & Bakliyat):** Kazanlarda yemek artarsa {ek_not} yurtlara '%50 İndirimli Gece Öğünü' bildirimi atılacak veya gıda bankasına soğuk zincirle teslim edilecektir.\n"
                
        return t

    # --- 4. MATEMATİKSEL OLARAK %100 TUTARLI VE ZERO-LEAKAGE METRİK HESAPLAMALARI ---
    # Upstream (Kaynakta Korunan Çiğ Stok): Tamamen planlama anında kesindir, tüm metriklerin ortak bazını oluşturur.
    df['kurtarilan_porsiyon'] = df.apply(lambda x: max(0, x['kapasite'] - x['onerilen_uretim']), axis=1)
    df['tasarruf_tl'] = df['kurtarilan_porsiyon'] * PORSIYON_MALIYET_TL
    df['onlenen_karbon_kg'] = df['kurtarilan_porsiyon'] * df['porsiyon_karbon_kg']
    df['korunan_su_litre'] = df['kurtarilan_porsiyon'] * df['porsiyon_su_litre']

    # Downstream (Tezgah ve Hizmet Seviyesi Analizi - Sadece 'analiz_talebi' kullanılır, gelecek sızıntısı sıfırdır)
    df['sistemsiz_israf_porsiyon'] = df.apply(lambda x: max(0, x['kapasite'] - x['analiz_talebi']), axis=1)
    df['ai_ile_israf_porsiyon'] = df.apply(lambda x: max(0, x['onerilen_uretim'] - x['analiz_talebi']), axis=1)
    df['karsilanamayan_talep'] = df.apply(lambda x: max(0, x['analiz_talebi'] - x['onerilen_uretim']), axis=1)
    df['hizmet_seviyesi'] = np.where(df['analiz_talebi'] > 0, ((df['analiz_talebi'] - df['karsilanamayan_talep']) / df['analiz_talebi']) * 100, 100.0)
    
    # Varyans Grafiği İçin Geleneksel Üretim Karbon İsrafı vs. AI Sonrası Karbon İsrafı
    df['beklenen_karbon_israfi'] = df['sistemsiz_israf_porsiyon'] * df['porsiyon_karbon_kg']
    df['gerceklesen_karbon_israfi'] = df['ai_ile_israf_porsiyon'] * df['porsiyon_karbon_kg']
    df['cascade_aksiyonu'] = df.apply(cascade_talimati, axis=1)

    # --- 5. ANA EKRAN VE SEKMELER ---
    st.title("🌱 Cascade AI | Kurumsal Kaynak & İklim Paneli")
    tab1, tab2, tab3 = st.tabs(["🧑‍🍳 Canlı Şef Operasyon Paneli", "📊 Kümülatif Performans & Karbon Analizi", "🔮 Gelecek Projeksiyonları (Tedarik Uyarıları)"])

    df_gecmis = df[df['tarih_dt'] <= secilen_gun].copy()
    df_gelecek = df[df['tarih_dt'] > secilen_gun].copy()

    with tab1:
        if secilen_gun not in gecerli_tarihler:
            st.warning(f"ℹ️ **Tatil / Kapalı Modu ({secilen_gun}):** Seçilen tarihte (Hafta Sonu, Yarıyıl Tatili veya Resmi/Dini Bayram) yemekhane operasyonu bulunmamaktadır. Günlük şef yönergesi için sol menüden bir iş günü seçiniz. Kurumsal raporlar için diğer sekmeleri inceleyebilirsiniz.")
        else:
            gv = df[df['tarih_dt'] == secilen_gun].iloc[0]
            if secilen_gun in canli_tahminler:
                st.success(f"📡 CANLI API SENKRONİZASYONU: {secilen_gun} tarihi için güncel Open-Meteo tahmini aktif edildi ve üretim algoritmaları kalibre edildi.")
            
            st.subheader(f"DSS Operasyon Özeti: {secilen_gun}")
            c1, c2, c3, c4 = st.columns(4)
            c1.info(f"🌡️ Hava: {gv['hava_durumu_c']}°C ({gv['hava_olayi']})")
            
            if gv['akademik_takvim'] == "Ramazan Ayı": c2.error(f"🌙 Takvim: {gv['akademik_takvim']}")
            else: c2.warning(f"📝 Takvim: {gv['akademik_takvim']}")
            
            c3.success(f"🍲 Menü: {gv['menu_tipi']} ({gv['kategori']})")
            c4.error(f"📉 AI Üretim Hedefi: {gv['onerilen_uretim']} Porsiyon")
            
            # Kurumsal KPI Şeridi (Şeffaf Sayısal Doğrulama)
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("📋 Planlanan Baz Kapasite", f"{gv['kapasite']:,} Porsiyon")
            k2.metric("🟩 Çekilen Çiğ Stok (Upstream)", f"{gv['kurtarilan_porsiyon']:,} Porsiyon", f"₺ {gv['tasarruf_tl']:,.0f} | {gv['onlenen_karbon_kg']:,.0f} kg CO2e")
            if secilen_gun < gercek_bugun:
                k3.metric("👥 Gerçekleşen Öğrenci Talebi", f"{gv['gercek_talep']:,} Porsiyon")
                k4.metric("🟧 Tezgahtan Artan (Downstream)", f"{gv['ai_ile_israf_porsiyon']:,} Porsiyon", f"Hizmet Seviyesi: %{gv['hizmet_seviyesi']:.1f}")
            else:
                k3.metric("🔮 Model Beklenen Talebi", f"{gv['beklenen_model_talebi']:,} Porsiyon")
                k4.metric("🛡️ Güvenlik Stoku (Safety Stock)", f"+{gv['onerilen_uretim'] - gv['beklenen_model_talebi']} Pors. (+%3.5)", "Stok Aşımı Koruması Aktif")

            if gv['karsilanamayan_talep'] > 0 and secilen_gun < gercek_bugun:
                st.error(f"⚠️ STOK AŞIMI RAPORU: Bu tarihte beklenmeyen talep sıçraması nedeniyle gerçek talep ({gv['gercek_talep']}) AI hedefini ({gv['onerilen_uretim']}) aşmış, Hizmet Seviyesi %{gv['hizmet_seviyesi']:.1f} olarak gerçekleşmiştir.")
            
            st.markdown(f"### 👨‍🍳 Kademeli Döngüsel Ekonomi (Cascade) Yönergesi *(Sonraki İş Günü: {gv['sonraki_tarih']} {gv['sonraki_is_gunu_adi']} - {gv['yarinki_menu']})*")
            st.info(gv['cascade_aksiyonu'])

    with tab2:
        if secilen_gun < gercek_bugun:
            st.subheader(f"Pilot Kurum Doğrulanmış Sürdürülebilirlik Raporu (Eylül 2025 - {secilen_gun})")
            st.caption("✅ *Bu rapor tamamlanmış gerçek operasyon günlerinin doğrulanmış verilerini içerir.*")
        else:
            st.subheader(f"Kümülatif Sürdürülebilirlik Raporu & Projeksiyonu (Eylül 2025 - {secilen_gun})")
            st.caption(f"ℹ️ *Veri Bütünlüğü Koruması (Zero Data Leakage): {gercek_bugun} öncesi doğrulanmış gerçek turnike verilerini, {gercek_bugun} - {secilen_gun} arası ise modelin beklenen talep projeksiyonlarını kapsar.*")
            
        if not df_gecmis.empty:
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("📦 Korunan Çiğ Gıda", f"{df_gecmis['kurtarilan_porsiyon'].sum():,} Pors.")
            col2.metric("💰 Konservatif Tasarruf", f"₺ {df_gecmis['tasarruf_tl'].sum():,.0f}")
            col3.metric("☁️ Korunan CO2e (Upstream)", f"{df_gecmis['onlenen_karbon_kg'].sum():,.0f} kg")
            col4.metric("💧 Korunan Su", f"{df_gecmis['korunan_su_litre'].sum():,.0f} L")
            col5.metric("🎯 Hizmet Seviyesi", f"% {df_gecmis['hizmet_seviyesi'].mean():.1f}") 
            
            st.divider()
            st.markdown("### ☁️ Aylık Karbon Ayak İzi Varyans Analizi: Geleneksel Üretim vs. Cascade AI (kg CO2e)")
            df_gecmis['ay_yil'] = pd.to_datetime(df_gecmis['tarih']).dt.to_period('M').astype(str)
            aylik_karbon = df_gecmis.groupby('ay_yil')[['beklenen_karbon_israfi', 'gerceklesen_karbon_israfi']].sum().reset_index()
            fig_karbon = px.bar(aylik_karbon, x='ay_yil', y=['beklenen_karbon_israfi', 'gerceklesen_karbon_israfi'], barmode='group', labels={'value': 'Karbon İsrafı (kg CO2e)', 'ay_yil': 'Aylar'})
            fig_karbon.for_each_trace(lambda t: t.update(name = {'beklenen_karbon_israfi': 'Geleneksel Sabit Üretim İsrafı', 'gerceklesen_karbon_israfi': 'Cascade AI Sonrası Kalan İsraf'}[t.name]))
            st.plotly_chart(fig_karbon, use_container_width=True)
        else:
            st.info("Seçilen tarihten önceye ait operasyon verisi bulunmuyor.")

    with tab3:
        st.subheader(f"Gelecek Akademik Dönem (Upstream) Öngörüleri ({secilen_gun} Sonrası)")
        if not df_gelecek.empty:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🔮 Planlanan Çiğ Kurtarma", f"{df_gelecek['kurtarilan_porsiyon'].sum():,} Pors.")
            col2.metric("🔮 Öngörülen Tasarruf", f"₺ {df_gelecek['tasarruf_tl'].sum():,.0f}")
            col3.metric("🔮 Hedeflenen CO2e Azaltımı", f"{df_gelecek['onlenen_karbon_kg'].sum():,.0f} kg")
            col4.metric("🔮 Korunacak Su", f"{df_gelecek['korunan_su_litre'].sum():,.0f} L")

            st.divider()
            st.markdown("### ⚠️ Logo Tiger ERP / Satın Alma Departmanı Erken Uyarı Listesi")
            riskli_gunler = df_gelecek[(df_gelecek['hava_olayi'].isin(['Kar Yağışlı', 'Yağmurlu'])) & 
                                       (df_gelecek['akademik_takvim'] != 'Normal Dönem') & 
                                       (df_gelecek['kategori'] == 'Sebze')].copy()
            
            if not riskli_gunler.empty:
                ort_kesinti_yuzde = (riskli_gunler['kurtarilan_porsiyon'] / riskli_gunler['kapasite'] * 100).mean()
                st.warning(f"Sistem, seçilen tarihten sonraki takvimde **{len(riskli_gunler)} adet Yüksek Atık Riskli Gün** (Sınav/Ramazan Dönemi + Yağışlı Hava + Düşük Tercihli Sebze Menüsü Çakışması) tespit etti. Bu tarihler için satın alma departmanına malzeme tedarikini ortalama **%{ort_kesinti_yuzde:.0f}** düşürme emri planlanmıştır:")
                
                gorunum_df = riskli_gunler[['tarih', 'hava_durumu_c', 'hava_olayi', 'akademik_takvim', 'menu_tipi', 'kapasite', 'onerilen_uretim', 'kurtarilan_porsiyon']].rename(columns={
                    'tarih': 'Tarih',
                    'hava_durumu_c': 'Sıcaklık (°C)',
                    'hava_olayi': 'Hava Olayı',
                    'akademik_takvim': 'Akademik Dönem',
                    'menu_tipi': 'Planlanan Menü',
                    'kapasite': 'Baz Kapasite',
                    'onerilen_uretim': 'AI Üretim Hedefi',
                    'kurtarilan_porsiyon': 'Tedarik Kesintisi (Pors.)'
                })
                st.dataframe(gorunum_df, use_container_width=True, hide_index=True)
            else:
                st.success("Seçilen tarihten sonraki dönemde üçlü risk çakışması tespit edilmedi.")
        else:
            st.info("Simülasyon döneminin sonuna ulaşıldı.")
