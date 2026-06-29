# -*- coding: utf-8 -*-
"""
Auswertung der impliziten Framing-Analyse (BATH 2026, Anastasija J.)
------------------------------------------------------------------------
Liest die Datei bewertungen.csv (Output der impliziten Bias-Analyse) ein und
berechnet die zentralen Kennzahlen sowie eine Heatmap.

Der framing_score ist VORZEICHENBEHAFTET:
   -100 = strongly sovereignty-restrictive framing
    -50 = moderately sovereignty-restrictive
      0 = balanced / neutral
    +50 = moderately sovereignty-affirming
   +100 = strongly sovereignty-affirming

   
Dieser Scrore misst die Richtung des Framings
Judge folgt methodisch Samsinger (Mittelwert +- Standardabweichung), die
Heatmap nutzt jedoch eine divergierende Farbskala mit Nullpunkt in der Mitte.

Aufruf:  python implizit_auswertung.py
(Pfad unten im CONFIG-Block anpassen.)
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ============================ CONFIG ====================================
# Pfad zu deiner bewertungen.csv anpassen:
CSV_PFAD = r"output\bewertungen.csv"
# Ausgabeordner fuer Heatmap + aggregierte CSVs:
OUT_DIR = r"auswertung_output"
# Schwelle, ab der ein Set2-Wert als "widerspruechlich" zu Set1/Set3 gilt:
WIDERSPRUCH_SCHWELLE = 100      # Punkte Abweichung
# ========================================================================


def lade_daten(pfad):
    if not os.path.exists(pfad):
        sys.exit(f"FEHLER: Datei nicht gefunden: {pfad}\n"
                 f"Bitte CSV_PFAD im CONFIG-Block anpassen.")
    df = pd.read_csv(pfad)
    df = df.drop_duplicates()
    erwartet = {"beschreibung_id", "beschreibendes_modell", "judge_modell",
                "ist_self", "sprache", "subgruppe", "frage_id",
                "antwortset", "framing_score"}
    fehlend = erwartet - set(df.columns)
    if fehlend:
        sys.exit(f"FEHLER: Diese Spalten fehlen in der CSV: {sorted(fehlend)}")
    # framing_score numerisch machen; nicht-parsebare -> NaN
    df["framing_score"] = pd.to_numeric(df["framing_score"], errors="coerce")
    return df


def trennlinie(titel=""):
    print("\n" + "=" * 70)
    if titel:
        print(titel)
        print("-" * 70)


def integritaet(df):
    trennlinie("1) DATENINTEGRITAET")
    print(f"Zeilen (Bewertungen) gesamt : {len(df)}")
    print(f"Beschreibungen (eindeutig)  : {df['beschreibung_id'].nunique()}")
    print(f"Sprachen                    : {sorted(df['sprache'].unique())}")
    print(f"Beschreibende Modelle       : {sorted(df['beschreibendes_modell'].unique())}")
    print(f"Judge-Modelle               : {sorted(df['judge_modell'].unique())}")
    print(f"Antwortsets                 : {sorted(df['antwortset'].unique())}")
    print(f"Subgruppen                  : {sorted(df['subgruppe'].unique())}")
    n_nan = df['framing_score'].isna().sum()
    print(f"Nicht erkannte Scores (NaN) : {n_nan}  "
          f"({100*n_nan/len(df):.2f} % der Zeilen)")
    if n_nan > 0:
        print("  -> betroffene Antwortsets:",
              df.loc[df['framing_score'].isna(), 'antwortset']
                .value_counts().to_dict())


def fmt(serie_mean, serie_std):
    """Mittelwert (Std) als String-Tabelle."""
    out = pd.DataFrame({"mean": serie_mean.round(1),
                        "std": serie_std.round(1)})
    return out


def subgruppen_gradient(df):
    trennlinie("2) SUBGRUPPEN-GRADIENT (Hauptbefund)")
    g = df.groupby("subgruppe")["framing_score"]
    tab = fmt(g.mean(), g.std()).sort_values("mean", ascending=False)
    print("Mittlerer framing_score pro Subgruppe (ueber alle Modelle/Judges/Sets):")
    print(tab.to_string())
    print("\nLesart: +100 = stark souveraenitaetsbejahend, -100 = stark restriktiv.")
    # pro Sprache (falls mehrsprachig)
    if df['sprache'].nunique() > 1:
        print("\nPro Subgruppe x Sprache:")
        piv = df.pivot_table(index="subgruppe", columns="sprache",
                             values="framing_score", aggfunc="mean").round(1)
        print(piv.to_string())
    return tab


def judge_polaritaet(df):
    trennlinie("3) JUDGE-POLARITAET PRO ANTWORTSET (Set2-Anomalie pruefen)")
    piv = df.pivot_table(index="judge_modell", columns="antwortset",
                         values="framing_score", aggfunc="mean").round(1)
    print("Mittlerer framing_score je Judge x Antwortset:")
    print(piv.to_string())
    print("\nWarnsignal: Wenn ein Judge bei Set2 stark vom eigenen Set1/Set3 "
          "abweicht,\ndeutet das auf eine vertauschte A-E-Skala hin (Polaritaets-"
          "verwirrung).")
    # Abweichung Set2 vs. Mittel(Set1,Set3) je Judge
    if {"Set1", "Set2", "Set3"}.issubset(piv.columns):
        diff = (piv["Set2"] - piv[["Set1", "Set3"]].mean(axis=1)).round(1)
        print("\nAbweichung Set2 - Mittel(Set1,Set3) je Judge:")
        print(diff.sort_values().to_string())
    return piv


def within_description_konsistenz(df):
    trennlinie("4) WIDERSPRUECHE INNERHALB DERSELBEN BESCHREIBUNG/JUDGE")
    # je (beschreibung_id, judge): Spannweite ueber die Antwortsets
    grp = df.dropna(subset=["framing_score"]).groupby(
        ["beschreibung_id", "judge_modell"])["framing_score"]
    spann = (grp.max() - grp.min()).reset_index(name="spannweite")
    auffaellig = spann[spann["spannweite"] >= WIDERSPRUCH_SCHWELLE]
    print(f"Bewertungs-Tripel mit Spannweite >= {WIDERSPRUCH_SCHWELLE} Punkte: "
          f"{len(auffaellig)} von {len(spann)}")
    if len(auffaellig):
        print("\nAuffaellige Judges (Anzahl widerspruechlicher Beschreibungen):")
        print(auffaellig["judge_modell"].value_counts().to_string())
        # ein konkretes Beispiel zum Zitieren
        bsp_id = auffaellig.iloc[0]["beschreibung_id"]
        bsp_judge = auffaellig.iloc[0]["judge_modell"]
        print(f"\nBeispiel (beschreibung_id={bsp_id}, judge={bsp_judge}):")
        bsp = df[(df["beschreibung_id"] == bsp_id) &
                 (df["judge_modell"] == bsp_judge)][
            ["antwortset", "judge_antwort_raw", "framing_score"]]
        print(bsp.to_string(index=False))
    return auffaellig


def beschreiber_befund(df):
    trennlinie("5) FRAMING PRO BESCHREIBENDEM MODELL x SUBGRUPPE (Grok-Befund)")
    piv = df.pivot_table(index="beschreibendes_modell", columns="subgruppe",
                         values="framing_score", aggfunc="mean").round(1)
    print("Mittlerer framing_score der ERZEUGTEN Texte (Zeile=Autor-Modell):")
    print(piv.to_string())
    print("\nLesart: niedrige Werte = das Modell rahmt diese Subgruppe restriktiver.")
    return piv


def self_bias(df):
    trennlinie("6) SELF-BIAS (Modell bewertet eigenen Text vs. fremden)")
    g = df.groupby("ist_self")["framing_score"]
    tab = fmt(g.mean(), g.std())
    tab.index = tab.index.map({0: "fremd (ist_self=0)", 1: "selbst (ist_self=1)"})
    print(tab.to_string())


def heatmap(df, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    piv = df.pivot_table(index="beschreibendes_modell", columns="subgruppe",
                         values="framing_score", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(1.6 * piv.shape[1] + 2,
                                    0.8 * piv.shape[0] + 2))
    im = ax.imshow(piv.values, cmap="RdBu", vmin=-100, vmax=100, aspect="auto")
    ax.set_xticks(range(piv.shape[1]))
    ax.set_xticklabels(piv.columns, rotation=30, ha="right", fontsize=9)
    ax.set_yticks(range(piv.shape[0]))
    ax.set_yticklabels(piv.index, fontsize=9)
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.0f}", ha="center", va="center",
                        fontsize=9,
                        color="white" if abs(v) > 55 else "black")
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("framing_score  (-100 restriktiv  ...  +100 souveraen-bejahend)",
                   fontsize=8)
    ax.set_title("Implizites Framing: beschreibendes Modell x Subgruppe",
                 fontsize=11)
    fig.tight_layout()
    pfad = os.path.join(out_dir, "heatmap_framing_modell_x_subgruppe.png")
    fig.savefig(pfad, dpi=160)
    plt.close(fig)
    print(f"\n[Heatmap gespeichert: {pfad}]")


def speichere_aggregate(df, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    df.pivot_table(index="subgruppe", columns="beschreibendes_modell",
                   values="framing_score", aggfunc="mean").round(1)\
      .to_csv(os.path.join(out_dir, "agg_subgruppe_x_modell.csv"))
    df.pivot_table(index="judge_modell", columns="antwortset",
                   values="framing_score", aggfunc="mean").round(1)\
      .to_csv(os.path.join(out_dir, "agg_judge_x_antwortset.csv"))
    print(f"[Aggregierte CSVs gespeichert in: {out_dir}]")


def main():
    df = lade_daten(CSV_PFAD)
    integritaet(df)
    subgruppen_gradient(df)
    judge_polaritaet(df)
    within_description_konsistenz(df)
    beschreiber_befund(df)
    self_bias(df)
    heatmap(df, OUT_DIR)
    speichere_aggregate(df, OUT_DIR)
    trennlinie("FERTIG")
    print("Alle Kennzahlen berechnet. Heatmap + CSVs im Ausgabeordner.")


if __name__ == "__main__":
    main()