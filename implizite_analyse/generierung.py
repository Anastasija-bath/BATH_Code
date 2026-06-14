# -*- coding: utf-8 -*-
"""
generierung.py — PHASE 1 der impliziten Framing-Bias-Analyse
BATH Anastasija Jevtic, FS26

Erzeugt Freitextbeschreibungen der vier Subgruppen.
Vollerhebung: 5 Fragen x 4 Subgruppen x 5 Modelle x 3 Sprachen x 3 Wdh = 900
Pilotmodus (PILOT=True): nur EN, 1 Wiederholung -> 100 Beschreibungen
"""

import os
import csv
import time
import requests

from prompts import (
    SUBGRUPPEN, FRAGEN, GEN_SYSTEM, SPRACHEN, MODELLE,
)

# ════════════════════════════════════════════════════════════
# KONFIGURATION
# ════════════════════════════════════════════════════════════
PILOT = False            # True = Pilotlauf (EN, 1 Wdh). False = Vollerhebung.
WIEDERHOLUNGEN = 3
PILOT_SPRACHEN = ["EN"]
PILOT_WIEDERHOLUNGEN = 1

OUTPUT_CSV = os.path.join("output", "beschreibungen.csv")
CHECKPOINT = os.path.join("output", "checkpoint_gen.txt")


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
# API-Aufruf mit Retry
# ════════════════════════════════════════════════════════════
def frage_modell(modell, system_prompt, user_prompt, max_versuche=3):
    payload = {
        "model": modell,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 400,
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
# Hauptlauf
# ════════════════════════════════════════════════════════════
def main():
    os.makedirs("output", exist_ok=True)

    sprachen = PILOT_SPRACHEN if PILOT else SPRACHEN
    wdh = PILOT_WIEDERHOLUNGEN if PILOT else WIEDERHOLUNGEN

    erledigt = lade_checkpoint()
    neu_datei = not os.path.exists(OUTPUT_CSV)

    gesamt = len(FRAGEN) * len(SUBGRUPPEN) * len(MODELLE) * len(sprachen) * wdh
    print(f"{'PILOT' if PILOT else 'VOLLERHEBUNG'} — geplante Beschreibungen: {gesamt}")
    print(f"Bereits erledigt (Checkpoint): {len(erledigt)}")

    zaehler = 0
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if neu_datei:
            writer.writerow([
                "beschreibung_id", "modell", "sprache", "subgruppe",
                "frage_id", "dimension", "wiederholung", "beschreibung"
            ])

        for modell in MODELLE:
            for sprache in sprachen:
                for sub_key, sub_labels in SUBGRUPPEN.items():
                    for frage_id, frage in FRAGEN.items():
                        for w in range(1, wdh + 1):
                            key = f"{modell}|{sprache}|{sub_key}|{frage_id}|W{w}"
                            if key in erledigt:
                                continue

                            gruppe = sub_labels[sprache]
                            system_prompt = GEN_SYSTEM[sprache]
                            user_prompt = frage[sprache].replace("{Gruppe}", gruppe)

                            antwort = frage_modell(modell, system_prompt, user_prompt)

                            beschreibung_id = key.replace("|", "_").replace("/", "-")
                            writer.writerow([
                                beschreibung_id, modell, sprache, sub_key,
                                frage_id, frage["dimension"], w, antwort
                            ])
                            f.flush()
                            speichere_checkpoint(key)

                            zaehler += 1
                            wartezeit = 1.0 if "gemini" in modell else 0.2
                            if zaehler % 10 == 0:
                                print(f"  {zaehler} Beschreibungen erzeugt... "
                                      f"(zuletzt: {sub_key}/{frage_id}/{modell.split('/')[-1]})")
                            time.sleep(wartezeit)

    print(f"\nFertig. {zaehler} neue Beschreibungen in {OUTPUT_CSV}")


if __name__ == "__main__":
    main()