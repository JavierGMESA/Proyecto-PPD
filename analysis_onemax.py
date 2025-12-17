#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


CSV_DIR = "./CSVsOnemax"
IMG_DIR = "./ImagenesResultadoOnemax"
os.makedirs(IMG_DIR, exist_ok=True)


VARIANTS_ALL = [
    "onemax_elite_seq", "onemax_elite_paral", "onemax_elite_dist", "onemax_elite_hibr",
    "onemax_izhi_seq",  "onemax_izhi_paral",  "onemax_izhi_dist",  "onemax_izhi_hibr",
]


GEN_COLS = [
    "gen", "seed", "threads",
    "best_global",
    "fit_best", "fit_worst", "fit_mean",
]


def plot_save(fig, name):
    path = os.path.join(IMG_DIR, name)
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)
    print(f"✓ guardada {path}")


def _glob_genstats(variant: str):
    return sorted(glob.glob(os.path.join(CSV_DIR, f"genstats_{variant}_run*.csv")))


def load_runs_genstats(variant: str):
    files = _glob_genstats(variant)
    runs = []
    for f in files:
        try:
            df = pd.read_csv(f)

            for c in GEN_COLS:
                if c not in df.columns:
                    df[c] = np.nan

            for c in ["gen", "best_global", "fit_best", "fit_mean", "fit_worst"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")

            runs.append(df)
        except Exception:
            pass
    return runs


def agg_by_generation(runs, cols):
    if not runs:
        return None
    df = pd.concat(runs, ignore_index=True)
    g = df.groupby("gen")[cols]
    return g.mean(), g.std()


def final_metric_list(runs, column):
    vals = []
    for df in runs:
        if not df.empty and column in df.columns:
            vals.append(df[column].iloc[-1])
    return vals


# =============================
# runs_summary loader
# =============================
def load_runs_summary():
    path = os.path.join(CSV_DIR, "runs_summary.csv")
    if not os.path.exists(path):
        return None

    df = pd.read_csv(path)

    df.columns = df.columns.astype(str).str.strip()
    if "suite" in df.columns:
        df["suite"] = df["suite"].astype(str).str.strip().str.lower()
    if "variant" in df.columns:
        df["variant"] = df["variant"].astype(str).str.strip()
    if "kind" in df.columns:
        df["kind"] = df["kind"].astype(str).str.strip().str.lower()

    for c in ["threads", "run_id", "seed", "wall_time_s", "energy_j", "avg_power_w", "final_best_global", "return_code"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


# =============================
# PLOTS genstats
# =============================
def plot_fitness_mean_all():
    fig, ax = plt.subplots(figsize=(10, 6))

    styles = {
        "onemax_elite_seq":   dict(lw=2),
        "onemax_elite_paral": dict(lw=2, ls="--"),
        "onemax_elite_dist":  dict(lw=2, ls=":"),
        "onemax_elite_hibr":  dict(lw=2, ls="-."),

        "onemax_izhi_seq":    dict(lw=2),
        "onemax_izhi_paral":  dict(lw=2, ls="--"),
        "onemax_izhi_dist":   dict(lw=2, ls=":"),
        "onemax_izhi_hibr":   dict(lw=2, ls="-."),
    }

    labels = {
        "onemax_elite_seq":   "Elite OneMax sec.",
        "onemax_elite_paral": "Elite OneMax OMP",
        "onemax_elite_dist":  "Elite OneMax MPI",
        "onemax_elite_hibr":  "Elite OneMax híbrido",

        "onemax_izhi_seq":    "Izhi OneMax sec.",
        "onemax_izhi_paral":  "Izhi OneMax OMP",
        "onemax_izhi_dist":   "Izhi OneMax MPI",
        "onemax_izhi_hibr":   "Izhi OneMax híbrido",
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
        print("Aviso: no hay CSV genstats_*.csv para fitness medio.")
        return

    ax.set_title("OneMax: Fitness medio por generación")
    ax.set_xlabel("Generación")
    ax.set_ylabel("Fitness")
    ax.grid(True)
    ax.legend()
    plot_save(fig, "onemax_fitness_medio_todas.png")


def plot_boxplot_final_fitness():
    tick_labels = ["E sec", "E OMP", "E MPI", "E híbr", "I sec", "I OMP", "I MPI", "I híbr"]
    series = []
    for v in VARIANTS_ALL:
        runs = load_runs_genstats(v)
        vals = final_metric_list(runs, "best_global")
        series.append(vals if vals else [np.nan])

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.boxplot(series, tick_labels=tick_labels)  # tick_labels en Matplotlib >= 3.9 [web:153]
    ax.set_title("OneMax: Fitness final (todas las variantes)")
    ax.set_ylabel("Fitness alcanzado")
    ax.grid(True)
    plot_save(fig, "onemax_fitness_final_boxplot_todas.png")


def plot_variant_evolution_triplets(variant):
    runs = load_runs_genstats(variant)
    cols = ["fit_best", "fit_mean", "fit_worst"]
    agg = agg_by_generation(runs, cols)
    if agg is None:
        print(f"Aviso: sin datos para {variant}")
        return
    mean, _ = agg

    fig, ax = plt.subplots(figsize=(10, 6))
    for c, ls in zip(cols, ["-", "--", ":"]):
        if c in mean.columns and not mean[c].isna().all():
            ax.plot(mean.index, mean[c].values, label=c, lw=2, ls=ls)

    ax.set_title(f"{variant}: Fitness best/mean/worst")
    ax.set_xlabel("Generación")
    ax.set_ylabel("Fitness")
    ax.grid(True)
    ax.legend()

    safe = variant.replace("onemax_", "").replace("_", "-")
    plot_save(fig, f"{safe}_fitness_triple.png")


# =============================
# PERF plots
# =============================
def perf_aggregate(df_summary: pd.DataFrame, variant: str) -> pd.DataFrame | None:
    if df_summary is None or df_summary.empty:
        return None
    d = df_summary[(df_summary["suite"] == "perf") & (df_summary["variant"] == variant)].copy()
    if d.empty:
        return None

    if d["threads"].notna().any():
        d_series = d.dropna(subset=["threads", "wall_time_s"]).copy()
        if d_series.empty:
            return None
        out = d_series.groupby("threads")[["wall_time_s", "energy_j", "avg_power_w"]].mean(numeric_only=True).reset_index()
        out["threads"] = out["threads"].astype(int)
        return out.sort_values("threads")

    wall = pd.to_numeric(d["wall_time_s"], errors="coerce").dropna()
    if wall.empty:
        return None
    row = {
        "threads": 1,
        "wall_time_s": float(wall.mean()),
        "energy_j": float(pd.to_numeric(d.get("energy_j", pd.Series([np.nan])), errors="coerce").dropna().mean()) if "energy_j" in d.columns else np.nan,
        "avg_power_w": float(pd.to_numeric(d.get("avg_power_w", pd.Series([np.nan])), errors="coerce").dropna().mean()) if "avg_power_w" in d.columns else np.nan,
    }
    return pd.DataFrame([row])


def get_T_at_threads(tab: pd.DataFrame, t: int) -> float | None:
    if tab is None or tab.empty:
        return None
    d = tab[tab["threads"] == t]
    if d.empty:
        return None
    return float(d["wall_time_s"].iloc[0])


def get_baseline_time_any(tab: pd.DataFrame) -> float | None:
    if tab is None or tab.empty:
        return None
    t1 = get_T_at_threads(tab, 1)
    if t1 is not None and np.isfinite(t1):
        return t1
    return float(pd.to_numeric(tab["wall_time_s"], errors="coerce").dropna().iloc[0]) if tab["wall_time_s"].notna().any() else None


def plot_perf_set(title: str, tab_series: pd.DataFrame, T_ref_speedup: float, out_prefix: str):
    if tab_series is None or tab_series.empty:
        print(f"Aviso: no hay datos PERF para {title}")
        return
    if T_ref_speedup is None or not np.isfinite(T_ref_speedup):
        print(f"Aviso: baseline inválido para {title}")
        return

    t = tab_series["threads"].values
    T = tab_series["wall_time_s"].values
    if len(t) == 0:
        print(f"Aviso: serie vacía para {title}")
        return

    speedup = T_ref_speedup / T
    eff = speedup / t

    T1 = get_T_at_threads(tab_series, 1)
    par = (T1 / T) if T1 is not None else None

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(t, speedup, marker="o", lw=2)
    ax.set_title(f"{title}: speedup")
    ax.set_xlabel("Hilos")
    ax.set_ylabel("Speedup")
    ax.grid(True)
    plot_save(fig, f"{out_prefix}_speedup.png")

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(t, eff, marker="o", lw=2)
    ax.set_title(f"{title}: eficiencia")
    ax.set_xlabel("Hilos")
    ax.set_ylabel("Eficiencia")
    ax.grid(True)
    plot_save(fig, f"{out_prefix}_efficiency.png")

    if par is not None:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(t, par, marker="o", lw=2)
        ax.set_title(f"{title}: paralecibilidad")
        ax.set_xlabel("Hilos")
        ax.set_ylabel("Paralecibilidad (T1 / Tp)")
        ax.grid(True)
        plot_save(fig, f"{out_prefix}_paralecibility.png")

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(t, T, marker="o", lw=2, label="serie")
    ax.axhline(T_ref_speedup, color="gray", ls="--", label="baseline ref")
    ax.set_title(f"{title}: tiempo de ejecución")
    ax.set_xlabel("Hilos")
    ax.set_ylabel("Tiempo (s)")
    ax.grid(True)
    ax.legend()
    plot_save(fig, f"{out_prefix}_times.png")


def plot_perf_all():
    df = load_runs_summary()
    if df is None or df.empty:
        print("Aviso: no hay runs_summary.csv")
        return

    tab_elite_seq  = perf_aggregate(df, "onemax_elite_seq")
    tab_elite_dist = perf_aggregate(df, "onemax_elite_dist")

    T_elite_seq  = get_baseline_time_any(tab_elite_seq)
    T_elite_dist = get_baseline_time_any(tab_elite_dist)

    tab = perf_aggregate(df, "onemax_elite_paral")
    if tab is not None and T_elite_seq is not None:
        plot_perf_set("OMP Elite (base: sec)", tab, T_elite_seq, "perf_elite_omp")
    else:
        print("Info: no hay datos PERF suficientes para OMP Elite (serie o baseline).")

    tab = perf_aggregate(df, "onemax_elite_hibr")
    if tab is not None and T_elite_dist is not None:
        plot_perf_set("Híbrida Elite (base: MPI)", tab, T_elite_dist, "perf_elite_hybrid")
    else:
        print("Info: no hay datos PERF suficientes para Híbrida Elite (serie o baseline).")


# =============================
# Consumo por versión (suite main)
# =============================
def plot_main_consumption_by_variant():
    df = load_runs_summary()
    if df is None or df.empty:
        return

    d = df[df["suite"] == "main"].copy()
    if d.empty:
        return

    # Excluir MPI e híbrido (consumo parcial: solo 1 nodo)
    d = d[~d["variant"].str.contains(r"(_dist|_hibr)$", na=False)].copy()
    if d.empty:
        print("Aviso: tras filtrar dist/hibr no quedan filas suite=main.")
        return

    order = [v for v in VARIANTS_ALL if v in d["variant"].unique() and not (v.endswith("_dist") or v.endswith("_hibr"))]

    def _boxplot_metric(metric_col: str, title: str, ylabel: str, out_png: str):
        series = []
        labels = []
        for v in order:
            vals = pd.to_numeric(d.loc[d["variant"] == v, metric_col], errors="coerce").dropna().values
            if vals.size == 0:
                continue
            series.append(vals)
            labels.append(v)

        if not series:
            print(f"Aviso: no hay datos válidos en {metric_col} para suite=main (sec/OMP).")
            return

        fig, ax = plt.subplots(figsize=(11, 5))
        ax.boxplot(series, tick_labels=labels)  # tick_labels en Matplotlib >= 3.9 [web:153]
        ax.set_title(title)
        ax.set_xlabel("Versión")
        ax.set_ylabel(ylabel)
        ax.tick_params(axis="x", rotation=35)
        ax.grid(True, axis="y")
        plot_save(fig, out_png)

    if "avg_power_w" in d.columns:
        _boxplot_metric(
            "avg_power_w",
            "OneMax (suite main): potencia (boxplot) solo sec/OMP",
            "Potencia (W)",
            "onemax_main_power_boxplot_sec_omp.png"
        )

    if "energy_j" in d.columns:
        _boxplot_metric(
            "energy_j",
            "OneMax (suite main): energía (boxplot) solo sec/OMP",
            "Energía (J)",
            "onemax_main_energy_boxplot_sec_omp.png"
        )


def main():
    plot_fitness_mean_all()
    plot_boxplot_final_fitness()

    for v in VARIANTS_ALL:
        plot_variant_evolution_triplets(v)

    plot_perf_all()
    plot_main_consumption_by_variant()

    print("✓ análisis OneMax completado")


if __name__ == "__main__":
    main()
