# -*- coding: utf-8 -*-
"""
bewertung.py — PHASE 2 der impliziten Framing-Bias-Analyse
BATH Anastasija Jevtic, FS26

Liest output/beschreibungen.csv und laesst jede Beschreibung von allen 5
Modellen (LLM-as-Judge) auf der gerichteten Framing-Achse bewerten (3 Sets).
Bewertung erfolgt BLIND (Judge sieht das erzeugende Modell nicht).
"""

import os
import csv
import re
import time
import requests

from prompts import (
    BEWERTUNG_SYSTEM, ANTWORTSETS, SET_HINWEIS, MODELLE,
)

# ════════════════════════════════════════════════════════════
# KONFIGURATION
# ════════════════════════════════════════════════════════════
PILOT = False   # muss zur Phase 1 passen
SELF_BEWERTUNG_ZULASSEN = True   # Modelle duerfen eigene Texte bewerten (markiert)

BESCHREIBUNGEN_CSV = os.path.join("output", "beschreibungen.csv")
OUTPUT_CSV = os.path.join("output", "bewertungen.csv")
CHECKPOINT = os.path.join("output", "checkpoint_bew.txt")

JUDGES = MODELLE


def lade_api_key():
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key
    env_pfad = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_pfad):
        with open(env_pfad, "r", encoding="utf-8") as f:
            for zeile in f:
                if zeile.strip().startswith("OPENROUTER_API_KEY"):
                    return zeile.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("Kein API-Key gefunden (OPENROUTER_API_KEY).")

API_KEY = lade_api_key()
API_URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


# ════════════════════════════════════════════════════════════
# Hilfsfunktionen fuer das robuste Set1-Matching
# ════════════════════════════════════════════════════════════
# Das generische "Framing"-Wort pro Sprache. Es wird beim Matching ignoriert,
# damit Antworten wie "Strongly sovereignty-affirming" (ohne "framing") oder
# mit fehlendem Bindestrich trotzdem korrekt erkannt werden.
FRAMING_WORT = {"EN": "framing", "FA": "قاب‌بندی", "AR": "تأطير"}


def _normalisiere(s):
    """Kleinschreibung, Bindestriche -> Leerzeichen, Satzzeichen entfernen,
    Mehrfach-Leerzeichen zusammenfassen."""
    s = s.strip().lower().replace("-", " ")
    for z in ".,;:!?()[]«»\"'،؛":
        s = s.replace(z, " ")
    return " ".join(s.split())


def _kern_tokens(option, sprache):
    """Distinktive Tokens einer Set1-Option ohne das generische Framing-Wort."""
    fw = _normalisiere(FRAMING_WORT[sprache])
    return [t for t in _normalisiere(option).split() if t != fw]


# ════════════════════════════════════════════════════════════
# Antwort eines Judge -> Score [-100..+100]
# ════════════════════════════════════════════════════════════
def parse_score(antwort_raw, set_name, sprache):
    optionen = ANTWORTSETS[set_name][sprache]
    ant = antwort_raw.strip()

    # ---- Set2 / Set3: Buchstaben bzw. Ziffern (inkl. FA/AR-Ziffern) ----
    if set_name in ("Set2", "Set3"):
        ziffer_map = {"١": "1", "٢": "2", "٣": "3", "٤": "4", "٥": "5",
                      "۱": "1", "۲": "2", "۳": "3", "۴": "4", "۵": "5"}
        ant_norm = ant
        for fremd, lat in ziffer_map.items():
            ant_norm = ant_norm.replace(fremd, lat)
        for opt, score in optionen.items():
            if ant_norm.strip() == opt:
                return score, opt
        for opt, score in optionen.items():
            if re.search(rf"(?<![A-Za-z0-9]){re.escape(opt)}(?![A-Za-z0-9])", ant_norm):
                return score, opt
        return None, None

    # ---- Set1: robuster Stamm-Matcher ----
    ant_norm = _normalisiere(ant)
    # 1) exakte (normalisierte) Uebereinstimmung
    for opt, score in optionen.items():
        if _normalisiere(opt) == ant_norm:
            return score, opt
    # 2) alle Kern-Tokens der Option im Antworttext vorhanden -> spezifischste Option
    ant_set = set(ant_norm.split())
    bester, beste_score, beste_n, gleichstand = None, None, 0, False
    for opt, score in optionen.items():
        kern = _kern_tokens(opt, sprache)
        if kern and all(t in ant_set for t in kern):
            if len(kern) > beste_n:
                bester, beste_score, beste_n, gleichstand = opt, score, len(kern), False
            elif len(kern) == beste_n:
                gleichstand = True
    if bester is not None and not gleichstand:
        return beste_score, bester
    return None, None


def baue_choices_string(set_name, sprache):
    optionen = list(ANTWORTSETS[set_name][sprache].keys())
    choices = ", ".join(optionen)
    choices += SET_HINWEIS[set_name][sprache]
    return choices


# ════════════════════════════════════════════════════════════
# API-Aufruf
# ════════════════════════════════════════════════════════════
def frage_judge(judge, system_prompt, text, max_versuche=3):
    payload = {
        "model": judge,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        "temperature": 0.0,
        "max_tokens": 40,
    }
    for versuch in range(max_versuche):
        try:
            r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=90)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            if versuch < max_versuche - 1:
                time.sleep(5)
            else:
                return f"[FEHLER: {e}]"


# ════════════════════════════════════════════════════════════
# Checkpoint
# ════════════════════════════════════════════════════════════
def lade_checkpoint():
    if os.path.exists(CHECKPOINT):
        with open(CHECKPOINT, "r", encoding="utf-8") as f:
            return set(z.strip() for z in f if z.strip())
    return set()

def speichere_checkpoint(key):
    with open(CHECKPOINT, "a", encoding="utf-8") as f:
        f.write(key + "\n")


# ════════════════════════════════════════════════════════════
# Beschreibungen laden
# ════════════════════════════════════════════════════════════
def lade_beschreibungen():
    if not os.path.exists(BESCHREIBUNGEN_CSV):
        raise RuntimeError(
            f"{BESCHREIBUNGEN_CSV} nicht gefunden. Zuerst generierung.py ausfuehren."
        )
    zeilen = []
    with open(BESCHREIBUNGEN_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["beschreibung"].startswith("[FEHLER"):
                continue
            zeilen.append(row)
    return zeilen


# ════════════════════════════════════════════════════════════
# Hauptlauf
# ════════════════════════════════════════════════════════════
def main():
    os.makedirs("output", exist_ok=True)
    beschreibungen = lade_beschreibungen()
    erledigt = lade_checkpoint()
    neu_datei = not os.path.exists(OUTPUT_CSV)

    set_namen = list(ANTWORTSETS.keys())
    gesamt = len(beschreibungen) * len(JUDGES) * len(set_namen)
    print(f"{'PILOT' if PILOT else 'VOLLERHEBUNG'} — Beschreibungen: {len(beschreibungen)}")
    print(f"Geplante Bewertungen: {gesamt}")
    print(f"Bereits erledigt (Checkpoint): {len(erledigt)}")

    zaehler = 0
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if neu_datei:
            writer.writerow([
                "bewertung_id", "beschreibung_id",
                "beschreibendes_modell", "judge_modell", "ist_self",
                "sprache", "subgruppe", "frage_id", "dimension",
                "antwortset", "judge_antwort_raw", "matched_option", "framing_score"
            ])

        for row in beschreibungen:
            text = row["beschreibung"]
            sprache = row["sprache"]
            besch_modell = row["modell"]

            for judge in JUDGES:
                ist_self = (judge == besch_modell)
                if ist_self and not SELF_BEWERTUNG_ZULASSEN:
                    continue

                for set_name in set_namen:
                    key = f"{row['beschreibung_id']}|{judge}|{set_name}"
                    if key in erledigt:
                        continue

                    choices = baue_choices_string(set_name, sprache)
                    system_prompt = BEWERTUNG_SYSTEM[sprache].replace("{choices}", choices)

                    antwort_raw = frage_judge(judge, system_prompt, text)
                    score, matched = parse_score(antwort_raw, set_name, sprache)

                    bewertung_id = key.replace("|", "_").replace("/", "-")
                    writer.writerow([
                        bewertung_id, row["beschreibung_id"],
                        besch_modell, judge, int(ist_self),
                        sprache, row["subgruppe"], row["frage_id"], row["dimension"],
                        set_name, antwort_raw,
                        matched if matched is not None else "",
                        score if score is not None else ""
                    ])
                    f.flush()
                    speichere_checkpoint(key)

                    zaehler += 1
                    wartezeit = 1.0 if "gemini" in judge else 0.2
                    if zaehler % 20 == 0:
                        print(f"  {zaehler} Bewertungen... "
                              f"(zuletzt: {row['subgruppe']}/{set_name}/{judge.split('/')[-1]})")
                    time.sleep(wartezeit)

    print(f"\nFertig. {zaehler} neue Bewertungen in {OUTPUT_CSV}")
    nicht_geparst = 0
    with open(OUTPUT_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["framing_score"] == "":
                nicht_geparst += 1
    if nicht_geparst:
        print(f"Hinweis: {nicht_geparst} Bewertungen ohne erkannten Score.")


if __name__ == "__main__":
    main()