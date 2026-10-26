"""Заслон разбора ленты t.me/s/italy_belgrade_slots.

Снимок ленты от 01.10.2026 и эталон пар (время, текст), снятый прежним
разбором регулярками до замены на html.parser (ход 206 узла Prenot@mi).
Запуск: python -m unittest discover -s .github/scripts/test
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ZDES = Path(__file__).resolve().parent
sys.path.insert(0, str(ZDES.parent))

import last_opening as lo  # noqa: E402

SNIMOK = (ZDES / "lenta-2026-10-01.html").read_text(encoding="utf-8")
ETALON_PAR = [tuple(p) for p in json.loads((ZDES / "etalon-par-2026-10-01.json").read_text(encoding="utf-8"))]

# По ленте 01.10.2026 вручную (ход 207 узла Prenot@mi), с правилом 👍 (11.10.2026):
# Туризм 28.09 и Шенген 30.09 — без 👍 в снимке, поэтому в таблице прежние 21.09 и 23.09.
ETALON_VIDOV = {
    "Учёба": "2026-09-21T14:07:15+00:00",
    "Туризм": "2026-09-21T14:32:15+00:00",
    "Работа по найму / Воссоединение семьи / Другие национальные визы": "2026-09-23T07:52:15+00:00",
    "Шенген: бизнес / транзит / спорт / туризм для членов семьи граждан ЕС": "2026-09-23T07:42:14+00:00",
}


def soobshchenie(tekst_html, vremya="2026-09-01T10:00:00+00:00", klass="tgme_widget_message_text js-message_text",
                 do_teksta="", reactions=(), post=0):
    data = f'<a class="tgme_widget_message_date" href="#"><time datetime="{vremya}">10:00</time></a>' if vremya else ""
    rx = "".join(f'<span class="tgme_reaction"><i class="emoji" style="x"><b>{e}</b></i>{n}</span>' for e, n in reactions)
    rx = f'<div class="tgme_widget_message_reactions js-message_reactions">{rx}</div>' if rx else ""
    dp = f' data-post="italy_belgrade_slots/{post}"' if post else ""
    return (f'<div class="tgme_widget_message_wrap js-widget_message_wrap"><div class="tgme_widget_message"{dp}>'
            f'{do_teksta}<div class="{klass}" dir="auto">{tekst_html}</div>'
            f'{rx}<div class="tgme_widget_message_footer">{data}</div></div></div>')


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
        # По парам, а не по po_vidam: у ответа 15:27 нет 👍, и фильтр лайков скрыл бы ошибку.
        self.assertFalse([t for t, s in lo.soobshcheniya(SNIMOK)
                          if t.startswith("2026-09-28T15:27") and any(m in s for m in lo.LABELS)])

    def test_layki_iz_snimka(self):
        # Число 👍 у сообщений снимка: 8 — семь, 10 — ни одного, 18 — ни одного.
        layki = {p: th for _, _, th, p in lo.messages(SNIMOK)}
        self.assertEqual((layki[8], layki[10], layki[18]), (7, 0, 0))


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
        # 👍 у ответа есть: фильтр лайков не должен прятать ошибку разбора цитаты.
        st = f"<html>{soobshchenie('Слот был, но забрали за 2 минуты', do_teksta=tsitata, reactions=[('👍', 1)])}</html>"
        self.assertEqual(lo.po_vidam(st), {})

    def test_sostoyanie_sbrasyvaetsya_na_novom_soobshchenii(self):
        para = razobrat(soobshchenie("а", vremya="2026-09-01T10:00:00+00:00"), soobshchenie("б", vremya=None),
                        soobshchenie("в", vremya="2026-09-03T10:00:00+00:00"))
        self.assertEqual(para, [("2026-09-01T10:00:00+00:00", "а"), ("2026-09-03T10:00:00+00:00", "в")])


class Layki(unittest.TestCase):
    """Слово Владельца 11.10.2026: открытие — только сообщение, у которого есть 👍."""
    OTKR = "🇮🇹 Консульство Италии, Белград 🟢 Туризм — ОТКРЫЛАСЬ ЗАПИСЬ"

    def vidy(self, *kuski):
        return lo.po_vidam(f"<html>{''.join(kuski)}</html>")

    def test_bez_layka_ne_otkrytie(self):
        self.assertEqual(self.vidy(soobshchenie(self.OTKR)), {})

    def test_drugaya_reaktsiya_ne_layk(self):
        self.assertEqual(self.vidy(soobshchenie(self.OTKR, reactions=[("🤷‍♂", 3), ("👎", 5)])), {})

    def test_layk_sredi_drugih(self):
        st = soobshchenie(self.OTKR, vremya="2026-09-02T10:00:00+00:00", reactions=[("🤷‍♂", 3), ("👍", 1)])
        self.assertEqual(self.vidy(st), {"Туризм": "2026-09-02T10:00:00+00:00"})

    def test_pozdnee_bez_layka_ne_perekryvaet(self):
        rannee = soobshchenie(self.OTKR, vremya="2026-09-02T10:00:00+00:00", reactions=[("👍", 2)])
        pozdnee = soobshchenie(self.OTKR, vremya="2026-09-05T10:00:00+00:00")
        self.assertEqual(self.vidy(rannee, pozdnee), {"Туризм": "2026-09-02T10:00:00+00:00"})


class NewLabel(unittest.TestCase):
    """С 12.10.2026 бот пишет «СТАЛА ДОСТУПНА ФОРМА ЗАПИСИ»; сайт знал только «ОТКРЫЛАСЬ ЗАПИСЬ»
    и с 14.10 не узнал ни одной новости — Шенген для семей ЕС стоял на 23.09 при новости 26.10."""

    SNIMOK_26 = (ZDES / "lenta-2026-10-26.html").read_text(encoding="utf-8")

    def test_snimok_26_oktyabrya(self):
        # Первая страница ленты 26.10.2026 ~10:40 UTC: №42 (09:02, 👍 2) и №40 (23.10, 👍 1).
        vidy = lo.po_vidam(self.SNIMOK_26)
        self.assertEqual(vidy["Шенген: бизнес / транзит / спорт / туризм для членов семьи граждан ЕС"],
                         "2026-10-26T09:02:13+00:00")
        self.assertEqual(vidy["Работа по найму / Воссоединение семьи / Другие национальные визы"],
                         "2026-10-23T14:49:47+00:00")

    def test_v_snimkah_net_neznakomyh_novostey(self):
        # Обе ленты: новости бота со старой и с новой меткой; комментарии, опрос, ответ с цитатой.
        self.assertEqual(lo.unknown_news(lo.messages(self.SNIMOK_26)), [])
        self.assertEqual(lo.unknown_news(lo.messages(SNIMOK)), [])

    def test_neznakomaya_metka_vidna(self):
        # Любой вид метки: заглавными, строчными, с предлогом — новость узнаётся по 🟢.
        for metka in ("ПОЯВИЛИСЬ СЛОТЫ", "Форма записи доступна", "ОТКРЫТА И ДОСТУПНА"):
            st = soobshchenie(f"🇮🇹 Консульство Италии, Белград 🟢 Туризм — {metka} Записаться → x",
                              reactions=[("👍", 1)], post=50)
            self.assertEqual(lo.unknown_news(lo.messages(f"<html>{st}</html>")), [50], metka)
            # Незнакомая метка открытием не считается: что она значит, решает человек, дописав LABELS.
            self.assertEqual(lo.po_vidam(f"<html>{st}</html>"), {}, metka)

    def test_tip_s_defisom(self):
        # Тип берётся как до 26.10: до тире перед меткой, а не до первого тире.
        st = soobshchenie("🟢 Виза D-TYPE — СТАЛА ДОСТУПНА ФОРМА ЗАПИСИ", vremya="2026-10-26T09:00:00+00:00",
                          reactions=[("👍", 1)])
        self.assertEqual(lo.po_vidam(f"<html>{st}</html>"), {"Виза D-TYPE": "2026-10-26T09:00:00+00:00"})

    def main_s(self, staroe):
        znakomaya = ("2026-10-26T09:02:13+00:00", "🟢 Туризм — СТАЛА ДОСТУПНА ФОРМА ЗАПИСИ", 1, 2)
        chuzhaya = ("2026-10-26T10:00:00+00:00", "🟢 Учёба — ПОЯВИЛИСЬ СЛОТЫ", 1, 3)
        with tempfile.TemporaryDirectory() as papka:
            fail = Path(papka) / "last.json"
            if staroe is not None:
                fail.write_text(json.dumps(staroe, ensure_ascii=False), encoding="utf-8")
            with mock.patch.object(lo, "FAIL", fail), \
                    mock.patch.object(lo, "whole_channel", lambda: [znakomaya, chuzhaya]):
                kod = lo.main()
            return kod, json.loads(fail.read_text(encoding="utf-8"))

    def test_main_krasneet_no_pishet_tablitsu(self):
        tablitsa = {"vidy": [{"vid": "Туризм", "last": "2026-10-26T09:02:13+00:00"}]}
        self.assertEqual(self.main_s(None), (2, tablitsa))
        # Таблица без перемен — всё равно красный: иначе краснел бы один прогон, а дальше молчание.
        self.assertEqual(self.main_s(tablitsa), (2, tablitsa))


class Listanie(unittest.TestCase):
    """Лента листается назад до начала; не дочитали — None, файл не трогаем."""

    def lenta(self, nomera, tekst=True, feed=True):
        kuski = "".join(soobshchenie(f"n{n}" if tekst else " ", post=n, reactions=[("👍", 1)]) for n in nomera)
        return f'<html><div class="{lo.FEED_MARK}">{kuski}</div></html>' if feed else f"<html>{kuski}</html>"

    def test_ne_lenta_none(self):
        # Заглушка вместо ленты (ограничение частоты): таблицу не трогаем, а не пишем пустую.
        self.assertIsNone(lo.whole_channel(lambda before: "<html>Too many requests</html>"))
        # Заглушка на второй странице: без проверки «это лента» она сошла бы за конец канала.
        self.assertIsNone(lo.whole_channel(lambda before: "<html>Too many requests</html>" if before else self.lenta([5, 6])))

    def test_net_soobshcheniy_s_tekstom_none(self):
        # Реакции есть, сообщений с текстом нет — сказать нечего, таблицу не стираем.
        self.assertIsNone(lo.whole_channel(lambda before: self.lenta([1], tekst=False)))

    def test_pustaya_pervaya_stranitsa_none(self):
        self.assertIsNone(lo.whole_channel(lambda before: self.lenta([])))

    def test_stranitsa_bez_teksta_ne_konets(self):
        # Опросы и фото без текста — тоже сообщения: по их номерам листаем дальше.
        stranitsy = {None: [7, 8], 7: [5, 6], 5: [1, 2]}
        vse = lo.whole_channel(lambda before: self.lenta(stranitsy[before], tekst=before != 7))
        self.assertEqual(sorted(m[3] for m in vse), [1, 2, 7, 8])

    def test_bez_reaktsiy_v_kanale_none(self):
        # Разметка реакций сменилась — правило 👍 стёрло бы таблицу; не пишем.
        bez = '<html><div class="tgme_channel_history">' + soobshchenie("n1", post=1) + "</div></html>"
        self.assertIsNone(lo.whole_channel(lambda before: bez))

    def test_vse_stranitsy(self):
        stranitsy = {None: [5, 6, 7], 5: [2, 3, 4], 2: [1]}
        vse = lo.whole_channel(lambda before: self.lenta(stranitsy[before]))
        self.assertEqual(sorted(m[3] for m in vse), [1, 2, 3, 4, 5, 6, 7])

    def test_konets_lenty_pustaya_stranitsa(self):
        stranitsy = {None: [5, 6], 5: []}
        vse = lo.whole_channel(lambda before: self.lenta(stranitsy[before]))
        self.assertEqual(sorted(m[3] for m in vse), [5, 6])

    def test_ne_listaetsya_nazad(self):
        # Листание не понято: на «до 5» пришло и новое (6), и старое (1). Без проверки «страница
        # старше» скрипт счёл бы ленту дочитанной на 1 и записал таблицу без 2–4.
        vse = lo.whole_channel(lambda before: self.lenta([1, 6] if before else [5, 6]))
        self.assertIsNone(vse)

    def test_upor_v_predel_stranits(self):
        vse = lo.whole_channel(lambda before: self.lenta([(before or lo.MAX_PAGES + 5) - 1]))
        self.assertIsNone(vse)


if __name__ == "__main__":
    unittest.main()
