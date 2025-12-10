import subprocess
import re
import csv
import os
import json

# ============================
# CONFIGURACIÓN
# ============================
N_RUNS = 5

EXEC_TRUCK_ELITE_SEQ   = "./cga_truck"
EXEC_TRUCK_IZHI_SEQ    = "./cga_izhi_truck"
EXEC_TRUCK_ELITE_PARAL = "./cga_paral_truck"
EXEC_TRUCK_IZHI_PARAL  = "./cga_paral_izhi_truck"
EXEC_TRUCK_ELITE_DIST  = "./cga_distrib_truck"
EXEC_TRUCK_IZHI_DIST   = "./cga_distrib_izhi_truck"
EXEC_TRUCK_ELITE_HIBR  = "./cga_hibrid_truck"
EXEC_TRUCK_IZHI_HIBR   = "./cga_hibrid_izhi_truck"

N_PROCESOS = 6
HOSTFILE   = "hosts.txt"
IFACE      = "tailscale0"

CSV_DIR = "./CSVsTruck"
os.makedirs(CSV_DIR, exist_ok=True)

PARAM_DIR = "./MejoresParametrosTruck"

# Archivos de mejores parámetros
JSON_IZHI_SEQ    = os.path.join(PARAM_DIR, "mejores_parametros_izhi_truck.json")
JSON_IZHI_PARAL  = os.path.join(PARAM_DIR, "mejores_parametros_paral_izhi_truck.json")
JSON_IZHI_DIST   = os.path.join(PARAM_DIR, "mejores_parametros_distrib_izhi_truck.json")
JSON_IZHI_HIBR   = os.path.join(PARAM_DIR, "mejores_parametros_hibrid_izhi_truck.json")

# Orden de parámetros (igual que en optimize_param_truck.py)
PARAM_ORDER = [
    "IniI", "IncMutI", "IncPosI", "IncNegI", "IncPicI",
    "IniA",
    "IniB", "IncPosB", "IncNegB", "IncPicB",
    "IniC", "IncPosC", "IncNegC", "IncPicC",
    "IniD", "IncPosD", "IncNegD", "IncPicD",
    "MAX_ULT_PICO", "MAX_PIC_SEG"
]

# Regex para parsear fitness
regex_elite = re.compile(r"Generación\s+(\d+).*Mejor fitness:\s+([0-9.+-eE]+)")
regex_izhi  = regex_elite


# ============================
# UTILIDADES
# ============================

def check_exec(path):
    if not os.path.exists(path):
        print(f"❌ ERROR: no se encuentra el ejecutable '{path}'")
        return False
    return True

def leer_mejores_parametros_json(path_json):
    if not os.path.exists(path_json):
        print(f"⚠️ No se encontró archivo de parámetros: {path_json}")
        return None
    try:
        with open(path_json, "r") as f:
            data = json.load(f)
        params_dict = data.get("parametros", {})
        # Construir lista en orden
        args = []
        for name in PARAM_ORDER:
            if name not in params_dict:
                print(f"⚠️ Falta parámetro '{name}' en {path_json}")
                return None
            args.append(str(params_dict[name]))
        print(f"✅ Parámetros cargados desde {path_json}")
        print("   Fitness mejor guardado:", data.get("fitness_mejor", "N/A"))
        return args
    except Exception as e:
        print(f"❌ Error al leer {path_json}: {e}")
        return None

def ejecutar_y_guardar(comando, regex, run_id, etiqueta):
    print(f"\n🔄 Ejecutando {etiqueta}, run {run_id}...")

    proc = subprocess.Popen(
        comando,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    csv_name = os.path.join(CSV_DIR, f"resultados_{etiqueta}_run{run_id}.csv")

    with open(csv_name, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["gen", "fitness"])

        for line in proc.stdout:
            m = regex.search(line)
            if m:
                gen, fit = m.groups()
                writer.writerow([int(gen), float(fit)])

    proc.wait()

    if proc.returncode != 0:
        print(f"  ⚠️ El programa terminó con código de error {proc.returncode}")
        stderr_output = proc.stderr.read()
        if stderr_output:
            print(f"  Error: {stderr_output}")
    else:
        print(f"  ✅ Guardado en {csv_name}")


# ============================
# MAIN
# ============================

if __name__ == "__main__":
    print("="*60)
    print("EJECUTANDO EXPERIMENTOS (TRUCK)")
    print("="*60)

    for exe in [
        EXEC_TRUCK_ELITE_SEQ, EXEC_TRUCK_IZHI_SEQ,
        EXEC_TRUCK_ELITE_PARAL, EXEC_TRUCK_IZHI_PARAL,
        EXEC_TRUCK_ELITE_DIST, EXEC_TRUCK_IZHI_DIST,
        EXEC_TRUCK_ELITE_HIBR, EXEC_TRUCK_IZHI_HIBR
    ]:
        check_exec(exe)

    # Cargar parámetros IZHI (pueden ser None si no existen)
    params_izhi_seq    = leer_mejores_parametros_json(JSON_IZHI_SEQ)
    params_izhi_paral  = leer_mejores_parametros_json(JSON_IZHI_PARAL)
    params_izhi_dist   = leer_mejores_parametros_json(JSON_IZHI_DIST)
    params_izhi_hibr   = leer_mejores_parametros_json(JSON_IZHI_HIBR)

    ejecutar_izhi_seq    = params_izhi_seq    is not None
    ejecutar_izhi_paral  = params_izhi_paral  is not None
    ejecutar_izhi_dist   = params_izhi_dist   is not None
    ejecutar_izhi_hibr   = params_izhi_hibr   is not None

    # 1) Elitista secuencial (no usa IZHI)
    print("\n" + "-"*60)
    print("TRUCK ELITISTA SECUENCIAL")
    print("-"*60)
    for run in range(1, N_RUNS + 1):
        ejecutar_y_guardar([EXEC_TRUCK_ELITE_SEQ], regex_elite, run, "truck_elite")

    # 2) Elitista paralela
    print("\n" + "-"*60)
    print("TRUCK ELITISTA PARALELA (OpenMP)")
    print("-"*60)
    for run in range(1, N_RUNS + 1):
        ejecutar_y_guardar([EXEC_TRUCK_ELITE_PARAL], regex_elite, run, "truck_elite_paral")

    # 3) Elitista distribuida
    print("\n" + "-"*60)
    print("TRUCK ELITISTA DISTRIBUIDA (MPI)")
    print("-"*60)
    for run in range(1, N_RUNS + 1):
        cmd = [
            "mpirun",
            "-np", str(N_PROCESOS),
            "--hostfile", HOSTFILE,
            "--mca", "btl_tcp_if_include", IFACE,
            EXEC_TRUCK_ELITE_DIST
        ]
        ejecutar_y_guardar(cmd, regex_elite, run, "truck_elite_distrib")

    # 4) Elitista híbrida
    print("\n" + "-"*60)
    print("TRUCK ELITISTA HÍBRIDA (MPI+OpenMP)")
    print("-"*60)
    for run in range(1, N_RUNS + 1):
        cmd = [
            "mpirun",
            "-np", str(N_PROCESOS),
            "--hostfile", HOSTFILE,
            "--mca", "btl_tcp_if_include", IFACE,
            EXEC_TRUCK_ELITE_HIBR
        ]
        ejecutar_y_guardar(cmd, regex_elite, run, "truck_elite_hibrid")

    # 5) Izhi secuencial
    if ejecutar_izhi_seq:
        print("\n" + "-"*60)
        print("TRUCK IZHIKEVICH SECUENCIAL")
        print("-"*60)
        for run in range(1, N_RUNS + 1):
            cmd = [EXEC_TRUCK_IZHI_SEQ] + params_izhi_seq
            ejecutar_y_guardar(cmd, regex_izhi, run, "truck_izhi")
    else:
        print("\n⚠️ Se omite TRUCK IZHI SECUENCIAL (no hay parámetros)")

    # 6) Izhi paralela
    if ejecutar_izhi_paral:
        print("\n" + "-"*60)
        print("TRUCK IZHIKEVICH PARALELA (OpenMP)")
        print("-"*60)
        for run in range(1, N_RUNS + 1):
            cmd = [EXEC_TRUCK_IZHI_PARAL] + params_izhi_paral
            ejecutar_y_guardar(cmd, regex_izhi, run, "truck_izhi_paral")
    else:
        print("\n⚠️ Se omite TRUCK IZHI PARALELA (no hay parámetros)")

    # 7) Izhi distribuida
    if ejecutar_izhi_dist:
        print("\n" + "-"*60)
        print("TRUCK IZHIKEVICH DISTRIBUIDA (MPI)")
        print("-"*60)
        for run in range(1, N_RUNS + 1):
            cmd = [
                "mpirun",
                "-np", str(N_PROCESOS),
                "--hostfile", HOSTFILE,
                "--mca", "btl_tcp_if_include", IFACE,
                EXEC_TRUCK_IZHI_DIST
            ] + params_izhi_dist
            ejecutar_y_guardar(cmd, regex_izhi, run, "truck_izhi_distrib")
    else:
        print("\n⚠️ Se omite TRUCK IZHI DISTRIBUIDA (no hay parámetros)")

    # 8) Izhi híbrida
    if ejecutar_izhi_hibr:
        print("\n" + "-"*60)
        print("TRUCK IZHIKEVICH HÍBRIDA (MPI+OpenMP)")
        print("-"*60)
        for run in range(1, N_RUNS + 1):
            cmd = [
                "mpirun",
                "-np", str(N_PROCESOS),
                "--hostfile", HOSTFILE,
                "--mca", "btl_tcp_if_include", IFACE,
                EXEC_TRUCK_IZHI_HIBR
            ] + params_izhi_hibr
            ejecutar_y_guardar(cmd, regex_izhi, run, "truck_izhi_hibrid")
    else:
        print("\n⚠️ Se omite TRUCK IZHI HÍBRIDA (no hay parámetros)")

    print("\n✅ FIN EXPERIMENTOS TRUCK")

