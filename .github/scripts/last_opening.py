"""Дата последнего «ОТКРЫЛАСЬ ЗАПИСЬ» в канале → last.json.

Читает открытую ленту t.me/s/<канал>; меняет last.json, только если нашлось
сообщение новее записанного.
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
        tekst = re.search(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', kusok, re.S)
        vremya = re.search(r'<time[^>]*datetime="([^"]+)"', kusok)
        if not (tekst and vremya):
            continue
        chisty = html.unescape(re.sub(r"<[^>]+>", " ", tekst.group(1)))
        yield vremya.group(1), re.sub(r"\s+", " ", chisty).strip()


def poslednee(stranica: str):
    naydeno = [(t, s) for t, s in soobshcheniya(stranica) if METKA in s]
    if not naydeno:
        return None
    t, s = max(naydeno)
    vid = re.search(r"🟢\s*(.*?)\s*[—-]\s*" + METKA, s)
    return {"last": t, "kind": vid.group(1) if vid else ""}


def main() -> int:
    zapros = urllib.request.Request(f"https://t.me/s/{KANAL}", headers={"User-Agent": "Mozilla/5.0"})
    stranica = urllib.request.urlopen(zapros, timeout=30).read().decode("utf-8")
    novoe = poslednee(stranica)
    if novoe is None:
        print("в ленте нет сообщений с меткой — last.json не трогаю")
        return 0
    staroe = json.loads(FAIL.read_text(encoding="utf-8")) if FAIL.exists() else {}
    if staroe.get("last", "") >= novoe["last"]:
        print("новее нет:", staroe.get("last"))
        return 0
    FAIL.write_text(json.dumps(novoe, ensure_ascii=False) + "\n", encoding="utf-8")
    print("записано:", novoe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
