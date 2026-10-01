"""Последнее «ОТКРЫЛАСЬ ЗАПИСЬ» в канале по каждому типу визы → last.json.

Читает открытую ленту t.me/s/<канал>: в ней только последние сообщения,
поэтому типы, ушедшие из ленты, берутся из прежнего last.json. Файл
меняется, только если по какому-то типу нашлась дата новее записанной.

Разбор ленты — html.parser стандартной библиотеки (01.10.2026). Было —
регулярные выражения по сырому HTML; заменено по карточке Штурмана КУР1
(О-07), план принят Советником с поправками (ЗАМ1): контракт — все пары
(время, текст) на снимке ленты равны прежним, заслон краснеет, если цитату
в ответе считать открытием. Ход 206 узла Prenot@mi.
"""
import html
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

KANAL = "italy_belgrade_slots"
METKA = "ОТКРЫЛАСЬ ЗАПИСЬ"
FAIL = Path(__file__).resolve().parents[2] / "last.json"


def _soobshcheniya_regulyarki(stranica: str):
    for kusok in stranica.split('class="tgme_widget_message_wrap')[1:]:
        # js-message_text — само сообщение; js-message_reply_text — цитата в ответе, её не считать
        tekst = re.search(r'class="tgme_widget_message_text js-message_text"[^>]*>(.*?)</div>', kusok, re.S)
        vremya = re.search(r'<time[^>]*datetime="([^"]+)"', kusok)
        if not (tekst and vremya):
            continue
        chisty = html.unescape(re.sub(r"<[^>]+>", " ", tekst.group(1)))
        yield vremya.group(1), re.sub(r"\s+", " ", chisty).strip()


class _Lenta(HTMLParser):
    """Лента t.me/s: по сообщению — время и собственный текст.

    Сообщение начинается с div.tgme_widget_message_wrap — состояние
    сбрасывается на каждом. Текст — div с классами tgme_widget_message_text
    и js-message_text (классы — множеством, порядок не важен); цитата в
    ответе помечена js-message_reply_text и не берётся. Время — datetime у
    <time> внутри a.tgme_widget_message_date, первое в сообщении.

    Глубина считается только по div: void-теги (img, br, meta…) закрывающего
    тега не имеют и счёт не сбивают. Любой тег внутри текста — пробел, как
    в прежнем разборе: слова вокруг <br>, <a>, <b> не склеиваются.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.soobshcheniya = []   # [время, текст]
        self._glubina_teksta = 0  # вложенность div внутри текста; 0 — вне текста
        self._v_date = False      # внутри a.tgme_widget_message_date

    def handle_starttag(self, teg, attrs):
        klassy = set((dict(attrs).get("class") or "").split())
        if teg == "div" and "tgme_widget_message_wrap" in klassy:
            self.soobshcheniya.append(["", ""])
            self._glubina_teksta, self._v_date = 0, False
        elif not self.soobshcheniya:
            return
        elif self._glubina_teksta:
            self.soobshcheniya[-1][1] += " "
            if teg == "div":
                self._glubina_teksta += 1
        elif teg == "div" and {"tgme_widget_message_text", "js-message_text"} <= klassy \
                and "js-message_reply_text" not in klassy:
            self._glubina_teksta = 1
        elif teg == "a" and "tgme_widget_message_date" in klassy:
            self._v_date = True
        elif teg == "time" and self._v_date and not self.soobshcheniya[-1][0]:
            self.soobshcheniya[-1][0] = dict(attrs).get("datetime") or ""

    def handle_endtag(self, teg):
        if self._glubina_teksta:
            self.soobshcheniya[-1][1] += " "
            if teg == "div":
                self._glubina_teksta -= 1
        elif teg == "a":
            self._v_date = False

    def handle_data(self, dannye):
        if self._glubina_teksta:
            self.soobshcheniya[-1][1] += dannye


def soobshcheniya(stranica: str):
    lenta = _Lenta()
    lenta.feed(stranica)
    lenta.close()
    for vremya, tekst in lenta.soobshcheniya:
        tekst = re.sub(r"\s+", " ", tekst).strip()
        if vremya and tekst:
            yield vremya, tekst


def po_vidam(stranica: str) -> dict:
    """Тип визы → время последнего открытия записи."""
    itog = {}
    for t, s in soobshcheniya(stranica):
        vid = re.search(r"🟢\s*(.*?)\s*[—-]\s*" + METKA, s)
        if vid and t > itog.get(vid.group(1), ""):
            itog[vid.group(1)] = t
    return itog


def main() -> int:
    zapros = urllib.request.Request(f"https://t.me/s/{KANAL}", headers={"User-Agent": "Mozilla/5.0"})
    stranica = urllib.request.urlopen(zapros, timeout=30).read().decode("utf-8")
    staroe = json.loads(FAIL.read_text(encoding="utf-8")) if FAIL.exists() else {}
    vidy = {v["vid"]: v["last"] for v in staroe.get("vidy", [])}
    novoe = dict(vidy)
    for vid, t in po_vidam(stranica).items():
        if t > novoe.get(vid, ""):
            novoe[vid] = t
    if novoe == vidy:
        print("новее нет")
        return 0
    stroki = sorted(({"vid": v, "last": t} for v, t in novoe.items()), key=lambda r: r["last"], reverse=True)
    FAIL.write_text(json.dumps({"vidy": stroki}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("записано:", stroki)
    return 0


if __name__ == "__main__":
    sys.exit(main())
