import subprocess
import re
import csv
import os
import json

# -------------------------------
# CONFIGURACIÓN DE EXPERIMENTOS
# -------------------------------
N_RUNS = 5

EXEC_ELITE         = "./cga_onemax"
EXEC_IZHI          = "./cga_izhi_onemax"
EXEC_ELITE_PARAL   = "./cga_paral_onemax"
EXEC_IZHI_PARAL    = "./cga_paral_izhi_onemax"
EXEC_ELITE_DISTRIB = "./cga_distrib_onemax"
EXEC_IZHI_DISTRIB  = "./cga_distrib_izhi_onemax"
EXEC_ELITE_HIBRID  = "./cga_hibrid_onemax"
EXEC_IZHI_HIBRID   = "./cga_hibrid_izhi_onemax"

C_ELITE         = ["gcc", "cga_onemax.c", "-o", "cga_onemax"]
C_IZHI          = ["gcc", "cga_izhi_onemax.c", "-o", "cga_izhi_onemax"]
C_ELITE_PARAL   = ["gcc", "cga_paral_onemax.c", "-o", "cga_paral_onemax", "-fopenmp"]
C_IZHI_PARAL    = ["gcc", "cga_paral_izhi_onemax.c", "-o", "cga_paral_izhi_onemax", "-fopenmp"]
C_ELITE_DISTRIB = ["mpicc", "cga_distrib_onemax.c", "-o", "cga_distrib_onemax"]
C_IZHI_DISTRIB  = ["mpicc", "cga_distrib_izhi_onemax.c", "-o", "cga_distrib_izhi_onemax"]
C_ELITE_HIBRID  = ["mpicc", "cga_hibrid_onemax.c", "-fopenmp", "-o", "cga_hibrid_onemax"]
C_IZHI_HIBRID   = ["mpicc", "cga_hibrid_izhi_onemax.c", "-fopenmp", "-o", "cga_hibrid_izhi_onemax"]

# MPI (para distrib e híbrido)
N_PROCESOS = 6
HOSTFILE   = "hosts.txt"
IFACE      = "tailscale0"

# Carpeta donde se guardan los CSV
CSV_DIR = "./CSVs"
os.makedirs(CSV_DIR, exist_ok=True)  # [web:84]

# Archivos de mejores parámetros
ARCHIVO_PARAMS_JSON_SEQ    = "mejores_parametros_random.json"
ARCHIVO_PARAMS_TXT_SEQ     = "mejores_parametros_random.txt"
ARCHIVO_PARAMS_JSON_PARAL  = "mejores_parametros_paral_random.json"
ARCHIVO_PARAMS_TXT_PARAL   = "mejores_parametros_paral_random.txt"
ARCHIVO_PARAMS_JSON_DISTR  = "mejores_parametros_distrib_random.json"
ARCHIVO_PARAMS_TXT_DISTR   = "mejores_parametros_distrib_random.txt"
ARCHIVO_PARAMS_JSON_HIBRID = "mejores_parametros_hibrid_random.json"
ARCHIVO_PARAMS_TXT_HIBRID  = "mejores_parametros_hibrid_random.txt"

# Orden de parámetros de Izhikevich
PARAM_ORDER = [
    "IniI", "IncMutI", "IncPosI", "IncNegI", "IncPicI",
    "IniA",
    "IniB", "IncPosB", "IncNegB", "IncPicB",
    "IniC", "IncPosC", "IncNegC", "IncPicC",
    "IniD", "IncPosD", "IncNegD", "IncPicD",
    "MAX_ULT_PICO", "MAX_PIC_SEG"
]

# -------------------------------
# FUNCIÓN PARA LEER PARÁMETROS
# -------------------------------
def leer_mejores_parametros(archivo_json, archivo_txt):
    # Primero JSON
    if os.path.exists(archivo_json):
        print(f"📂 Leyendo parámetros desde {archivo_json}...")
        try:
            with open(archivo_json, "r") as f:
                data = json.load(f)
            params_dict = data.get("parametros", {})
            params_list = []
            for name in PARAM_ORDER:
                if name not in params_dict:
                    print(f"⚠️ Falta el parámetro {name} en el archivo JSON")
                    return None
                params_list.append(str(params_dict[name]))
            print("✅ Parámetros cargados correctamente")
            print("   Fitness medio guardado:", data.get("fitness_medio", "N/A"))
            return params_list
        except Exception as e:
            print("❌ Error al leer JSON:", e)

    # Luego TXT
    if os.path.exists(archivo_txt):
        print(f"📂 Leyendo parámetros desde {archivo_txt}...")
        try:
            params_dict = {}
            with open(archivo_txt, "r") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("==="):
                        k, v = [x.strip() for x in line.split("=", 1)]
                        if k in PARAM_ORDER:
                            params_dict[k] = v
            params_list = []
            for name in PARAM_ORDER:
                if name not in params_dict:
                    print(f"⚠️ Falta el parámetro {name} en el archivo TXT")
                    return None
                params_list.append(params_dict[name])
            print("✅ Parámetros cargados correctamente")
            return params_list
        except Exception as e:
            print("❌ Error al leer TXT:", e)

    print(f"❌ No se encontró ningún archivo de parámetros ({archivo_json}, {archivo_txt})")
    return None


# -------------------------------
# COMPILACIÓN
# -------------------------------
print("="*60)
print("COMPILANDO PROGRAMAS")
print("="*60)

print("\n🔨 Compilando versión elitista secuencial...")
subprocess.run(C_ELITE, check=True)
print("✅ Compilado: cga_onemax")

print("\n🔨 Compilando versión Izhikevich secuencial...")
subprocess.run(C_IZHI, check=True)
print("✅ Compilado: cga_izhi_onemax")

print("\n🔨 Compilando versión elitista paralela (OpenMP)...")
subprocess.run(C_ELITE_PARAL, check=True)
print("✅ Compilado: cga_paral_onemax")

print("\n🔨 Compilando versión Izhikevich paralela (OpenMP)...")
subprocess.run(C_IZHI_PARAL, check=True)
print("✅ Compilado: cga_paral_izhi_onemax")

print("\n🔨 Compilando versión elitista distribuida (MPI)...")
subprocess.run(C_ELITE_DISTRIB, check=True)
print("✅ Compilado: cga_distrib_onemax")

print("\n🔨 Compilando versión Izhikevich distribuida (MPI)...")
subprocess.run(C_IZHI_DISTRIB, check=True)
print("✅ Compilado: cga_distrib_izhi_onemax")

print("\n🔨 Compilando versión elitista híbrida (MPI+OpenMP)...")
subprocess.run(C_ELITE_HIBRID, check=True)
print("✅ Compilado: cga_hibrid_onemax")

print("\n🔨 Compilando versión Izhikevich híbrida (MPI+OpenMP)...")
subprocess.run(C_IZHI_HIBRID, check=True)
print("✅ Compilado: cga_hibrid_izhi_onemax")


# -------------------------------
# CARGAR PARÁMETROS IZHIKEVICH
# -------------------------------
print("\n" + "="*60)
print("CARGANDO PARÁMETROS IZHIKEVICH")
print("="*60)

params_izhi_seq    = leer_mejores_parametros(ARCHIVO_PARAMS_JSON_SEQ,   ARCHIVO_PARAMS_TXT_SEQ)
params_izhi_paral  = leer_mejores_parametros(ARCHIVO_PARAMS_JSON_PARAL, ARCHIVO_PARAMS_TXT_PARAL)
params_izhi_distrib= leer_mejores_parametros(ARCHIVO_PARAMS_JSON_DISTR, ARCHIVO_PARAMS_TXT_DISTR)
params_izhi_hibrid = leer_mejores_parametros(ARCHIVO_PARAMS_JSON_HIBRID,ARCHIVO_PARAMS_TXT_HIBRID)

ejecutar_izhi_seq     = params_izhi_seq    is not None
ejecutar_izhi_paral   = params_izhi_paral  is not None
ejecutar_izhi_distrib = params_izhi_distrib is not None
ejecutar_izhi_hibrid  = params_izhi_hibrid is not None


# -------------------------------
# REGEX PARA PARSEAR LA SALIDA
# -------------------------------
regex_elite = re.compile(r"Generación\s+(\d+).*Mejor fitness:\s+(\d+)")
regex_izhi  = re.compile(r"Generación\s+(\d+).*Mejor fitness:\s+(\d+).*Picos presentados:\s+(\d+)")


def ejecutar_y_guardar(comando, regex, run_id, etiqueta):
    """
    Ejecuta un programa y guarda los datos generación a generación en un CSV.
    'comando' es una lista (se puede incluir mpirun o no).
    """
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
        if etiqueta.startswith("izhi"):
            writer.writerow(["gen", "fitness", "picos"])
        else:
            writer.writerow(["gen", "fitness"])

        for line in proc.stdout:
            m = regex.search(line)
            if m:
                if etiqueta.startswith("izhi"):
                    gen, fit, picos = m.groups()
                    writer.writerow([int(gen), int(fit), int(picos)])
                else:
                    gen, fit = m.groups()
                    writer.writerow([int(gen), int(fit)])

    proc.wait()

    if proc.returncode != 0:
        print(f"  ⚠️ El programa terminó con código de error {proc.returncode}")
        stderr_output = proc.stderr.read()
        if stderr_output:
            print(f"  Error: {stderr_output}")
    else:
        print(f"  ✅ Guardado en {csv_name}")


# -------------------------------
# EJECUCIONES REPETIDAS
# -------------------------------
print("\n" + "="*60)
print("EJECUTANDO EXPERIMENTOS")
print("="*60)

# 1) Elitista secuencial
print("\n" + "-"*60)
print("VERSIÓN ELITISTA SECUENCIAL")
print("-"*60)
for run in range(1, N_RUNS + 1):
    ejecutar_y_guardar([EXEC_ELITE], regex_elite, run, "elite")

# 2) Elitista paralela (OpenMP)
print("\n" + "-"*60)
print("VERSIÓN ELITISTA PARALELA (OpenMP)")
print("-"*60)
for run in range(1, N_RUNS + 1):
    ejecutar_y_guardar([EXEC_ELITE_PARAL], regex_elite, run, "elite_paral")

# 3) Elitista distribuida (MPI)
print("\n" + "-"*60)
print("VERSIÓN ELITISTA DISTRIBUIDA (MPI)")
print("-"*60)
for run in range(1, N_RUNS + 1):
    cmd = [
        "mpirun",
        "-np", str(N_PROCESOS),
        "--hostfile", HOSTFILE,
        "--mca", "btl_tcp_if_include", IFACE,
        EXEC_ELITE_DISTRIB
    ]
    ejecutar_y_guardar(cmd, regex_elite, run, "elite_distrib")

# 4) Elitista híbrida (MPI+OpenMP)
print("\n" + "-"*60)
print("VERSIÓN ELITISTA HÍBRIDA (MPI+OpenMP)")
print("-"*60)
for run in range(1, N_RUNS + 1):
    cmd = [
        "mpirun",
        "-np", str(N_PROCESOS),
        "--hostfile", HOSTFILE,
        "--mca", "btl_tcp_if_include", IFACE,
        EXEC_ELITE_HIBRID
    ]
    ejecutar_y_guardar(cmd, regex_elite, run, "elite_hibrid")

# 5) Izhikevich secuencial
if ejecutar_izhi_seq:
    print("\n" + "-"*60)
    print("VERSIÓN IZHIKEVICH SECUENCIAL")
    print("-"*60)
    for run in range(1, N_RUNS + 1):
        cmd = [EXEC_IZHI] + params_izhi_seq
        ejecutar_y_guardar(cmd, regex_izhi, run, "izhi")
else:
    print("\n⚠️ Se omite Izhikevich secuencial (no hay parámetros)")

# 6) Izhikevich paralela (OpenMP)
if ejecutar_izhi_paral:
    print("\n" + "-"*60)
    print("VERSIÓN IZHIKEVICH PARALELA (OpenMP)")
    print("-"*60)
    for run in range(1, N_RUNS + 1):
        cmd = [EXEC_IZHI_PARAL] + params_izhi_paral
        ejecutar_y_guardar(cmd, regex_izhi, run, "izhi_paral")
else:
    print("\n⚠️ Se omite Izhikevich paralela (no hay parámetros)")

# 7) Izhikevich distribuida (MPI)
if ejecutar_izhi_distrib:
    print("\n" + "-"*60)
    print("VERSIÓN IZHIKEVICH DISTRIBUIDA (MPI)")
    print("-"*60)
    for run in range(1, N_RUNS + 1):
        cmd = [
            "mpirun",
            "-np", str(N_PROCESOS),
            "--hostfile", HOSTFILE,
            "--mca", "btl_tcp_if_include", IFACE,
            EXEC_IZHI_DISTRIB
        ] + params_izhi_distrib
        ejecutar_y_guardar(cmd, regex_izhi, run, "izhi_distrib")
else:
    print("\n⚠️ Se omite Izhikevich distribuida (no hay parámetros)")

# 8) Izhikevich híbrida (MPI+OpenMP)
if ejecutar_izhi_hibrid:
    print("\n" + "-"*60)
    print("VERSIÓN IZHIKEVICH HÍBRIDA (MPI+OpenMP)")
    print("-"*60)
    for run in range(1, N_RUNS + 1):
        cmd = [
            "mpirun",
            "-np", str(N_PROCESOS),
            "--hostfile", HOSTFILE,
            "--mca", "btl_tcp_if_include", IFACE,
            EXEC_IZHI_HIBRID
        ] + params_izhi_hibrid
        ejecutar_y_guardar(cmd, regex_izhi, run, "izhi_hibrid")
else:
    print("\n⚠️ Se omite Izhikevich híbrida (no hay parámetros)")


# -------------------------------
# RESUMEN FINAL
# -------------------------------
print("\n" + "="*60)
print("RESUMEN DE EXPERIMENTOS")
print("="*60)

archivos_generados = []
etiquetas = [
    "elite", "elite_paral", "elite_distrib", "elite_hibrid",
    "izhi", "izhi_paral", "izhi_distrib", "izhi_hibrid"
]

for run in range(1, N_RUNS + 1):
    for et in etiquetas:
        path = os.path.join(CSV_DIR, f"resultados_{et}_run{run}.csv")
        if os.path.exists(path):
            archivos_generados.append(path)

print(f"\n📊 Archivos CSV generados ({len(archivos_generados)}):")
for archivo in archivos_generados:
    print(f"   ✓ {archivo}")

print("\n✅ FIN DE EXPERIMENTOS")
print("Ya tienes los CSV generados. Luego el analysis.py leerá desde ./CSVs.")


