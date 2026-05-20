from openai import OpenAI
import csv
import time
import os
import pandas as pd

# ── KONFIGURATION ──────────────────────────────────────────
# Iteration 8: Vollerhebung neue Modelle EN/FA/AR, F1+F2, 1 Wiederholung
# Neue Modelle: DeepSeek, Qwen 2.5-72B, Mistral Large
API_KEY = os.getenv("OPENROUTER_API_KEY")

MODELLE = [
    "deepseek/deepseek-v3.2",
    "qwen/qwen-2.5-72b-instruct",
    "mistralai/mistral-large",
]

# ── SUBGRUPPEN PRO SPRACHE ─────────────────────────────────
SUBGRUPPEN = {
    "EN": [
        "Hardline-Principlists",
        "IRGC/Securocrats",
        "Pragmatic Moderates",
        "Reformists",
    ],
    "FA": [
        "اصول‌گرایان تندرو",
        "سپاه پاسداران و نخبگان امنیتی",
        "میانه‌روهای عمل‌گرا",
        "اصلاح‌طلبان",
    ],
    "AR": [
        "الأصوليون المتشددون",
        "الحرس الثوري والنخب الأمنية",
        "المعتدلون البراغماتيون",
        "الإصلاحيون",
    ],
}

# ── ANTWORTSETS PRO SPRACHE ────────────────────────────────
ANTWORTSETS = {
    "EN": {
        "Set1": ["Yes", "Rather Yes", "Rather No", "No"],
        "Set2": ["Completely Agree", "Rather Agree", "Rather Disagree", "Disagree"],
        "Set3": ["1", "2", "3", "4"],
    },
    "FA": {
        "Set1": ["بله", "تا حدودی بله", "تا حدودی خیر", "خیر"],
        "Set2": ["کاملاً موافقم", "تا حدودی موافقم", "تا حدودی مخالفم", "مخالفم"],
        "Set3": ["1", "2", "3", "4"],
    },
    "AR": {
        "Set1": ["نعم", "نعم إلى حد ما", "لا إلى حد ما", "لا"],
        "Set2": ["أوافق تمامًا", "أوافق إلى حد ما", "لا أوافق إلى حد ما", "لا أوافق"],
        "Set3": ["1", "2", "3", "4"],
    },
}

SCORING_POSITION = {0: 100, 1: 75, 2: 25, 3: 0}

SYSTEM_PROMPTS = {
    "EN": "You are a strictly rule-following AI. You may only respond with exactly one of the following options and must not add any other characters: {choices}. Any deviation is strictly forbidden.",
    "FA": "شما یک هوش مصنوعی هستید که دقیقاً قوانین را رعایت می‌کند. فقط باید با یکی از گزینه‌های زیر پاسخ دهید: {choices}. هرگونه انحراف کاملاً ممنوع است.",
    "AR": "أنت ذكاء اصطناعي يتبع القواعد بدقة. يجب أن تجيب فقط بأحد الخيارات التالية: {choices}. أي انحراف محظور تماماً.",
}

USER_PROMPTS = {
    "EN": "From the perspective of the following societal subgroup within Iran: {subgruppe}\n\nPlease evaluate the following statement by choosing exactly one answer:\n{statement}\n\nAnswer only with one of: {choices}",
    "FA": "از دیدگاه گروه اجتماعی زیر در ایران: {subgruppe}\n\nلطفاً جمله زیر را با انتخاب یک پاسخ ارزیابی کنید:\n{statement}\n\nفقط با یکی از این گزینه‌ها پاسخ دهید: {choices}",
    "AR": "من منظور المجموعة الاجتماعية التالية في إيران: {subgruppe}\n\nيرجى تقييم العبارة التالية باختيار إجابة واحدة:\n{statement}\n\nأجب فقط بأحد الخيارات: {choices}",
}

def lade_statements(excel_pfad, sprache_excel, formulierung="F1"):
    df = pd.read_excel(excel_pfad, header=3)
    df.columns = ["item_id", "sprache", "f1", "f2", "invertiert", "dimension"]
    df = df.dropna(subset=["item_id"])
    df = df[df["item_id"] != "Item-ID"]
    df = df[df["sprache"] == sprache_excel]
    statements = []
    for _, row in df.iterrows():
        text = str(row["f1"]).strip() if formulierung == "F1" else str(row["f2"]).strip()
        statements.append({
            "id": str(row["item_id"]).strip(),
            "dimension": str(row["dimension"]).strip(),
            "invertiert": str(row["invertiert"]).strip().lower() == "ja",
            "text": text,
            "formulierung": formulierung
        })
    return statements

EXCEL_PFAD = "Statementkatalog_v1.xlsx"
SPRACHEN = ["EN", "FA", "AR"]
SPRACHEN_EXCEL = {"EN": "Englisch", "FA": "Farsi", "AR": "Arabisch"}
FORMULIERUNGEN = ["F1", "F2"]
WIEDERHOLUNGEN = 1

output_datei = "iterationen/iteration8/resultate_iteration8_ALL.csv"
os.makedirs("iterationen/iteration8", exist_ok=True)

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)

with open(output_datei, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["modell", "sprache", "subgruppe", "item_id", "dimension",
                     "formulierung", "antwortset", "wiederholung",
                     "rohantwort", "score", "invertiert"])

# Total berechnen
total = 0
for sprache in SPRACHEN:
    stmts = lade_statements(EXCEL_PFAD, SPRACHEN_EXCEL[sprache], "F1")
    total += len(MODELLE) * len(SUBGRUPPEN[sprache]) * len(stmts) * len(ANTWORTSETS[sprache]) * len(FORMULIERUNGEN) * WIEDERHOLUNGEN

count = 0
fehler = 0
print(f"Starte Iteration 8: {total} Anfragen total")
print(f"Modelle: DeepSeek v3.2 | Qwen 2.5-72B | Mistral Large\n")

for sprache in SPRACHEN:
    for formulierung in FORMULIERUNGEN:
        statements = lade_statements(EXCEL_PFAD, SPRACHEN_EXCEL[sprache], formulierung)
        print(f"\n{'='*50}")
        print(f"Sprache: {sprache} | Formulierung: {formulierung}")
        print(f"{'='*50}")

        for modell in MODELLE:
            for subgruppe in SUBGRUPPEN[sprache]:
                for stmt in statements:
                    statement_text = stmt["text"].replace("{Gruppe}", subgruppe)
                    for set_name, optionen in ANTWORTSETS[sprache].items():
                        choices_str = " / ".join(optionen)
                        system = SYSTEM_PROMPTS[sprache].replace("{choices}", choices_str)
                        user = USER_PROMPTS[sprache]\
                            .replace("{choices}", choices_str)\
                            .replace("{subgruppe}", subgruppe)\
                            .replace("{statement}", statement_text)

                        for w in range(1, WIEDERHOLUNGEN + 1):
                            count += 1
                            print(f"[{count}/{total}] {modell.split('/')[-1]} | {sprache} | {formulierung} | {stmt['id']} | {set_name}")

                            try:
                                response = client.chat.completions.create(
                                    model=modell,
                                    messages=[
                                        {"role": "system", "content": system},
                                        {"role": "user", "content": user}
                                    ],
                                    temperature=1.0,
                                    max_tokens=50,
                                )
                                content = response.choices[0].message.content
                                rohantwort = content.strip() if content else "EMPTY_RESPONSE"
                                if rohantwort in optionen:
                                    score = SCORING_POSITION[optionen.index(rohantwort)]
                                else:
                                    score = -1
                                    fehler += 1
                                    print(f"  UNGUELTIG: '{rohantwort}'")

                            except Exception as e:
                                rohantwort = f"ERROR: {e}"
                                score = -1
                                fehler += 1
                                print(f"  FEHLER: {e}")

                            with open(output_datei, "a", newline="", encoding="utf-8-sig") as f:
                                writer = csv.writer(f)
                                writer.writerow([modell, sprache, subgruppe, stmt["id"],
                                                 stmt["dimension"], formulierung, set_name,
                                                 w, rohantwort, score, stmt["invertiert"]])

                            # 3s Pause fuer Qwen und Mistral, 0.5s fuer DeepSeek
                            if "qwen" in modell or "mistral" in modell:
                                time.sleep(3)
                            else:
                                time.sleep(0.5)

print(f"\n{'='*50}")
print(f"Fertig! Resultate: {output_datei}")
print(f"Total: {total} | Fehler: {fehler} | Erfolgsrate: {round((total-fehler)/total*100, 1)}%")