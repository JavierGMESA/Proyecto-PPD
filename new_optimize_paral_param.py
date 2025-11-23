import subprocess
import random
import time
import json
import os
import numpy as np

# ==========================================
# RANGOS DE LOS PARÁMETROS A OPTIMIZAR
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

# Orden de los parámetros según tu programa C
PARAM_ORDER = [
    "IniI", "IncMutI", "IncPosI", "IncNegI", "IncPicI",
    "IniA",
    "IniB", "IncPosB", "IncNegB", "IncPicB",
    "IniC", "IncPosC", "IncNegC", "IncPicC",
    "IniD", "IncPosD", "IncNegD", "IncPicD",
    "MAX_ULT_PICO", "MAX_PIC_SEG"
]

# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

def generar_parametros():
    """Genera un diccionario con valores aleatorios dentro del rango."""
    params = {}
    for k, (min_val, max_val) in RANGOS.items():
        if k.startswith("MAX"):
            # Enteros para MAX_ULT_PICO y MAX_PIC_SEG
            params[k] = random.randint(int(min_val), int(max_val))
        else:
            # Flotantes para el resto
            params[k] = random.uniform(min_val, max_val)
    return params


def ejecutar_programa(params, nombre="cga_paral_izhi_onemax"):
    """Ejecuta el binario C con los parámetros y devuelve el fitness final."""
    # Construir comando con parámetros en el orden correcto
    cmd = [f"./{nombre}"]
    for param_name in PARAM_ORDER:
        cmd.append(str(params[param_name]))
    
    try:
        salida = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=30).decode()
    except subprocess.CalledProcessError as e:
        print("❌ ERROR: El programa C ha fallado con exit code", e.returncode)
        print("Salida del programa:")
        print(e.output.decode())
        return None
    except subprocess.TimeoutExpired:
        print("❌ ERROR: El programa tardó más de 30 segundos (timeout)")
        return None
    
    # Buscar fitness en la salida
    for linea in salida.splitlines():
        if "Mejor fitness encontrado" in linea:
            try:
                return int(linea.split(":")[1].strip())
            except:
                return None
    
    return None


def guardar_mejor(params, fitness, media=None):
    """Guarda los mejores parámetros en un archivo."""
    with open("mejores_parametros_paral_random.txt", "w") as f:
        f.write("=== MEJORES PARÁMETROS ENCONTRADOS ===\n\n")
        for param_name in PARAM_ORDER:
            f.write(f"{param_name} = {params[param_name]}\n")
        f.write(f"\nFITNESS_MEDIO = {media if media else fitness}\n")
        if media:
            f.write(f"FITNESS_MEJOR = {fitness}\n")
    
    # También guardar en JSON para fácil lectura por programas
    with open("mejores_parametros_paral_random.json", "w") as f:
        json.dump({
            "fitness_medio": media if media else fitness,
            "fitness_mejor": fitness,
            "parametros": params
        }, f, indent=4)


# ==========================================
# PROCESO PRINCIPAL
# ==========================================
if __name__ == "__main__":
    
    print("=== OPTIMIZADOR ALEATORIO DE PARÁMETROS IZHIKEVICH ===")
    print("Pulsa CTRL + C para detener (los mejores parámetros se guardarán).\n")
    
    # Verificar que existe el ejecutable
    if not os.path.exists("./cga_paral_izhi_onemax"):
        print("❌ ERROR: No se encuentra el ejecutable './cga_paral_izhi_onemax'")
        print("Compila el programa primero con: gcc cga_paral_izhi_onemax.c -o cga_paral_izhi_onemax -lm")
        exit(1)
    
    # Comprobar si hay un mejor previo guardado
    best_fitness_mean = -1
    best_fitness_max = -1
    best_params = None
    
    if os.path.exists("mejores_parametros_paral_random.json"):
        try:
            with open("mejores_parametros_paral_random.json") as f:
                data = json.load(f)
                best_fitness_mean = data.get("fitness_medio", -1)
                best_fitness_max = data.get("fitness_mejor", -1)
                best_params = data.get("parametros")
            print(f"📂 Parámetros previos cargados:")
            print(f"   Fitness medio = {best_fitness_mean}")
            print(f"   Fitness máximo = {best_fitness_max}\n")
        except:
            print("⚠️ No se pudieron cargar parámetros previos\n")
    
    N_REPETICIONES = 5
    iteracion = 0
    
    try:
        while True:
            iteracion += 1
            print(f"\n{'='*60}")
            print(f"ITERACIÓN {iteracion}")
            print(f"{'='*60}")
            
            # ------------------------------
            # 1. Generar nueva combinación aleatoria
            # ------------------------------
            params = generar_parametros()
            
            print("\n📋 Combinación generada:")
            for param_name in PARAM_ORDER:
                print(f"  {param_name:15s} = {params[param_name]}")
            
            # ------------------------------
            # 2. Ejecutar varias veces
            # ------------------------------
            resultados = []
            
            print(f"\n🔄 Ejecutando {N_REPETICIONES} repeticiones...")
            for i in range(N_REPETICIONES):
                print(f"   Ejecución {i+1}/{N_REPETICIONES}...", end=" ")
                f = ejecutar_programa(params)
                
                if f is None:
                    print("❌ Error o timeout")
                    break
                
                print(f"✓ Fitness = {f}")
                resultados.append(f)
            
            # ------------------------------
            # 3. Evaluar resultados
            # ------------------------------
            if not resultados:
                print("\n⚠️ Combinación descartada (errores en ejecución)")
                continue
            
            media = np.mean(resultados)
            maximo = max(resultados)
            minimo = min(resultados)
            desv = np.std(resultados)
            
            print(f"\n📊 Resultados:")
            print(f"   Media:       {media:.2f}")
            print(f"   Máximo:      {maximo}")
            print(f"   Mínimo:      {minimo}")
            print(f"   Desv. Std:   {desv:.2f}")
            
            # ------------------------------
            # 4. Comparar con mejor resultado
            # ------------------------------
            if media > best_fitness_mean:
                print("\n🎉 ¡NUEVOS MEJORES PARÁMETROS ENCONTRADOS! 🎉")
                print(f"   Fitness medio anterior: {best_fitness_mean:.2f}")
                print(f"   Fitness medio nuevo:    {media:.2f}")
                print(f"   Mejora:                 +{media - best_fitness_mean:.2f}")
                
                best_fitness_mean = media
                best_fitness_max = maximo
                best_params = params
                guardar_mejor(params, maximo, media)
            else:
                print(f"\n   Mejor media actual: {best_fitness_mean:.2f}")
            
            print(f"\n⏳ Esperando 1 segundo antes de la próxima iteración...")
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\n🛑 INTERRUPCIÓN DETECTADA (CTRL + C)")
        
        if best_params is not None:
            print("\n💾 Guardando mejores parámetros encontrados...")
            guardar_mejor(best_params, best_fitness_max, best_fitness_mean)
            print(f"\n✅ Mejores parámetros guardados:")
            print(f"   - mejores_parametros_random.txt")
            print(f"   - mejores_parametros_random.json")
            print(f"\n📈 Mejor fitness medio: {best_fitness_mean:.2f}")
            print(f"📈 Mejor fitness máximo: {best_fitness_max}")
        else:
            print("\n⚠️ No se encontraron parámetros válidos durante la ejecución")
        
        print("\n👋 Saliendo...")
        exit(0)
