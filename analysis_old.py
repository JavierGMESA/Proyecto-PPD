import pandas as pd
import matplotlib.pyplot as plt
import glob
import numpy as np
import os

# -----------------------------
# Crear carpeta de resultados
# -----------------------------
carpeta = "ImagenesResultado"
os.makedirs(carpeta, exist_ok=True)

# -----------------------------
# Funciones de carga
# -----------------------------
def cargar_resultados(pattern):
    files = sorted(glob.glob(pattern))
    dfs = [pd.read_csv(f) for f in files]
    return dfs

elite_runs = cargar_resultados("resultados_elite_run*.csv")
izhi_runs  = cargar_resultados("resultados_izhi_run*.csv")

def media_por_generacion(runs, col):
    df_concat = pd.concat(runs)
    grouped = df_concat.groupby("gen")[col]
    return grouped.mean(), grouped.std()

mean_elite, std_elite = media_por_generacion(elite_runs, "fitness")
mean_izhi,  std_izhi  = media_por_generacion(izhi_runs,  "fitness")
mean_picos, std_picos = media_por_generacion(izhi_runs, "picos")

# ================================
# 1. FITNESS MEDIO
# ================================
plt.figure(figsize=(10,6))
plt.plot(mean_elite.index, mean_elite.values, label="Elitista", linewidth=2)
plt.plot(mean_izhi.index,  mean_izhi.values,  label="Izhikevich", linewidth=2)
plt.fill_between(mean_elite.index, mean_elite - std_elite, mean_elite + std_elite, alpha=0.2)
plt.fill_between(mean_izhi.index,  mean_izhi - std_izhi,  mean_izhi + std_izhi, alpha=0.2)
plt.title("Fitness medio por generación")
plt.xlabel("Generación")
plt.ylabel("Fitness")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(carpeta, "fitness_medio.png"), dpi=170)
plt.close()

# ================================
# 2. PICOS MEDIOS
# ================================
plt.figure(figsize=(10,6))
plt.plot(mean_picos.index, mean_picos.values, linewidth=2)
plt.fill_between(mean_picos.index, mean_picos - std_picos, mean_picos + std_picos, alpha=0.2)
plt.title("Picos medios por generación (Izhikevich)")
plt.xlabel("Generación")
plt.ylabel("Número de picos")
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(carpeta, "picos_medios.png"), dpi=170)
plt.close()

# ================================
# 3. BOXPLOT DEL FITNESS FINAL
# ================================
final_fitness_elite = [df["fitness"].iloc[-1] for df in elite_runs]
final_fitness_izhi  = [df["fitness"].iloc[-1] for df in izhi_runs]

plt.figure(figsize=(7,6))
plt.boxplot([final_fitness_elite, final_fitness_izhi], labels=["Elitista", "Izhikevich"])
plt.title("Comparación del fitness final")
plt.ylabel("Fitness alcanzado")
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(carpeta, "fitness_final_boxplot.png"), dpi=170)
plt.close()