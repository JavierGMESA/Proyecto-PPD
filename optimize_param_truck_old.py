import subprocess
import random
import time
import json
import os
import numpy as np

# ============================
# CONFIGURACIÓN GENERAL
# ============================

# Directorio donde se guardan los mejores parámetros
OUTPUT_DIR = "./MejoresParametrosTruck"
os.makedirs(OUTPUT_DIR, exist_ok=True)  # [web:137]

# Ejecutables
EXECUTABLES = {
    1: "cga_izhi_truck",
    2: "cga_paral_izhi_truck",
    3: "cga_distrib_izhi_truck",
    4: "cga_hibrid_izhi_truck",
}

# Config MPI para las versiones distribuidas/híbridas
N_PROCESOS = 6
HOSTFILE   = "hosts.txt"
IFACE      = "tailscale0"

# Nombre base de los ficheros según elección
NAMES = {
    1: "mejores_parametros_izhi_truck",
    2: "mejores_parametros_paral_izhi_truck",
    3: "mejores_parametros_distrib_izhi_truck",
    4: "mejores_parametros_hibrid_izhi_truck",
}

N_REPETICIONES = 5   # número de veces que evalúas cada conjunto de parámetros

# RANGOS de los parámetros Izhikevich (igual que en OneMax)
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

# ============================
# LECTURA OPCIÓN USUARIO
# ============================

def elegir_ejecutable():
    print("¿Qué versión de cga_izhi_truck quieres optimizar?")
    print("  1) cga_izhi_truck (secuencial)")
    print("  2) cga_paral_izhi_truck (OpenMP)")
    print("  3) cga_distrib_izhi_truck (MPI)")
    print("  4) cga_hibrid_izhi_truck (MPI+OpenMP)")

    while True:
        try:
            op = int(input("Elige opción [1-4]: ").strip())
            if op in (1, 2, 3, 4):
                return op
        except ValueError:
            pass
        print("Opción inválida, prueba de nuevo.")

# ============================
# GENERACIÓN DE PARÁMETROS
# ============================

def generar_parametros():
    params = {}
    for k, (vmin, vmax) in RANGOS.items():
        if k.startswith("MAX"):
            params[k] = random.randint(int(vmin), int(vmax))
        else:
            params[k] = random.uniform(vmin, vmax)
    return params

# ============================
# EJECUCIÓN DEL PROGRAMA
# ============================

def construir_comando(opcion, exe_path, params_dict):
    """
    Devuelve la lista de argumentos para subprocess.run
    según sea secuencial, OMP, MPI o híbrido.
    """
    base = [exe_path]
    args_izhi = [str(params_dict[name]) for name in PARAM_ORDER]

    # 1 y 2: secuencial y OpenMP → sin mpirun
    if opcion in (1, 2):
        return base + args_izhi

    # 3 y 4: versiones MPI → mpirun
    cmd = [
        "mpirun",
        "-np", str(N_PROCESOS),
        "--hostfile", HOSTFILE,
        "--mca", "btl_tcp_if_include", IFACE,
        exe_path
    ]
    return cmd + args_izhi  # [web:59]

def ejecutar_programa(opcion, exe_path, params_dict):
    cmd = construir_comando(opcion, exe_path, params_dict)

    try:
        salida = subprocess.check_output(
            cmd, stderr=subprocess.STDOUT, timeout=300, text=True
        )
    except subprocess.CalledProcessError as e:
        print("❌ ERROR: el programa ha fallado con código", e.returncode)
        print(e.output)
        return None
    except subprocess.TimeoutExpired:
        print("❌ ERROR: timeout ejecutando el programa")
        return None

    # Parsear fitness de la salida (igual que en tus scripts anteriores)
    fitness = None
    for linea in salida.splitlines():
        if "Mejor fitness encontrado" in linea:
            try:
                # asumiendo formato: "Mejor fitness encontrado: X"
                fitness = float(linea.split(":")[1].strip())
            except Exception:
                fitness = None
    return fitness

# ============================
# GUARDAR Y CARGAR MEJORES
# ============================

def rutas_salida(nombre_base):
    txt  = os.path.join(OUTPUT_DIR, nombre_base + ".txt")
    jsn  = os.path.join(OUTPUT_DIR, nombre_base + ".json")
    return txt, jsn

def guardar_mejor(nombre_base, params, fitness):
    txt, jsn = rutas_salida(nombre_base)

    with open(txt, "w") as f:
        f.write(f"=== MEJORES PARÁMETROS TRUCK ===\n\n")
        for name in PARAM_ORDER:
            f.write(f"{name} = {params[name]}\n")
        f.write(f"\nFITNESS_MEJOR = {fitness}\n")

    with open(jsn, "w") as f:
        json.dump(
            {
                "fitness_mejor": fitness,
                "parametros": params,
            },
            f,
            indent=4,
        )

def cargar_previos(nombre_base):
    _, jsn = rutas_salida(nombre_base)
    if not os.path.exists(jsn):
        return None, None
    try:
        with open(jsn) as f:
            data = json.load(f)
        return data.get("parametros"), data.get("fitness_mejor")
    except Exception as e:
        print("⚠️ No se pudieron cargar parámetros previos:", e)
        return None, None

# ============================
# PROCESO PRINCIPAL
# ============================

if __name__ == "__main__":
    opcion = elegir_ejecutable()
    exe_name = EXECUTABLES[opcion]
    nombre_base = NAMES[opcion]

    exe_path = "./" + exe_name
    if not os.path.exists(exe_path):
        print(f"❌ ERROR: no se encuentra el ejecutable '{exe_path}'")
        print("Compila antes con make.")
        raise SystemExit(1)

    print(f"\n=== OPTIMIZADOR ALEATORIO PARÁMETROS IZHI (TRUCK) ===")
    print(f"Ejecutable: {exe_path}")
    print(f"Salida de mejores parámetros en: {OUTPUT_DIR}\n")

    best_params, best_fit = cargar_previos(nombre_base)
    if best_params is not None:
        print("📂 Cargados mejores parámetros previos:")
        print("   Fitness mejor:", best_fit)

    if best_fit is None:
        best_fit = -1e9

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
            print(f"\n🔄 Ejecutando {N_REPETICIONES} repeticiones...")
            for i in range(N_REPETICIONES):
                print(f"   Ejecución {i+1}/{N_REPETICIONES}...", end=" ")
                fit = ejecutar_programa(opcion, exe_path, params)
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
            maximo = float(max(resultados))
            minimo = float(min(resultados))
            desv = float(np.std(resultados))

            print("\n📊 Resultados:")
            print(f"   Media:  {media:.6f}")
            print(f"   Máx:    {maximo:.6f}")
            print(f"   Mín:    {minimo:.6f}")
            print(f"   Desv:   {desv:.6f}")

            # Criterio: mejorar el máximo o la media, según prefieras
            if media > best_fit:
                print("\n🎉 NUEVOS MEJORES PARÁMETROS TRUCK 🎉")
                print(f"   Antes: {best_fit:.6f}")
                print(f"   Ahora: {media:.6f}")
                best_fit = media
                best_params = params
                guardar_mejor(nombre_base, best_params, best_fit)

            print("\n⏳ Esperando 1 segundo antes de la siguiente combinación...")
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n🛑 CTRL+C detectado. Guardando mejores parámetros (TRUCK)...")
        if best_params is not None:
            guardar_mejor(nombre_base, best_params, best_fit)
            print("✅ Guardados en", OUTPUT_DIR)
        else:
            print("⚠️ No se encontraron parámetros válidos.")
