
import hmac
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st
from hakaret_tespiti import supheli_ifadeleri_bul


# =========================================================
# 1. SAYFA AYARLARI VE GÖRÜNÜM
# =========================================================

st.set_page_config(
    page_title="Güvenli Okul | 3.0",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = Path(__file__).with_name("guvenli_okul_demo.db")

DURUMLAR = [
    "İnceleme bekliyor",
    "İnceleniyor",
    "Takip gerekiyor",
    "Sonuçlandırıldı",
]

BIRIMLER = [
    "Henüz atanmadı",
    "Demo rehberlik birimi",
    "Demo yönetim birimi",
    "Demo destek ekibi",
]

OLAY_TURLERI = [
    "Hakaret veya alay",
    "Tehdit",
    "Dışlama",
    "Dijital zorbalık",
    "Fiziksel zorbalık şüphesi",
    "Diğer",
]

st.markdown(
    """
    <style>
    .stApp {
        background: #f4f7fb;
    }

    [data-testid="stSidebar"] {
        background: #101c35;
    }

    [data-testid="stSidebar"] * {
        color: #f4f7ff;
    }

    .hero {
        padding: 2rem;
        border-radius: 20px;
        background: linear-gradient(120deg, #142744, #28649a);
        color: white;
        margin-bottom: 1.2rem;
    }

    .hero h1 {
        color: white;
        font-size: 2.35rem;
        margin-bottom: .5rem;
    }

    .hero p {
        color: #e4efff;
        font-size: 1.05rem;
        margin-bottom: 0;
    }

    .muted {
        color: #64748b;
        font-size: .9rem;
    }

    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #e2e8f0;
        padding: 1rem;
        border-radius: 14px;
    }

    div[data-testid="stForm"] {
        background: white;
        padding: 1.2rem;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 2. YÖNETİCİ AYARLARI
# Streamlit Cloud > Settings > Secrets
# =========================================================

try:
    ADMIN_USERNAME = str(st.secrets["admin"]["username"])
    ADMIN_PASSWORD = str(st.secrets["admin"]["password"])
except (KeyError, FileNotFoundError):
    ADMIN_USERNAME = ""
    ADMIN_PASSWORD = ""


# =========================================================
# 3. VERİTABANI VE GÜVENLİ ŞEMA GÜNCELLEMESİ
# =========================================================

def baglanti_ac():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def sutun_ekle(conn, tablo, sutun, tanim):
    mevcut = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({tablo})")
    }
    if sutun not in mevcut:
        conn.execute(
            f"ALTER TABLE {tablo} ADD COLUMN {sutun} {tanim}"
        )


def islem_kaydi(conn, takip_no, islem, ayrinti=""):
    conn.execute(
        """
        INSERT INTO islem_gecmisi
        (takip_no, zaman, islem, ayrinti)
        VALUES (?, ?, ?, ?)
        """,
        (
            takip_no,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            islem,
            ayrinti,
        ),
    )


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

        # Eski veritabanını silmeden yeni alanları ekle.
        sutun_ekle(conn, "bildirimler", "anonim", "INTEGER NOT NULL DEFAULT 1")
        sutun_ekle(conn, "bildirimler", "ad", "TEXT NOT NULL DEFAULT ''")
        sutun_ekle(conn, "bildirimler", "soyad", "TEXT NOT NULL DEFAULT ''")
        sutun_ekle(conn, "bildirimler", "sinif", "TEXT NOT NULL DEFAULT ''")
        sutun_ekle(conn, "bildirimler", "birim", "TEXT NOT NULL DEFAULT 'Henüz atanmadı'")
        sutun_ekle(conn, "bildirimler", "son_guncelleme", "TEXT NOT NULL DEFAULT ''")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS inceleme_notlari (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                takip_no TEXT NOT NULL,
                zaman TEXT NOT NULL,
                not_metni TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS islem_gecmisi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                takip_no TEXT NOT NULL,
                zaman TEXT NOT NULL,
                islem TEXT NOT NULL,
                ayrinti TEXT NOT NULL DEFAULT ''
            )
            """
        )


def demo_kayitlari_ekle():
    """Yalnızca kurgu örnekleri; mevcut kayıtları tekrar eklemez."""
    with baglanti_ac() as conn:
        adet = conn.execute(
            "SELECT COUNT(*) FROM bildirimler"
        ).fetchone()[0]

        if adet:
            return

        ornekler = [
            (
                "DEMO-A102",
                "Hakaret veya alay",
                "Sınıfta",
                "Bugün",
                "Birden fazla kez",
                "Kurgusal örnek: Bir öğrenci sınıf sohbetinde alay edildiğini bildiriyor.",
                "İnsan değerlendirmesi gerekli",
                "İnceleme bekliyor",
            ),
            (
                "DEMO-B204",
                "Dışlama",
                "Okul bahçesinde",
                "Bu hafta",
                "Birkaç kez",
                "Kurgusal örnek: Bir öğrenci grup etkinliklerine alınmadığını düşünüyor.",
                "İnsan değerlendirmesi gerekli",
                "İnceleniyor",
            ),
            (
                "DEMO-C306",
                "Dijital zorbalık",
                "Mesajlaşmada",
                "Dün",
                "Bir kez",
                "Kurgusal örnek: Bir öğrenci rahatsız edici bir mesaj aldığını bildiriyor.",
                "Örnek ifade eşleşmesi yok",
                "İnceleme bekliyor",
            ),
        ]

        for r in ornekler:
            conn.execute(
                """
                INSERT INTO bildirimler (
                    takip_no, olusturma_zamani, olay_turu, ortam,
                    zaman_bilgisi, tekrar_durumu, aciklama,
                    eslesmeler, durum, demo, anonim, birim,
                    son_guncelleme
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, ?, ?)
                """,
                (
                    r[0],
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    *r[1:],
                    "Henüz atanmadı",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            islem_kaydi(conn, r[0], "Demo kaydı oluşturuldu")


def kayitlari_getir():
    with baglanti_ac() as conn:
        return [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM bildirimler ORDER BY id DESC"
            ).fetchall()
        ]


def bildirim_ekle(
    olay_turu,
    ortam,
    zaman_bilgisi,
    tekrar_durumu,
    aciklama,
    anonim,
    ad,
    soyad,
    sinif,
):
    bulunanlar = supheli_ifadeleri_bul(aciklama)
    takip_no = "GO-" + uuid.uuid4().hex[:8].upper()
    eslesmeler = (
        ", ".join(bulunanlar)
        if bulunanlar
        else "Belirgin eşleşme yok"
    )
    simdi = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Anonim bildirimlerde kimlik alanları veritabanına yazılmaz.
    if anonim:
        ad, soyad, sinif = "", "", ""

    with baglanti_ac() as conn:
        conn.execute(
            """
            INSERT INTO bildirimler (
                takip_no, olusturma_zamani, olay_turu, ortam,
                zaman_bilgisi, tekrar_durumu, aciklama,
                eslesmeler, durum, demo, anonim, ad, soyad,
                sinif, birim, son_guncelleme
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
            """,
            (
                takip_no, simdi, olay_turu, ortam,
                zaman_bilgisi, tekrar_durumu, aciklama,
                eslesmeler, "İnceleme bekliyor", int(anonim),
                ad, soyad, sinif, "Henüz atanmadı", simdi,
            ),
        )
        islem_kaydi(conn, takip_no, "Yeni demo bildirimi oluşturuldu")

    return takip_no, bulunanlar


def durum_ve_birim_guncelle(takip_no, yeni_durum, yeni_birim):
    simdi = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with baglanti_ac() as conn:
        eski = conn.execute(
            "SELECT durum, birim FROM bildirimler WHERE takip_no = ?",
            (takip_no,),
        ).fetchone()

        if not eski:
            return

        if eski["durum"] != yeni_durum:
            islem_kaydi(
                conn, takip_no, "Durum değiştirildi",
                f"{eski['durum']} → {yeni_durum}",
            )

        if eski["birim"] != yeni_birim:
            islem_kaydi(
                conn, takip_no, "Birim ataması değiştirildi",
                f"{eski['birim']} → {yeni_birim}",
            )

        conn.execute(
            """
            UPDATE bildirimler
            SET durum = ?, birim = ?, son_guncelleme = ?
            WHERE takip_no = ?
            """,
            (yeni_durum, yeni_birim, simdi, takip_no),
        )


def not_ekle(takip_no, metin):
    simdi = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with baglanti_ac() as conn:
        conn.execute(
            """
            INSERT INTO inceleme_notlari (takip_no, zaman, not_metni)
            VALUES (?, ?, ?)
            """,
            (takip_no, simdi, metin),
        )
        islem_kaydi(conn, takip_no, "İnceleme notu eklendi")


def notlari_getir(takip_no):
    with baglanti_ac() as conn:
        return [
            dict(r) for r in conn.execute(
                """
                SELECT zaman, not_metni
                FROM inceleme_notlari
                WHERE takip_no = ?
                ORDER BY id DESC
                """,
                (takip_no,),
            ).fetchall()
        ]


def gecmisi_getir(takip_no):
    with baglanti_ac() as conn:
        return [
            dict(r) for r in conn.execute(
                """
                SELECT zaman, islem, ayrinti
                FROM islem_gecmisi
                WHERE takip_no = ?
                ORDER BY id DESC
                """,
                (takip_no,),
            ).fetchall()
        ]


veritabani_hazirla()
demo_kayitlari_ekle()


# =========================================================
# 4. YAN MENÜ VE YÖNETİCİ OTURUMU
# =========================================================

if "yonetici_giris" not in st.session_state:
    st.session_state.yonetici_giris = False

st.sidebar.markdown("# 🛡️ Güvenli Okul")
st.sidebar.caption("Akran zorbalığı bildirim ve inceleme demosu")
st.sidebar.divider()

sayfa = st.sidebar.radio(
    "MENÜ",
    [
        "Genel bakış",
        "Yeni bildirim",
        "Yönetici girişi",
        "Güvenli kullanım",
    ],
)

st.sidebar.divider()
st.sidebar.info(
    "3.0 DEMO\n\nGerçek bir okul sistemine bağlı değildir. "
    "Gerçek öğrenci bilgileri girmeyin."
)

if st.session_state.yonetici_giris:
    st.sidebar.success("Yönetici oturumu açık")
    if st.sidebar.button("Güvenli çıkış yap", use_container_width=True):
        st.session_state.yonetici_giris = False
        st.rerun()


# =========================================================
# 5. GENEL BAKIŞ
# Bu sayfada yalnızca genel, hassas olmayan bilgi gösterilir.
# =========================================================

if sayfa == "Genel bakış":
    st.markdown(
        """
        <div class="hero">
            <h1>🛡️ Güvenli Okul</h1>
            <p>Bildirimleri düzenli incelemek ve güvenli okul kültürünü
            desteklemek için geliştirilmiş araştırma prototipi.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info(
        "Demo uygulamasıdır. Buradaki örnekler kurgusaldır; "
        "gerçek okula veya rehberlik servisine bildirim gönderilmez."
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Demo sürümü", "3.0")
    c2.metric("Yönetici incelemesi", "İnsan denetimli")
    c3.metric("Gerçek veri", "Kullanılmıyor")

    st.subheader("Bu projenin amacı")
    st.write(
        "Akran zorbalığı şüphelerini düzenli biçimde kaydetme, "
        "insan incelemesini destekleme ve inceleme adımlarını "
        "izlenebilir bir iş akışında modelleme."
    )

    st.subheader("Güvenlik yaklaşımı")
    st.markdown(
        """
        - Bildirim listesi ve ayrıntıları yönetici oturumu gerektirir.
        - Anonim bildirim seçeneği vardır.
        - Otomatik ifade eşleşmeleri karar veya kanıt sayılmaz.
        - Demo kayıtları gerçek öğrenci verileri değildir.
        """
    )


# =========================================================
# 6. YENİ BİLDİRİM
# Yönetici girişi gerektirmez; yönetim kayıtları gösterilmez.
# =========================================================

elif sayfa == "Yeni bildirim":
    st.title("📝 Yeni demo bildirimi")
    st.write("Lütfen yalnızca kurgusal test bilgileri kullan.")

    st.warning(
        "Bu sürüm gerçek ve gizli bildirimler için tasarlanmamıştır. "
        "Gerçek ad, okul numarası, telefon, adres veya başka bir "
        "öğrenciyi tanımlayan bilgi girmeyin."
    )

    with st.form("bildirim_formu", clear_on_submit=True):
        anonim = st.checkbox(
            "Anonim demo bildirimi oluştur",
            value=True,
        )

        st.caption(
            "Anonim seçenek açıkken ad, soyad ve sınıf alanları "
            "kayda alınmaz."
        )

        ad = st.text_input(
            "Ad (yalnızca kurgusal test bilgisi)",
            max_chars=40,
            disabled=anonim,
        )
        soyad = st.text_input(
            "Soyad (yalnızca kurgusal test bilgisi)",
            max_chars=40,
            disabled=anonim,
        )
        sinif = st.selectbox(
            "Sınıf / şube (demo)",
            ["Seçilmedi", "5-A", "6-A", "7-A", "8-A",
             "9-A", "10-A", "11-A", "12-A"],
            disabled=anonim,
        )

        olay_turu = st.selectbox("Olay türü", OLAY_TURLERI)

        ortam = st.selectbox(
            "Olayın gerçekleştiği ortam",
            [
                "Sınıfta", "Okul bahçesinde", "Koridorda",
                "Sosyal medyada", "Mesajlaşmada", "Diğer",
            ],
        )

        zaman_bilgisi = st.selectbox(
            "Yaklaşık zaman",
            ["Bugün", "Dün", "Bu hafta", "Daha önce", "Emin değilim"],
        )

        tekrar_durumu = st.radio(
            "Tekrarlanma durumu",
            ["Bir kez", "Birkaç kez", "Birden fazla kez", "Emin değilim"],
            horizontal=True,
        )

        aciklama = st.text_area(
            "Olay açıklaması (kurgu test metni)",
            placeholder="Örnek: Kurgusal bir öğrenci grup sohbetinde alay edildiğini söylüyor.",
            max_chars=3000,
            height=150,
        )

        onay = st.checkbox(
            "Yalnızca kurgusal demo verisi girdiğimi onaylıyorum."
        )

        gonder = st.form_submit_button(
            "Demo bildirimini oluştur",
            type="primary",
            use_container_width=True,
        )

    if gonder:
        if not aciklama.strip():
            st.error("Lütfen kurgusal bir test açıklaması gir.")
        elif not onay:
            st.error("Önce demo verisi onayını işaretle.")
        elif not anonim and sinif == "Seçilmedi":
            st.error("Kimlik bilgili demo için bir örnek sınıf seç.")
        else:
            try:
                takip_no, bulunanlar = bildirim_ekle(
                    olay_turu,
                    ortam,
                    zaman_bilgisi,
                    tekrar_durumu,
                    aciklama.strip(),
                    anonim,
                    ad.strip(),
                    soyad.strip(),
                    "" if sinif == "Seçilmedi" else sinif,
                )

                st.success("Kurgusal demo bildirimi oluşturuldu.")
                st.write("Takip kodun:")
                st.code(takip_no)

                st.info(
                    "Bu kod bir demo referansıdır. Gerçek bir kuruma "
                    "bildirim gönderilmedi."
                )

                if bulunanlar:
                    st.warning(
                        "İnsan incelemesine yardımcı olabilecek "
                        "ifade eşleşmeleri: " + ", ".join(bulunanlar)
                    )
                else:
                    st.caption(
                        "Belirgin ifade eşleşmesi bulunmadı. "
                        "Bu, zorbalık olmadığı anlamına gelmez."
                    )

            except sqlite3.Error:
                st.error("Demo kaydı oluşturulamadı. Uygulama günlüklerini kontrol et.")


# =========================================================
# 7. YÖNETİCİ GİRİŞİ
# =========================================================

elif sayfa == "Yönetici girişi":
    st.markdown(
        """
        <div class="hero">
            <h1>🔐 Yönetici girişi</h1>
            <p>Bildirim inceleme alanı yalnızca yetkili demo oturumuna açıktır.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.yonetici_giris:
        st.success("Yönetici oturumu zaten açık.")
        st.write("Bildirim inceleme menüsünü açabilirsin.")
    elif not ADMIN_USERNAME or not ADMIN_PASSWORD:
        st.error(
            "Yönetici bilgileri ayarlanmamış. "
            "Streamlit Cloud > Settings > Secrets bölümünü yapılandır."
        )
    else:
        with st.form("yonetici_giris_formu"):
            kullanici = st.text_input("Kullanıcı adı")
            parola = st.text_input("Parola", type="password")
            giris_yap = st.form_submit_button(
                "Giriş yap",
                type="primary",
                use_container_width=True,
            )

        if giris_yap:
            kullanici_dogru = hmac.compare_digest(
                kullanici, ADMIN_USERNAME
            )
            parola_dogru = hmac.compare_digest(
                parola, ADMIN_PASSWORD
            )

            if kullanici_dogru and parola_dogru:
                st.session_state.yonetici_giris = True
                st.success("Demo yönetici girişi başarılı.")
                st.rerun()
            else:
                st.error("Kullanıcı adı veya parola hatalı.")


# =========================================================
# 8. YÖNETİCİ İNCELEME PANELİ
# Kayıtları getirme işlemi yalnızca oturum kontrolünden sonra.
# =========================================================

elif sayfa == "Bildirim inceleme":
    st.title("🗂️ Bildirim inceleme")

    if not st.session_state.yonetici_giris:
        st.warning(
            "Bu alan yalnızca yönetici oturumuna açıktır. "
            "Önce Yönetici girişi bölümünden giriş yap."
        )
        st.stop()

    kayitlar = kayitlari_getir()

    bekleyen = sum(k["durum"] == "İnceleme bekliyor" for k in kayitlar)
    incelenen = sum(k["durum"] == "İnceleniyor" for k in kayitlar)
    takip = sum(k["durum"] == "Takip gerekiyor" for k in kayitlar)
    sonuclanan = sum(k["durum"] == "Sonuçlandırıldı" for k in kayitlar)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam kayıt", len(kayitlar))
    c2.metric("Bekleyen", bekleyen)
    c3.metric("İnceleniyor / takip", incelenen + takip)
    c4.metric("Sonuçlandırılan", sonuclanan)

    st.divider()

    arama = st.text_input(
        "Takip kodu veya olay türüyle ara",
        placeholder="Ör. GO-1234ABCD veya Dijital zorbalık",
    )

    durum_filtresi = st.selectbox(
        "Durum filtresi",
        ["Tüm durumlar"] + DURUMLAR,
    )

    gorunen = []
    for k in kayitlar:
        if durum_filtresi != "Tüm durumlar" and k["durum"] != durum_filtresi:
            continue

        if arama.strip():
            aranacak = (
                k["takip_no"] + " " + k["olay_turu"]
            ).casefold()
            if arama.strip().casefold() not in aranacak:
                continue

        gorunen.append(k)

    st.caption(f"{len(gorunen)} kayıt gösteriliyor.")

    if not gorunen:
        st.info("Bu filtreyle eşleşen kayıt yok.")

    for k in gorunen:
        baslik = (
            f"{k['takip_no']} · {k['olay_turu']} · {k['durum']}"
        )

        with st.expander(baslik):
            sol, sag = st.columns(2)

            with sol:
                st.write(f"**Olay türü:** {k['olay_turu']}")
                st.write(f"**Ortam:** {k['ortam']}")
                st.write(f"**Yaklaşık zaman:** {k['zaman_bilgisi']}")
                st.write(f"**Tekrarlanma:** {k['tekrar_durumu']}")
                st.write(f"**Oluşturulma:** {k['olusturma_zamani']}")

            with sag:
                st.write(f"**Anonim:** {'Evet' if k['anonim'] else 'Hayır'}")

                if not k["anonim"]:
                    st.write(f"**Ad:** {k['ad'] or 'Belirtilmedi'}")
                    st.write(f"**Soyad:** {k['soyad'] or 'Belirtilmedi'}")
                    st.write(f"**Sınıf:** {k['sinif'] or 'Belirtilmedi'}")

                st.write(f"**İfade eşleşmeleri:** {k['eslesmeler']}")
                st.write(f"**Atanan birim:** {k['birim']}")

            st.markdown("**Açıklama**")
            st.write(k["aciklama"])

            st.caption(
                "Otomatik eşleşmeler karar veya kanıt değildir; "
                "insan değerlendirmesi gerekir."
            )

            with st.form(f"inceleme_{k['takip_no']}"):
                secili_durum = st.selectbox(
                    "Durum",
                    DURUMLAR,
                    index=DURUMLAR.index(k["durum"])
                    if k["durum"] in DURUMLAR else 0,
                )

                secili_birim = st.selectbox(
                    "Sorumlu demo birim",
                    BIRIMLER,
                    index=BIRIMLER.index(k["birim"])
                    if k["birim"] in BIRIMLER else 0,
                )

                kaydet = st.form_submit_button("Durumu ve birimi kaydet")

            if kaydet:
                try:
                    durum_ve_birim_guncelle(
                        k["takip_no"], secili_durum, secili_birim
                    )
                    st.success("İnceleme bilgileri kaydedildi.")
                    st.rerun()
                except sqlite3.Error:
                    st.error("Değişiklik kaydedilemedi.")

            st.markdown("**İnceleme notları**")

            with st.form(f"not_{k['takip_no']}"):
                not_metni = st.text_area(
                    "Yeni not (yalnızca kurgusal demo içeriği)",
                    max_chars=1000,
                    key=f"not_metni_{k['takip_no']}",
                )
                not_gonder = st.form_submit_button("Not ekle")

            if not_gonder:
                if not not_metni.strip():
                    st.error("Boş not eklenemez.")
                else:
                    try:
                        not_ekle(k["takip_no"], not_metni.strip())
                        st.success("Not eklendi.")
                        st.rerun()
                    except sqlite3.Error:
                        st.error("Not kaydedilemedi.")

            st.markdown("**Not geçmişi**")
            notlar = notlari_getir(k["takip_no"])

            if not notlar:
                st.caption("Henüz not eklenmedi.")
            else:
                for n in notlar:
                    st.write(f"**{n['zaman']}** — {n['not_metni']}")

            st.markdown("**İşlem geçmişi**")
            gecmis = gecmisi_getir(k["takip_no"])

            if not gecmis:
                st.caption("Henüz işlem geçmişi yok.")
            else:
                for g in gecmis:
                    st.write(f"**{g['zaman']}** · {g['islem']}")
                    if g["ayrinti"]:
                        st.caption(g["ayrinti"])


# =========================================================
# 9. GÜVENLİ KULLANIM
# =========================================================

elif sayfa == "Güvenli kullanım":
    st.title("ℹ️ Güvenli kullanım")

    st.subheader("Bu demo neler yapar?")
    st.markdown(
        """
        - Kurgusal bildirim oluşturur.
        - Anonim demo bildirimi seçeneği sunar.
        - Yönetici girişinden sonra kayıtları listeler.
        - Durum ve sorumlu demo birimini günceller.
        - İnceleme notlarını ve işlem geçmişini saklar.
        - İfade eşleşmelerini yalnızca yardımcı sinyal olarak gösterir.
        """
    )

    st.subheader("Sınırlar")
    st.markdown(
        """
        - Gerçek bir okul veya rehberlik servisine bağlı değildir.
        - Acil yardım veya resmi bildirim hizmeti değildir.
        - Zorbalık hakkında otomatik kesin karar vermez.
        - Demo oturumu, tek başına üretim düzeyinde kimlik doğrulama değildir.
        - Yerel SQLite dosyasının bulut ortamında kalıcı olacağı garanti edilmez.
        """
    )

    st.warning(
        "Gerçek öğrenci verileri kullanılmadan önce okul onayı, "
        "veri koruma planı, güçlü erişim kontrolü, güvenli yedekleme "
        "ve saklama/silme politikaları gerekir."
    )


# =========================================================
# 10. ALT BİLGİ
# =========================================================

st.divider()
st.caption(
    "🛡️ Güvenli Okul 3.0 · Araştırma ve demo prototipi · "
    "Gerçek okul sistemi değildir."
)
