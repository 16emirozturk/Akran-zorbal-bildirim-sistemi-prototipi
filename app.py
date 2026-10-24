
# Streamlit kütüphanesini içe aktarır; web arayüzünü bununla oluşturacağız.
import streamlit as st

# Metinleri standartlaştırmak için Unicode araçlarını içe aktarır.
import unicodedata

# Sayfanın başlığını ve tarayıcı sekmesindeki simgesini ayarlar.
st.set_page_config(page_title="Güvenli Okul", page_icon="🛡️")

# Uygulamanın ana başlığını ekrana yazar.
st.title("🛡️ Güvenli Okul")

# Uygulamanın amacını öğrenciye açıklar.
st.write("Akran zorbalığı şüphesini bildirmek ve destek istemek için güvenli bir prototip.")

# Bu uyarı, uygulamanın gerçek bir acil yardım hattı olmadığını belirtir.
st.info("Bu bir öğrenci projesi prototipidir. Gerçek bildirimler şu anda rehberlik servisine gönderilmez.")


# Türkçe şüpheli ifade tespit fonksiyonunu ayrı dosyadan alır.
from hakaret_tespiti import supheli_ifadeleri_bul


def metni_analiz_et(metin):
    # Ayrı dosyadaki analiz fonksiyonunu kullanır.
    bulunanlar = supheli_ifadeleri_bul(metin)

    if bulunanlar:
        sonuc = "İnceleme öneriliyor"
        aciklama = (
            "Bazı ifadeler ek değerlendirme gerektirebilir. "
            "Bu sonuç tek başına zorbalık kanıtı değildir."
        )
    else:
        sonuc = "Belirgin eşleşme bulunmadı"
        aciklama = (
            "Bu sonuç zorbalık olmadığı anlamına gelmez. "
            "İnsan değerlendirmesi yine de gerekebilir."
        )

    return sonuc, bulunanlar, aciklama


# Bildirimleri geçici olarak bellekte tutacak listeyi ilk kullanımda oluşturur.
if "bildirimler" not in st.session_state:
    st.session_state["bildirimler"] = []

# Öğrenciye formun ne için olduğunu anlatır.
st.subheader("Yeni bildirim")

# Öğrencinin olay türünü seçebileceği bir açılır liste oluşturur.
olay_turu = st.selectbox(
    "Olayın türü",
    ["Hakaret veya alay", "Tehdit", "Dışlama", "Dijital zorbalık", "Diğer"]
)

# Olayın nerede yaşandığını seçmesini sağlar.
ortam = st.selectbox(
    "Olay nerede yaşandı?",
    ["Sınıfta", "Okul bahçesinde", "Sosyal medyada", "Mesajlaşmada", "Diğer"]
)

# Öğrencinin olayla ilgili açıklama yazabileceği metin alanını oluşturur.
aciklama_metni = st.text_area(
    "Ne yaşandığını anlatabilirsin. İsim, telefon veya adres yazma.",
    placeholder="Örneğin: Bir grup öğrenci sınıf sohbetinde sürekli alay eden mesajlar yazıyor."
)

# Bildirim düğmesine basıldığında çalışacak bölümü başlatır.
if st.button("Bildirimi incele"):

    # Boş bir açıklama gönderilmesini önler.
    if not aciklama_metni.strip():
        st.warning("Lütfen olay hakkında kısa bir açıklama yaz.")

    # Açıklama varsa analiz ve kayıt işlemlerini yapar.
    else:
        # Yazılan metni basit kelime eşleştirme yöntemiyle inceler.
        sonuc, bulunanlar, analiz_aciklamasi = metni_analiz_et(aciklama_metni)

        # İncelenmesi gereken bir kayıt oluşturur.
        kayit = {
            "Olay türü": olay_turu,
            "Ortam": ortam,
            "Analiz sonucu": sonuc,
            "Açıklama": aciklama_metni
        }

        # Eşleşen ifadeleri varsa kayda ekler.
        kayit["Eşleşen ifadeler"] = ", ".join(bulunanlar) if bulunanlar else "Yok"

        # Yeni kaydı geçici bildirim listesine ekler.
        st.session_state["bildirimler"].append(kayit)

        # Analizin sonucunu kullanıcıya gösterir.
        st.subheader("Ön değerlendirme")
        st.write("**Sonuç:**", sonuc)
        st.write(analiz_aciklamasi)

        # Eşleşme varsa hangi ifadelerin eşleştiğini gösterir.
        if bulunanlar:
            st.write("**Eşleşen örnek ifadeler:**", ", ".join(bulunanlar))

        # Her durumda insan değerlendirmesinin gerekli olduğunu hatırlatır.
        st.warning("Otomatik analiz kesin karar değildir. Bağlamı bir insan değerlendirmelidir.")

        # Bildirim alındığında kullanıcıya destekleyici mesaj verir.
        st.success("Bildirim bu prototipin geçici listesine eklendi.")

# Rehberlik inceleme alanını ekrana getirir.
st.subheader("Rehberlik inceleme listesi (demo)")

# Geçici listede kayıt varsa bunları sırayla gösterir.
if st.session_state["bildirimler"]:
    # Her bildirimi numarasıyla birlikte ekrana yazar.
    for numara, kayit in enumerate(st.session_state["bildirimler"], start=1):
        # Her kayıt için ayrı bir açılır bölüm oluşturur.
        with st.expander(f"Bildirim {numara} — {kayit['Analiz sonucu']}"):
            # Olayın türünü gösterir.
            st.write("**Olay türü:**", kayit["Olay türü"])

            # Olayın gerçekleştiği ortamı gösterir.
            st.write("**Ortam:**", kayit["Ortam"])

            # Analizle eşleşen ifadeleri gösterir.
            st.write("**Eşleşmeler:**", kayit["Eşleşen ifadeler"])

            # Bildirim açıklamasını gösterir.
            st.write("**Açıklama:**", kayit["Açıklama"])
else:
    # Henüz kayıt yoksa kullanıcıya bilgi verir.
    st.write("Henüz bir bildirim oluşturulmadı.")

# Prototipin veri saklama sınırını açıklar.
st.caption("Demo kayıtları geçici olarak bellekte tutulur. Sayfa veya uygulama yeniden başlatıldığında kaybolabilir.")
