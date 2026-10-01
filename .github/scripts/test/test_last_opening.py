"""Заслон разбора ленты t.me/s/italy_belgrade_slots.

Снимок ленты от 01.10.2026 и эталон пар (время, текст), снятый прежним
разбором регулярками до замены на html.parser (ход 206 узла Prenot@mi).
Запуск: python -m unittest discover -s .github/scripts/test
"""
import json
import sys
import unittest
from pathlib import Path

ZDES = Path(__file__).resolve().parent
sys.path.insert(0, str(ZDES.parent))

import last_opening as lo  # noqa: E402

SNIMOK = (ZDES / "lenta-2026-10-01.html").read_text(encoding="utf-8")
ETALON_PAR = [tuple(p) for p in json.loads((ZDES / "etalon-par-2026-10-01.json").read_text(encoding="utf-8"))]

# По ленте 01.10.2026 вручную (ход 207 узла Prenot@mi).
ETALON_VIDOV = {
    "Учёба": "2026-09-21T14:07:15+00:00",
    "Туризм": "2026-09-28T11:54:04+00:00",
    "Работа по найму / Воссоединение семьи / Другие национальные визы": "2026-09-23T07:52:15+00:00",
    "Шенген: бизнес / транзит / спорт / туризм для членов семьи граждан ЕС": "2026-09-30T18:11:29+00:00",
}


def soobshchenie(tekst_html, vremya="2026-09-01T10:00:00+00:00", klass="tgme_widget_message_text js-message_text",
                 do_teksta=""):
    data = f'<a class="tgme_widget_message_date" href="#"><time datetime="{vremya}">10:00</time></a>' if vremya else ""
    return (f'<div class="tgme_widget_message_wrap js-widget_message_wrap"><div class="tgme_widget_message">'
            f'{do_teksta}<div class="{klass}" dir="auto">{tekst_html}</div>'
            f'<div class="tgme_widget_message_footer">{data}</div></div></div>')


def razobrat(*kuski):
    return list(lo.soobshcheniya(f"<html><body>{''.join(kuski)}</body></html>"))


class Snimok(unittest.TestCase):
    def test_vse_pary_kak_v_etalone(self):
        self.assertEqual(list(lo.soobshcheniya(SNIMOK)), ETALON_PAR)

    def test_po_vidam(self):
        self.assertEqual(lo.po_vidam(SNIMOK), ETALON_VIDOV)

    def test_tsitata_v_otvete_ne_otkrytie(self):
        # 28.09 15:27:36 — ответ-комментарий «Слот был, но забрали за 2 минуты»
        # с цитатой «Туризм — ОТКРЫЛАСЬ ЗАПИСЬ». Сочти цитату — Туризм уедет на 15:27.
        self.assertEqual(lo.po_vidam(SNIMOK)["Туризм"], "2026-09-28T11:54:04+00:00")


class Sinteticheskie(unittest.TestCase):
    METKA = "🇮🇹 Консульство Италии, Белград 🟢 Учёба — ОТКРЫЛАСЬ ЗАПИСЬ"

    def test_klassy_v_drugom_poryadke(self):
        self.assertEqual(razobrat(soobshchenie("а", klass="js-message_text tgme_widget_message_text extra"))[0][1], "а")

    def test_sushchnosti(self):
        self.assertEqual(razobrat(soobshchenie("«A &amp; B» &quot;x&quot;"))[0][1], "«A & B» \"x\"")

    def test_vlozhennye_inline_i_br_ne_skleivayut_slova(self):
        self.assertEqual(razobrat(soobshchenie("<b>Туризм</b>—<i>ОТКРЫЛАСЬ</i><br>ЗАПИСЬ"))[0][1],
                         "Туризм — ОТКРЫЛАСЬ ЗАПИСЬ")

    def test_void_tegi_ne_sbivayut_granitsy(self):
        para = razobrat(soobshchenie('раз<img src="x"><br>два<meta x="1">'), soobshchenie("три"))
        self.assertEqual([t for _, t in para], ["раз два", "три"])

    def test_bez_teksta_propuskaetsya(self):
        self.assertEqual(razobrat(soobshchenie("   ")), [])

    def test_bez_vremeni_propuskaetsya(self):
        self.assertEqual(razobrat(soobshchenie("а", vremya=None)), [])

    def test_vremya_tolko_iz_daty_soobshcheniya(self):
        # <time> в тексте или в цитате — не время сообщения
        lishnee = '<time datetime="2020-01-01T00:00:00+00:00">x</time>'
        para = razobrat(soobshchenie("а" + lishnee, do_teksta=lishnee))
        self.assertEqual(para[0][0], "2026-09-01T10:00:00+00:00")

    def test_tsitata_s_metkoy_ne_otkrytie(self):
        tsitata = f'<div class="tgme_widget_message_text js-message_reply_text">{self.METKA}</div>'
        st = f"<html>{soobshchenie('Слот был, но забрали за 2 минуты', do_teksta=tsitata)}</html>"
        self.assertEqual(lo.po_vidam(st), {})

    def test_sostoyanie_sbrasyvaetsya_na_novom_soobshchenii(self):
        para = razobrat(soobshchenie("а", vremya="2026-09-01T10:00:00+00:00"), soobshchenie("б", vremya=None),
                        soobshchenie("в", vremya="2026-09-03T10:00:00+00:00"))
        self.assertEqual(para, [("2026-09-01T10:00:00+00:00", "а"), ("2026-09-03T10:00:00+00:00", "в")])


if __name__ == "__main__":
    unittest.main()
