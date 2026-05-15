import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import math
import os

# ── KONFIGURATION ──────────────────────────────────────────
CSV_DATEI = "iterationen/iteration4/resultate_iteration4_EN.csv"  # Dateiname anpassen je nach Iteration
OUTPUT_ORDNER = "iterationen/iteration4/auswertung"

# ── SETUP ──────────────────────────────────────────────────
os.makedirs(OUTPUT_ORDNER, exist_ok=True)

# ── DATEN LADEN ────────────────────────────────────────────
df = pd.read_csv(CSV_DATEI, encoding="utf-8-sig")
print(f"✅ {len(df)} Zeilen geladen aus {CSV_DATEI}")

# Nur valide Antworten (score != -1)
df_valid = df[df["score"] != -1].copy()
print(f"✅ {len(df_valid)} valide Antworten ({round(len(df_valid)/len(df)*100,1)}% Erfolgsrate)")
print()

# ── FEHLERANALYSE PRO MODELL ────────────────────────────────
print("=" * 50)
print("FEHLERANALYSE PRO MODELL")
print("=" * 50)
for modell in df["modell"].unique():
    total = len(df[df["modell"] == modell])
    errors = len(df[(df["modell"] == modell) & (df["score"] == -1)])
    erfolg = round((total - errors) / total * 100, 1)
    print(f"{modell.split('/')[-1]:30} | {total-errors}/{total} valide | {erfolg}%")

print()

# ── INVERTIERUNG ANWENDEN ──────────────────────────────────
# Bei invertierten Items: Score umkehren (100->0, 75->25, 25->75, 0->100)
def invertiere(score, invertiert):
    if invertiert and score != -1:
        return 100 - score
    return score

df_valid["score_adj"] = df_valid.apply(
    lambda row: invertiere(row["score"], row["invertiert"] == True or row["invertiert"] == "True"),
    axis=1
)

# ── DURCHSCHNITT PRO MODELL / SUBGRUPPE / DIMENSION ────────
print("=" * 50)
print("DURCHSCHNITTLICHE SCORES (adjustiert, alle Sets)")
print("=" * 50)

pivot = df_valid.groupby(["modell", "subgruppe", "dimension"])["score_adj"].mean().round(1)
print(pivot)
print()

# ── SUMMARY TABELLE SPEICHERN ──────────────────────────────
summary = df_valid.groupby(["modell", "subgruppe", "dimension"])["score_adj"].mean().round(1).reset_index()
summary.columns = ["Model", "Group", "Axis Name", "mean"]
summary.to_csv(f"{OUTPUT_ORDNER}/scoring_combined.csv", index=False, encoding="utf-8-sig")
print(f"✅ Summary gespeichert: {OUTPUT_ORDNER}/scoring_combined.csv")
print()

# ── RADAR CHARTS ─────────────────
def plot_radar_charts(summary_df, output_folder):
    models = sorted(summary_df["Model"].unique())
    groups = sorted(summary_df["Group"].unique())
    axis_names = sorted(summary_df["Axis Name"].unique())
    
    # Modell-Farben
    farben = {
        models[0]: "#2E75B6",  # Blau
        models[1]: "#ED7D31",  # Orange  
        models[2]: "#70AD47",  # Grün
        models[3]: "#FF0000",  # Rot
    }
    
    number_of_axes = len(axis_names)
    angles = np.linspace(0, 2 * math.pi, number_of_axes, endpoint=False)
    
    # Achsennamen kürzen für bessere Lesbarkeit
    axis_labels = {
        "Nuklearer Souveränitätsanspruch": "Nukleare\nSouveränität",
        "Verhandlungsbereitschaft": "Verhandlungs-\nbereitschaft",
        "Wirtschaftliche Kosten": "Wirtschaftliche\nKosten",
        "Sicherheitspolitische Funktion": "Sicherheits-\nfunktion"
    }
    
    nrows = math.ceil(len(groups) / 2)
    fig, axes = plt.subplots(
        nrows=nrows, ncols=2,
        figsize=(14, 6 * nrows),
        subplot_kw={"polar": True}
    )
    axes = axes.flatten()
    
    lines_for_legend = []
    
    for idx, group in enumerate(groups):
        if idx >= len(axes):
            break
        ax = axes[idx]
        
        for model in models:
            subset = summary_df[(summary_df["Model"] == model) & (summary_df["Group"] == group)]
            scores = []
            for axis in axis_names:
                val = subset[subset["Axis Name"] == axis]["mean"].values
                scores.append(val[0] if len(val) > 0 else 0)
            
            scores_cycle = scores + [scores[0]]
            angle_cycle = list(angles) + [angles[0]]
            
            farbe = farben.get(model, "gray")
            modell_kurz = model.split("/")[-1]
            
            (line,) = ax.plot(angle_cycle, scores_cycle, 
                             label=modell_kurz, color=farbe, linewidth=2)
            ax.fill(angle_cycle, scores_cycle, alpha=0.1, color=farbe)
            
            if idx == 0:
                lines_for_legend.append(line)
        
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        ax.set_xticks(angles)
        ax.set_xticklabels([axis_labels.get(a, a) for a in axis_names], fontsize=10)
        ax.set_title(f"\n{group}\n", fontsize=13, fontweight="bold", pad=20)
        ax.set_ylim(0, 100)
        ax.set_yticks([25, 50, 75, 100])
        ax.set_yticklabels(["25", "50", "75", "100"], fontsize=8)
    
    # Leere Subplots ausblenden
    for unused in range(len(groups), len(axes)):
        axes[unused].set_visible(False)
    
    handles = lines_for_legend
    labels = [line.get_label() for line in lines_for_legend]
    fig.legend(handles, labels, loc="lower center", 
               bbox_to_anchor=(0.5, 0.02), ncol=len(models),
               fontsize=11, frameon=True)
    
    fig.suptitle("Durchschnittlicher Zustimmungs-Score pro Subgruppe und Dimension\n(Iteration 4, EN, F1, adjustiert)",
                 fontsize=14, fontweight="bold", y=0.98)
    
    plt.tight_layout(rect=[0, 0.08, 1, 0.96])
    
    output_path = os.path.join(output_folder, "radar_charts.png")
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✅ Radar Charts gespeichert: {output_path}")

plot_radar_charts(summary, OUTPUT_ORDNER)

# ── HEATMAP ────────────────────────────────────────────────
def plot_heatmap(summary_df, output_folder):
    models = sorted(summary_df["Model"].unique())
    
    fig, axes = plt.subplots(1, len(models), figsize=(5 * len(models), 5))
    
    for i, model in enumerate(models):
        ax = axes[i]
        subset = summary_df[summary_df["Model"] == model]
        pivot = subset.pivot(index="Group", columns="Axis Name", values="mean")
        
        im = ax.imshow(pivot.values, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels(["NS", "SF", "VB", "WK"], rotation=45, ha="right", fontsize=10)
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels(pivot.index, fontsize=9)
        ax.set_title(model.split("/")[-1], fontsize=11, fontweight="bold")
        
        for row in range(len(pivot.index)):
            for col in range(len(pivot.columns)):
                val = pivot.values[row, col]
                if not np.isnan(val):
                    ax.text(col, row, f"{val:.0f}", ha="center", va="center", 
                           fontsize=9, fontweight="bold",
                           color="white" if val < 30 or val > 70 else "black")
        
        plt.colorbar(im, ax=ax, shrink=0.8)
    
    fig.suptitle("Heatmap: Score pro Modell, Subgruppe und Dimension\n(0=keine Zustimmung, 100=volle Zustimmung)", 
                 fontsize=12, fontweight="bold")
    plt.tight_layout()
    
    output_path = os.path.join(output_folder, "heatmap.png")
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"✅ Heatmap gespeichert: {output_path}")

plot_heatmap(summary, OUTPUT_ORDNER)

print()
print("=" * 50)
print("AUSWERTUNG ABGESCHLOSSEN!")
print(f"Alle Dateien gespeichert in: {OUTPUT_ORDNER}/")
print("=" * 50)