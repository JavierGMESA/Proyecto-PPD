import subprocess
import re
import csv
import os
import json

# -------------------------------
# CONFIGURACIÓN DE EXPERIMENTOS
# -------------------------------
N_RUNS = 5                              # Número de veces que se ejecuta cada programa
EXEC_ELITE = "./cga_onemax"             # Ubicación versión elitista
EXEC_IZHI  = "./cga_izhi_onemax"        # Ubicación versión izhikevich

C_ELITE = ["gcc", "cga_onemax.c", "-o", "cga_onemax"]               # Comando compilación elitista
C_IZHI  = ["gcc", "cga_izhi_onemax.c", "-o", "cga_izhi_onemax"]     # Comando compilación izhikevich

# Archivos donde están los mejores parámetros
ARCHIVO_PARAMS_JSON = "mejores_parametros_random.json"
ARCHIVO_PARAMS_TXT = "mejores_parametros_random.txt"

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
def leer_mejores_parametros():
    """
    Lee los mejores parámetros desde el archivo JSON o TXT.
    Devuelve una lista con los valores en el orden correcto.
    """
    # Intentar primero con JSON (más fiable)
    if os.path.exists(ARCHIVO_PARAMS_JSON):
        print(f"📂 Leyendo parámetros desde {ARCHIVO_PARAMS_JSON}...")
        try:
            with open(ARCHIVO_PARAMS_JSON, 'r') as f:
                data = json.load(f)
                params_dict = data.get("parametros", {})
                
            # Convertir a lista en el orden correcto
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
    if os.path.exists(ARCHIVO_PARAMS_TXT):
        print(f"📂 Leyendo parámetros desde {ARCHIVO_PARAMS_TXT}...")
        try:
            params_dict = {}
            with open(ARCHIVO_PARAMS_TXT, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('==='):
                        parts = line.split('=')
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip()
                            if key in PARAM_ORDER:
                                params_dict[key] = value
            
            # Convertir a lista en el orden correcto
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
    print(f"   Buscados: {ARCHIVO_PARAMS_JSON}, {ARCHIVO_PARAMS_TXT}")
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

# -------------------------------
# CARGAR PARÁMETROS IZHIKEVICH
# -------------------------------
print("\n" + "="*60)
print("CARGANDO PARÁMETROS IZHIKEVICH")
print("="*60)

params_izhi = leer_mejores_parametros()

if params_izhi is None:
    print("\n⚠️ No se pudieron cargar los parámetros de Izhikevich")
    print("⚠️ Solo se ejecutará la versión elitista")
    ejecutar_izhi = False
else:
    ejecutar_izhi = True
    print("\n📋 Parámetros a utilizar:")
    for i, param_name in enumerate(PARAM_ORDER):
        print(f"   {param_name:15s} = {params_izhi[i]}")

# -------------------------------
# REGEX PARA PARSEAR LA SALIDA
# -------------------------------
regex_elite = re.compile(r"Generación\s+(\d+).*Mejor fitness:\s+(\d+)")
regex_izhi  = re.compile(r"Generación\s+(\d+).*Mejor fitness:\s+(\d+).*Picos presentados:\s+(\d+)")


def ejecutar_y_guardar(comando, regex, run_id, etiqueta):
    """
    Ejecuta un programa y guarda los datos generación a generación en un CSV.
    
    Args:
        comando: lista con el comando a ejecutar (ej: ["./programa", "arg1", "arg2"])
        regex: expresión regular para parsear la salida
        run_id: número de ejecución (1, 2, 3...)
        etiqueta: "elite" o "izhi"
    """
    print(f"\n🔄 Ejecutando {etiqueta}, run {run_id}...")

    proc = subprocess.Popen(
        comando,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    csv_name = f"resultados_{etiqueta}_run{run_id}.csv"

    with open(csv_name, "w", newline="") as f:
        writer = csv.writer(f)
        if etiqueta == "izhi":
            writer.writerow(["gen", "fitness", "picos"])
        else:
            writer.writerow(["gen", "fitness"])

        for line in proc.stdout:
            m = regex.search(line)
            if m:
                if etiqueta == "izhi":
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

# Ejecutar versión elitista
print("\n" + "-"*60)
print("VERSIÓN ELITISTA (sin Izhikevich)")
print("-"*60)

for run in range(1, N_RUNS + 1):
    ejecutar_y_guardar([EXEC_ELITE], regex_elite, run, "elite")

# Ejecutar versión Izhikevich (si se cargaron los parámetros)
if ejecutar_izhi:
    print("\n" + "-"*60)
    print("VERSIÓN IZHIKEVICH (con parámetros optimizados)")
    print("-"*60)
    
    for run in range(1, N_RUNS + 1):
        # Construir comando con parámetros
        comando_izhi = [EXEC_IZHI] + params_izhi
        ejecutar_y_guardar(comando_izhi, regex_izhi, run, "izhi")
else:
    print("\n⚠️ Se omitieron las ejecuciones de Izhikevich (no hay parámetros)")

# -------------------------------
# RESUMEN FINAL
# -------------------------------
print("\n" + "="*60)
print("RESUMEN DE EXPERIMENTOS")
print("="*60)

archivos_generados = []
for run in range(1, N_RUNS + 1):
    elite_csv = f"resultados_elite_run{run}.csv"
    if os.path.exists(elite_csv):
        archivos_generados.append(elite_csv)
    
    if ejecutar_izhi:
        izhi_csv = f"resultados_izhi_run{run}.csv"
        if os.path.exists(izhi_csv):
            archivos_generados.append(izhi_csv)

print(f"\n📊 Archivos CSV generados ({len(archivos_generados)}):")
for archivo in archivos_generados:
    print(f"   ✓ {archivo}")

print("\n✅ FIN DE EXPERIMENTOS")
print("Ya tienes los CSV generados. Avisa cuando quieras generar las gráficas.")

