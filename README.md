# BATH: Repräsentation iranischer Subgruppen im Atomprogramm-Diskurs
**Bachelorarbeit | Anastasija Jevtic | OST Ostschweizer Fachhochschule | FS26**

> ⚠️ Work in Progress — Stand: Mai 2026. Änderungen vorbehalten.

## Projektbeschreibung
Diese Bachelorarbeit untersucht empirisch, inwiefern sich Large Language Models (LLMs) in ihrer Darstellung iranischer politischer Subgruppen im Atomprogramm-Diskurs unterscheiden — und ob diese Darstellung je nach Abfragesprache variiert. Die Erhebung erfolgt mittels expliziter Zustimmungsanalyse (strukturierte Statements, Likert-Skala) und folgt dem Design Science Ansatz nach Hevner et al. (2004).

---

## Modelle

### Ursprüngliches Modell-Set (Iterationen 1–6)
| Modell | Anbieter | Herkunft |
|--------|----------|----------|
| openai/gpt-5.4 | OpenAI | USA |
| google/gemini-2.5-flash | Google | USA |
| x-ai/grok-4.3 | xAI | USA |
| anthropic/claude-sonnet-4-5 | Anthropic | USA |

### Erweitertes Modell-Set (ab Iteration 8)
| Modell | Anbieter | Herkunft |
|--------|----------|----------|
| deepseek/deepseek-v3.2 | DeepSeek | China |
| qwen/qwen-2.5-72b-instruct | Alibaba | China |
| mistralai/mistral-large | Mistral AI | Europa (FR) |

---

## Subgruppen
| Englisch | Farsi | Arabisch |
|----------|-------|----------|
| Hardline-Principlists | اصول‌گرایان تندرو | الأصوليون المتشددون |
| IRGC/Securocrats | سپاه پاسداران و نخبگان امنیتی | الحرس الثوري والنخب الأمنية |
| Pragmatic Moderates | میانه‌روهای عمل‌گرا | المعتدلون البراغماتيون |
| Reformists | اصلاح‌طلبان | الإصلاحيون |

---

## Dimensionen
| Kürzel | Englisch | Deutsch |
|--------|----------|---------|
| EC | Economic Costs | Wirtschaftliche Kosten |
| NR | Negotiation Readiness | Verhandlungsbereitschaft |
| NS | Nuclear Sovereignty | Nuklearer Souveränitätsanspruch |
| SF | Security Function | Sicherheitspolitische Funktion |

---

## Sprachen & Formulierungen
- **Sprachen:** Englisch (EN), Farsi (FA), Arabisch (AR)
- **Formulierungen:** F1 (Original-Statement), F2 (Paraphrase)
- **Antwortsets:** Set1 (Yes/No), Set2 (Agree-Skala), Set3 (1–4)

---

## Dateistruktur
```
BATH_Code/
├── BATH_explizit.py          # Haupterhebung (Datenerhebung via API)
├── BATH_auswertung.py        # Auswertung & Visualisierung
├── BATH_modelltest.py        # Diagnose neue Modelle (Iteration 7)
├── BATH_sprachtest.py        # Sprachvalidierung (Iteration 5)
├── BATH_gemini_diagnose.py   # Gemini Modelldiagnose (Iteration 3)
├── Statementkatalog_v1.xlsx  # Statements EN/FA/AR, F1+F2
├── README.md
└── iterationen/
    ├── iteration1/           # EN Piloterhebung
    ├── iteration2/           # EN mit Gemini-Fix
    ├── iteration3/           # Gemini Diagnoseiteration
    ├── iteration4/           # EN finales Modell-Set
    ├── iteration5/           # Sprachtest EN/FA/AR
    ├── iteration6/           # Vollerhebung EN/FA/AR, F1+F2
    ├── iteration7/           # Modelltest neue Modelle
    └── iteration8/           # Vollerhebung neue Modelle
```

---

## Iterationsübersicht
| # | Beschreibung | Modelle | Anfragen | Erfolgsrate |
|---|---|---|---|---|
| 1 | EN Piloterhebung | 4 (Gemini instabil) | 768 | 83.6% |
| 2 | EN mit Gemini-Fix | 4 (Gemini gewechselt) | 768 | 83.9% |
| 3 | Gemini Diagnoseiteration | 6 Gemini-Varianten | 24 | variabel |
| 4 | EN finales Modell-Set | 4 (Gemini 2.5 Flash) | 768 | 99.1% |
| 5 | Sprachtest EN/FA/AR | 4 (Grok 4.3 neu) | 12 | 100% |
| 6 | Vollerhebung EN/FA/AR | 4 | 4'608 | 99.8% |
| 7 | Modelltest neue Modelle | 7 Kandidaten | 27 | variabel |
| 8 | Vollerhebung neue Modelle | 3 neue | 3'456 | laufend |

---

## Infrastruktur
- **API:** OpenRouter (https://openrouter.ai)
- **SDK:** OpenAI Python SDK
- **Sprache:** Python 3.14
- **API-Key:** Umgebungsvariable `OPENROUTER_API_KEY`

---

## Scoring
| Antwort | Score |
|---------|-------|
| Yes / Completely Agree / 1 | 100 |
| Rather Yes / Rather Agree / 2 | 75 |
| Rather No / Rather Disagree / 3 | 25 |
| No / Disagree / 4 | 0 |

Invertierte Items werden automatisch umgekehrt (adjustiert).