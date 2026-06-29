import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import math
import os
from scipy import stats
from itertools import combinations

# ── KONFIGURATION ──────────────────────────────────────────
CSV_DATEI = "iterationen/iteration9/resultate_iteration9_ALL.csv"
OUTPUT_ORDNER = "iterationen/iteration9/auswertung"
ITERATIONS_NR = "Iteration 9"

os.makedirs(OUTPUT_ORDNER, exist_ok=True)

# ── MAPPINGS ───────────────────────────────────────────────
SUBGRUPPEN_EN = {
    "اصول\u200cگرایان تندرو": "Hardline-Principlists",
    "سپاه پاسداران و نخبگان امنیتی": "IRGC/Securocrats",
    "میانه\u200cروهای عمل\u200cگرا": "Pragmatic Moderates",
    "اصلاح\u200cطلبان": "Reformists",
    "الأصوليون المتشددون": "Hardline-Principlists",
    "الحرس الثوري والنخب الأمنية": "IRGC/Securocrats",
    "المعتدلون البراغماتيون": "Pragmatic Moderates",
    "الإصلاحيون": "Reformists",
    "Hardline-Principlists": "Hardline-Principlists",
    "IRGC/Securocrats": "IRGC/Securocrats",
    "Pragmatic Moderates": "Pragmatic Moderates",
    "Reformists": "Reformists",
}

DIMENSIONEN_EN = {
    "Nuklearer Souveränitätsanspruch": "Nuclear Sovereignty",
    "Verhandlungsbereitschaft": "Negotiation Readiness",
    "Wirtschaftliche Kosten": "Economic Costs",
    "Sicherheitspolitische Funktion": "Security Function",
    "Nuclear Sovereignty": "Nuclear Sovereignty",
    "Negotiation Readiness": "Negotiation Readiness",
    "Economic Costs": "Economic Costs",
    "Security Function": "Security Function",
    "NS": "Nuclear Sovereignty",
    "NR": "Negotiation Readiness",
    "EC": "Economic Costs",
    "SF": "Security Function",
}

DIMENSIONEN_ORDER = [
    "Economic Costs",
    "Negotiation Readiness",
    "Nuclear Sovereignty",
    "Security Function",
]

AXIS_LABELS = {
    "Nuclear Sovereignty": "Nuclear\nSovereignty",
    "Negotiation Readiness": "Negotiation\nReadiness",
    "Economic Costs": "Economic\nCosts",
    "Security Function": "Security\nFunction",
}

AXIS_SHORT = {
    "Economic Costs": "EC",
    "Negotiation Readiness": "NR",
    "Nuclear Sovereignty": "NS",
    "Security Function": "SF",
}

SUBGRUPPEN_ORDER = [
    "Hardline-Principlists",
    "IRGC/Securocrats",
    "Pragmatic Moderates",
    "Reformists",
]

MODELL_FARBEN = {
    "claude-sonnet-4-5": "#2E75B6",
    "gemini-2.5-flash": "#ED7D31",
    "gpt-5.4": "#70AD47",
    "grok-4.3": "#FF0000",
    "deepseek-v3.2": "#9B59B6",
}

# Farben für die vier Subgruppen (für den Radar pro Modell)
GRUPPEN_FARBEN = {
    "Hardline-Principlists": "#C0392B",
    "IRGC/Securocrats": "#E67E22",
    "Pragmatic Moderates": "#27AE60",
    "Reformists": "#2980B9",
}

# ── DATEN LADEN ────────────────────────────────────────────
df = pd.read_csv(CSV_DATEI, encoding="utf-8-sig")
print(f"Geladen: {len(df)} Zeilen")

df["subgruppe"] = df["subgruppe"].map(lambda x: SUBGRUPPEN_EN.get(str(x).strip(), x))
df["dimension"] = df["dimension"].map(lambda x: DIMENSIONEN_EN.get(str(x).strip(), x))

df_valid = df[df["score"] != -1].copy()
print(f"Valide: {len(df_valid)} ({round(len(df_valid)/len(df)*100,2)}%)")
print()

# ── FEHLERANALYSE ──────────────────────────────────────────
print("=" * 60)
print("ERFOLGSRATE PRO MODELL UND SPRACHE")
print("=" * 60)
for modell in sorted(df["modell"].unique()):
    for sprache in sorted(df["sprache"].unique()):
        subset = df[(df["modell"] == modell) & (df["sprache"] == sprache)]
        if len(subset) == 0:
            continue
        errors = len(subset[subset["score"] == -1])
        rate = round((len(subset)-errors)/len(subset)*100, 1)
        print(f"{modell.split('/')[-1]:25} | {sprache} | {len(subset)-errors}/{len(subset)} | {rate}%")
print()

# ── INVERTIERUNG ───────────────────────────────────────────
def invertiere(score, invertiert):
    if str(invertiert).lower() in ["true", "ja"] and score != -1:
        return 100 - score
    return score

df_valid["score_adj"] = df_valid.apply(
    lambda row: invertiere(row["score"], row["invertiert"]), axis=1)

# ── SPRACHEN UND FORMULIERUNGEN ────────────────────────────
sprachen = sorted(df_valid["sprache"].unique())
formulierungen = sorted(df_valid["formulierung"].unique())

# ── STATISTIK BERECHNEN (Median + Quartile statt Mittelwert + SD) ──
def berechne_statistik(subset):
    """Berechnet Median, 1. und 3. Quartil sowie n pro Modell/Subgruppe/Dimension."""
    summary = subset.groupby(
        ["modell", "subgruppe", "dimension"]
    )["score_adj"].agg(
        median="median",
        q1=lambda x: x.quantile(0.25),
        q3=lambda x: x.quantile(0.75),
        n="count"
    ).round(2).reset_index()
    summary.columns = ["Model", "Group", "Axis Name", "median", "q1", "q3", "n"]
    return summary

# ── KRUSKAL-WALLIS + MANN-WHITNEY TESTS ────────────────────
def signifikanztest(subset, gruppenvar, output_path):
    """Kruskal-Wallis Test + paarweise Mann-Whitney-U Tests."""
    alpha = 0.05
    ergebnisse = []

    gruppen_werte = subset.groupby(gruppenvar)["score_adj"].apply(list).to_dict()
    gruppen = list(gruppen_werte.keys())

    if len(gruppen) < 2:
        return None

    kw_stat, kw_p = stats.kruskal(*[gruppen_werte[g] for g in gruppen])
    ergebnisse.append({
        "Test": "Kruskal-Wallis",
        "Gruppe 1": "alle",
        "Gruppe 2": "-",
        "Statistik": round(kw_stat, 4),
        "p-Wert": round(kw_p, 4),
        "Signifikant (alpha=0.05)": "Ja" if kw_p < alpha else "Nein"
    })

    if kw_p < alpha:
        paare = list(combinations(gruppen, 2))
        alpha_korr = alpha / len(paare)
        for g1, g2 in paare:
            u_stat, u_p = stats.mannwhitneyu(
                gruppen_werte[g1], gruppen_werte[g2], alternative="two-sided")
            ergebnisse.append({
                "Test": "Mann-Whitney-U",
                "Gruppe 1": str(g1),
                "Gruppe 2": str(g2),
                "Statistik": round(u_stat, 4),
                "p-Wert": round(u_p, 4),
                "Signifikant (alpha=0.05)": "Ja" if u_p < alpha_korr else "Nein"
            })

    df_ergebnisse = pd.DataFrame(ergebnisse)
    df_ergebnisse.to_csv(output_path, index=False, encoding="utf-8-sig")
    return df_ergebnisse

# ── RADAR PRO MODELL (small multiples) ─────────────────────
def plot_radar_pro_modell(df_input, sprache, output_path,
                          modell_spalte="modell", sub_spalte="subgruppe",
                          dim_spalte="dimension", wert_spalte="score_adj",
                          titel_zusatz=""):
    """Ein Radar pro Modell nebeneinander (small multiples).
    Zeigt die vier Subgruppen-Profile je Modell -> Modellvergleich auf einen Blick.
    Verwendet Mediane (konsistent mit den Heatmaps)."""

    subset = df_input[df_input["sprache"] == sprache] if sprache else df_input
    if len(subset) == 0:
        return

    models = sorted(subset[modell_spalte].unique())
    groups = [g for g in SUBGRUPPEN_ORDER if g in subset[sub_spalte].unique()]
    axis_names = [d for d in DIMENSIONEN_ORDER if d in subset[dim_spalte].unique()]

    if not groups or not axis_names:
        return

    angles = np.linspace(0, 2 * math.pi, len(axis_names), endpoint=False)

    fig, axes = plt.subplots(1, len(models),
                             figsize=(4.4 * len(models), 5),
                             subplot_kw={"polar": True})
    if len(models) == 1:
        axes = [axes]

    for i, model in enumerate(models):
        ax = axes[i]
        for group in groups:
            medians = []
            for dim in axis_names:
                v = subset[(subset[modell_spalte] == model) &
                           (subset[sub_spalte] == group) &
                           (subset[dim_spalte] == dim)][wert_spalte]
                medians.append(float(v.median()) if len(v) > 0 else 0)
            vals = medians + [medians[0]]
            ang = list(angles) + [angles[0]]
            farbe = GRUPPEN_FARBEN.get(group, "#888888")
            ax.plot(ang, vals, color=farbe, linewidth=2, label=group)
            ax.fill(ang, vals, color=farbe, alpha=0.10)

        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        ax.set_xticks(angles)
        ax.set_xticklabels([AXIS_SHORT.get(a, a) for a in axis_names], fontsize=10)
        ax.set_ylim(0, 100)
        ax.set_yticks([25, 50, 75, 100])
        ax.set_yticklabels(["25", "50", "75", "100"], fontsize=7)
        ax.tick_params(pad=6)
        ax.set_title(model.split("/")[-1], fontsize=12, fontweight="bold", pad=18)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=11,
               bbox_to_anchor=(0.5, -0.04))
    sprache_label = {"EN": "Englisch", "FA": "Farsi", "AR": "Arabisch"}.get(sprache, sprache or "alle Sprachen")
    fig.suptitle(f"Subgruppen-Profile pro Modell — {ITERATIONS_NR}{titel_zusatz}\n"
                 f"(Median je Dimension{', ' + sprache_label if sprache else ', über alle Sprachen'}, "
                 f"über Formulierungen und Antwortsets)",
                 fontsize=13, fontweight="bold", y=1.04)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Radar pro Modell gespeichert: {output_path}")

# ── HEATMAP MIT MEDIAN + QUARTILE ──────────────────────────
def plot_heatmap(summary_df, titel, output_path):
    models = sorted(summary_df["Model"].unique())
    groups = [g for g in SUBGRUPPEN_ORDER if g in summary_df["Group"].unique()]
    axis_names = [d for d in DIMENSIONEN_ORDER if d in summary_df["Axis Name"].unique()]

    if not models or not groups:
        return

    fig, axes = plt.subplots(1, len(models), figsize=(5 * len(models), 5))
    if len(models) == 1:
        axes = [axes]

    for i, model in enumerate(models):
        ax = axes[i]
        subset = summary_df[summary_df["Model"] == model]

        data_med = []
        data_q1 = []
        data_q3 = []
        for group in groups:
            rm, rq1, rq3 = [], [], []
            for axis in axis_names:
                val = subset[(subset["Group"] == group) & (subset["Axis Name"] == axis)]
                rm.append(float(val["median"].values[0]) if len(val) > 0 else np.nan)
                rq1.append(float(val["q1"].values[0]) if len(val) > 0 else np.nan)
                rq3.append(float(val["q3"].values[0]) if len(val) > 0 else np.nan)
            data_med.append(rm); data_q1.append(rq1); data_q3.append(rq3)

        arr = np.array(data_med); q1a = np.array(data_q1); q3a = np.array(data_q3)
        im = ax.imshow(arr, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")

        ax.set_xticks(range(len(axis_names)))
        ax.set_xticklabels([AXIS_SHORT.get(a, a) for a in axis_names], rotation=0, fontsize=10)
        ax.set_yticks(range(len(groups)))
        ax.set_yticklabels(groups, fontsize=8)
        ax.set_title(model.split("/")[-1], fontsize=10, fontweight="bold")

        for row in range(len(groups)):
            for col in range(len(axis_names)):
                val = arr[row, col]
                if not np.isnan(val):
                    tc = "white" if val < 30 or val > 70 else "black"
                    ax.text(col, row - 0.1, f"{val:.0f}", ha="center", va="center",
                            fontsize=10, fontweight="bold", color=tc)
                    ax.text(col, row + 0.2, f"[{q1a[row,col]:.0f}-{q3a[row,col]:.0f}]",
                            ha="center", va="center", fontsize=6.5, color=tc, alpha=0.9)

        plt.colorbar(im, ax=ax, shrink=0.8)

    fig.suptitle(titel, fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Heatmap gespeichert: {output_path}")

# ── HEATMAP PRO DIMENSION (Median + Quartile) ──────────────
def plot_heatmap_pro_dimension(summary_df, sprache, formulierung, output_ordner):
    models = sorted(summary_df["Model"].unique())
    groups = [g for g in SUBGRUPPEN_ORDER if g in summary_df["Group"].unique()]
    axis_names = [d for d in DIMENSIONEN_ORDER if d in summary_df["Axis Name"].unique()]
    modell_labels = [m.split("/")[-1] for m in models]

    for dimension in axis_names:
        fig, ax = plt.subplots(figsize=(10, 4))
        data_med, data_q1, data_q3, data_n = [], [], [], []
        for group in groups:
            rm, rq1, rq3, rn = [], [], [], []
            for model in models:
                val = summary_df[(summary_df["Model"] == model) &
                                 (summary_df["Group"] == group) &
                                 (summary_df["Axis Name"] == dimension)]
                rm.append(float(val["median"].values[0]) if len(val) > 0 else np.nan)
                rq1.append(float(val["q1"].values[0]) if len(val) > 0 else np.nan)
                rq3.append(float(val["q3"].values[0]) if len(val) > 0 else np.nan)
                rn.append(int(val["n"].values[0]) if len(val) > 0 else 0)
            data_med.append(rm); data_q1.append(rq1); data_q3.append(rq3); data_n.append(rn)

        arr = np.array(data_med); q1a = np.array(data_q1); q3a = np.array(data_q3)
        im = ax.imshow(arr, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")

        ax.set_xticks(range(len(models)))
        ax.set_xticklabels(modell_labels, fontsize=10, rotation=15, ha="right")
        ax.set_yticks(range(len(groups)))
        ax.set_yticklabels(groups, fontsize=10)

        for row in range(len(groups)):
            for col in range(len(models)):
                val = arr[row, col]
                if not np.isnan(val):
                    tc = "white" if val < 30 or val > 70 else "black"
                    ax.text(col, row - 0.12, f"{val:.0f}", ha="center", va="center",
                            fontsize=12, fontweight="bold", color=tc)
                    ax.text(col, row + 0.22, f"[{q1a[row,col]:.0f}-{q3a[row,col]:.0f}]",
                            ha="center", va="center", fontsize=7.5, color=tc, alpha=0.9)

        plt.colorbar(im, ax=ax, shrink=0.9, label="Zustimmungs-Score (Median)")
        n_zelle = data_n[0][0] if data_n and data_n[0] else 0
        dim_short = AXIS_SHORT.get(dimension, dimension)
        ax.set_title(
            f"{dimension} — {ITERATIONS_NR} | {sprache} | {formulierung}\n"
            f"(Median und [1.-3. Quartil]; n={n_zelle} pro Zelle)",
            fontsize=11, fontweight="bold", pad=15)

        plt.tight_layout()
        output_path = os.path.join(output_ordner, f"heatmap_dim_{dim_short}_{sprache}_{formulierung}.png")
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Heatmap-Dimension gespeichert: {output_path}")

# ── GEMITTELTE HEATMAP (Median + Quartile) ─────────────────
def plot_heatmap_gemittelt(df_valid, sprache, output_ordner):
    """Heatmap pro Dimension, gemittelt über F1+F2 und alle Antwortsets.
    Median + [Q1-Q3]. Zeilen = Subgruppen, Spalten = Modelle."""
    subset = df_valid[df_valid["sprache"] == sprache]
    if len(subset) == 0:
        return

    models = sorted(subset["modell"].unique())
    groups = [g for g in SUBGRUPPEN_ORDER if g in subset["subgruppe"].unique()]
    modell_labels = [m.split("/")[-1] for m in models]

    for dimension in DIMENSIONEN_ORDER:
        if dimension not in subset["dimension"].unique():
            continue

        fig, ax = plt.subplots(figsize=(10, 4))
        data_med, data_q1, data_q3, data_n = [], [], [], []
        for group in groups:
            rm, rq1, rq3, rn = [], [], [], []
            for model in models:
                v = subset[(subset["modell"] == model) &
                           (subset["subgruppe"] == group) &
                           (subset["dimension"] == dimension)]["score_adj"]
                rm.append(float(v.median()) if len(v) > 0 else np.nan)
                rq1.append(float(v.quantile(0.25)) if len(v) > 0 else np.nan)
                rq3.append(float(v.quantile(0.75)) if len(v) > 0 else np.nan)
                rn.append(len(v))
            data_med.append(rm); data_q1.append(rq1); data_q3.append(rq3); data_n.append(rn)

        arr = np.array(data_med); q1a = np.array(data_q1); q3a = np.array(data_q3)
        im = ax.imshow(arr, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")

        ax.set_xticks(range(len(models)))
        ax.set_xticklabels(modell_labels, fontsize=10, rotation=15, ha="right")
        ax.set_yticks(range(len(groups)))
        ax.set_yticklabels(groups, fontsize=10)

        for row in range(len(groups)):
            for col in range(len(models)):
                val = arr[row, col]
                if not np.isnan(val):
                    tc = "white" if val < 30 or val > 70 else "black"
                    ax.text(col, row - 0.12, f"{val:.0f}", ha="center", va="center",
                            fontsize=12, fontweight="bold", color=tc)
                    ax.text(col, row + 0.22, f"[{q1a[row,col]:.0f}-{q3a[row,col]:.0f}]",
                            ha="center", va="center", fontsize=7.5, color=tc, alpha=0.9)

        plt.colorbar(im, ax=ax, shrink=0.9, label="Zustimmungs-Score (Median)")
        sprache_label = {"EN": "Englisch", "FA": "Farsi", "AR": "Arabisch"}.get(sprache, sprache)
        dim_short = AXIS_SHORT.get(dimension, dimension)
        n_zelle = data_n[0][0] if data_n and data_n[0] else 0
        ax.set_title(
            f"{dimension} — {ITERATIONS_NR} | {sprache_label}\n"
            f"(Median und [1.-3. Quartil], gemittelt über F1+F2 und alle Antwortsets; n={n_zelle} pro Zelle)",
            fontsize=11, fontweight="bold", pad=15)

        plt.tight_layout()
        output_path = os.path.join(output_ordner, f"heatmap_gemittelt_{dim_short}_{sprache}.png")
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Gemittelte Heatmap gespeichert: {output_path}")

# ── STANDARDFEHLER-HILFSFUNKTION ───────────────────────────
def standardfehler(serie):
    """Standardfehler des Mittelwerts = SD / sqrt(n)."""
    n = len(serie)
    if n < 2:
        return 0.0
    return float(serie.std() / np.sqrt(n))

# ── BALKEN: SPRACHVERGLEICH (mit Standardfehler) ───────────
def plot_sprachvergleich(df_valid, output_path):
    models = sorted(df_valid["modell"].unique())
    sprachen_labels = {"EN": "Englisch", "FA": "Farsi", "AR": "Arabisch"}
    sprachen_lst = ["EN", "FA", "AR"]

    fig, axes = plt.subplots(1, len(models), figsize=(5 * len(models), 5))
    if len(models) == 1:
        axes = [axes]

    for i, model in enumerate(models):
        ax = axes[i]
        modell_kurz = model.split("/")[-1]
        farbe = MODELL_FARBEN.get(modell_kurz, "#888888")
        means, ses = [], []
        for sprache in sprachen_lst:
            s = df_valid[(df_valid["modell"] == model) & (df_valid["sprache"] == sprache)]["score_adj"]
            means.append(s.mean()); ses.append(standardfehler(s))
        ax.bar([sprachen_labels[s] for s in sprachen_lst], means, color=farbe, alpha=0.8,
               yerr=ses, capsize=5, error_kw={"linewidth": 1.5})
        ax.set_ylim(0, 110)
        ax.set_title(modell_kurz, fontsize=10, fontweight="bold")
        ax.set_ylabel("Ø Agreement Score (± Standardfehler)" if i == 0 else "")
        ax.tick_params(axis='x', labelsize=9, pad=8)
        ax.axhline(y=50, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)

    fig.suptitle(f"Sprachvergleich — {ITERATIONS_NR}\n"
                 f"(Mittelwert ± Standardfehler über alle Dimensionen und Subgruppen)",
                 fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Gespeichert: {output_path}")

# ── BALKEN: FORMULIERUNG F1 vs F2 (mit Standardfehler) ─────
def plot_formulierungsvergleich(df_valid, output_path):
    models = sorted(df_valid["modell"].unique())
    formulierungen_lst = ["F1", "F2"]
    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(models)); width = 0.35
    colors = ["#2E75B6", "#ED7D31"]
    for j, form in enumerate(formulierungen_lst):
        means, ses = [], []
        for model in models:
            s = df_valid[(df_valid["modell"] == model) & (df_valid["formulierung"] == form)]["score_adj"]
            means.append(s.mean()); ses.append(standardfehler(s))
        ax.bar(x + j*width - width/2, means, width, label=form, color=colors[j], alpha=0.8,
               yerr=ses, capsize=4, error_kw={"linewidth": 1.5})
    ax.set_xticks(x)
    ax.set_xticklabels([m.split("/")[-1] for m in models], rotation=15, ha="right")
    ax.set_ylabel("Ø Agreement Score (± Standardfehler)")
    ax.set_ylim(0, 110)
    ax.set_title(f"Formulierungsvergleich F1 vs F2 — {ITERATIONS_NR}\n"
                 f"(Mittelwert ± Standardfehler über alle Sprachen, Dimensionen und Subgruppen)",
                 fontsize=11, fontweight="bold")
    ax.legend()
    ax.axhline(y=50, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Gespeichert: {output_path}")

# ── BALKEN: ANTWORTSETS (mit Standardfehler) ───────────────
def plot_antwortset_vergleich(df_valid, output_path):
    models = sorted(df_valid["modell"].unique())
    sets = ["Set1", "Set2", "Set3"]
    colors = ["#2E75B6", "#ED7D31", "#70AD47"]
    fig, ax = plt.subplots(figsize=(14, 5))
    x = np.arange(len(models)); width = 0.25
    for j, set_name in enumerate(sets):
        means, ses = [], []
        for model in models:
            s = df_valid[(df_valid["modell"] == model) & (df_valid["antwortset"] == set_name)]["score_adj"]
            means.append(s.mean() if len(s) > 0 else 0); ses.append(standardfehler(s))
        ax.bar(x + (j-1)*width, means, width, label=set_name, color=colors[j], alpha=0.8,
               yerr=ses, capsize=3, error_kw={"linewidth": 1.2})
    ax.set_xticks(x)
    ax.set_xticklabels([m.split("/")[-1] for m in models], rotation=15, ha="right")
    ax.set_ylabel("Ø Agreement Score (± Standardfehler)")
    ax.set_ylim(0, 110)
    ax.set_title(f"Antwortset-Vergleich Set1 vs Set2 vs Set3 — {ITERATIONS_NR}\n"
                 f"(Mittelwert ± Standardfehler über alle Sprachen, Dimensionen und Subgruppen)",
                 fontsize=11, fontweight="bold")
    ax.legend()
    ax.axhline(y=50, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Gespeichert: {output_path}")

# ── BALKEN: MODELLVERGLEICH PRO SUBGRUPPE (mit Standardfehler) ──
def plot_modellvergleich(df_valid, output_path):
    groups = [g for g in SUBGRUPPEN_ORDER if g in df_valid["subgruppe"].unique()]
    models = sorted(df_valid["modell"].unique())
    colors = [MODELL_FARBEN.get(m.split("/")[-1], "#888888") for m in models]

    fig, axes = plt.subplots(1, len(groups), figsize=(4 * len(groups), 5))
    if len(groups) == 1:
        axes = [axes]

    for i, group in enumerate(groups):
        ax = axes[i]
        means, ses = [], []
        for model in models:
            s = df_valid[(df_valid["modell"] == model) & (df_valid["subgruppe"] == group)]["score_adj"]
            means.append(s.mean()); ses.append(standardfehler(s))
        modell_labels = [m.split("/")[-1] for m in models]
        ax.bar(modell_labels, means, color=colors, alpha=0.8,
               yerr=ses, capsize=4, error_kw={"linewidth": 1.5})
        ax.set_ylim(0, 110)
        ax.set_title(group, fontsize=9, fontweight="bold")
        ax.set_ylabel("Ø Score (± Standardfehler)" if i == 0 else "")
        ax.tick_params(axis="x", rotation=45)
        ax.axhline(y=50, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)

    fig.suptitle(f"Modellvergleich pro Subgruppe — {ITERATIONS_NR}\n"
                 f"(Mittelwert ± Standardfehler über alle Dimensionen, Sprachen und Formulierungen)",
                 fontsize=11, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Gespeichert: {output_path}")

# ══════════════════════════════════════════════════════════
# HAUPTAUSWERTUNG
# ══════════════════════════════════════════════════════════
print("=" * 60)
print("VISUALISIERUNGEN ERSTELLEN")
print("=" * 60)

for sprache in sprachen:
    for formulierung in formulierungen:
        subset = df_valid[(df_valid["sprache"] == sprache) &
                          (df_valid["formulierung"] == formulierung)]
        if len(subset) == 0:
            continue
        print(f"\n── {sprache} | {formulierung} ──")
        summary_df = berechne_statistik(subset)
        titel = f"Agreement Score — {ITERATIONS_NR} | {sprache} | {formulierung}\n(Median und [1.-3. Quartil])"
        plot_heatmap(summary_df, titel,
                     os.path.join(OUTPUT_ORDNER, f"heatmap_{sprache}_{formulierung}.png"))
        summary_df.to_csv(
            os.path.join(OUTPUT_ORDNER, f"scoring_{sprache}_{formulierung}.csv"),
            index=False, encoding="utf-8-sig")
        plot_heatmap_pro_dimension(summary_df, sprache, formulierung, OUTPUT_ORDNER)

        kw_path = os.path.join(OUTPUT_ORDNER, f"signifikanz_modelle_{sprache}_{formulierung}.csv")
        signifikanztest(subset, "modell", kw_path)
        kw_path2 = os.path.join(OUTPUT_ORDNER, f"signifikanz_subgruppen_{sprache}_{formulierung}.csv")
        signifikanztest(subset, "subgruppe", kw_path2)

# ── GESAMTÜBERSICHT ────────────────────────────────────────
print()
print("=" * 60)
print("GESAMTÜBERSICHT ÜBER ALLE SPRACHEN")
print("=" * 60)
gesamt = df_valid.groupby(["modell", "subgruppe", "dimension"])["score_adj"].agg(
    median="median", q1=lambda x: x.quantile(0.25), q3=lambda x: x.quantile(0.75), n="count"
).round(2).reset_index()
gesamt.columns = ["Model", "Group", "Axis Name", "median", "q1", "q3", "n"]
gesamt.to_csv(os.path.join(OUTPUT_ORDNER, "scoring_GESAMT.csv"), index=False, encoding="utf-8-sig")
print("Gesamt-Scoring gespeichert: scoring_GESAMT.csv")
signifikanztest(df_valid, "modell", os.path.join(OUTPUT_ORDNER, "signifikanz_modelle_GESAMT.csv"))

# ── GEMITTELTE HEATMAPS + RADAR PRO MODELL ─────────────────
print()
print("=" * 60)
print("GEMITTELTE HEATMAPS + RADAR PRO MODELL (pro Sprache)")
print("=" * 60)
for sprache in sprachen:
    print(f"\n── {sprache} (gemittelt) ──")
    plot_heatmap_gemittelt(df_valid, sprache, OUTPUT_ORDNER)
    plot_radar_pro_modell(df_valid, sprache,
                          os.path.join(OUTPUT_ORDNER, f"radar_pro_modell_{sprache}.png"))

# Radar pro Modell GESAMT (über alle Sprachen)
print("\n── Radar pro Modell (GESAMT, über alle Sprachen) ──")
plot_radar_pro_modell(df_valid, None,
                      os.path.join(OUTPUT_ORDNER, "radar_pro_modell_GESAMT.png"))

# ── ZUSATZANALYSEN: BALKEN MIT STANDARDFEHLER ──────────────
print()
print("=" * 60)
print("ZUSATZANALYSEN (Balken mit Standardfehler)")
print("=" * 60)

print("\n── Sprachvergleich ──")
plot_sprachvergleich(df_valid, os.path.join(OUTPUT_ORDNER, "vergleich_sprachen.png"))
sprach_summary = df_valid.groupby(["modell", "sprache"])["score_adj"].agg(
    mean="mean", se=lambda x: x.std()/np.sqrt(len(x)), n="count").round(2).reset_index()
sprach_summary.columns = ["Modell", "Sprache", "Mittelwert", "Standardfehler", "n"]
sprach_summary.to_csv(os.path.join(OUTPUT_ORDNER, "vergleich_sprachen.csv"), index=False, encoding="utf-8-sig")
signifikanztest(df_valid, "sprache", os.path.join(OUTPUT_ORDNER, "signifikanz_sprachen_GESAMT.csv"))

print("\n── Formulierungsvergleich ──")
plot_formulierungsvergleich(df_valid, os.path.join(OUTPUT_ORDNER, "vergleich_formulierung_F1_F2.png"))
signifikanztest(df_valid, "formulierung", os.path.join(OUTPUT_ORDNER, "signifikanz_formulierung_GESAMT.csv"))

print("\n── Antwortset-Vergleich ──")
plot_antwortset_vergleich(df_valid, os.path.join(OUTPUT_ORDNER, "vergleich_antwortsets.png"))
signifikanztest(df_valid, "antwortset", os.path.join(OUTPUT_ORDNER, "signifikanz_antwortset_GESAMT.csv"))

print("\n── Modellvergleich ──")
plot_modellvergleich(df_valid, os.path.join(OUTPUT_ORDNER, "vergleich_modelle_subgruppen.png"))

print()
print("=" * 60)
print(f"FERTIG! Alle Dateien in: {OUTPUT_ORDNER}")
print("=" * 60)