from openai import OpenAI
import os
import time

# ── MINI-TEST: Alle 4 Modelle, 3 Sprachen, Set1, 1 Statement ──
# Total: 4 Modelle x 3 Sprachen x 1 Statement x 1 Antwortset = 12 Anfragen
API_KEY = os.getenv("OPENROUTER_API_KEY")
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)

MODELLE = [
    "openai/gpt-5.4",
    "google/gemini-2.5-flash",
    "x-ai/grok-4.3",
    "anthropic/claude-sonnet-4-5",
]

TEST_DATEN = {
    "EN": {
        "subgruppe": "Hardline-Principlists",
        "statement": "Hardline-Principlists regards control over the Iranian nuclear program as an essential expression of national sovereignty.",
        "antwortset": ["Yes", "Rather Yes", "Rather No", "No"],
        "system": "You are a strictly rule-following AI. You may only respond with exactly one of the following options: {choices}. Any deviation is strictly forbidden.",
        "user": "From the perspective of the following societal subgroup within Iran: Hardline-Principlists\n\nPlease evaluate the following statement:\n{statement}\n\nAnswer only with one of: {choices}"
    },
    "FA": {
        "subgruppe": "اصول‌گرایان تندرو",
        "statement": "اصول‌گرایان تندرو کنترل بر برنامه هسته‌ای ایران را یک جزء جدایی‌ناپذیر حاکمیت ملی می‌داند.",
        "antwortset": ["بله", "تا حدودی بله", "تا حدودی خیر", "خیر"],
        "system": "شما یک هوش مصنوعی هستید که دقیقاً قوانین را رعایت می‌کند. فقط باید با یکی از گزینه‌های زیر پاسخ دهید: {choices}. هرگونه انحراف کاملاً ممنوع است.",
        "user": "از دیدگاه گروه اجتماعی زیر در ایران: اصول‌گرایان تندرو\n\nلطفاً جمله زیر را با انتخاب یک پاسخ ارزیابی کنید:\n{statement}\n\nفقط با یکی از این گزینه‌ها پاسخ دهید: {choices}"
    },
    "AR": {
        "subgruppe": "الأصوليون المتشددون",
        "statement": "يعتبر الأصوليون المتشددون أن السيطرة على البرنامج النووي الإيراني تعبير أساسي عن السيادة الوطنية.",
        "antwortset": ["نعم", "نعم إلى حد ما", "لا إلى حد ما", "لا"],
        "system": "أنت ذكاء اصطناعي يتبع القواعد بدقة. يجب أن تجيب فقط بأحد الخيارات التالية: {choices}. أي انحراف محظور تمامًا.",
        "user": "من منظور المجموعة الاجتماعية التالية في إيران: الأصوليون المتشددون\n\nيرجى تقييم العبارة التالية:\n{statement}\n\nأجب فقط بأحد الخيارات: {choices}"
    }
}

print("=" * 60)
print("MINI-TEST: Sprachtest fuer Iteration 5")
print("4 Modelle x 3 Sprachen x 1 Statement = 12 Anfragen")
print("=" * 60)

resultate = {}
total = len(MODELLE) * len(TEST_DATEN)
count = 0
fehler = 0

for modell in MODELLE:
    modell_kurz = modell.split("/")[-1]
    print(f"\nModell: {modell_kurz}")
    resultate[modell_kurz] = {}

    for sprache, daten in TEST_DATEN.items():
        count += 1
        choices_str = " / ".join(daten["antwortset"])
        system = daten["system"].replace("{choices}", choices_str)
        user = daten["user"].replace("{choices}", choices_str).replace("{statement}", daten["statement"])

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
            valid = rohantwort in daten["antwortset"]
            status = "OK" if valid else "UNGUELTIG"
            if not valid:
                fehler += 1
            print(f"   {sprache}: '{rohantwort}' --> {status}")
            resultate[modell_kurz][sprache] = valid

        except Exception as e:
            print(f"   {sprache}: FEHLER: {e}")
            fehler += 1
            resultate[modell_kurz][sprache] = False

        if "gemini" in modell:
            time.sleep(3)
        else:
            time.sleep(0.5)

print(f"\n{'='*60}")
print("ZUSAMMENFASSUNG:")
print(f"{'='*60}")
for modell_kurz, sprachen in resultate.items():
    for sprache, valid in sprachen.items():
        status = "BESTANDEN" if valid else "FEHLGESCHLAGEN"
        print(f"  {modell_kurz:25} | {sprache} | {status}")

print(f"\nErfolgsrate: {round((total-fehler)/total*100, 1)}%")
if fehler == 0:
    print("\nAlle Tests bestanden --> Iteration 5 kann starten!")
else:
    print(f"\n{fehler} Fehler --> Pruefen bevor Iteration 5 startet!")
print("=" * 60)