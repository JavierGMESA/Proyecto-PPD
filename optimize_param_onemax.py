import os
import json
import random
import subprocess
import numpy as np


# =========================
# CONFIG
# =========================
OUTPUT_DIR = "./MejoresParametrosOneMax"
os.makedirs(OUTPUT_DIR, exist_ok=True)

FINAL_FITNESS_TAGS = [
    "Mejor fitness global:",
    "Mejor fitness encontrado:",
    "Best global fitness:",
    "Global best fitness:"
]

TIMEOUT_SEC = 15000

# Se sobrescribe por len(seeds)
N_REPS = 12

WARMUP_RANDOM = 25
TOP_FRAC = 0.30
P_EXPLOIT = 0.70
P_EXPLORE = 0.30

# MPI config
N_PROCESOS = 6
HOSTFILE = "hosts.txt"
IFACE = "tailscale0"

# Ejecutables OneMax (Izhikevich)
EXECUTABLES = {
    1: "./cga_izhi_onemax",
    2: "./cga_paral_izhi_onemax",
    3: "./cga_distrib_izhi_onemax",
    4: "./cga_hibrid_izhi_onemax",
}

BASE_NAMES = {
    1: "mejores_parametros_izhi_onemax",
    2: "mejores_parametros_paral_izhi_onemax",
    3: "mejores_parametros_distrib_izhi_onemax",
    4: "mejores_parametros_hibrid_izhi_onemax",
}

# Espacio de parámetros (igual que Truck)
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

SEEDS_FILE = "./seeds.txt"


# =========================
# Helpers
# =========================
def cargar_seeds(path=SEEDS_FILE):
    if not os.path.exists(path):
        raise FileNotFoundError(f"No existe {path}")

    seeds = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            seeds.append(int(line))

    if len(seeds) == 0:
        raise ValueError("seeds.txt está vacío")

    return seeds


def elegir_version():
    print("¿Qué versión IZHI ONEMAX quieres optimizar?")
    print("  1) Izhikevich secuencial")
    print("  2) Izhikevich OpenMP")
    print("  3) Izhikevich MPI")
    print("  4) Izhikevich híbrido (MPI+OpenMP)")
    while True:
        try:
            op = int(input("Elige opción [1-4]: ").strip())
            if op in (1, 2, 3, 4):
                return op
        except ValueError:
            pass
        print("Opción inválida, prueba de nuevo.")


def pedir_threads(opcion):
    n_threads = None
    if opcion in (2, 4):
        n_threads = int(input("Número de hilos OpenMP: ").strip())
    return n_threads


def rutas_salida(nombre_base):
    return (
        os.path.join(OUTPUT_DIR, nombre_base + ".txt"),
        os.path.join(OUTPUT_DIR, nombre_base + ".json"),
    )


def cargar_mejor(nombre_base):
    _, js = rutas_salida(nombre_base)
    if not os.path.exists(js):
        return None, None
    try:
        with open(js, "r") as f:
            data = json.load(f)
        return data.get("parametros"), data.get("fitness_mejor")
    except Exception:
        return None, None


def guardar_mejor(nombre_base, params, best_fit):
    txt, js = rutas_salida(nombre_base)

    with open(txt, "w") as f:
        f.write("=== MEJORES PARAMETROS IZHI ONEMAX ===\n\n")
        for name in PARAM_ORDER:
            f.write(f"{name} = {params[name]}\n")
        f.write(f"\nFITNESS_GLOBAL_MEJOR = {best_fit}\n")

    with open(js, "w") as f:
        json.dump({"fitness_mejor": best_fit, "parametros": params}, f, indent=4)


def parse_fitness_global(output_text):
    # Busca los tags “fuertes” desde el final del log
    for line in output_text.splitlines()[::-1]:
        for tag in FINAL_FITNESS_TAGS:
            if tag in line:
                try:
                    return float(line.split(tag, 1)[1].strip().split()[0])
                except Exception:
                    pass

    # Fallback: intenta extraer algún número de una línea típica
    for line in output_text.splitlines()[::-1]:
        if "Mejor fitness" in line:
            parts = line.replace("|", " ").replace(":", " ").split()
            floats = []
            for p in parts:
                try:
                    floats.append(float(p))
                except Exception:
                    pass
            if floats:
                return floats[0]

    return None


def construir_comando(opcion, exe_path, seed, n_threads, params_dict):
    args_params = [str(params_dict[k]) for k in PARAM_ORDER]

    # 1) Secuencial: ./cga_izhi_onemax seed <20 params>
    if opcion == 1:
        return [exe_path, str(seed)] + args_params

    # 2) OpenMP: ./cga_paral_izhi_onemax seed nthreads <20 params>
    if opcion == 2:
        return [exe_path, str(seed), str(n_threads)] + args_params

    # 3) MPI: mpirun ... ./cga_distrib_izhi_onemax seed <20 params>
    if opcion == 3:
        return [
            "mpirun", "-np", str(N_PROCESOS),
            "--hostfile", HOSTFILE,
            "--mca", "btl_tcp_if_include", IFACE,
            exe_path, str(seed)
        ] + args_params

    # 4) Híbrido: mpirun ... ./cga_hibrid_izhi_onemax seed nthreads <20 params>
    return [
        "mpirun", "-np", str(N_PROCESOS),
        "--hostfile", HOSTFILE,
        "--mca", "btl_tcp_if_include", IFACE,
        exe_path, str(seed), str(n_threads)
    ] + args_params


def ejecutar_once(opcion, exe_path, seed, n_threads, params_dict):
    cmd = construir_comando(opcion, exe_path, seed, n_threads, params_dict)
    try:
        out = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, timeout=TIMEOUT_SEC, text=True
        )
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except subprocess.CalledProcessError as e:
        return None, e.output

    fit = parse_fitness_global(out)
    return fit, out


# =========================
# Generador "Bayes/TPE-like"
# =========================
def random_params():
    p = {}
    for k, (a, b) in RANGOS.items():
        if k.startswith("MAX") or k in ("IniI", "IniD"):
            p[k] = random.randint(int(a), int(b))
        else:
            p[k] = random.uniform(a, b)
    return p


def clip_value(k, v):
    a, b = RANGOS[k]
    if k.startswith("MAX") or k in ("IniI", "IniD"):
        v = int(round(v))
        return max(int(a), min(int(b), v))
    return max(a, min(b, float(v)))


def propose_params(history):
    if len(history) < WARMUP_RANDOM:
        return random_params()

    hist_sorted = sorted(history, key=lambda t: t[1], reverse=True)
    cut = max(1, int(TOP_FRAC * len(hist_sorted)))
    good = hist_sorted[:cut]

    if random.random() < P_EXPLORE:
        return random_params()

    newp = {}
    for k in PARAM_ORDER:
        vals = [g[0][k] for g in good]
        mu = float(np.mean(vals))
        sd = float(np.std(vals))
        rng = RANGOS[k][1] - RANGOS[k][0]
        sd = max(sd, 0.05 * rng)

        sample = random.gauss(mu, sd)
        newp[k] = clip_value(k, sample)

    return newp


# =========================
# MAIN
# =========================
if __name__ == "__main__":
    opcion = elegir_version()
    exe_path = EXECUTABLES[opcion]
    nombre_base = BASE_NAMES[opcion]

    if not os.path.exists(exe_path):
        print(f"❌ No existe el ejecutable: {exe_path}")
        raise SystemExit(1)

    seeds = cargar_seeds()
    if len(seeds) < N_REPS:
        raise ValueError(f"{SEEDS_FILE} debe tener al menos {N_REPS} seeds.")

    n_threads = pedir_threads(opcion)

    best_params, best_fit = cargar_mejor(nombre_base)
    if best_fit is None:
        best_fit = -1e18

    history = []
    iteracion = 0

    print(f"\nOptimización IZHI ONEMAX -> {exe_path}")
    print(f"Seeds: {seeds}  (N_REPS={N_REPS})")
    if n_threads is not None:
        print(f"OpenMP threads: {n_threads}")
    print(f"Guardado en: {OUTPUT_DIR}")
    print("CTRL+C para parar.\n")

    try:
        while True:
            iteracion += 1
            params = propose_params(history)

            print(f"\n==============================")
            print(f"ITERACIÓN {iteracion}")
            print(f"==============================")

            fits = []
            for rep in range(N_REPS):
                seed = seeds[rep]
                print(f"[rep {rep+1}/{N_REPS}] seed={seed} ejecutando...")

                fit, out = ejecutar_once(opcion, exe_path, seed, n_threads, params)
                if fit is None:
                    print("[WARN] ejecución fallida/timeout. Últimas líneas:")
                    if isinstance(out, str):
                        print("\n".join(out.splitlines()[-10:]))
                    else:
                        print(out)
                    fits = []
                    break

                print(f"[rep {rep+1}/{N_REPS}] fitness_global={fit:.6f}")
                fits.append(fit)

            if not fits:
                continue

            score = float(np.mean(fits))
            history.append((params, score))

            print(f"[iter {iteracion}] mean_fitness_global={score:.6f} | best={best_fit:.6f}")

            if score > best_fit:
                best_fit = score
                best_params = params
                print(f"🎉 NUEVO MEJOR (OneMax) -> {best_fit:.6f}")
                guardar_mejor(nombre_base, best_params, best_fit)

    except KeyboardInterrupt:
        print("\n\n🛑 Parado por usuario.")
        if best_params is not None:
            guardar_mejor(nombre_base, best_params, best_fit)
            print("✅ Mejor guardado.")
