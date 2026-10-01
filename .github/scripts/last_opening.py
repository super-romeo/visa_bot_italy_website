"""Последнее «ОТКРЫЛАСЬ ЗАПИСЬ» в канале по каждому типу визы → last.json.

Читает открытую ленту t.me/s/<канал>: в ней только последние сообщения,
поэтому типы, ушедшие из ленты, берутся из прежнего last.json. Файл
меняется, только если по какому-то типу нашлась дата новее записанной.
"""
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

KANAL = "italy_belgrade_slots"
METKA = "ОТКРЫЛАСЬ ЗАПИСЬ"
FAIL = Path(__file__).resolve().parents[2] / "last.json"


def soobshcheniya(stranica: str):
    for kusok in stranica.split('class="tgme_widget_message_wrap')[1:]:
        # js-message_text — само сообщение; js-message_reply_text — цитата в ответе, её не считать
        tekst = re.search(r'class="tgme_widget_message_text js-message_text"[^>]*>(.*?)</div>', kusok, re.S)
        vremya = re.search(r'<time[^>]*datetime="([^"]+)"', kusok)
        if not (tekst and vremya):
            continue
        chisty = html.unescape(re.sub(r"<[^>]+>", " ", tekst.group(1)))
        yield vremya.group(1), re.sub(r"\s+", " ", chisty).strip()


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
