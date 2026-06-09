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

# ── STATISTIK BERECHNEN ────────────────────────────────────
def berechne_statistik(subset):
    """Berechnet Mittelwert und SD pro Modell/Subgruppe/Dimension."""
    summary = subset.groupby(
        ["modell", "subgruppe", "dimension"]
    )["score_adj"].agg(["mean", "std", "count"]).round(2).reset_index()
    summary.columns = ["Model", "Group", "Axis Name", "mean", "sd", "n"]
    summary["sd"] = summary["sd"].fillna(0)
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

    # Kruskal-Wallis
    kw_stat, kw_p = stats.kruskal(*[gruppen_werte[g] for g in gruppen])
    ergebnisse.append({
        "Test": "Kruskal-Wallis",
        "Gruppe 1": "alle",
        "Gruppe 2": "-",
        "Statistik": round(kw_stat, 4),
        "p-Wert": round(kw_p, 4),
        "Signifikant (α=0.05)": "Ja" if kw_p < alpha else "Nein"
    })

    # Paarweise Mann-Whitney-U (nur wenn Kruskal-Wallis signifikant)
    if kw_p < alpha:
        paare = list(combinations(gruppen, 2))
        # Bonferroni-Korrektur
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
                "Signifikant (α=0.05)": "Ja" if u_p < alpha_korr else "Nein"
            })

    df_ergebnisse = pd.DataFrame(ergebnisse)
    df_ergebnisse.to_csv(output_path, index=False, encoding="utf-8-sig")
    return df_ergebnisse

# ── RADAR CHART MIT SD ─────────────────────────────────────
def plot_radar(summary_df, titel, output_path):
    models = sorted(summary_df["Model"].unique())
    groups = [g for g in SUBGRUPPEN_ORDER if g in summary_df["Group"].unique()]
    axis_names = [d for d in DIMENSIONEN_ORDER if d in summary_df["Axis Name"].unique()]

    if not groups or not axis_names:
        return

    number_of_axes = len(axis_names)
    angles = np.linspace(0, 2 * math.pi, number_of_axes, endpoint=False)

    nrows = math.ceil(len(groups) / 2)
    ncols = min(2, len(groups))
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols,
                             figsize=(7 * ncols, 6 * nrows),
                             subplot_kw={"polar": True})

    if len(groups) == 1:
        axes = [axes]
    elif nrows == 1:
        axes = list(axes)
    else:
        axes = axes.flatten()

    lines_for_legend = []

    for idx, group in enumerate(groups):
        if idx >= len(axes):
            break
        ax = axes[idx]

        for model in models:
            subset = summary_df[
                (summary_df["Model"] == model) &
                (summary_df["Group"] == group)
            ]
            scores = []
            sds = []
            for axis in axis_names:
                val = subset[subset["Axis Name"] == axis]
                scores.append(float(val["mean"].values[0]) if len(val) > 0 else 0)
                sds.append(float(val["sd"].values[0]) if len(val) > 0 else 0)

            scores_cycle = scores + [scores[0]]
            angle_cycle = list(angles) + [angles[0]]
            modell_kurz = model.split("/")[-1]
            farbe = MODELL_FARBEN.get(modell_kurz, "#888888")

            (line,) = ax.plot(angle_cycle, scores_cycle,
                             label=modell_kurz, color=farbe, linewidth=2)
            ax.fill(angle_cycle, scores_cycle, alpha=0.08, color=farbe)

            # SD als Schattierung
            scores_upper = [min(100, s + sd) for s, sd in zip(scores, sds)]
            scores_lower = [max(0, s - sd) for s, sd in zip(scores, sds)]
            scores_upper_cycle = scores_upper + [scores_upper[0]]
            scores_lower_cycle = scores_lower + [scores_lower[0]]
            ax.fill_between(angle_cycle, scores_lower_cycle, scores_upper_cycle,
                           alpha=0.05, color=farbe)

            if idx == 0:
                lines_for_legend.append(line)

        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        ax.set_xticks(angles)
        ax.set_xticklabels([AXIS_LABELS.get(a, a) for a in axis_names], fontsize=9)
        ax.tick_params(pad=20)
        ax.set_title(f"\n{group}\n", fontsize=11, fontweight="bold", pad=20)
        ax.set_ylim(0, 100)
        ax.set_yticks([25, 50, 75, 100])

    for unused in range(len(groups), len(axes)):
        axes[unused].set_visible(False)

    labels = [line.get_label() for line in lines_for_legend]
    fig.legend(lines_for_legend, labels, loc="lower center",
               bbox_to_anchor=(0.5, 0.02), ncol=len(models), fontsize=10)
    fig.suptitle(titel, fontsize=13, fontweight="bold", y=0.98)
    plt.tight_layout(rect=[0, 0.06, 1, 0.96])
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Radar gespeichert: {output_path}")

# ── HEATMAP MIT SD ─────────────────────────────────────────
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

        data_mean = []
        data_sd = []
        for group in groups:
            row_mean = []
            row_sd = []
            for axis in axis_names:
                val = subset[
                    (subset["Group"] == group) &
                    (subset["Axis Name"] == axis)
                ]
                row_mean.append(float(val["mean"].values[0]) if len(val) > 0 else np.nan)
                row_sd.append(float(val["sd"].values[0]) if len(val) > 0 else np.nan)
            data_mean.append(row_mean)
            data_sd.append(row_sd)

        data_arr = np.array(data_mean)
        sd_arr = np.array(data_sd)

        im = ax.imshow(data_arr, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")

        ax.set_xticks(range(len(axis_names)))
        ax.set_xticklabels([AXIS_SHORT.get(a, a) for a in axis_names],
                           rotation=0, fontsize=10)
        ax.set_yticks(range(len(groups)))
        ax.set_yticklabels(groups, fontsize=8)
        ax.set_title(model.split("/")[-1], fontsize=10, fontweight="bold")

        for row in range(len(groups)):
            for col in range(len(axis_names)):
                val = data_arr[row, col]
                sd = sd_arr[row, col]
                if not np.isnan(val):
                    text_color = "white" if val < 30 or val > 70 else "black"
                    # Mittelwert gross, SD klein darunter
                    ax.text(col, row - 0.1, f"{val:.0f}",
                           ha="center", va="center", fontsize=10,
                           fontweight="bold", color=text_color)
                    ax.text(col, row + 0.18, f"±{sd:.0f}",
                           ha="center", va="center", fontsize=7,
                           color=text_color, alpha=0.85)

        plt.colorbar(im, ax=ax, shrink=0.8)

    fig.suptitle(titel, fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Heatmap gespeichert: {output_path}")

# ── HEATMAP PRO DIMENSION (Samsinger-Stil) ─────────────────
def plot_heatmap_pro_dimension(summary_df, sprache, formulierung, output_ordner):
    """Eine Heatmap pro Dimension: Zeilen = Subgruppen, Spalten = Modelle."""
    models = sorted(summary_df["Model"].unique())
    groups = [g for g in SUBGRUPPEN_ORDER if g in summary_df["Group"].unique()]
    axis_names = [d for d in DIMENSIONEN_ORDER if d in summary_df["Axis Name"].unique()]
    
    modell_labels = [m.split("/")[-1] for m in models]
    
    for dimension in axis_names:
        fig, ax = plt.subplots(figsize=(10, 4))
        
        data_mean = []
        data_sd = []
        
        for group in groups:
            row_mean = []
            row_sd = []
            for model in models:
                val = summary_df[
                    (summary_df["Model"] == model) &
                    (summary_df["Group"] == group) &
                    (summary_df["Axis Name"] == dimension)
                ]
                row_mean.append(float(val["mean"].values[0]) if len(val) > 0 else np.nan)
                row_sd.append(float(val["sd"].values[0]) if len(val) > 0 else np.nan)
            data_mean.append(row_mean)
            data_sd.append(row_sd)
        
        data_arr = np.array(data_mean)
        sd_arr = np.array(data_sd)
        
        im = ax.imshow(data_arr, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
        
        ax.set_xticks(range(len(models)))
        ax.set_xticklabels(modell_labels, fontsize=10, rotation=15, ha="right")
        ax.set_yticks(range(len(groups)))
        ax.set_yticklabels(groups, fontsize=10)
        
        for row in range(len(groups)):
            for col in range(len(models)):
                val = data_arr[row, col]
                sd = sd_arr[row, col]
                if not np.isnan(val):
                    text_color = "white" if val < 30 or val > 70 else "black"
                    ax.text(col, row - 0.12, f"{val:.0f}",
                           ha="center", va="center", fontsize=12,
                           fontweight="bold", color=text_color)
                    ax.text(col, row + 0.2, f"±{sd:.0f}",
                           ha="center", va="center", fontsize=8,
                           color=text_color, alpha=0.85)
        
        plt.colorbar(im, ax=ax, shrink=0.9, label="Agreement Score")
        
        dim_short = AXIS_SHORT.get(dimension, dimension)
        ax.set_title(
            f"{dimension} — Iteration 9 | {sprache} | {formulierung}\n"
            f"(Durchschnittlicher Zustimmungs-Score ± Standardabweichung)",
            fontsize=11, fontweight="bold", pad=15
        )
        
        plt.tight_layout()
        output_path = os.path.join(output_ordner, f"heatmap_dim_{dim_short}_{sprache}_{formulierung}.png")
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Heatmap-Dimension gespeichert: {output_path}")

# ── GEMITTELTE HEATMAP (F1+F2+Sets zusammengefasst) ───────
def plot_heatmap_gemittelt(df_valid, sprache, output_ordner):
    """Heatmap pro Dimension gemittelt über F1+F2 und alle Antwortsets.
    Zeilen = Subgruppen, Spalten = Modelle. 4 Heatmaps pro Sprache."""
    
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
        
        data_mean = []
        data_sd = []
        
        for group in groups:
            row_mean = []
            row_sd = []
            for model in models:
                val = subset[
                    (subset["modell"] == model) &
                    (subset["subgruppe"] == group) &
                    (subset["dimension"] == dimension)
                ]["score_adj"]
                row_mean.append(float(val.mean()) if len(val) > 0 else np.nan)
                row_sd.append(float(val.std()) if len(val) > 0 else np.nan)
            data_mean.append(row_mean)
            data_sd.append(row_sd)
        
        data_arr = np.array(data_mean)
        sd_arr = np.array(data_sd)
        
        im = ax.imshow(data_arr, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
        
        ax.set_xticks(range(len(models)))
        ax.set_xticklabels(modell_labels, fontsize=10, rotation=15, ha="right")
        ax.set_yticks(range(len(groups)))
        ax.set_yticklabels(groups, fontsize=10)
        
        for row in range(len(groups)):
            for col in range(len(models)):
                val = data_arr[row, col]
                sd = sd_arr[row, col]
                if not np.isnan(val):
                    text_color = "white" if val < 30 or val > 70 else "black"
                    ax.text(col, row - 0.12, f"{val:.0f}",
                           ha="center", va="center", fontsize=12,
                           fontweight="bold", color=text_color)
                    ax.text(col, row + 0.2, f"±{sd:.0f}",
                           ha="center", va="center", fontsize=8,
                           color=text_color, alpha=0.85)
        
        plt.colorbar(im, ax=ax, shrink=0.9, label="Agreement Score")
        
        sprache_label = {"EN": "Englisch", "FA": "Farsi", "AR": "Arabisch"}.get(sprache, sprache)
        dim_short = AXIS_SHORT.get(dimension, dimension)
        
        ax.set_title(
            f"{dimension} — Iteration 9 | {sprache_label}\n"
            f"(Durchschnittlicher Zustimmungs-Score ± SD, gemittelt über F1+F2 und alle Antwortsets)",
            fontsize=11, fontweight="bold", pad=15
        )
        
        plt.tight_layout()
        output_path = os.path.join(output_ordner, f"heatmap_gemittelt_{dim_short}_{sprache}.png")
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Gemittelte Heatmap gespeichert: {output_path}")

# ── GEMITTELTER RADAR CHART ────────────────────────────────
def plot_radar_gemittelt(df_valid, sprache, output_ordner):
    """Radar Chart gemittelt über F1+F2 und alle Antwortsets pro Sprache."""
    
    subset = df_valid[df_valid["sprache"] == sprache]
    if len(subset) == 0:
        return
    
    models = sorted(subset["modell"].unique())
    groups = [g for g in SUBGRUPPEN_ORDER if g in subset["subgruppe"].unique()]
    axis_names = [d for d in DIMENSIONEN_ORDER if d in subset["dimension"].unique()]
    
    if not groups or not axis_names:
        return
    
    number_of_axes = len(axis_names)
    angles = np.linspace(0, 2 * math.pi, number_of_axes, endpoint=False)
    
    nrows = math.ceil(len(groups) / 2)
    ncols = min(2, len(groups))
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols,
                             figsize=(7 * ncols, 6 * nrows),
                             subplot_kw={"polar": True})
    
    if len(groups) == 1:
        axes = [axes]
    elif nrows == 1:
        axes = list(axes)
    else:
        axes = axes.flatten()
    
    lines_for_legend = []
    
    for idx, group in enumerate(groups):
        if idx >= len(axes):
            break
        ax = axes[idx]
        
        for model in models:
            val_subset = subset[
                (subset["modell"] == model) &
                (subset["subgruppe"] == group)
            ]
            
            scores = []
            sds = []
            for axis in axis_names:
                dim_vals = val_subset[val_subset["dimension"] == axis]["score_adj"]
                scores.append(float(dim_vals.mean()) if len(dim_vals) > 0 else 0)
                sds.append(float(dim_vals.std()) if len(dim_vals) > 0 else 0)
            
            scores_cycle = scores + [scores[0]]
            angle_cycle = list(angles) + [angles[0]]
            modell_kurz = model.split("/")[-1]
            farbe = MODELL_FARBEN.get(modell_kurz, "#888888")
            
            (line,) = ax.plot(angle_cycle, scores_cycle,
                             label=modell_kurz, color=farbe, linewidth=2)
            ax.fill(angle_cycle, scores_cycle, alpha=0.08, color=farbe)
            
            # SD Schattierung
            scores_upper = [min(100, s + sd) for s, sd in zip(scores, sds)]
            scores_lower = [max(0, s - sd) for s, sd in zip(scores, sds)]
            ax.fill_between(angle_cycle,
                           scores_lower + [scores_lower[0]],
                           scores_upper + [scores_upper[0]],
                           alpha=0.05, color=farbe)
            
            if idx == 0:
                lines_for_legend.append(line)
        
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        ax.set_xticks(angles)
        ax.set_xticklabels([AXIS_LABELS.get(a, a) for a in axis_names], fontsize=9)
        ax.tick_params(pad=20)
        ax.set_title(f"\n{group}\n", fontsize=11, fontweight="bold", pad=20)
        ax.set_ylim(0, 100)
        ax.set_yticks([25, 50, 75, 100])
    
    for unused in range(len(groups), len(axes)):
        axes[unused].set_visible(False)
    
    labels = [line.get_label() for line in lines_for_legend]
    fig.legend(lines_for_legend, labels, loc="lower center",
               bbox_to_anchor=(0.5, 0.02), ncol=len(models), fontsize=10)
    
    sprache_label = {"EN": "Englisch", "FA": "Farsi", "AR": "Arabisch"}.get(sprache, sprache)
    fig.suptitle(
        f"Agreement Score — Iteration 9 | {sprache_label}\n"
        f"(Mittelwert ± SD, gemittelt über F1+F2 und alle Antwortsets)",
        fontsize=13, fontweight="bold", y=0.98
    )
    plt.tight_layout(rect=[0, 0.06, 1, 0.96])
    
    output_path = os.path.join(output_ordner, f"radar_gemittelt_{sprache}.png")
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Gemittelter Radar Chart gespeichert: {output_path}")




# ── HAUPTAUSWERTUNG ────────────────────────────────────────
print("=" * 60)
print("VISUALISIERUNGEN ERSTELLEN")
print("=" * 60)

for sprache in sprachen:
    for formulierung in formulierungen:
        subset = df_valid[
            (df_valid["sprache"] == sprache) &
            (df_valid["formulierung"] == formulierung)
        ]
        if len(subset) == 0:
            continue

        print(f"\n── {sprache} | {formulierung} ──")

        # Statistik berechnen
        summary_df = berechne_statistik(subset)

        # Titel
        titel = f"Agreement Score — {ITERATIONS_NR} | {sprache} | {formulierung}\n(Mittelwert ± Standardabweichung)"

        # Visualisierungen
        plot_radar(summary_df, titel,
                  os.path.join(OUTPUT_ORDNER, f"radar_{sprache}_{formulierung}.png"))
        plot_heatmap(summary_df, titel,
                    os.path.join(OUTPUT_ORDNER, f"heatmap_{sprache}_{formulierung}.png"))

        # Scoring CSV mit SD
        summary_df.to_csv(
            os.path.join(OUTPUT_ORDNER, f"scoring_{sprache}_{formulierung}.csv"),
            index=False, encoding="utf-8-sig")
        print(f"  Scoring CSV gespeichert")

        # Neue Heatmaps pro Dimension (Samsinger-Stil)
        plot_heatmap_pro_dimension(summary_df, sprache, formulierung, OUTPUT_ORDNER)

        # Signifikanztests: Modellvergleich
        kw_path = os.path.join(OUTPUT_ORDNER, f"signifikanz_modelle_{sprache}_{formulierung}.csv")
        kw_ergebnis = signifikanztest(subset, "modell", kw_path)
        if kw_ergebnis is not None:
            kw_row = kw_ergebnis[kw_ergebnis["Test"] == "Kruskal-Wallis"].iloc[0]
            print(f"  Kruskal-Wallis (Modelle): H={kw_row['Statistik']}, p={kw_row['p-Wert']} → {'signifikant' if kw_row['Signifikant (α=0.05)'] == 'Ja' else 'nicht signifikant'}")

        # Signifikanztests: Subgruppenvergleich
        kw_path2 = os.path.join(OUTPUT_ORDNER, f"signifikanz_subgruppen_{sprache}_{formulierung}.csv")
        kw_ergebnis2 = signifikanztest(subset, "subgruppe", kw_path2)
        if kw_ergebnis2 is not None:
            kw_row2 = kw_ergebnis2[kw_ergebnis2["Test"] == "Kruskal-Wallis"].iloc[0]
            print(f"  Kruskal-Wallis (Subgruppen): H={kw_row2['Statistik']}, p={kw_row2['p-Wert']} → {'signifikant' if kw_row2['Signifikant (α=0.05)'] == 'Ja' else 'nicht signifikant'}")

# ── GESAMTÜBERSICHT ────────────────────────────────────────
print()
print("=" * 60)
print("GESAMTÜBERSICHT ÜBER ALLE SPRACHEN")
print("=" * 60)

# Gesamtstatistik pro Modell über alle Sprachen
gesamt = df_valid.groupby(["modell", "subgruppe", "dimension"])["score_adj"].agg(
    ["mean", "std", "count"]).round(2).reset_index()
gesamt.columns = ["Model", "Group", "Axis Name", "mean", "sd", "n"]
gesamt.to_csv(
    os.path.join(OUTPUT_ORDNER, "scoring_GESAMT.csv"),
    index=False, encoding="utf-8-sig")
print(f"Gesamt-Scoring gespeichert: scoring_GESAMT.csv")

# Gesamter Kruskal-Wallis über alle Sprachen
kw_gesamt = signifikanztest(df_valid, "modell",
    os.path.join(OUTPUT_ORDNER, "signifikanz_modelle_GESAMT.csv"))
if kw_gesamt is not None:
    kw_row = kw_gesamt[kw_gesamt["Test"] == "Kruskal-Wallis"].iloc[0]
    print(f"Kruskal-Wallis gesamt (Modelle): p={kw_row['p-Wert']} → {'signifikant' if kw_row['Signifikant (α=0.05)'] == 'Ja' else 'nicht signifikant'}")

print()
print("=" * 60)
print(f"FERTIG! Alle Dateien in: {OUTPUT_ORDNER}")
print("=" * 60)


# ══════════════════════════════════════════════════════════
# ZUSATZANALYSEN (Beats Robustheitsfragen + Samsinger-Stil)
# ══════════════════════════════════════════════════════════

# Gemittelte Heatmaps pro Sprache
print()
print("=" * 60)
print("GEMITTELTE HEATMAPS (F1+F2+Sets)")
print("=" * 60)
for sprache in sprachen:
    print(f"\n── {sprache} (gemittelt) ──")
    plot_heatmap_gemittelt(df_valid, sprache, OUTPUT_ORDNER)
    plot_radar_gemittelt(df_valid, sprache, OUTPUT_ORDNER)

print()
print("=" * 60)
print("ZUSATZANALYSEN")
print("=" * 60)

# ── 1. SPRACHVERGLEICH ─────────────────────────────────────
print("\n── Sprachvergleich EN vs FA vs AR ──")

def plot_sprachvergleich(df_valid, output_path):
    """Balkendiagramm: Score pro Sprache und Modell, aggregiert über alle Dimensionen."""
    models = sorted(df_valid["modell"].unique())
    sprachen_labels = {"EN": "Englisch", "FA": "Farsi", "AR": "Arabisch"}
    sprachen = ["EN", "FA", "AR"]
    
    fig, axes = plt.subplots(1, len(models), figsize=(5 * len(models), 5))
    if len(models) == 1:
        axes = [axes]
    
    for i, model in enumerate(models):
        ax = axes[i]
        modell_kurz = model.split("/")[-1]
        farbe = MODELL_FARBEN.get(modell_kurz, "#888888")
        
        means = []
        sds = []
        for sprache in sprachen:
            subset = df_valid[(df_valid["modell"] == model) & (df_valid["sprache"] == sprache)]
            means.append(subset["score_adj"].mean())
            sds.append(subset["score_adj"].std())
        
        ax.bar([sprachen_labels[s] for s in sprachen], means, color=farbe, alpha=0.8, yerr=sds,
               capsize=5, error_kw={"linewidth": 1.5})
        ax.set_ylim(0, 120)
        ax.set_title(modell_kurz, fontsize=10, fontweight="bold")
        ax.set_ylabel("Ø Agreement Score" if i == 0 else "")
        ax.set_xlabel("")
        ax.tick_params(axis='x', labelsize=9, pad=8)
        ax.axhline(y=50, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)

    fig.suptitle(f"Sprachvergleich — {ITERATIONS_NR}\n(Ø Agreement Score ± SD über alle Dimensionen und Subgruppen)",
                fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Gespeichert: {output_path}")

def plot_formulierungsvergleich(df_valid, output_path):
    """F1 vs F2 Vergleich pro Modell."""
    models = sorted(df_valid["modell"].unique())
    formulierungen = ["F1", "F2"]
    fig, ax = plt.subplots(figsize=(12, 5))
    x = np.arange(len(models))
    width = 0.35
    colors = ["#2E75B6", "#ED7D31"]
    for j, form in enumerate(formulierungen):
        means = []
        sds = []
        for model in models:
            subset = df_valid[(df_valid["modell"] == model) & (df_valid["formulierung"] == form)]
            means.append(subset["score_adj"].mean())
            sds.append(subset["score_adj"].std())
        ax.bar(x + j*width - width/2, means, width, label=form,
               color=colors[j], alpha=0.8, yerr=sds, capsize=4,
               error_kw={"linewidth": 1.5})
    ax.set_xticks(x)
    ax.set_xticklabels([m.split("/")[-1] for m in models], rotation=15, ha="right")
    ax.set_ylabel("Ø Agreement Score")
    ax.set_ylim(0, 120)
    ax.set_title(f"Formulierungsvergleich F1 vs F2 — {ITERATIONS_NR}\n(Ø Agreement Score ± SD über alle Sprachen, Dimensionen und Subgruppen)",
                fontsize=11, fontweight="bold")
    ax.legend()
    ax.axhline(y=50, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Gespeichert: {output_path}")

plot_sprachvergleich(df_valid, os.path.join(OUTPUT_ORDNER, "vergleich_sprachen.png"))

# CSV Sprachvergleich
sprach_summary = df_valid.groupby(["modell", "sprache"])["score_adj"].agg(
    ["mean", "std", "count"]).round(2).reset_index()
sprach_summary.columns = ["Modell", "Sprache", "Mittelwert", "SD", "n"]
sprach_summary.to_csv(os.path.join(OUTPUT_ORDNER, "vergleich_sprachen.csv"),
                     index=False, encoding="utf-8-sig")

kw_sprache = signifikanztest(df_valid, "sprache",
    os.path.join(OUTPUT_ORDNER, "signifikanz_sprachen_GESAMT.csv"))
if kw_sprache is not None:
    kw_row = kw_sprache[kw_sprache["Test"] == "Kruskal-Wallis"].iloc[0]
    print(f"  Kruskal-Wallis (Sprachen): p={kw_row['p-Wert']} → {'signifikant' if kw_row['Signifikant (α=0.05)'] == 'Ja' else 'nicht signifikant'}")

print("\n── Formulierungsvergleich F1 vs F2 ──")
plot_formulierungsvergleich(df_valid, os.path.join(OUTPUT_ORDNER, "vergleich_formulierung_F1_F2.png"))

# CSV Formulierungsvergleich
form_summary = df_valid.groupby(["modell", "formulierung"])["score_adj"].agg(
    ["mean", "std", "count"]).round(2).reset_index()
form_summary.columns = ["Modell", "Formulierung", "Mittelwert", "SD", "n"]
form_summary.to_csv(os.path.join(OUTPUT_ORDNER, "vergleich_formulierung_F1_F2.csv"),
                   index=False, encoding="utf-8-sig")

# Kruskal-Wallis für Formulierung
kw_form = signifikanztest(df_valid, "formulierung",
    os.path.join(OUTPUT_ORDNER, "signifikanz_formulierung_GESAMT.csv"))
if kw_form is not None:
    kw_row = kw_form[kw_form["Test"] == "Kruskal-Wallis"].iloc[0]
    print(f"  Kruskal-Wallis (Formulierung): p={kw_row['p-Wert']} → {'signifikant' if kw_row['Signifikant (α=0.05)'] == 'Ja' else 'nicht signifikant'}")

# ── 3. ANTWORTSET-VERGLEICH Set1 vs Set2 vs Set3 ──────────
print("\n── Antwortset-Vergleich Set1 vs Set2 vs Set3 ──")

def plot_antwortset_vergleich(df_valid, output_path):
    """Set1 vs Set2 vs Set3 Vergleich pro Modell."""
    models = sorted(df_valid["modell"].unique())
    sets = ["Set1", "Set2", "Set3"]
    colors = ["#2E75B6", "#ED7D31", "#70AD47"]
    
    fig, ax = plt.subplots(figsize=(14, 5))
    x = np.arange(len(models))
    width = 0.25
    
    for j, set_name in enumerate(sets):
        means = []
        sds = []
        for model in models:
            subset = df_valid[(df_valid["modell"] == model) & (df_valid["antwortset"] == set_name)]
            means.append(subset["score_adj"].mean() if len(subset) > 0 else 0)
            sds.append(subset["score_adj"].std() if len(subset) > 0 else 0)
        
        offset = (j - 1) * width
        bars = ax.bar(x + offset, means, width, label=set_name,
                     color=colors[j], alpha=0.8, yerr=sds, capsize=3,
                     error_kw={"linewidth": 1.2})
    
    ax.set_xticks(x)
    ax.set_xticklabels([m.split("/")[-1] for m in models], rotation=15, ha="right")
    ax.set_ylabel("Ø Agreement Score")
    ax.set_ylim(0, 120)
    ax.set_title(f"Antwortset-Vergleich Set1 vs Set2 vs Set3 — {ITERATIONS_NR}\n(Ø Agreement Score ± SD über alle Sprachen, Dimensionen und Subgruppen)",
                fontsize=11, fontweight="bold")
    ax.legend()
    ax.axhline(y=50, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Gespeichert: {output_path}")

plot_antwortset_vergleich(df_valid, os.path.join(OUTPUT_ORDNER, "vergleich_antwortsets.png"))

# CSV Antwortset
set_summary = df_valid.groupby(["modell", "antwortset"])["score_adj"].agg(
    ["mean", "std", "count"]).round(2).reset_index()
set_summary.columns = ["Modell", "Antwortset", "Mittelwert", "SD", "n"]
set_summary.to_csv(os.path.join(OUTPUT_ORDNER, "vergleich_antwortsets.csv"),
                  index=False, encoding="utf-8-sig")

# Kruskal-Wallis für Antwortset
kw_set = signifikanztest(df_valid, "antwortset",
    os.path.join(OUTPUT_ORDNER, "signifikanz_antwortset_GESAMT.csv"))
if kw_set is not None:
    kw_row = kw_set[kw_set["Test"] == "Kruskal-Wallis"].iloc[0]
    print(f"  Kruskal-Wallis (Antwortset): p={kw_row['p-Wert']} → {'signifikant' if kw_row['Signifikant (α=0.05)'] == 'Ja' else 'nicht signifikant'}")

# ── 4. MODELLVERGLEICH GESAMT ──────────────────────────────
print("\n── Modellvergleich über alle Dimensionen ──")

def plot_modellvergleich(df_valid, output_path):
    """Aggregierter Modellvergleich pro Subgruppe."""
    groups = [g for g in SUBGRUPPEN_ORDER if g in df_valid["subgruppe"].unique()]
    models = sorted(df_valid["modell"].unique())
    colors = [MODELL_FARBEN.get(m.split("/")[-1], "#888888") for m in models]
    
    fig, axes = plt.subplots(1, len(groups), figsize=(4 * len(groups), 5))
    if len(groups) == 1:
        axes = [axes]
    
    for i, group in enumerate(groups):
        ax = axes[i]
        means = []
        sds = []
        for model in models:
            subset = df_valid[(df_valid["modell"] == model) & (df_valid["subgruppe"] == group)]
            means.append(subset["score_adj"].mean())
            sds.append(subset["score_adj"].std())
        
        modell_labels = [m.split("/")[-1] for m in models]
        bars = ax.bar(modell_labels, means, color=colors, alpha=0.8,
                     yerr=sds, capsize=4, error_kw={"linewidth": 1.5})
        ax.set_ylim(0, 120)
        ax.set_title(group, fontsize=9, fontweight="bold")
        ax.set_ylabel("Ø Score" if i == 0 else "")
        ax.tick_params(axis="x", rotation=45)
        ax.axhline(y=50, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
    
    fig.suptitle(f"Modellvergleich pro Subgruppe — {ITERATIONS_NR}\n(Ø Agreement Score ± SD über alle Dimensionen, Sprachen und Formulierungen)",
                fontsize=11, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Gespeichert: {output_path}")

plot_modellvergleich(df_valid, os.path.join(OUTPUT_ORDNER, "vergleich_modelle_subgruppen.png"))

print()
print("=" * 60)
print("ALLE ZUSATZANALYSEN ABGESCHLOSSEN!")
print(f"Dateien in: {OUTPUT_ORDNER}")
print("=" * 60)