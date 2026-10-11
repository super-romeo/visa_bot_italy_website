"""Последнее «ОТКРЫЛАСЬ ЗАПИСЬ» в канале по каждому типу визы → last.json.

Открытием считается только сообщение, у которого есть хотя бы одна реакция 👍
(слово Владельца 11.10.2026: «считать появлением слотов только если у
соответствующего сообщения в канале хоть кто-то отреагировал палец вверх»).

Лента t.me/s/<канал> отдаёт последние сообщения страницей; скрипт листает её
назад (?before=<номер>) до начала канала и каждый раз считает таблицу заново.
Прежний last.json больше не источник: 👍 ставят и снимают после публикации, и
старое открытие без 👍 осталось бы в таблице навсегда. Не дочитали ленту до
конца (сеть, разметка) — файл не трогаем.

Разбор ленты — html.parser стандартной библиотеки (01.10.2026). Было —
регулярные выражения по сырому HTML; заменено по карточке Штурмана КУР1
(О-07), план принят Советником с поправками (ЗАМ1): контракт — все пары
(время, текст) на снимке ленты равны прежним, заслон краснеет, если цитату
в ответе считать открытием. Ход 206 узла Prenot@mi.
"""
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

KANAL = "italy_belgrade_slots"
METKA = "ОТКРЫЛАСЬ ЗАПИСЬ"
THUMBS_UP = "👍"
FAIL = Path(__file__).resolve().parents[2] / "last.json"
# Страниц ленты не больше этого: канал — десятки сообщений, страница — около двадцати.
# Упёрлись — значит лента не кончилась, и неполная таблица хуже прежней: не пишем.
MAX_PAGES = 50


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
        self.soobshcheniya = []   # [время, текст, 👍, номер сообщения]
        self._glubina_teksta = 0  # вложенность div внутри текста; 0 — вне текста
        self._v_date = False      # внутри a.tgme_widget_message_date
        self._reaction = None     # [эмодзи, остальное] внутри span.tgme_reaction
        self._in_emoji = False    # внутри <b> реакции — там сам эмодзи
        self.reactions_seen = 0   # реакций любого вида на странице — признак, что разметку понимаем

    def handle_starttag(self, teg, attrs):
        klassy = set((dict(attrs).get("class") or "").split())
        if teg == "div" and "tgme_widget_message_wrap" in klassy:
            self.soobshcheniya.append(["", "", 0, 0])
            self._glubina_teksta, self._v_date, self._reaction = 0, False, None
        elif not self.soobshcheniya:
            return
        elif teg == "div" and "tgme_widget_message" in klassy and not self._glubina_teksta:
            # data-post="<канал>/<номер>" — по номеру лента листается назад.
            nomer = (dict(attrs).get("data-post") or "").rsplit("/", 1)[-1]
            if nomer.isdigit():
                self.soobshcheniya[-1][3] = int(nomer)
        elif teg == "span" and "tgme_reaction" in klassy and not self._glubina_teksta:
            self._reaction = ["", ""]
            self.reactions_seen += 1
        elif self._reaction is not None and teg == "b":
            self._in_emoji = True
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
        elif self._reaction is not None and teg == "b":
            self._in_emoji = False
        elif self._reaction is not None and teg == "span":
            # «<i class="emoji"><b>👍</b></i>7»: эмодзи в <b>, число — после.
            emodzi, ostalnoe = self._reaction
            chislo = re.search(r"\d+", ostalnoe)
            if emodzi.strip() == THUMBS_UP and chislo:
                self.soobshcheniya[-1][2] += int(chislo.group())
            self._reaction, self._in_emoji = None, False

    def handle_data(self, dannye):
        if self._glubina_teksta:
            self.soobshcheniya[-1][1] += dannye
        elif self._reaction is not None:
            self._reaction[0 if self._in_emoji else 1] += dannye


def _parse(stranica: str) -> _Lenta:
    lenta = _Lenta()
    lenta.feed(stranica)
    lenta.close()
    return lenta


def _clean(entries):
    for vremya, tekst, thumbs, post in entries:
        tekst = re.sub(r"\s+", " ", tekst).strip()
        if vremya and tekst:
            yield vremya, tekst, thumbs, post


def messages(stranica: str):
    """Сообщения ленты с текстом: (время, текст, число 👍, номер сообщения)."""
    yield from _clean(_parse(stranica).soobshcheniya)


def soobshcheniya(stranica: str):
    """Пары (время, текст) — контракт снимка ленты 01.10.2026."""
    for vremya, tekst, _, _ in messages(stranica):
        yield vremya, tekst


def po_vidam(soobshch) -> dict:
    """Тип визы → время последнего открытия записи, у которого есть 👍.

    `soobshch` — страница ленты (str) либо уже разобранные сообщения.
    """
    if isinstance(soobshch, str):
        soobshch = messages(soobshch)
    itog = {}
    for t, s, thumbs, _ in soobshch:
        vid = re.search(r"🟢\s*(.*?)\s*[—-]\s*" + METKA, s)
        if vid and thumbs >= 1 and t > itog.get(vid.group(1), ""):
            itog[vid.group(1)] = t
    return itog


def fetch_page(before=None) -> str:
    adres = f"https://t.me/s/{KANAL}" + (f"?before={before}" if before else "")
    zapros = urllib.request.Request(adres, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(zapros, timeout=30).read().decode("utf-8")


FEED_MARK = "tgme_channel_history"


def whole_channel(fetch=fetch_page):
    """Все сообщения канала с текстом: страницы назад до начала. Не дочитали — None.

    «Не дочитали» — всё, что не похоже на настоящую ленту: страница без блока ленты
    (заглушка, ограничение частоты), пустая первая страница, страница «до N» с номером ≥ N
    (листание не понято), ни одной реакции во всём канале (разметка реакций сменилась —
    иначе правило 👍 молча стёрло бы таблицу), упор в MAX_PAGES. Пустая страница «до N» —
    настоящий конец ленты. Номера берутся у всех сообщений, и без текста тоже (опрос, фото):
    иначе страница из таких сообщений выглядела бы концом.
    """
    vse, before, reactions = {}, None, 0
    for _ in range(MAX_PAGES):
        stranica = fetch(before)
        if FEED_MARK not in stranica:
            return None
        lenta = _parse(stranica)
        reactions += lenta.reactions_seen
        posts = [m for m in lenta.soobshcheniya if m[3]]
        if before is not None and any(m[3] >= before for m in posts):
            return None
        if not posts:
            break
        for m in _clean(posts):
            vse[m[3]] = m
        before = min(m[3] for m in posts)
        if before <= 1:
            break
    else:
        return None
    if not vse or not reactions:
        return None
    return list(vse.values())


def main() -> int:
    vse = whole_channel()
    if vse is None:
        print("ленту не дочитали — last.json не трогаю")
        return 1
    novoe = po_vidam(vse)
    staroe = json.loads(FAIL.read_text(encoding="utf-8")) if FAIL.exists() else {}
    if novoe == {v["vid"]: v["last"] for v in staroe.get("vidy", [])}:
        print("без перемен")
        return 0
    stroki = sorted(({"vid": v, "last": t} for v, t in novoe.items()), key=lambda r: r["last"], reverse=True)
    FAIL.write_text(json.dumps({"vidy": stroki}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("записано:", stroki)
    return 0


if __name__ == "__main__":
    sys.exit(main())
