import subprocess
import random
import time
import json
import os
import numpy as np

# ==========================================
# CONFIGURACIÓN MPI
# ==========================================
N_PROCESOS = 6
HOSTFILE   = "hosts.txt"
IFACE      = "tailscale0"
EXEC_NAME  = "cga_distrib_izhi_onemax"

# ==========================================
# RANGOS DE LOS PARÁMETROS A OPTIMIZAR
# (mismos que en los otros optimizadores)
# ==========================================
RANGOS = {
    "IniI": (1, 20),
    "IncMutI": (0.0001, 0.1),
    "IncPosI": (-0.1, 0.1),
    "IncNegI": (-0.1, 0.1),
    "IncPicI": (-0.1, 0.1),

    "IniA": (0.05, 0.5),

    "IniB": (0.05, 0.3),
    "IncPosB": (-0.01, 0.01),
    "IncNegB": (-0.01, 0.01),
    "IncPicB": (-0.01, 0.01),

    "IniC": (-80, -30),
    "IncPosC": (-1.0, 1.0),
    "IncNegC": (-1.0, 1.0),
    "IncPicC": (-1.0, 1.0),

    "IniD": (1, 8),
    "IncPosD": (-0.1, 0.1),
    "IncNegD": (-0.1, 0.1),
    "IncPicD": (-0.1, 0.1),

    "MAX_ULT_PICO": (10, 200),
    "MAX_PIC_SEG": (5, 100)
}

PARAM_ORDER = [
    "IniI", "IncMutI", "IncPosI", "IncNegI", "IncPicI",
    "IniA",
    "IniB", "IncPosB", "IncNegB", "IncPicB",
    "IniC", "IncPosC", "IncNegC", "IncPicC",
    "IniD", "IncPosD", "IncNegD", "IncPicD",
    "MAX_ULT_PICO", "MAX_PIC_SEG"
]

BEST_TXT  = "mejores_parametros_distrib_random.txt"
BEST_JSON = "mejores_parametros_distrib_random.json"


# ==========================================
# FUNCIONES AUXILIARES
# ==========================================
def generar_parametros():
    params = {}
    for k, (vmin, vmax) in RANGOS.items():
        if k.startswith("MAX"):
            params[k] = random.randint(int(vmin), int(vmax))
        else:
            params[k] = random.uniform(vmin, vmax)
    return params


def ejecutar_programa_mpi(params):
    """
    Ejecuta:
    mpirun -np N_PROCESOS --hostfile HOSTFILE --mca btl_tcp_if_include IFACE \
           ./EXEC_NAME <20 params>
    y devuelve el fitness final (o None si hay error).
    """
    cmd = [
        "mpirun",
        "-np", str(N_PROCESOS),
        "--hostfile", HOSTFILE,
        "--mca", "btl_tcp_if_include", IFACE,
        f"./{EXEC_NAME}",
    ]
    for name in PARAM_ORDER:
        cmd.append(str(params[name]))

    try:
        salida = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, timeout=120
        ).decode()
    except subprocess.CalledProcessError as e:
        print("❌ ERROR: el programa MPI ha fallado con exit code", e.returncode)
        print("Salida del programa:")
        print(e.output.decode())
        return None
    except subprocess.TimeoutExpired:
        print("❌ ERROR: timeout ejecutando el programa MPI")
        return None

    fitness = None
    for linea in salida.splitlines():
        if "Mejor fitness encontrado" in linea:
            try:
                fitness = int(linea.split(":")[1].strip())
            except:
                fitness = None
    return fitness


def guardar_mejor(params, fitness_max, fitness_med=None):
    with open(BEST_TXT, "w") as f:
        f.write("=== MEJORES PARÁMETROS (DISTRIB) ===\n\n")
        for name in PARAM_ORDER:
            f.write(f"{name} = {params[name]}\n")
        if fitness_med is not None:
            f.write(f"\nFITNESS_MEDIO = {fitness_med}\n")
            f.write(f"FITNESS_MEJOR = {fitness_max}\n")
        else:
            f.write(f"\nFITNESS_MEJOR = {fitness_max}\n")

    with open(BEST_JSON, "w") as f:
        json.dump(
            {
                "fitness_medio": fitness_med,
                "fitness_mejor": fitness_max,
                "parametros": params,
            },
            f,
            indent=4,
        )


# ==========================================
# PROCESO PRINCIPAL
# ==========================================
if __name__ == "__main__":
    print("=== OPTIMIZADOR ALEATORIO (DISTRIB / MPI) ===")
    print(f"Ejecutable: {EXEC_NAME}")
    print(f"mpirun -np {N_PROCESOS} --hostfile {HOSTFILE} --mca btl_tcp_if_include {IFACE}\n")

    if not os.path.exists(f"./{EXEC_NAME}"):
        print(f"❌ ERROR: no se encuentra el ejecutable './{EXEC_NAME}'")
        print("Compila primero, por ejemplo:")
        print("  mpicc cga_distrib_izhi_onemax.c -o cga_distrib_izhi_onemax -lm")
        raise SystemExit(1)

    best_mean = -1.0
    best_max = -1
    best_params = None

    if os.path.exists(BEST_JSON):
        try:
            with open(BEST_JSON) as f:
                data = json.load(f)
            best_mean = data.get("fitness_medio", -1.0)
            best_max = data.get("fitness_mejor", -1)
            best_params = data.get("parametros", None)
            print("📂 Cargados mejores parámetros previos (DISTRIB):")
            print("   Fitness medio:", best_mean)
            print("   Fitness mejor:", best_max)
        except Exception as e:
            print("⚠️ No se pudieron cargar parámetros previos:", e)

    N_REPETICIONES = 5
    iteracion = 0

    try:
        while True:
            iteracion += 1
            print("\n" + "=" * 60)
            print(f"ITERACIÓN {iteracion}")
            print("=" * 60)

            params = generar_parametros()
            print("\n📋 Combinación generada:")
            for name in PARAM_ORDER:
                print(f"  {name:15s} = {params[name]}")

            resultados = []
            print(f"\n🔄 Ejecutando {N_REPETICIONES} repeticiones (MPI distrib)...")
            for i in range(N_REPETICIONES):
                print(f"   Ejecución {i+1}/{N_REPETICIONES}...", end=" ")
                fit = ejecutar_programa_mpi(params)
                if fit is None:
                    print("❌ Error / timeout")
                    resultados = []
                    break
                print(f"✓ Fitness = {fit}")
                resultados.append(fit)

            if not resultados:
                print("\n⚠️ Combinación descartada (errores en ejecución)")
                continue

            media = float(np.mean(resultados))
            maximo = int(max(resultados))
            minimo = int(min(resultados))
            desv = float(np.std(resultados))

            print("\n📊 Resultados:")
            print(f"   Media:  {media:.2f}")
            print(f"   Máx:    {maximo}")
            print(f"   Mín:    {minimo}")
            print(f"   Desv:   {desv:.2f}")

            if media > best_mean:
                print("\n🎉 NUEVOS MEJORES PARÁMETROS (DISTRIB) 🎉")
                print(f"   Antes: {best_mean:.2f}")
                print(f"   Ahora: {media:.2f}")
                best_mean = media
                best_max = maximo
                best_params = params
                guardar_mejor(params, best_max, best_mean)

            print("\n⏳ Esperando 1 segundo antes de la siguiente combinación...")
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n🛑 CTRL+C detectado. Guardando mejores parámetros (DISTRIB)...")
        if best_params is not None:
            guardar_mejor(best_params, best_max, best_mean)
            print(f"✅ Guardados en {BEST_TXT} y {BEST_JSON}")
        else:
            print("⚠️ No se encontraron parámetros válidos.")
