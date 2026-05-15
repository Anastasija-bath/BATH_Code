from openai import OpenAI
import csv
import time
import os
import pandas as pd

# ── KONFIGURATION ──────────────────────────────────────────
# Iteration 3: Gemini Diagnoseiteration
# Ziel: Isolierung der Fehlerursache bei Gemini-Modellen über OpenRouter

API_KEY = os.getenv("OPENROUTER_API_KEY")

MODELLE = [
    "google/gemini-2.5-pro",
    "google/gemini-2.5-flash",
    "google/gemini-2.5-pro-preview",
    "google/gemini-2.0-flash-001",
    "google/gemini-3-flash-preview",
    "google/gemini-3.1-flash-lite",
]

# Minimale Konfiguration: nur 1 Subgruppe, 1 Antwortset
SUBGRUPPEN = ["Hardline-Principlists"]

ANTWORTSETS = {
    "Set1": ["Yes", "Rather Yes", "Rather No", "No"],
}

SCORING = {
    "Yes": 100, "Rather Yes": 75, "Rather No": 25, "No": 0,
}

# Nur NS-Dimension (4 Items)
STATEMENTS = [
    {"id": "NS1", "dimension": "Nuklearer Souveränitätsanspruch", "invertiert": False,
     "F1": "{Gruppe} regards control over the Iranian nuclear program as an essential expression of national sovereignty."},
    {"id": "NS2", "dimension": "Nuklearer Souveränitätsanspruch", "invertiert": False,
     "F1": "{Gruppe} supports Iran deciding independently on the scope and direction of its nuclear program."},
    {"id": "NS3", "dimension": "Nuklearer Souveränitätsanspruch", "invertiert": False,
     "F1": "{Gruppe} sees the Iranian nuclear program as an expression of national independence and political self-determination."},
    {"id": "NS4", "dimension": "Nuklearer Souveränitätsanspruch", "invertiert": True,
     "F1": "{Gruppe} does not attribute any special significance to the Iranian nuclear program in terms of national sovereignty."},
]

WIEDERHOLUNGEN = 1
output_datei = "iterationen/iteration3/resultate_iteration3_gemini_diagnose.csv"

# Ordner erstellen falls nicht vorhanden
os.makedirs("iterationen/iteration3", exist_ok=True)

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)

with open(output_datei, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["modell", "subgruppe", "item_id", "dimension",
                     "formulierung", "antwortset", "wiederholung",
                     "rohantwort", "score", "invertiert", "status"])

total = len(MODELLE) * len(SUBGRUPPEN) * len(STATEMENTS) * len(ANTWORTSETS) * WIEDERHOLUNGEN
count = 0
print(f"Starte Gemini Diagnoseiteration (Iteration 3): {total} Anfragen total\n")
print("=" * 60)

for modell in MODELLE:
    print(f"\n🔍 Teste Modell: {modell}")
    modell_fehler = 0
    modell_total = 0

    for subgruppe in SUBGRUPPEN:
        for stmt in STATEMENTS:
            statement_text = stmt["F1"].replace("{Gruppe}", subgruppe)
            for set_name, optionen in ANTWORTSETS.items():
                choices_str = " / ".join(optionen)
                system_prompt = (
                    f"You are a strictly rule-following AI. You may only respond with "
                    f"exactly one of the following options and must not add any other "
                    f"characters: {choices_str}. Any deviation is strictly forbidden."
                )
                user_prompt = (
                    f"From the perspective of the following societal subgroup within Iran: "
                    f"{subgruppe}\n\n"
                    f"Please evaluate the following statement by choosing exactly one answer:\n"
                    f"{statement_text}\n\n"
                    f"Answer only with one of: {choices_str}"
                )
                for w in range(1, WIEDERHOLUNGEN + 1):
                    count += 1
                    modell_total += 1
                    try:
                        response = client.chat.completions.create(
                            model=modell,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            temperature=1.0,
                            max_tokens=50,
                        )
                        content = response.choices[0].message.content
                        rohantwort = content.strip() if content else "EMPTY_RESPONSE"
                        score = SCORING.get(rohantwort, -1)
                        status = "OK" if score != -1 else "UNGÜLTIG"
                        if score == -1:
                            modell_fehler += 1
                            print(f"  ⚠️  {stmt['id']} | {set_name}: '{rohantwort}'")
                        else:
                            print(f"  ✅ {stmt['id']} | {set_name}: '{rohantwort}' (Score: {score})")
                    except Exception as e:
                        rohantwort = f"ERROR: {e}"
                        score = -1
                        status = "ERROR"
                        modell_fehler += 1
                        print(f"  ❌ {stmt['id']} | {set_name}: {e}")

                    with open(output_datei, "a", newline="", encoding="utf-8-sig") as f:
                        writer = csv.writer(f)
                        writer.writerow([modell, subgruppe, stmt["id"],
                                         stmt["dimension"], "F1", set_name,
                                         w, rohantwort, score, stmt["invertiert"], status])
                    time.sleep(3)

    erfolgsrate = round((modell_total - modell_fehler) / modell_total * 100, 1)
    print(f"  → Erfolgsrate: {erfolgsrate}% ({modell_total - modell_fehler}/{modell_total})")

print(f"\n{'='*60}")
print(f"DIAGNOSE ABGESCHLOSSEN")
print(f"Resultate gespeichert in: {output_datei}")
print(f"\nEmpfehlung:")
print(f"Modelle mit 100% Erfolgsrate → für Haupterhebung verwenden")
print(f"Modelle mit <50% Erfolgsrate → ausschliessen")