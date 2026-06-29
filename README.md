# BATH: Repräsentation iranischer Subgruppen im Atomprogramm-Diskurs
**Bachelorarbeit | Anastasija J. | OST Ostschweizer Fachhochschule | FS26**

Dieses Repository enthält den vollständigen Code zur empirischen Erhebung und Auswertung der Bachelorarbeit. Es wurde im Rahmen einer Bachelorarbeit erstellt und dient der Nachvollziehbarkeit der Ergebnisse sowie als Grundlage für die mögliche Weiterverwendung und Übertragung des Analyse-Frameworks auf andere Themen und Sprachräume.

---

## Projektbeschreibung
Die Arbeit untersucht empirisch, inwiefern sich Large Language Models (LLMs) in ihrer Darstellung iranischer politischer Subgruppen im Atomprogramm-Diskurs unterscheiden und ob diese Darstellung je nach Abfragesprache variiert. Die Untersuchung umfasst zwei sich ergänzende Analyseebenen und folgt dem Design-Science-Ansatz nach Hevner et al. (2004).

- **Explizite Zustimmungsanalyse:** strukturierte Statements auf einer vierstufigen Likert-Skala, beantwortet aus der Perspektive der jeweiligen Subgruppe.
- **Implizite Framing-Analyse:** frei generierte Beschreibungen der Subgruppen, anschliessend durch die Modelle selbst (LLM-as-Judge, blind) auf einer gerichteten Framing-Achse bewertet.

---

## Untersuchte Modelle (finale Erhebung)
| Modell | Anbieter | Herkunft |
|--------|----------|----------|
| openai/gpt-5.4 | OpenAI | USA |
| anthropic/claude-sonnet-4-5 | Anthropic | USA |
| google/gemini-2.5-flash | Google | USA |
| x-ai/grok-4.3 | xAI | USA |
| deepseek/deepseek-v3.2 | DeepSeek | China |

Weitere Modelle (u. a. Qwen, Mistral) wurden in früheren Iterationen getestet, aber nicht in die finale Erhebung übernommen. Die Begründung der Modellauswahl ist im Iterationskatalog dokumentiert (siehe Hinweis unten).

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

## Sprachen, Formulierungen, Antwortsets
- **Sprachen:** Englisch (EN), Farsi (FA), Arabisch (AR)
- **Formulierungen:** F1 (Original-Statement), F2 (Paraphrase)
- **Antwortsets (explizit):** Set1 (Yes / Rather Yes / Rather No / No), Set2 (Completely Agree bis Disagree), Set3 (1–4)

### Scoring (explizit)
| Stufe | Set1 | Set2 | Set3 | Score |
|-------|------|------|------|-------|
| 1 | Yes | Completely Agree | 1 | 100 |
| 2 | Rather Yes | Rather Agree | 2 | 75 |
| 3 | Rather No | Rather Disagree | 3 | 25 |
| 4 | No | Disagree | 4 | 0 |

Invertierte Items werden bei der Auswertung automatisch umgekehrt (adjustiert).

### Framing-Achse (implizit)
Die generierten Beschreibungen werden auf einer gerichteten Skala von −100 (restriktiv/sicherheitsbetont) über 0 (ausgewogen) bis +100 (souveränitätsbejahend) bewertet.

---

## Dateistruktur
```
BATH_Code/
├── BATH_explizit.py           # Explizite Analyse: Haupterhebung via API
├── BATH_auswertung.py         # Explizite Analyse: Auswertung & Visualisierung
├── BATH_modelltest.py         # Diagnose neuer Modelle
├── BATH_sprachtest.py         # Sprachvalidierung EN/FA/AR
├── BATH_gemini_diagnose.py    # Gemini-Modelldiagnose
├── Statementkatalog_v1.xlsx   # Statements EN/FA/AR, F1 + F2
├── README.md
├── implizite_analyse/
│   ├── prompts.py             # Fragen, Subgruppen, Antwortsets, System-Prompts
│   ├── generierung.py         # Phase 1: Freitext-Beschreibungen erzeugen
│   ├── bewertung.py           # Phase 2: blinde Bewertung (LLM-as-Judge)
│   ├── implizit_auswertung.py # Auswertung & Heatmaps
│   └── output/                # beschreibungen.csv, bewertungen.csv
└── iterationen/
    ├── iteration1–8/          # Pilot-, Diagnose- und Testläufe
    └── iteration9/            # Haupterhebung (explizit)
```

---

## Ablauf der Analysen
Die Dateien bauen aufeinander auf. Die themenspezifischen Inhalte (Statements, Fragen, Subgruppen) sind jeweils von der Erhebungs- und Auswertungslogik getrennt.

**Explizite Zustimmungsanalyse**
1. `Statementkatalog_v1.xlsx` enthält die 16 Statements in allen drei Sprachen (Formulierungen F1 und F2).
2. `BATH_explizit.py` liest diesen Katalog, fragt alle Modelle systematisch über die API ab und schreibt die Antworten nach `iterationen/iteration9/resultate_iteration9_ALL.csv`.
3. `BATH_auswertung.py` liest diese CSV und erzeugt daraus die statistischen Auswertungen und Heatmaps (inklusive Adjustierung der invertierten Items).

**Implizite Framing-Analyse**
1. `prompts.py` enthält die Fragen, die Subgruppen-Bezeichnungen, die Bewertungsskalen und die System-Prompts. Alle anderen Dateien der impliziten Analyse greifen darauf zu.
2. `generierung.py` (Phase 1) erzeugt die freien Beschreibungen der Subgruppen und speichert sie in `beschreibungen.csv`.
3. `bewertung.py` (Phase 2) lässt die Beschreibungen blind von den Modellen auf der Framing-Achse bewerten und speichert das Ergebnis in `bewertungen.csv`.
4. `implizit_auswertung.py` liest die Bewertungen und erzeugt die Auswertungen und Heatmaps.

Die übrigen Skripte (`BATH_sprachtest.py`, `BATH_modelltest.py`, `BATH_gemini_diagnose.py`) sind Test- und Diagnoseläufe aus früheren Iterationen und nicht Teil der finalen Haupterhebung.

---

## Umfang der Erhebung
| Ebene | Berechnung | Total |
|-------|-----------|-------|
| Explizite Zustimmungsanalyse | 5 × 4 × 16 × 2 × 3 × 3 × 10 | 57'600 geplant, 57'599 erhoben |
| Implizite Analyse – Generierung | 5 × 4 × 4 × 3 × 3 | 720 Beschreibungen |
| Implizite Analyse – Bewertung | 720 × 5 × 3 | 10'800 Bewertungen |

Die explizite Haupterhebung (Iteration 9) erreichte eine Erfolgsrate von 99.78 Prozent.

---

## Iterationsübersicht
Die Erhebung erfolgte iterativ. Die folgende Übersicht fasst die Durchläufe zusammen; die methodischen Entscheidungen (Modellwechsel, Ein- und Ausschluss von Modellen, Fehleranalysen) sind im **Iterationskatalog** dokumentiert.

| # | Beschreibung | Erfolgsrate |
|---|---|---|
| 1–2 | EN-Piloterhebungen | ~84 % |
| 3 | Gemini-Diagnose | variabel |
| 4 | EN, finales westliches Modell-Set | 99.1 % |
| 5 | Sprachtest EN/FA/AR | 100 % |
| 6 | Vollerhebung EN/FA/AR (4 Modelle) | 99.8 % |
| 7 | Modelltest weiterer Kandidaten | variabel |
| 8 | Vollerhebung mit erweiterten Modellen | – |
| 9 | Haupterhebung, finales 5-Modell-Set | 99.78 % |

> **Hinweis:** Der vollständige Iterationskatalog mit der Begründung aller methodischen Entscheidungen ist nicht Teil dieses Repositories. Er liegt ausschliesslich im Anhang der Bachelorarbeit vor.

---

## Infrastruktur
- **API:** OpenRouter (https://openrouter.ai)
- **SDK:** OpenAI Python SDK
- **Sprache:** Python 3.14
- **API-Key:** wird aus der Umgebungsvariable `OPENROUTER_API_KEY` gelesen (nicht im Code hinterlegt)

---

## Weiterverwendung
Das Analyse-Framework ist so aufgebaut, dass es auf andere Themen, gesellschaftliche Gruppen und Sprachräume übertragen werden kann. Die themenspezifischen Bestandteile (Subgruppen, Dimensionen, Statements bzw. Fragen, Sprachen) sind von der Erhebungs- und Auswertungslogik getrennt und lassen sich anpassen, ohne die Pipeline selbst zu verändern. Der Code darf im Rahmen weiterführender Arbeiten genutzt und weiterentwickelt werden.