
import re
import unicodedata


# Başlangıç listesi: örnek hakaret ve aşağılama ifadeleri.
# Eksiksiz değildir; eşleşme zorbalığın kanıtı sayılmaz.
ORNEK_IFADELER = [
    "aptal",
    "salak",
    "gerizekali",
    "ahmak",
    "budala",
    "beyinsiz",
    "akılsız",
    "beceriksiz",
    "ezik",
    "loser",
    "manyak",
    "terbiyesiz",
    "saygisiz",
    "ukala",
    "kibirli",
    "yalanci",
    "ikiyuzlu",
    "karaktersiz",
    "vicdansiz",
    "korkak",
    "rezil",
    "iğrenç",
    "itici",
    "çirkin",
    "şişko",
    "zavalli",
    "komik görünüyorsun",
    "senden nefret ediyorum",
    "kimse seni sevmiyor",
    "kimse seni istemiyor",
    "seninle dalga geçiyorum",
    "seninle dalga geçiyorlar",
    "defol git",
    "kes sesini",
    "sus artik",
    "sen yapamazsin",
    "hiçbir işe yaramıyorsun",
    "işe yaramaz",
    "adam olmaz senden",
    "seni kimse takmıyor",
    "senin aklın yok",
]


def metni_normalize_et(metin: str) -> str:
    """Metni karşılaştırma için standartlaştırır."""
    metin = unicodedata.normalize("NFC", metin.casefold())
    metin = re.sub(r"[^\w\s]", " ", metin, flags=re.UNICODE)
    metin = re.sub(r"\s+", " ", metin).strip()
    return metin


def supheli_ifadeleri_bul(metin: str) -> list[str]:
    """Eşleşen örnek ifadeleri döndürür."""
    temiz_metin = metni_normalize_et(metin)
    bulunanlar = []

    for ifade in ORNEK_IFADELER:
        temiz_ifade = metni_normalize_et(ifade)
        desen = rf"(?<!\w){re.escape(temiz_ifade)}(?!\w)"

        if re.search(desen, temiz_metin):
            bulunanlar.append(ifade)

    return bulunanlar


def inceleme_gerekli_mi(metin: str) -> bool:
    """İnsan incelemesi gerekip gerekmediğini işaretler."""
    return bool(supheli_ifadeleri_bul(metin))
