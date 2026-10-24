
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st
from hakaret_tespiti import supheli_ifadeleri_bul


# --------------------------------------------------
# SAYFA AYARLARI
# --------------------------------------------------

st.set_page_config(
    page_title="Güvenli Okul",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = Path(__file__).with_name("guvenli_okul_demo.db")

st.markdown(
    """
    <style>
    .stApp {
        background: #f5f7fb;
    }
    [data-testid="stSidebar"] {
        background: #101c35;
    }
    [data-testid="stSidebar"] * {
        color: #f4f7ff;
    }
    .hero {
        padding: 1.5rem 1.7rem;
        border-radius: 18px;
        background: linear-gradient(120deg, #152b50, #285c8e);
        color: white;
        margin-bottom: 1.2rem;
    }
    .hero h1 {
        color: white;
        margin-bottom: .4rem;
    }
    .hero p {
        color: #e2ecfb;
        margin-bottom: 0;
    }
    .small-note {
        color: #637083;
        font-size: .9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------
# VERİTABANI
# --------------------------------------------------

def baglanti_ac():
    return sqlite3.connect(DB_PATH, timeout=10)


def veritabani_hazirla():
    with baglanti_ac() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bildirimler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                takip_no TEXT UNIQUE NOT NULL,
                olusturma_zamani TEXT NOT NULL,
                olay_turu TEXT NOT NULL,
                ortam TEXT NOT NULL,
                zaman_bilgisi TEXT NOT NULL,
                tekrar_durumu TEXT NOT NULL,
                aciklama TEXT NOT NULL,
                eslesmeler TEXT NOT NULL,
                durum TEXT NOT NULL DEFAULT 'İnceleme bekliyor',
                demo INTEGER NOT NULL DEFAULT 1
            )
            """
        )


def demo_kayitlari_ekle():
    """Veritabanı boşsa yalnızca kurgusal örnek kayıtlar ekler."""
    with baglanti_ac() as conn:
        adet = conn.execute(
            "SELECT COUNT(*) FROM bildirimler"
        ).fetchone()[0]

        if adet > 0:
            return

        ornekler = [
            (
                "DEMO-A102",
                "Hakaret veya alay",
                "Sınıfta",
                "Bugün",
                "Birden fazla kez",
                "Kurgusal örnek: Bir öğrenci sınıf sohbetinde başka bir öğrenciyle alay edildiğini bildiriyor.",
                "Örnek ifade eşleşmesi yok",
                "İnceleme bekliyor",
                1,
            ),
            (
                "DEMO-B204",
                "Dışlama",
                "Okul bahçesinde",
                "Bu hafta",
                "Birkaç kez",
                "Kurgusal örnek: Bir öğrenci grup etkinliklerine sürekli alınmadığını düşünüyor.",
                "İnsan değerlendirmesi gerekli",
                "İnceleniyor",
                1,
            ),
            (
                "DEMO-C306",
                "Dijital zorbalık",
                "Mesajlaşmada",
                "Dün",
                "Bir kez",
                "Kurgusal örnek: Bir öğrenci rahatsız edici bir mesaj aldığını bildiriyor.",
                "İnsan değerlendirmesi gerekli",
                "İnceleme bekliyor",
                1,
            ),
        ]

        for kayit in ornekler:
            conn.execute(
                """
                INSERT INTO bildirimler (
                    takip_no, olusturma_zamani, olay_turu, ortam,
                    zaman_bilgisi, tekrar_durumu, aciklama,
                    eslesmeler, durum, demo
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    kayit[0],
                    datetime.now().strftime("%Y-%m-%d %H:%M"),
                    *kayit[1:],
                ),
            )


def bildirim_ekle(
    olay_turu,
    ortam,
    zaman_bilgisi,
    tekrar_durumu,
    aciklama,
):
    bulunanlar = supheli_ifadeleri_bul(aciklama)

    takip_no = "GO-" + uuid.uuid4().hex[:8].upper()
    eslesmeler = ", ".join(bulunanlar) if bulunanlar else "Belirgin eşleşme yok"

    with baglanti_ac() as conn:
        conn.execute(
            """
            INSERT INTO bildirimler (
                takip_no, olusturma_zamani, olay_turu, ortam,
                zaman_bilgisi, tekrar_durumu, aciklama,
                eslesmeler, durum, demo
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                takip_no,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                olay_turu,
                ortam,
                zaman_bilgisi,
                tekrar_durumu,
                aciklama,
                eslesmeler,
                "İnceleme bekliyor",
            ),
        )

    return takip_no, bulunanlar


def kayitlari_getir():
    with baglanti_ac() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM bildirimler ORDER BY id DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def durum_guncelle(takip_no, yeni_durum):
    with baglanti_ac() as conn:
        conn.execute(
            "UPDATE bildirimler SET durum = ? WHERE takip_no = ?",
            (yeni_durum, takip_no),
        )


veritabani_hazirla()
demo_kayitlari_ekle()


# --------------------------------------------------
# YAN MENÜ
# --------------------------------------------------

st.sidebar.markdown("# 🛡️ Güvenli Okul")
st.sidebar.caption("Öğrenci destek ve bildirim prototipi")
st.sidebar.divider()

sayfa = st.sidebar.radio(
    "MENÜ",
    [
        "Genel bakış",
        "Yeni bildirim",
        "Bildirim inceleme",
        "Güvenli kullanım",
    ],
)

st.sidebar.divider()
st.sidebar.warning(
    "Bu uygulama demo amaçlıdır. Gerçek bir okul sistemine bağlı değildir."
)


# --------------------------------------------------
# ORTAK VERİLER
# --------------------------------------------------

kayitlar = kayitlari_getir()
bekleyen = sum(
    1 for k in kayitlar if k["durum"] == "İnceleme bekliyor"
)
incelenen = sum(
    1 for k in kayitlar if k["durum"] == "İnceleniyor"
)
sonuclanan = sum(
    1 for k in kayitlar if k["durum"] == "Sonuçlandırıldı"
)


# --------------------------------------------------
# GENEL BAKIŞ
# --------------------------------------------------

if sayfa == "Genel bakış":
    st.markdown(
        """
        <div class="hero">
            <h1>🛡️ Güvenli Okul</h1>
            <p>
                Güvenli bir okul ortamı için bildirimleri düzenle,
                takip et ve dikkatle incele.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info(
        "Demo modu: Bu ekrandaki örnek kayıtlar kurgusaldır. "
        "Gerçek bir rehberlik servisine bildirim gönderilmez."
    )

    st.subheader("Genel durum")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam kayıt", len(kayitlar))
    c2.metric("İnceleme bekliyor", bekleyen)
    c3.metric("İnceleniyor", incelenen)
    c4.metric("Sonuçlandırıldı", sonuclanan)

    st.divider()
    sol, sag = st.columns([1.3, 1])

    with sol:
        st.subheader("Son bildirimler")
        if kayitlar:
            for kayit in kayitlar[:5]:
                with st.container(border=True):
                    st.write(f"**{kayit['olay_turu']}**")
                    st.caption(
                        f"{kayit['takip_no']} · "
                        f"{kayit['olusturma_zamani']}"
                    )
                    st.write(f"Durum: **{kayit['durum']}**")
        else:
            st.write("Henüz kayıt bulunmuyor.")

    with sag:
        st.subheader("Durum dağılımı")
        durum_verisi = {
            "Durum": [
                "İnceleme bekliyor",
                "İnceleniyor",
                "Sonuçlandırıldı",
            ],
            "Sayı": [bekleyen, incelenen, sonuclanan],
        }
        st.bar_chart(durum_verisi, x="Durum", y="Sayı")

    st.caption(
        "Otomatik eşleşmeler yalnızca incelemeye yardımcı olur; "
        "zorbalığın kanıtı veya kesin kararı değildir."
    )


# --------------------------------------------------
# YENİ BİLDİRİM
# --------------------------------------------------

elif sayfa == "Yeni bildirim":
    st.title("Yeni bildirim")
    st.write(
        "Olayı mümkün olduğunca açık anlat. "
        "Kişisel bilgileri paylaşma."
    )

    st.warning(
        "Bu demo gerçek ve gizli bildirimler için güvenli değildir. "
        "Gerçek ad, telefon, adres, okul numarası veya başka bir "
        "öğrenciyi tanımlayan bilgi girme."
    )

    with st.form("bildirim_formu", clear_on_submit=True):
        olay_turu = st.selectbox(
            "Olay türü",
            [
                "Hakaret veya alay",
                "Tehdit",
                "Dışlama",
                "Dijital zorbalık",
                "Fiziksel zorbalık şüphesi",
                "Diğer",
            ],
        )

        ortam = st.selectbox(
            "Olay nerede yaşandı?",
            [
                "Sınıfta",
                "Okul bahçesinde",
                "Koridorda",
                "Sosyal medyada",
                "Mesajlaşmada",
                "Diğer",
            ],
        )

        zaman_bilgisi = st.selectbox(
            "Olay ne zaman yaşandı?",
            ["Bugün", "Dün", "Bu hafta", "Daha önce", "Emin değilim"],
        )

        tekrar_durumu = st.radio(
            "Bu durum tekrarlandı mı?",
            ["Bir kez", "Birkaç kez", "Birden fazla kez", "Emin değilim"],
            horizontal=True,
        )

        aciklama = st.text_area(
            "Olayı anlat",
            placeholder=(
                "Örnek: Bir öğrenci grup sohbetinde alay edildiğini "
                "ve bunun birkaç kez tekrarlandığını söylüyor."
            ),
            max_chars=3000,
            height=150,
        )

        onay = st.checkbox(
            "Gerçek kişi bilgileri içermeyen, yalnızca demo amaçlı "
            "bir test metni girdiğimi onaylıyorum."
        )

        gonder = st.form_submit_button(
            "Bildirimi analiz et",
            type="primary",
            use_container_width=True,
        )

    if gonder:
        if not aciklama.strip():
            st.error("Lütfen test açıklaması gir.")
        elif not onay:
            st.error("Devam etmek için demo kullanım onayını işaretle.")
        else:
            try:
                takip_no, bulunanlar = bildirim_ekle(
                    olay_turu,
                    ortam,
                    zaman_bilgisi,
                    tekrar_durumu,
                    aciklama.strip(),
                )

                st.success("Demo bildirimi kaydedildi.")
                st.subheader("Takip bilgisi")
                st.code(takip_no)

                if bulunanlar:
                    st.warning(
                        "Bazı ifadeler insan incelemesi için işaretlendi: "
                        + ", ".join(bulunanlar)
                    )
                else:
                    st.info(
                        "Belirgin bir listedeki ifade eşleşmedi. "
                        "Bu, zorbalık olmadığı anlamına gelmez."
                    )

                st.caption(
                    "Bu kayıt yalnızca demo veritabanına eklendi. "
                    "Okula veya rehberlik servisine gönderilmedi."
                )

            except sqlite3.Error:
                st.error(
                    "Demo veritabanına kayıt sırasında hata oluştu. "
                    "Lütfen uygulama günlüklerini kontrol et."
                )


# --------------------------------------------------
# BİLDİRİM İNCELEME
# --------------------------------------------------

elif sayfa == "Bildirim inceleme":
    st.title("Bildirim inceleme")
    st.write(
        "Bu ekran, demo kayıtlarını incelemek ve durumlarını "
        "test etmek için hazırlanmıştır."
    )

    st.warning(
        "Gerçek bir rehberlik personeli hesabı veya erişim kontrolü "
        "yoktur. Bu nedenle gerçek öğrenci kayıtları kullanmayın."
    )

    filtre = st.selectbox(
        "Duruma göre filtrele",
        [
            "Tüm kayıtlar",
            "İnceleme bekliyor",
            "İnceleniyor",
            "Sonuçlandırıldı",
        ],
    )

    filtreli = [
        k for k in kayitlar
        if filtre == "Tüm kayıtlar" or k["durum"] == filtre
    ]

    st.caption(f"{len(filtreli)} kayıt gösteriliyor.")

    if not filtreli:
        st.info("Bu filtrede kayıt bulunamadı.")

    for kayit in filtreli:
        with st.expander(
            f"{kayit['takip_no']} · {kayit['olay_turu']} · {kayit['durum']}"
        ):
            sol, sag = st.columns(2)

            with sol:
                st.write(f"**Olay türü:** {kayit['olay_turu']}")
                st.write(f"**Ortam:** {kayit['ortam']}")
                st.write(f"**Yaklaşık zaman:** {kayit['zaman_bilgisi']}")
                st.write(f"**Tekrarlanma:** {kayit['tekrar_durumu']}")

            with sag:
                st.write(f"**Oluşturulma:** {kayit['olusturma_zamani']}")
                st.write(f"**Eşleşmeler:** {kayit['eslesmeler']}")
                st.write(f"**Durum:** {kayit['durum']}")

            st.write("**Açıklama**")
            st.write(kayit["aciklama"])

            yeni_durum = st.selectbox(
                "Demo durumunu güncelle",
                [
                    "İnceleme bekliyor",
                    "İnceleniyor",
                    "Sonuçlandırıldı",
                ],
                index=[
                    "İnceleme bekliyor",
                    "İnceleniyor",
                    "Sonuçlandırıldı",
                ].index(kayit["durum"]),
                key=f"durum_{kayit['takip_no']}",
            )

            if st.button(
                "Durumu kaydet",
                key=f"save_{kayit['takip_no']}",
            ):
                try:
                    durum_guncelle(kayit["takip_no"], yeni_durum)
                    st.success("Demo durumu güncellendi.")
                    st.rerun()
                except sqlite3.Error:
                    st.error("Durum kaydedilemedi.")


# --------------------------------------------------
# GÜVENLİ KULLANIM
# --------------------------------------------------

elif sayfa == "Güvenli kullanım":
    st.title("Güvenli kullanım")
    st.write(
        "Güvenli Okul, akran zorbalığı şüphesini düzenli biçimde "
        "anlatabilmek ve inceleme sürecini modellemek için geliştirilir."
    )

    st.subheader("Bu sürüm neler yapabilir?")
    st.markdown(
        """
        - Demo bildirimleri oluşturabilir.
        - Her kayıt için takip numarası üretebilir.
        - Örnek ifade eşleşmelerini gösterebilir.
        - Demo kayıtlarını SQLite veritabanında tutabilir.
        - Kayıtların demo durumunu değiştirebilir.
        """
    )

    st.subheader("Bu sürüm neler yapamaz?")
    st.markdown(
        """
        - Okula veya rehberlik servisine bildirim gönderemez.
        - Zorbalık olup olmadığına kesin karar veremez.
        - Kullanıcı kimliğini doğrulamaz.
        - Rehberlik personeline özel, güvenli bir yönetici alanı sağlamaz.
        - Bütün hakaretleri veya tehditleri yakalamayı garanti edemez.
        """
    )

    st.info(
        "Gerçek kullanımdan önce yetkili bir okul çalışanıyla birlikte "
        "gizlilik, erişim kontrolü, veri saklama süresi ve güvenli "
        "bildirim süreci tasarlanmalıdır."
    )


# --------------------------------------------------
# ALT BİLGİ
# --------------------------------------------------

st.divider()
st.caption(
    "Güvenli Okul · Aşama 2 demo sürümü · "
    "Gerçek okul sistemi değildir."
)
