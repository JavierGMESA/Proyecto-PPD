import subprocess
import re
import csv
import os
import json


# -------------------------------
# CONFIGURACIÓN DE EXPERIMENTOS
# -------------------------------
N_RUNS = 5                              # Número de veces que se ejecuta cada programa

EXEC_ELITE       = "./cga_onemax"              # Ubicación versión elitista
EXEC_IZHI        = "./cga_izhi_onemax"         # Ubicación versión izhikevich
EXEC_ELITE_PARAL = "./cga_paral_onemax"        # Ubicación versión elitista paralela
EXEC_IZHI_PARAL  = "./cga_paral_izhi_onemax"   # Ubicación versión izhikevich paralela

C_ELITE       = ["gcc", "cga_onemax.c", "-o", "cga_onemax"]                     # Comando compilación elitista
C_IZHI        = ["gcc", "cga_izhi_onemax.c", "-o", "cga_izhi_onemax"]           # Comando compilación izhikevich
C_ELITE_PARAL = ["gcc", "cga_paral_onemax.c", "-o", "cga_paral_onemax", "-fopenmp"]     # Paralelo
C_IZHI_PARAL  = ["gcc", "cga_paral_izhi_onemax.c", "-o", "cga_paral_izhi_onemax", "-fopenmp"]

# Carpeta donde se guardan los CSV
CSV_DIR = "./CSVs"
os.makedirs(CSV_DIR, exist_ok=True)  # [web:13][web:7]


# Archivos donde están los mejores parámetros
ARCHIVO_PARAMS_JSON_SEQ   = "mejores_parametros_random.json"
ARCHIVO_PARAMS_TXT_SEQ    = "mejores_parametros_random.txt"
ARCHIVO_PARAMS_JSON_PARAL = "mejores_parametros_paral_random.json"
ARCHIVO_PARAMS_TXT_PARAL  = "mejores_parametros_paral_random.txt"


# Orden de los parámetros para pasarlos al programa C
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
    """
    Lee los mejores parámetros desde el archivo JSON o TXT.
    Devuelve una lista con los valores en el orden correcto.
    """
    # Intentar primero con JSON (más fiable)
    if os.path.exists(archivo_json):
        print(f"📂 Leyendo parámetros desde {archivo_json}...")
        try:
            with open(archivo_json, 'r') as f:
                data = json.load(f)
                params_dict = data.get("parametros", {})
                
            params_list = []
            for param_name in PARAM_ORDER:
                if param_name in params_dict:
                    params_list.append(str(params_dict[param_name]))
                else:
                    print(f"⚠️ Falta el parámetro {param_name} en el archivo")
                    return None
            
            print(f"✅ Parámetros cargados correctamente")
            print(f"   Fitness medio guardado: {data.get('fitness_medio', 'N/A')}")
            return params_list
            
        except Exception as e:
            print(f"❌ Error al leer JSON: {e}")
    
    # Si no existe JSON, intentar con TXT
    if os.path.exists(archivo_txt):
        print(f"📂 Leyendo parámetros desde {archivo_txt}...")
        try:
            params_dict = {}
            with open(archivo_txt, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('==='):
                        parts = line.split('=')
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip()
                            if key in PARAM_ORDER:
                                params_dict[key] = value
            
            params_list = []
            for param_name in PARAM_ORDER:
                if param_name in params_dict:
                    params_list.append(params_dict[param_name])
                else:
                    print(f"⚠️ Falta el parámetro {param_name} en el archivo")
                    return None
            
            print(f"✅ Parámetros cargados correctamente")
            return params_list
            
        except Exception as e:
            print(f"❌ Error al leer TXT: {e}")
    
    print(f"❌ No se encontró ningún archivo de parámetros")
    print(f"   Buscados: {archivo_json}, {archivo_txt}")
    return None



# -------------------------------
# COMPILACIÓN
# -------------------------------
print("="*60)
print("COMPILANDO PROGRAMAS")
print("="*60)

print("\n🔨 Compilando versión elitista...")
subprocess.run(C_ELITE, check=True)
print("✅ Compilado: cga_onemax")

print("\n🔨 Compilando versión Izhikevich...")
subprocess.run(C_IZHI, check=True)
print("✅ Compilado: cga_izhi_onemax")

print("\n🔨 Compilando versión elitista paralela...")
subprocess.run(C_ELITE_PARAL, check=True)
print("✅ Compilado: cga_paral_onemax")

print("\n🔨 Compilando versión Izhikevich paralela...")
subprocess.run(C_IZHI_PARAL, check=True)
print("✅ Compilado: cga_paral_izhi_onemax")


# -------------------------------
# CARGAR PARÁMETROS IZHIKEVICH
# -------------------------------
print("\n" + "="*60)
print("CARGANDO PARÁMETROS IZHIKEVICH")
print("="*60)

params_izhi_seq   = leer_mejores_parametros(ARCHIVO_PARAMS_JSON_SEQ,   ARCHIVO_PARAMS_TXT_SEQ)
params_izhi_paral = leer_mejores_parametros(ARCHIVO_PARAMS_JSON_PARAL, ARCHIVO_PARAMS_TXT_PARAL)

ejecutar_izhi_seq   = params_izhi_seq   is not None
ejecutar_izhi_paral = params_izhi_paral is not None

if ejecutar_izhi_seq:
    print("\n📋 Parámetros secuenciales a utilizar:")
    for i, param_name in enumerate(PARAM_ORDER):
        print(f"   {param_name:15s} = {params_izhi_seq[i]}")
else:
    print("\n⚠️ No se pudieron cargar los parámetros de Izhikevich secuencial")

if ejecutar_izhi_paral:
    print("\n📋 Parámetros paralelos a utilizar:")
    for i, param_name in enumerate(PARAM_ORDER):
        print(f"   {param_name:15s} = {params_izhi_paral[i]}")
else:
    print("\n⚠️ No se pudieron cargar los parámetros de Izhikevich paralelo")


# -------------------------------
# REGEX PARA PARSEAR LA SALIDA
# -------------------------------
regex_elite = re.compile(r"Generación\s+(\d+).*Mejor fitness:\s+(\d+)")
regex_izhi  = re.compile(r"Generación\s+(\d+).*Mejor fitness:\s+(\d+).*Picos presentados:\s+(\d+)")



def ejecutar_y_guardar(comando, regex, run_id, etiqueta):
    """
    Ejecuta un programa y guarda los datos generación a generación en un CSV.
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

# 1) Versión elitista secuencial
print("\n" + "-"*60)
print("VERSIÓN ELITISTA (sin Izhikevich)")
print("-"*60)

for run in range(1, N_RUNS + 1):
    ejecutar_y_guardar([EXEC_ELITE], regex_elite, run, "elite")

# 2) Versión elitista paralela
print("\n" + "-"*60)
print("VERSIÓN ELITISTA PARALELA (sin Izhikevich)")
print("-"*60)

for run in range(1, N_RUNS + 1):
    ejecutar_y_guardar([EXEC_ELITE_PARAL], regex_elite, run, "elite_paral")

# 3) Versión Izhikevich secuencial
if ejecutar_izhi_seq:
    print("\n" + "-"*60)
    print("VERSIÓN IZHIKEVICH (secuencial, con parámetros optimizados)")
    print("-"*60)
    
    for run in range(1, N_RUNS + 1):
        comando_izhi = [EXEC_IZHI] + params_izhi_seq
        ejecutar_y_guardar(comando_izhi, regex_izhi, run, "izhi")
else:
    print("\n⚠️ Se omitieron las ejecuciones de Izhikevich secuencial (no hay parámetros)")

# 4) Versión Izhikevich paralela
if ejecutar_izhi_paral:
    print("\n" + "-"*60)
    print("VERSIÓN IZHIKEVICH PARALELA (con parámetros optimizados)")
    print("-"*60)
    
    for run in range(1, N_RUNS + 1):
        comando_izhi_paral = [EXEC_IZHI_PARAL] + params_izhi_paral
        ejecutar_y_guardar(comando_izhi_paral, regex_izhi, run, "izhi_paral")
else:
    print("\n⚠️ Se omitieron las ejecuciones de Izhikevich paralela (no hay parámetros)")


# -------------------------------
# RESUMEN FINAL
# -------------------------------
print("\n" + "="*60)
print("RESUMEN DE EXPERIMENTOS")
print("="*60)

archivos_generados = []
etiquetas = ["elite", "elite_paral", "izhi", "izhi_paral"]

for run in range(1, N_RUNS + 1):
    for et in etiquetas:
        path = os.path.join(CSV_DIR, f"resultados_{et}_run{run}.csv")
        if os.path.exists(path):
            archivos_generados.append(path)

print(f"\n📊 Archivos CSV generados ({len(archivos_generados)}):")
for archivo in archivos_generados:
    print(f"   ✓ {archivo}")

print("\n✅ FIN DE EXPERIMENTOS")

