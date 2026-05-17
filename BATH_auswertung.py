import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import math
import os

# ── KONFIGURATION ──────────────────────────────────────────
# Pfad anpassen je nach Iteration:
# Iteration 1: CSV_DATEI = "iterationen/iteration1/resultate_iteration1_EN.csv"
# Iteration 2: CSV_DATEI = "iterationen/iteration2/resultate_iteration2_EN.csv"
# Iteration 4: CSV_DATEI = "iterationen/iteration4/resultate_iteration4_EN.csv"
# Iteration 6: CSV_DATEI = "iterationen/iteration6/resultate_iteration6_ALL.csv"

CSV_DATEI = "iterationen/iteration6/resultate_iteration6_ALL.csv"
OUTPUT_ORDNER = "iterationen/iteration6/auswertung"
ITERATIONS_NR = "Iteration 6"

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

SUBGRUPPEN_ORDER = [
    "Hardline-Principlists",
    "IRGC/Securocrats",
    "Pragmatic Moderates",
    "Reformists",
]

MODELL_FARBEN = {
    "claude-sonnet-4-5": "#2E75B6",
    "gemini-2.5-flash": "#ED7D31",
    "gemini-2.5-pro": "#ED7D31",
    "gemini-3.1-pro-preview": "#ED7D31",
    "gpt-5.4": "#70AD47",
    "grok-3": "#FF0000",
    "grok-4.3": "#FF0000",
}

# ── DATEN LADEN ────────────────────────────────────────────
df = pd.read_csv(CSV_DATEI, encoding="utf-8-sig")
print(f"Geladen: {len(df)} Zeilen")

df["subgruppe"] = df["subgruppe"].map(lambda x: SUBGRUPPEN_EN.get(str(x).strip(), x))
df["dimension"] = df["dimension"].map(lambda x: DIMENSIONEN_EN.get(str(x).strip(), x))

df_valid = df[df["score"] != -1].copy()
print(f"Valide: {len(df_valid)} ({round(len(df_valid)/len(df)*100,1)}%)")
print()

# ── FEHLERANALYSE ──────────────────────────────────────────
print("=" * 60)
print("ERROR ANALYSIS PER MODEL")
print("=" * 60)
for modell in sorted(df["modell"].unique()):
    total = len(df[df["modell"] == modell])
    errors = len(df[(df["modell"] == modell) & (df["score"] == -1)])
    print(f"{modell.split('/')[-1]:25} | {total-errors}/{total} | {round((total-errors)/total*100,1)}%")
print()

# ── INVERTIERUNG ───────────────────────────────────────────
def invertiere(score, invertiert):
    if str(invertiert).lower() in ["true", "ja"] and score != -1:
        return 100 - score
    return score

df_valid["score_adj"] = df_valid.apply(
    lambda row: invertiere(row["score"], row["invertiert"]), axis=1)

# ── SPRACHEN UND FORMULIERUNGEN ────────────────────────────
if "sprache" in df_valid.columns:
    sprachen = sorted(df_valid["sprache"].unique())
else:
    sprachen = ["EN"]
    df_valid["sprache"] = "EN"

if "formulierung" in df_valid.columns:
    formulierungen = sorted(df_valid["formulierung"].unique())
else:
    formulierungen = ["F1"]
    df_valid["formulierung"] = "F1"

# ── RADAR CHART ────────────────────────────────────────────
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
            for axis in axis_names:
                val = subset[subset["Axis Name"] == axis]["mean"].values
                scores.append(float(val[0]) if len(val) > 0 else 0)

            scores_cycle = scores + [scores[0]]
            angle_cycle = list(angles) + [angles[0]]
            modell_kurz = model.split("/")[-1]
            farbe = MODELL_FARBEN.get(modell_kurz, "#888888")

            (line,) = ax.plot(angle_cycle, scores_cycle,
                             label=modell_kurz, color=farbe, linewidth=2)
            ax.fill(angle_cycle, scores_cycle, alpha=0.1, color=farbe)

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
    print(f"Gespeichert: {output_path}")

# ── HEATMAP ────────────────────────────────────────────────
def plot_heatmap(summary_df, titel, output_path):
    models = sorted(summary_df["Model"].unique())
    groups = [g for g in SUBGRUPPEN_ORDER if g in summary_df["Group"].unique()]
    axis_names = [d for d in DIMENSIONEN_ORDER if d in summary_df["Axis Name"].unique()]

    if not models or not groups:
        return

    axis_short = {
        "Economic Costs": "EC",
        "Negotiation Readiness": "NR",
        "Nuclear Sovereignty": "NS",
        "Security Function": "SF"
    }

    fig, axes = plt.subplots(1, len(models), figsize=(5 * len(models), 5))
    if len(models) == 1:
        axes = [axes]

    for i, model in enumerate(models):
        ax = axes[i]
        subset = summary_df[summary_df["Model"] == model]

        data = []
        for group in groups:
            row = []
            for axis in axis_names:
                val = subset[
                    (subset["Group"] == group) &
                    (subset["Axis Name"] == axis)
                ]["mean"].values
                row.append(float(val[0]) if len(val) > 0 else np.nan)
            data.append(row)

        data_arr = np.array(data)
        im = ax.imshow(data_arr, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")

        ax.set_xticks(range(len(axis_names)))
        ax.set_xticklabels([axis_short.get(a, a) for a in axis_names],
                           rotation=0, fontsize=10)
        ax.set_yticks(range(len(groups)))
        ax.set_yticklabels(groups, fontsize=8)
        ax.set_title(model.split("/")[-1], fontsize=10, fontweight="bold")

        for row in range(len(groups)):
            for col in range(len(axis_names)):
                val = data_arr[row, col]
                if not np.isnan(val):
                    ax.text(col, row, f"{val:.0f}", ha="center", va="center",
                           fontsize=9, fontweight="bold",
                           color="white" if val < 30 or val > 70 else "black")

        plt.colorbar(im, ax=ax, shrink=0.8)

    fig.suptitle(titel, fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Gespeichert: {output_path}")

# ── ALLE KOMBINATIONEN AUSWERTEN ───────────────────────────
print("=" * 60)
print("CREATING VISUALIZATIONS")
print("=" * 60)

for sprache in sprachen:
    for formulierung in formulierungen:
        subset = df_valid[
            (df_valid["sprache"] == sprache) &
            (df_valid["formulierung"] == formulierung)
        ]
        if len(subset) == 0:
            continue

        summary_df = subset.groupby(
            ["modell", "subgruppe", "dimension"]
        )["score_adj"].mean().round(1).reset_index()
        summary_df.columns = ["Model", "Group", "Axis Name", "mean"]

        # Titel mit spezifischer Sprache und Formulierung
        titel = f"Agreement Score — {ITERATIONS_NR} | {sprache} | {formulierung}"
        print(f"\n{sprache} | {formulierung}:")

        plot_radar(summary_df, titel,
                  os.path.join(OUTPUT_ORDNER, f"radar_{sprache}_{formulierung}.png"))
        plot_heatmap(summary_df, titel,
                    os.path.join(OUTPUT_ORDNER, f"heatmap_{sprache}_{formulierung}.png"))
        summary_df.to_csv(
            os.path.join(OUTPUT_ORDNER, f"scoring_{sprache}_{formulierung}.csv"),
            index=False, encoding="utf-8-sig")

print()
print("=" * 60)
print("DONE! Files saved in:", OUTPUT_ORDNER)
print("=" * 60)