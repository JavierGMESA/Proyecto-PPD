#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, glob, re, math
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Rutas segun tu proyecto
CSV_DIR = "./CSVsTruck"
IMG_DIR = "./ImagenesResultadoTruck"
os.makedirs(IMG_DIR, exist_ok=True)

# Variantes (etiquetas tal y como las escribe run_experiments_truck.py)
VARIANTS_ALL = [
    "truck_elite_seq", "truck_elite_paral", "truck_elite_dist", "truck_elite_hibr",
    "truck_izhi_seq",  "truck_izhi_paral", "truck_izhi_dist",  "truck_izhi_hibr",
]
IZHI_VARIANTS = ["truck_izhi_seq", "truck_izhi_paral", "truck_izhi_dist", "truck_izhi_hibr"]

# Columnas que produce run_experiments_truck.py en los CSV por generación
GEN_COLS = [
    "gen","seed","threads",
    "best_global","picos",
    "fit_best","fit_worst","fit_mean",
    "green_best","green_worst","green_mean",
    "emis_best","emis_worst","emis_mean",
]




# ======= PARCHE TEMPORAL EMISSIONS (escala x100) =======
FIX_EMISSIONS_SCALE = True  # pon False o comenta este bloque cuando rehagas los CSV

def _fix_emis_mean_scale(df: pd.DataFrame) -> pd.DataFrame:
    # emis_mean en CSV está /100 -> lo corregimos multiplicando x100
    if FIX_EMISSIONS_SCALE and "emis_mean" in df.columns:
        df["emis_mean"] = df["emis_mean"] * 100.0
    return df
# =======================================================





def _glob_genstats(variant):
    pat = os.path.join(CSV_DIR, f"genstats_{variant}_run*.csv")
    return sorted(glob.glob(pat))

def _glob_perf(variant):
    pat = os.path.join(CSV_DIR, f"perf_{variant}_t*_run*.csv")
    return sorted(glob.glob(pat))

def load_runs_genstats(variant):
    files = _glob_genstats(variant)
    runs = []
    for f in files:
        try:
            df = pd.read_csv(f)

            # aplicar parche temporal de emisiones
            df = _fix_emis_mean_scale(df)

            # Asegura columnas esperadas si faltan
            for c in GEN_COLS:
                if c not in df.columns:
                    df[c] = np.nan
            runs.append(df)
        except Exception:
            pass
    return runs

def agg_by_generation(runs, cols):
    if not runs:
        return None
    df = pd.concat(runs, ignore_index=True)
    g = df.groupby("gen")[cols]
    mean = g.mean()
    std = g.std()
    return mean, std

def final_metric_list(runs, column):
    vals = []
    for df in runs:
        if not df.empty and column in df.columns:
            vals.append(df[column].iloc[-1])
    return vals

def plot_save(fig, name):
    path = os.path.join(IMG_DIR, name)
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)
    print(f"✓ guardada {path}")

# =========================================
# 1) Evolución fitness medio (8 variantes)
# =========================================
def plot_fitness_mean_all():
    fig, ax = plt.subplots(figsize=(10,6))
    styles = {
        "truck_elite_seq":   dict(lw=2),
        "truck_elite_paral": dict(lw=2, ls="--"),
        "truck_elite_dist":  dict(lw=2, ls=":"),
        "truck_elite_hibr":  dict(lw=2, ls="-."),
        "truck_izhi_seq":    dict(lw=2),
        "truck_izhi_paral":  dict(lw=2, ls="--"),
        "truck_izhi_dist":   dict(lw=2, ls=":"),
        "truck_izhi_hibr":   dict(lw=2, ls="-."),
    }
    labels = {
        "truck_elite_seq":   "Elite Truck sec.",
        "truck_elite_paral": "Elite Truck OMP",
        "truck_elite_dist":  "Elite Truck MPI",
        "truck_elite_hibr":  "Elite Truck híbrido",
        "truck_izhi_seq":    "Izhi Truck sec.",
        "truck_izhi_paral":  "Izhi Truck OMP",
        "truck_izhi_dist":   "Izhi Truck MPI",
        "truck_izhi_hibr":   "Izhi Truck híbrido",
    }

    plotted_any = False
    for v in VARIANTS_ALL:
        runs = load_runs_genstats(v)
        agg = agg_by_generation(runs, ["fit_mean"])
        if agg is None: 
            continue
        mean, _ = agg
        ax.plot(mean.index, mean["fit_mean"].values, label=labels[v], **styles[v])
        plotted_any = True

    if not plotted_any:
        print("Aviso: no hay CSV genstats_*.csv para esta figura.")
        return
    ax.set_title("Truck: Fitness medio por generación")
    ax.set_xlabel("Generación")
    ax.set_ylabel("Fitness")
    ax.grid(True)
    ax.legend()
    plot_save(fig, "truck_fitness_medio_todas.png")

# =========================================
# 2) Boxplot fitness final (8 variantes)
# =========================================
def plot_boxplot_final_fitness():
    labels = ["E sec","E OMP","E MPI","E híbr","I sec","I OMP","I MPI","I híbr"]
    series = []
    for v in VARIANTS_ALL:
        runs = load_runs_genstats(v)
        vals = final_metric_list(runs, "best_global")
        series.append(vals if vals else [np.nan])

    fig, ax = plt.subplots(figsize=(10,6))
    ax.boxplot(series, labels=labels)
    ax.set_title("Truck: Fitness final (todas las variantes)")
    ax.set_ylabel("Fitness alcanzado")
    ax.grid(True)
    plot_save(fig, "truck_fitness_final_boxplot_todas.png")

# ==================================================
# 3) Por variante: best/mean/worst de fitness/green/emis
# ==================================================
def plot_variant_evolution_triplets(variant):
    runs = load_runs_genstats(variant)
    agg = agg_by_generation(runs, ["fit_best","fit_mean","fit_worst","green_best","green_mean","green_worst","emis_best","emis_mean","emis_worst"])
    if agg is None:
        print(f"Aviso: sin datos para {variant}")
        return
    mean, _ = agg

    def _one(fig_title, cols, ylab, fname):
        fig, ax = plt.subplots(figsize=(10,6))
        for c, ls in zip(cols, ["-","--",":"]):
            if c in mean.columns:
                ax.plot(mean.index, mean[c].values, label=c, lw=2, ls=ls)
        ax.set_title(fig_title)
        ax.set_xlabel("Generación")
        ax.set_ylabel(ylab)
        ax.grid(True)
        ax.legend()
        plot_save(fig, fname)

    safe = variant.replace("truck_","").replace("_","-")
    _one(f"{variant}: Fitness best/mean/worst", ["fit_best","fit_mean","fit_worst"], "Fitness", f"{safe}_fitness_triple.png")
    _one(f"{variant}: Green kms best/mean/worst", ["green_best","green_mean","green_worst"], "Green kms", f"{safe}_green_triple.png")
    _one(f"{variant}: Emissions best/mean/worst", ["emis_best","emis_mean","emis_worst"], "Emissions", f"{safe}_emis_triple.png")

# =========================================
# 4) Picos por generación (solo variantes Izhi)
# =========================================
def plot_izhi_peaks_all():
    fig, ax = plt.subplots(figsize=(10,6))
    plotted = False
    for v in IZHI_VARIANTS:
        runs = load_runs_genstats(v)
        agg = agg_by_generation(runs, ["picos"])
        if agg is None:
            continue
        mean, _ = agg
        if "picos" in mean.columns:
            ax.plot(mean.index, mean["picos"].values, label=v, lw=2)
            plotted = True
    if not plotted:
        print("Aviso: no hay columnas 'picos' o CSV para Izhi.")
        return
    ax.set_title("Izhi Truck: picos medios por generación")
    ax.set_xlabel("Generación")
    ax.set_ylabel("Picos")
    ax.grid(True)
    ax.legend()
    plot_save(fig, "truck_izhi_picos_medio.png")

# =========================================
# 5) Speedup, eficiencia y tiempos (suite PERF)
#    - OMP: baseline = secuencial
#    - Híbrida: baseline = distribuida
# =========================================
def load_runs_summary():
    path = os.path.join(CSV_DIR, "runs_summary.csv")
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    return df

def perf_aggregate(df, variant):
    d = df[(df["suite"]=="perf") & (df["variant"]==variant)].copy()
    if d.empty:
        return None
    # wall_time_s y energy_j como medias por threads
    grp = d.groupby("threads")
    out = grp[["wall_time_s","energy_j","avg_power_w"]].mean(numeric_only=True)
    # normaliza tipos
    out = out.reset_index()
    out["threads"] = pd.to_numeric(out["threads"], errors="coerce")
    out = out.sort_values("threads")
    return out

def plot_perf_speedup_efficiency_times():
    df = load_runs_summary()
    if df is None or df.empty:
        print("Aviso: no hay runs_summary.csv")
        return

    def _plot_set(title_suffix, omp_variant, baseline_variant, fname_prefix):
        omp = perf_aggregate(df, omp_variant)
        base = perf_aggregate(df, baseline_variant)
        if omp is None or base is None or base.empty:
            print(f"Aviso: faltan datos para {omp_variant} o {baseline_variant}")
            return

        # baseline: usar tiempo de threads=1 si existe; si no, media global
        if (base["threads"]==1).any():
            T_base = float(base[base["threads"]==1]["wall_time_s"].values[0])
        else:
            T_base = float(base["wall_time_s"].mean())

        # Series
        threads = omp["threads"].values
        T_omp   = omp["wall_time_s"].values
        speedup = T_base / T_omp
        eff     = speedup / threads

        # Speedup
        fig, ax = plt.subplots(figsize=(8,5))
        ax.plot(threads, speedup, marker="o", lw=2)
        ax.set_title(f"{title_suffix}: speedup")
        ax.set_xlabel("Hilos")
        ax.set_ylabel("Speedup")
        ax.grid(True)
        plot_save(fig, f"{fname_prefix}_speedup.png")

        # Eficiencia
        fig, ax = plt.subplots(figsize=(8,5))
        ax.plot(threads, eff, marker="o", lw=2)
        ax.set_title(f"{title_suffix}: eficiencia")
        ax.set_xlabel("Hilos")
        ax.set_ylabel("Eficiencia")
        ax.grid(True)
        plot_save(fig, f"{fname_prefix}_efficiency.png")

        # Tiempos
        fig, ax = plt.subplots(figsize=(8,5))
        ax.plot(threads, T_omp, marker="o", lw=2)
        ax.axhline(T_base, color="gray", ls="--", label="baseline")
        ax.set_title(f"{title_suffix}: tiempo de ejecución")
        ax.set_xlabel("Hilos")
        ax.set_ylabel("Tiempo (s)")
        ax.grid(True)
        ax.legend()
        plot_save(fig, f"{fname_prefix}_times.png")

        # Energía/potencia si existe
        if "energy_j" in omp.columns and not omp["energy_j"].isna().all():
            fig, ax = plt.subplots(figsize=(8,5))
            ax.plot(threads, omp["energy_j"].values, marker="o", lw=2)
            ax.set_title(f"{title_suffix}: energía")
            ax.set_xlabel("Hilos")
            ax.set_ylabel("Energía (J)")
            ax.grid(True)
            plot_save(fig, f"{fname_prefix}_energy.png")

        if "avg_power_w" in omp.columns and not omp["avg_power_w"].isna().all():
            fig, ax = plt.subplots(figsize=(8,5))
            ax.plot(threads, omp["avg_power_w"].values, marker="o", lw=2)
            ax.set_title(f"{title_suffix}: potencia media")
            ax.set_xlabel("Hilos")
            ax.set_ylabel("Potencia (W)")
            ax.grid(True)
            plot_save(fig, f"{fname_prefix}_power.png")

    # Paralela OMP (elite e Izhi) con baseline secuencial
    _plot_set("OMP Elite", "truck_elite_paral", "truck_elite_seq", "perf_elite_omp")
    _plot_set("OMP Izhi",  "truck_izhi_paral",  "truck_izhi_seq",  "perf_izhi_omp")

    # Híbrida con baseline distribuida
    _plot_set("Híbrida Elite (base: MPI)", "truck_elite_hibr", "truck_elite_dist", "perf_elite_hybrid")
    _plot_set("Híbrida Izhi (base: MPI)",  "truck_izhi_hibr",  "truck_izhi_dist",  "perf_izhi_hybrid")

def main():
    # 1) Curva fitness medio (8 variantes)
    plot_fitness_mean_all()
    # 2) Boxplot fitness final
    plot_boxplot_final_fitness()
    # 3) Tripletas por variante (fitness, green, emis)
    for v in VARIANTS_ALL:
        plot_variant_evolution_triplets(v)
    # 4) Picos en Izhi
    plot_izhi_peaks_all()
    # 5) Speedup/eficiencia/tiempos/energía (suite PERF)
    plot_perf_speedup_efficiency_times()
    print("✓ análisis Truck completado")

if __name__ == "__main__":
    main()

