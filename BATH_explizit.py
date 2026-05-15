from openai import OpenAI
import csv
import time
import os
import pandas as pd

# ── KONFIGURATION ──────────────────────────────────────────
# Iteration 4: Vollständiger EN-Test mit neuem Gemini-Modell (gemini-2.5-flash)
API_KEY = os.getenv("OPENROUTER_API_KEY")

MODELLE = [
    "openai/gpt-5.4",
    "google/gemini-2.5-flash",          # NEU: ersetzt gemini-2.5-pro
    "x-ai/grok-3",
    "anthropic/claude-sonnet-4-5",
]

SUBGRUPPEN = [
    "Hardline-Principlists",
    "IRGC/Securocrats",
    "Pragmatic Moderates",
    "Reformists",
]

ANTWORTSETS = {
    "Set1": ["Yes", "Rather Yes", "Rather No", "No"],
    "Set2": ["Completely Agree", "Rather Agree", "Rather Disagree", "Disagree"],
    "Set3": ["1", "2", "3", "4"],
}

SCORING = {
    "Yes": 100, "Rather Yes": 75, "Rather No": 25, "No": 0,
    "Completely Agree": 100, "Rather Agree": 75, "Rather Disagree": 25, "Disagree": 0,
    "1": 100, "2": 75, "3": 25, "4": 0
}

def lade_statements(excel_pfad, sprache="Englisch"):
    df = pd.read_excel(excel_pfad, header=3)
    df.columns = ["item_id", "sprache", "f1", "f2", "invertiert", "dimension"]
    df = df.dropna(subset=["item_id"])
    df = df[df["item_id"] != "Item-ID"]
    df = df[df["sprache"] == sprache]
    statements = []
    for _, row in df.iterrows():
        statements.append({
            "id": str(row["item_id"]).strip(),
            "dimension": str(row["dimension"]).strip(),
            "invertiert": str(row["invertiert"]).strip().lower() == "ja",
            "F1": str(row["f1"]).strip()
        })
    return statements

SPRACHE = "Englisch"
EXCEL_PFAD = "Statementkatalog_v1.xlsx"
STATEMENTS = lade_statements(EXCEL_PFAD, SPRACHE)
print(f"✅ {len(STATEMENTS)} Statements geladen ({SPRACHE})")

WIEDERHOLUNGEN = 1
output_datei = "iterationen/iteration4/resultate_iteration4_EN.csv"

os.makedirs("iterationen/iteration4", exist_ok=True)

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)

with open(output_datei, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["modell", "subgruppe", "item_id", "dimension",
                     "formulierung", "antwortset", "wiederholung",
                     "rohantwort", "score", "invertiert"])

total = len(MODELLE) * len(SUBGRUPPEN) * len(STATEMENTS) * len(ANTWORTSETS) * WIEDERHOLUNGEN
count = 0
fehler = 0
print(f"Starte Iteration 4 EN: {total} Anfragen total\n")

for modell in MODELLE:
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
                    print(f"[{count}/{total}] {modell} | {subgruppe} | {stmt['id']} | {set_name} | W{w}")
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
                        if score == -1:
                            fehler += 1
                            print(f"  ⚠️  Ungültige Antwort: '{rohantwort}'")
                    except Exception as e:
                        rohantwort = f"ERROR: {e}"
                        score = -1
                        fehler += 1
                        print(f"  ❌ Fehler: {e}")

                    with open(output_datei, "a", newline="", encoding="utf-8-sig") as f:
                        writer = csv.writer(f)
                        writer.writerow([modell, subgruppe, stmt["id"],
                                         stmt["dimension"], "F1", set_name,
                                         w, rohantwort, score, stmt["invertiert"]])

                    if "gemini" in modell:
                        time.sleep(3)
                    else:
                        time.sleep(0.5)

print(f"\n{'='*50}")
print(f"Fertig! Resultate: {output_datei}")
print(f"Total: {total} | Fehler: {fehler} | Erfolgsrate: {round((total-fehler)/total*100, 1)}%")