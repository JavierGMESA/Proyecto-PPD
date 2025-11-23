import subprocess
import itertools
import numpy as np
import os
import json

# Parámetros que vamos a explorar (ejemplo)
search_space = {
    "IniI":     [10, 15, 20],
    "IncMutI":  [0.01, 0.02],
    "IncPosI":  [0.1, 0.2],
    "IncNegI":  [-0.02, -0.05],
    "IncPicI":  [-0.01],
    "IniA":     [0.1, 0.2],
    "IniB":     [0.05, 0.1],
    "IncPosB":  [-0.0001],
    "IncNegB":  [0.001],
    "IncPicB":  [0.001],
    "IniC":     [-40, -35],
    "IncPosC":  [0.1],
    "IncNegC":  [-0.075],
    "IncPicC":  [-0.075],
    "IniD":     [3],
    "IncPosD":  [-0.005],
    "IncNegD":  [0.02],
    "IncPicD":  [0.02],
    "MAX_ULT_PICO": [45],
    "MAX_PIC_SEG":  [30]
}

param_names = list(search_space.keys())

# Generar todas las combinaciones
combinations = list(itertools.product(*search_space.values()))

N_RUNS = 5
best_mean = -1
best_params = None

def run_izhi(params):
    cmd = ["./cga_izhi_onemax"] + [str(p) for p in params]
    fitnesses = []
    for i in range(N_RUNS):
        out = subprocess.check_output(cmd).decode()
        # buscas la línea "Mejor fitness encontrado:"
        for line in out.split("\n"):
            if "Mejor fitness encontrado" in line:
                f = int(line.split(":")[1])
                fitnesses.append(f)
    return np.mean(fitnesses)

# 1) Ejecutar elitista
#print("Ejecutando elitista...")
#elite_fits = []
#for i in range(N_RUNS):
#    out = subprocess.check_output(["./cga_onemax"]).decode()
#    for line in out.split("\n"):
#        if "Mejor fitness encontrado" in line:
#            f = int(line.split(":")[1])
#            elite_fits.append(f)
#
#mean_elite = np.mean(elite_fits)
#print("Fitness medio elitista:", mean_elite)

# 2) Buscar parámetros izhi
print("Buscando mejores parámetros...")

for idx, combo in enumerate(combinations):
    print(f"Probando combo {idx+1}/{len(combinations)}...")

    mean_fit = run_izhi(combo)

    if mean_fit > best_mean:
        best_mean = mean_fit
        best_params = combo
        # guardar en archivo de texto
        with open("mejores_parametros_izhi.txt", "w") as f:
            for name, value in zip(param_names, combo):
                f.write(f"{name} = {value}\n")
            f.write(f"MEAN_FITNESS = {mean_fit}\n")

print("\n=== RESULTADO FINAL ===")
print("Mejor fitness medio obtenido:", best_mean)
print("Mejores parámetros guardados en mejores_parametros_izhi.txt")
