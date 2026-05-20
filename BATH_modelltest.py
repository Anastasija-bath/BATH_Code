from openai import OpenAI
import os
import time

# ── ITERATION 7: Modelltest Durchlauf 3 — Qwen Diagnose ───
# Alle relevanten Qwen Modelle testen
# Total: 4 Modelle x 3 Sprachen = 12 Anfragen

API_KEY = os.getenv("OPENROUTER_API_KEY")
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)

MODELLE = [
    "qwen/qwen3-32b",
    "qwen/qwen3-14b",
    "qwen/qwen-2.5-72b-instruct",
    "qwen/qwen3-8b",
]

TEST_DATEN = {
    "EN": {
        "subgruppe": "Hardline-Principlists",
        "statement": "Hardline-Principlists regards control over the Iranian nuclear program as an essential expression of national sovereignty.",
        "antwortset": ["Yes", "Rather Yes", "Rather No", "No"],
        "system": "You are a strictly rule-following AI. You may only respond with exactly one of the following options: {choices}. Any deviation is strictly forbidden.",
        "user": "From the perspective of the following societal subgroup within Iran: {subgruppe}\n\nPlease evaluate the following statement:\n{statement}\n\nAnswer only with one of: {choices}"
    },
    "FA": {
        "subgruppe": "اصول‌گرایان تندرو",
        "statement": "اصول‌گرایان تندرو کنترل بر برنامه هسته‌ای ایران را یک جزء جدایی‌ناپذیر حاکمیت ملی می‌داند.",
        "antwortset": ["بله", "تا حدودی بله", "تا حدودی خیر", "خیر"],
        "system": "شما یک هوش مصنوعی هستید که دقیقاً قوانین را رعایت می‌کند. فقط باید با یکی از گزینه‌های زیر پاسخ دهید: {choices}. هرگونه انحراف کاملاً ممنوع است.",
        "user": "از دیدگاه گروه اجتماعی زیر در ایران: {subgruppe}\n\nلطفاً جمله زیر را با انتخاب یک پاسخ ارزیابی کنید:\n{statement}\n\nفقط با یکی از این گزینه‌ها پاسخ دهید: {choices}"
    },
    "AR": {
        "subgruppe": "الأصوليون المتشددون",
        "statement": "يعتبر الأصوليون المتشددون أن السيطرة على البرنامج النووي الإيراني تعبير أساسي عن السيادة الوطنية.",
        "antwortset": ["نعم", "نعم إلى حد ما", "لا إلى حد ما", "لا"],
        "system": "أنت ذكاء اصطناعي يتبع القواعد بدقة. يجب أن تجيب فقط بأحد الخيارات التالية: {choices}. أي انحراف محظور تماماً.",
        "user": "من منظور المجموعة الاجتماعية التالية في إيران: {subgruppe}\n\nيرجى تقييم العبارة التالية:\n{statement}\n\nأجب فقط بأحد الخيارات: {choices}"
    },
}

print("=" * 60)
print("ITERATION 7 - Durchlauf 3: Qwen Diagnose")
print(f"{len(MODELLE)} Modelle x 3 Sprachen = {len(MODELLE)*3} Anfragen")
print("=" * 60)

resultate = {}
total = len(MODELLE) * len(TEST_DATEN)
fehler = 0

for modell in MODELLE:
    modell_kurz = modell.split("/")[-1]
    print(f"\nModell: {modell_kurz}")
    resultate[modell_kurz] = {}

    for sprache, daten in TEST_DATEN.items():
        choices_str = " / ".join(daten["antwortset"])
        system = daten["system"].replace("{choices}", choices_str)
        user = daten["user"].replace("{choices}", choices_str)\
                            .replace("{subgruppe}", daten["subgruppe"])\
                            .replace("{statement}", daten["statement"])

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
            print(f"   {sprache}: '{rohantwort[:60]}' --> {status}")
            resultate[modell_kurz][sprache] = valid

        except Exception as e:
            print(f"   {sprache}: FEHLER: {str(e)[:80]}")
            fehler += 1
            resultate[modell_kurz][sprache] = False

        time.sleep(3)

print(f"\n{'='*60}")
print("ZUSAMMENFASSUNG:")
print(f"{'='*60}")
for modell_kurz, sprachen in resultate.items():
    for sprache, valid in sprachen.items():
        status = "BESTANDEN" if valid else "FEHLGESCHLAGEN"
        print(f"  {modell_kurz:30} | {sprache} | {status}")

erfolgsrate = round((total - fehler) / total * 100, 1)
print(f"\nErfolgsrate: {erfolgsrate}%")
if fehler == 0:
    print("Alle Tests bestanden!")
else:
    print(f"{fehler} Fehler")
print("=" * 60)