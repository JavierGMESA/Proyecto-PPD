import subprocess
import re
import csv
import os

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
os.makedirs(CSV_DIR, exist_ok=True)  # [web:135]

# Regex como en OneMax (ajusta si tu salida cambia)
regex_elite = re.compile(r"Generación\s+(\d+).*Mejor fitness:\s+([0-9.+-eE]+)")
regex_izhi  = regex_elite  # mismo formato de línea

def check_exec(path):
    if not os.path.exists(path):
        print(f"❌ ERROR: no se encuentra el ejecutable '{path}'")
        return False
    return True

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

    # 1) Elitista secuencial
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

    # 3) Elitista distribuida (MPI)
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

    # 4) Elitista híbrida (MPI+OpenMP)
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
    print("\n" + "-"*60)
    print("TRUCK IZHIKEVICH SECUENCIAL")
    print("-"*60)
    for run in range(1, N_RUNS + 1):
        ejecutar_y_guardar([EXEC_TRUCK_IZHI_SEQ], regex_izhi, run, "truck_izhi")

    # 6) Izhi paralela
    print("\n" + "-"*60)
    print("TRUCK IZHIKEVICH PARALELA (OpenMP)")
    print("-"*60)
    for run in range(1, N_RUNS + 1):
        ejecutar_y_guardar([EXEC_TRUCK_IZHI_PARAL], regex_izhi, run, "truck_izhi_paral")

    # 7) Izhi distribuida
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
        ]
        ejecutar_y_guardar(cmd, regex_izhi, run, "truck_izhi_distrib")

    # 8) Izhi híbrida
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
        ]
        ejecutar_y_guardar(cmd, regex_izhi, run, "truck_izhi_hibrid")

    print("\n✅ FIN EXPERIMENTOS TRUCK")
