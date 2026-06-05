from openai import OpenAI
import csv, time, os, pandas as pd

API_KEY = os.getenv("OPENROUTER_API_KEY")

# ── MODELLE ────────────────────────────────────────────────
MODELLE = [
    "openai/gpt-5.4",
    "anthropic/claude-sonnet-4-5",
    "google/gemini-2.5-flash",
    "x-ai/grok-4.3",
    "deepseek/deepseek-v3.2",
]

# ── SUBGRUPPEN ─────────────────────────────────────────────
SUBGRUPPEN = {
    "EN": ["Hardline-Principlists", "IRGC/Securocrats", "Pragmatic Moderates", "Reformists"],
    "FA": ["اصول‌گرایان تندرو", "سپاه پاسداران و نخبگان امنیتی", "میانه‌روهای عمل‌گرا", "اصلاح‌طلبان"],
    "AR": ["الأصوليون المتشددون", "الحرس الثوري والنخب الأمنية", "المعتدلون البراغماتيون", "الإصلاحيون"],
}

# ── ANTWORTSETS ────────────────────────────────────────────
ANTWORTSETS = {
    "EN": {
        "Set1": ["Yes", "Rather Yes", "Rather No", "No"],
        "Set2": ["Completely Agree", "Rather Agree", "Rather Disagree", "Disagree"],
        "Set3": ["1", "2", "3", "4"],
    },
    "FA": {
        "Set1": ["بله", "تا حدودی بله", "تا حدودی خیر", "خیر"],
        "Set2": ["کاملاً موافقم", "تا حدودی موافقم", "تا حدودی مخالفم", "کاملاً مخالفم"],
        "Set3": ["1", "2", "3", "4"],
    },
    "AR": {
        "Set1": ["نعم", "نعم إلى حد ما", "لا إلى حد ما", "لا"],
        "Set2": ["أوافق تمامًا", "أوافق إلى حد ما", "لا أوافق إلى حد ما", "لا أوافق"],
        "Set3": ["1", "2", "3", "4"],
    },
}

SCORING = {0: 100, 1: 75, 2: 25, 3: 0}
SPRACHEN_EXCEL = {"EN": "Englisch", "FA": "Farsi", "AR": "Arabisch"}
SPRACHEN = ["EN", "FA", "AR"]
FORMULIERUNGEN = ["F1", "F2"]
WIEDERHOLUNGEN = 10
EXCEL_PFAD = "Statementkatalog_v1.xlsx"

# ── PFADE ──────────────────────────────────────────────────
OUTPUT_CSV = "iterationen/iteration9/resultate_iteration9_ALL.csv"
CHECKPOINT_FILE = "iterationen/iteration9/checkpoint.txt"
os.makedirs("iterationen/iteration9", exist_ok=True)

# ── PROMPTS ────────────────────────────────────────────────
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

# ── STATEMENTS LADEN ───────────────────────────────────────
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
        })
    return statements

# ── CHECKPOINT ────────────────────────────────────────────
def lade_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def speichere_checkpoint(key):
    with open(CHECKPOINT_FILE, "a", encoding="utf-8") as f:
        f.write(key + "\n")

# ── FLEXIBLES MATCHING ─────────────────────────────────────
ARABISCH_ZU_WESTERN = {"۱": "1", "۲": "2", "۳": "3", "۴": "4"}

def match_antwort(rohantwort, optionen, set_name):
    """Flexibles Matching mit Normalisierung."""
    # Normalisierung: Punkte, Ausrufezeichen, Leerzeichen entfernen
    normiert = rohantwort.strip(".,!؟?").strip()
    
    # Direktes Match
    for i, option in enumerate(optionen):
        if normiert == option or normiert == option.strip(".,!؟?").strip():
            return SCORING[i]
    
    # Arabische Ziffern für Set3
    if set_name == "Set3":
        western = ARABISCH_ZU_WESTERN.get(normiert, normiert)
        if western in optionen:
            return SCORING[optionen.index(western)]
    
    return -1

# ── START ─────────────────────────────────────────────────
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=API_KEY)
erledigte = lade_checkpoint()
print(f"✅ Checkpoint: {len(erledigte):,} Abfragen bereits erledigt")

if not os.path.exists(OUTPUT_CSV):
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["modell", "sprache", "subgruppe", "item_id", "dimension",
                         "formulierung", "antwortset", "wiederholung",
                         "rohantwort", "score", "invertiert"])
    print("📄 Neue CSV erstellt")
else:
    print("📄 Bestehende CSV weitergeführt")

# Total berechnen
total = 0
for sprache in SPRACHEN:
    stmts = lade_statements(EXCEL_PFAD, SPRACHEN_EXCEL[sprache], "F1")
    total += (len(MODELLE) * len(SUBGRUPPEN[sprache]) * len(stmts) *
              len(ANTWORTSETS[sprache]) * len(FORMULIERUNGEN) * WIEDERHOLUNGEN)

ausstehend = total - len(erledigte)
print(f"\n🚀 Starte Iteration 9 — Haupterhebung")
print(f"   Total: {total:,} | Erledigt: {len(erledigte):,} | Ausstehend: {ausstehend:,}")
print(f"   Modelle: {[m.split('/')[-1] for m in MODELLE]}")
print("=" * 60)

count = 0
fehler = 0
start_zeit = time.time()

for sprache in SPRACHEN:
    for formulierung in FORMULIERUNGEN:
        statements = lade_statements(EXCEL_PFAD, SPRACHEN_EXCEL[sprache], formulierung)
        for modell in MODELLE:
            for subgruppe in SUBGRUPPEN[sprache]:
                for stmt in statements:
                    statement_text = stmt["text"].replace("{Gruppe}", subgruppe)
                    for set_name, optionen in ANTWORTSETS[sprache].items():
                        choices_str = " / ".join(optionen)
                        system = SYSTEM_PROMPTS[sprache].replace("{choices}", choices_str)
                        user = (USER_PROMPTS[sprache]
                                .replace("{choices}", choices_str)
                                .replace("{subgruppe}", subgruppe)
                                .replace("{statement}", statement_text))

                        for w in range(1, WIEDERHOLUNGEN + 1):
                            count += 1
                            ck = f"{modell}|{sprache}|{formulierung}|{subgruppe}|{stmt['id']}|{set_name}|W{w}"
                            if ck in erledigte:
                                continue

                            if count % 200 == 0:
                                elapsed = time.time() - start_zeit
                                done = count - len(erledigte)
                                if done > 0:
                                    eta_min = int((ausstehend - done) / (done / elapsed) / 60)
                                    print(f"[{count:,}/{total:,}] {modell.split('/')[-1]} | {sprache} | W{w} | Fehler: {fehler} | ETA: ~{eta_min} Min")

                            rohantwort = "ERROR"
                            score = -1
                            for attempt in range(3):
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
                                    rohantwort = content.strip() if content else "EMPTY"
                                    score = match_antwort(rohantwort, optionen, set_name)
                                    if score == -1:
                                        fehler += 1
                                    break
                                except Exception as e:
                                    if attempt < 2:
                                        time.sleep(5)
                                    else:
                                        rohantwort = "ERROR"
                                        score = -1
                                        fehler += 1

                            with open(OUTPUT_CSV, "a", newline="", encoding="utf-8-sig") as f:
                                writer = csv.writer(f)
                                writer.writerow([modell, sprache, subgruppe, stmt["id"],
                                                 stmt["dimension"], formulierung, set_name,
                                                 w, rohantwort, score, stmt["invertiert"]])
                            speichere_checkpoint(ck)
                            time.sleep(1 if "gemini" in modell else 0.2)

print("\n" + "=" * 60)
print("✅ ITERATION 9 ABGESCHLOSSEN!")
valide = total - fehler
print(f"   Total: {total:,} | Fehler: {fehler} | Erfolgsrate: {round(valide/total*100,1)}%")
print(f"   CSV: {OUTPUT_CSV}")
print("=" * 60)