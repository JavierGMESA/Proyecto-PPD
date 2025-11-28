import pandas as pd
import matplotlib.pyplot as plt
import glob
import numpy as np
import os

# -----------------------------
# Carpetas
# -----------------------------
carpeta_imgs = "ImagenesResultado"
os.makedirs(carpeta_imgs, exist_ok=True)

CSV_DIR = "./CSVs"

# -----------------------------
# Funciones de carga
# -----------------------------
def cargar_resultados(pattern):
    files = sorted(glob.glob(pattern))
    dfs = [pd.read_csv(f) for f in files]
    return dfs

elite_runs         = cargar_resultados(os.path.join(CSV_DIR, "resultados_elite_run*.csv"))
elite_paral_runs   = cargar_resultados(os.path.join(CSV_DIR, "resultados_elite_paral_run*.csv"))
elite_distrib_runs = cargar_resultados(os.path.join(CSV_DIR, "resultados_elite_distrib_run*.csv"))
elite_hibrid_runs  = cargar_resultados(os.path.join(CSV_DIR, "resultados_elite_hibrid_run*.csv"))

izhi_runs          = cargar_resultados(os.path.join(CSV_DIR, "resultados_izhi_run*.csv"))
izhi_paral_runs    = cargar_resultados(os.path.join(CSV_DIR, "resultados_izhi_paral_run*.csv"))
izhi_distrib_runs  = cargar_resultados(os.path.join(CSV_DIR, "resultados_izhi_distrib_run*.csv"))
izhi_hibrid_runs   = cargar_resultados(os.path.join(CSV_DIR, "resultados_izhi_hibrid_run*.csv"))

def media_por_generacion(runs, col):
    df_concat = pd.concat(runs)
    grouped = df_concat.groupby("gen")[col]
    return grouped.mean(), grouped.std()

mean_elite,         std_elite         = media_por_generacion(elite_runs,         "fitness")
mean_elite_paral,   std_elite_paral   = media_por_generacion(elite_paral_runs,   "fitness")
mean_elite_distrib, std_elite_distrib = media_por_generacion(elite_distrib_runs, "fitness")
mean_elite_hibrid,  std_elite_hibrid  = media_por_generacion(elite_hibrid_runs,  "fitness")

mean_izhi,          std_izhi          = media_por_generacion(izhi_runs,          "fitness")
mean_izhi_paral,    std_izhi_paral    = media_por_generacion(izhi_paral_runs,    "fitness")
mean_izhi_distrib,  std_izhi_distrib  = media_por_generacion(izhi_distrib_runs,  "fitness")
mean_izhi_hibrid,   std_izhi_hibrid   = media_por_generacion(izhi_hibrid_runs,   "fitness")

mean_picos,         std_picos         = media_por_generacion(izhi_runs,          "picos")
mean_picos_paral,   std_picos_paral   = media_por_generacion(izhi_paral_runs,    "picos")
mean_picos_distrib, std_picos_distrib = media_por_generacion(izhi_distrib_runs,  "picos")
mean_picos_hibrid,  std_picos_hibrid  = media_por_generacion(izhi_hibrid_runs,   "picos")

# ================================
# 1. FITNESS MEDIO (todas variantes)
# ================================
plt.figure(figsize=(10, 6))

# Elitistas
plt.plot(mean_elite.index,         mean_elite.values,         label="Elitista sec.",       linewidth=2)
plt.plot(mean_elite_paral.index,   mean_elite_paral.values,   label="Elitista OMP",        linewidth=2, linestyle="--")
plt.plot(mean_elite_distrib.index, mean_elite_distrib.values, label="Elitista MPI",        linewidth=2, linestyle=":")
plt.plot(mean_elite_hibrid.index,  mean_elite_hibrid.values,  label="Elitista híbrido",    linewidth=2, linestyle="-.")

# Izhikevich
plt.plot(mean_izhi.index,          mean_izhi.values,          label="Izhikevich sec.",     linewidth=2)
plt.plot(mean_izhi_paral.index,    mean_izhi_paral.values,    label="Izhikevich OMP",      linewidth=2, linestyle="--")
plt.plot(mean_izhi_distrib.index,  mean_izhi_distrib.values,  label="Izhikevich MPI",      linewidth=2, linestyle=":")
plt.plot(mean_izhi_hibrid.index,   mean_izhi_hibrid.values,   label="Izhikevich híbrido",  linewidth=2, linestyle="-.")

# Bandas de desviación (para no saturar, sólo en las variantes secuenciales)
plt.fill_between(mean_elite.index,
                 mean_elite - std_elite,
                 mean_elite + std_elite,
                 alpha=0.15)
plt.fill_between(mean_izhi.index,
                 mean_izhi - std_izhi,
                 mean_izhi + std_izhi,
                 alpha=0.15)

plt.title("Fitness medio por generación (todas las variantes)")
plt.xlabel("Generación")
plt.ylabel("Fitness")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(carpeta_imgs, "fitness_medio_todas.png"), dpi=170)
plt.close()

# ================================
# 2. PICOS MEDIOS (sólo Izhikevich)
# ================================
plt.figure(figsize=(10, 6))

plt.plot(mean_picos.index,         mean_picos.values,         label="Izhi sec.",      linewidth=2)
plt.plot(mean_picos_paral.index,   mean_picos_paral.values,   label="Izhi OMP",       linewidth=2, linestyle="--")
plt.plot(mean_picos_distrib.index, mean_picos_distrib.values, label="Izhi MPI",       linewidth=2, linestyle=":")
plt.plot(mean_picos_hibrid.index,  mean_picos_hibrid.values,  label="Izhi híbrido",   linewidth=2, linestyle="-.")

plt.fill_between(mean_picos.index,
                 mean_picos - std_picos,
                 mean_picos + std_picos,
                 alpha=0.2)

plt.title("Picos medios por generación (Izhikevich)")
plt.xlabel("Generación")
plt.ylabel("Número de picos")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(carpeta_imgs, "picos_medios_todas.png"), dpi=170)
plt.close()

# ================================
# 3. BOXPLOT DEL FITNESS FINAL
# ================================
final_fitness_elite         = [df["fitness"].iloc[-1] for df in elite_runs]
final_fitness_elite_paral   = [df["fitness"].iloc[-1] for df in elite_paral_runs]
final_fitness_elite_distrib = [df["fitness"].iloc[-1] for df in elite_distrib_runs]
final_fitness_elite_hibrid  = [df["fitness"].iloc[-1] for df in elite_hibrid_runs]

final_fitness_izhi          = [df["fitness"].iloc[-1] for df in izhi_runs]
final_fitness_izhi_paral    = [df["fitness"].iloc[-1] for df in izhi_paral_runs]
final_fitness_izhi_distrib  = [df["fitness"].iloc[-1] for df in izhi_distrib_runs]
final_fitness_izhi_hibrid   = [df["fitness"].iloc[-1] for df in izhi_hibrid_runs]

plt.figure(figsize=(10, 6))
plt.boxplot(
    [
        final_fitness_elite,
        final_fitness_elite_paral,
        final_fitness_elite_distrib,
        final_fitness_elite_hibrid,
        final_fitness_izhi,
        final_fitness_izhi_paral,
        final_fitness_izhi_distrib,
        final_fitness_izhi_hibrid
    ],
    labels=[
        "Elit. sec.",
        "Elit. OMP",
        "Elit. MPI",
        "Elit. híbr.",
        "Izhi sec.",
        "Izhi OMP",
        "Izhi MPI",
        "Izhi híbr."
    ]
)

plt.title("Comparación del fitness final (todas las variantes)")
plt.ylabel("Fitness alcanzado")
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(carpeta_imgs, "fitness_final_boxplot_todas.png"), dpi=170)
plt.close()
