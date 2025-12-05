import pandas as pd
import matplotlib.pyplot as plt
import glob
import os

CSV_DIR = "./CSVsTruck"
IMG_DIR = "./ImagenesResultadoTruck"
os.makedirs(IMG_DIR, exist_ok=True)  # [web:135]

def cargar_resultados(pattern):
    files = sorted(glob.glob(os.path.join(CSV_DIR, pattern)))  # [web:143]
    return [pd.read_csv(f) for f in files]

def media_por_generacion(runs):
    df_concat = pd.concat(runs)
    grouped = df_concat.groupby("gen")["fitness"]
    return grouped.mean(), grouped.std()

# Cargar runs
elite_runs         = cargar_resultados("resultados_truck_elite_run*.csv")
elite_paral_runs   = cargar_resultados("resultados_truck_elite_paral_run*.csv")
elite_distrib_runs = cargar_resultados("resultados_truck_elite_distrib_run*.csv")
elite_hibrid_runs  = cargar_resultados("resultados_truck_elite_hibrid_run*.csv")

izhi_runs          = cargar_resultados("resultados_truck_izhi_run*.csv")
izhi_paral_runs    = cargar_resultados("resultados_truck_izhi_paral_run*.csv")
izhi_distrib_runs  = cargar_resultados("resultados_truck_izhi_distrib_run*.csv")
izhi_hibrid_runs   = cargar_resultados("resultados_truck_izhi_hibrid_run*.csv")

# Medias y desviaciones
mean_elite,         std_elite         = media_por_generacion(elite_runs)
mean_elite_paral,   std_elite_paral   = media_por_generacion(elite_paral_runs)
mean_elite_distrib, std_elite_distrib = media_por_generacion(elite_distrib_runs)
mean_elite_hibrid,  std_elite_hibrid  = media_por_generacion(elite_hibrid_runs)

mean_izhi,          std_izhi          = media_por_generacion(izhi_runs)
mean_izhi_paral,    std_izhi_paral    = media_por_generacion(izhi_paral_runs)
mean_izhi_distrib,  std_izhi_distrib  = media_por_generacion(izhi_distrib_runs)
mean_izhi_hibrid,   std_izhi_hibrid   = media_por_generacion(izhi_hibrid_runs)

# 1) Fitness medio por generación (todas variantes)
plt.figure(figsize=(10, 6))

plt.plot(mean_elite.index,         mean_elite.values,         label="Elite Truck sec.",      linewidth=2)
plt.plot(mean_elite_paral.index,   mean_elite_paral.values,   label="Elite Truck OMP",       linewidth=2, linestyle="--")
plt.plot(mean_elite_distrib.index, mean_elite_distrib.values, label="Elite Truck MPI",       linewidth=2, linestyle=":")
plt.plot(mean_elite_hibrid.index,  mean_elite_hibrid.values,  label="Elite Truck híbrido",   linewidth=2, linestyle="-.")

plt.plot(mean_izhi.index,          mean_izhi.values,          label="Izhi Truck sec.",       linewidth=2)
plt.plot(mean_izhi_paral.index,    mean_izhi_paral.values,    label="Izhi Truck OMP",        linewidth=2, linestyle="--")
plt.plot(mean_izhi_distrib.index,  mean_izhi_distrib.values,  label="Izhi Truck MPI",        linewidth=2, linestyle=":")
plt.plot(mean_izhi_hibrid.index,   mean_izhi_hibrid.values,   label="Izhi Truck híbrido",    linewidth=2, linestyle="-.")

plt.title("Truck: Fitness medio por generación")
plt.xlabel("Generación")
plt.ylabel("Fitness")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, "truck_fitness_medio_todas.png"), dpi=170)
plt.close()

# 2) Boxplot del fitness final
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
        final_fitness_izhi_hibrid,
    ],
    labels=[
        "E sec",
        "E OMP",
        "E MPI",
        "E híbr",
        "I sec",
        "I OMP",
        "I MPI",
        "I híbr",
    ]
)

plt.title("Truck: Fitness final (todas las variantes)")
plt.ylabel("Fitness alcanzado")
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, "truck_fitness_final_boxplot_todas.png"), dpi=170)
plt.close()
