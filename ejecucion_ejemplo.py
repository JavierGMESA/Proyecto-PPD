#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import subprocess
from pathlib import Path

# Según tu run_experiments_onemax.py
EXEC_ELITE_CANDIDATES = ["./cga_paral_onemax", "./cgaparalonemax"]
EXEC_IZHI_CANDIDATES  = ["./cga_paral_izhi_onemax", "./cgaparalizhionemax"]

PARAM_DIR = Path("./MejoresParametrosOneMax")
IZHI_BASE = "mejores_parametros_paral_izhi_onemax"

# Orden exacto de parámetros Izhi (copiado de run_experiments_onemax.py)
PARAM_ORDER = [
    "IniI", "IncMutI", "IncPosI", "IncNegI", "IncPicI",
    "IniA",
    "IniB", "IncPosB", "IncNegB", "IncPicB",
    "IniC", "IncPosC", "IncNegC", "IncPicC",
    "IniD", "IncPosD", "IncNegD", "IncPicD",
    "MAX_ULT_PICO", "MAX_PIC_SEG"
]

# Defaults OpenMP (igual idea que tu runner; puedes simplificar si quieres)
OMP_DYNAMIC = "false"
OMP_WAIT_POLICY = "PASSIVE"
OMP_PROC_BIND = "true"
OMP_PLACES = "cores"

SEEDS_FILE = Path("./seeds.txt")


def which_exec(candidates):
    for c in candidates:
        if Path(c).exists():
            return c
    return None


def try_make_targets():
    # Intenta compilar con nombres "con _" y si falla, prueba sin "_"
    target_sets = [
        ["cga_paral_onemax", "cga_paral_izhi_onemax"],
        ["cgaparalonemax", "cgaparalizhionemax"],
    ]
    last_err = None
    for targets in target_sets:
        try:
            print("Compilando:", " ".join(targets))
            subprocess.run(["make"] + targets, check=True)
            return True
        except subprocess.CalledProcessError as e:
            last_err = e
            print("No se pudo con targets:", targets)
    if last_err:
        raise last_err
    return False


def read_int(prompt, default=None, min_value=1):
    while True:
        s = input(prompt).strip()
        if not s and default is not None:
            return default
        try:
            v = int(s)
            if v < min_value:
                print(f"Introduce un entero >= {min_value}.")
                continue
            return v
        except ValueError:
            print("Introduce un número entero válido.")

def read_first_seed(path: Path) -> int:
    if not path.exists():
        raise FileNotFoundError(f"No existe {path}")
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            return int(s)
    raise ValueError("seeds.txt está vacío o no tiene semillas válidas")



def load_izhi_args():
    json_path = PARAM_DIR / f"{IZHI_BASE}.json"
    txt_path  = PARAM_DIR / f"{IZHI_BASE}.txt"

    if json_path.exists():
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        params = data.get("parametros", {})
        missing = [k for k in PARAM_ORDER if k not in params]
        if missing:
            raise RuntimeError(f"Faltan claves en {json_path}: {missing}")
        return [str(params[k]) for k in PARAM_ORDER]

    if txt_path.exists():
        params = {}
        with open(txt_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" not in line or line.startswith("===") or not line:
                    continue
                k, v = [x.strip() for x in line.split("=", 1)]
                params[k] = v
        missing = [k for k in PARAM_ORDER if k not in params]
        if missing:
            raise RuntimeError(f"Faltan claves en {txt_path}: {missing}")
        return [str(params[k]) for k in PARAM_ORDER]

    raise FileNotFoundError(
        "No encuentro parámetros Izhi.\n"
        f"Esperaba uno de:\n- {json_path}\n- {txt_path}\n"
        "Genera/copia esos ficheros (los mismos que usa run_experiments_onemax.py) y reintenta."
    )


def run_program(exe, seed, threads, extra_args=None):
    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = str(threads)
    env["OMP_DYNAMIC"] = OMP_DYNAMIC
    env["OMP_WAIT_POLICY"] = OMP_WAIT_POLICY
    env["OMP_PROC_BIND"] = OMP_PROC_BIND
    env["OMP_PLACES"] = OMP_PLACES

    cmd = [exe, str(seed), str(threads)]
    if extra_args:
        cmd += list(extra_args)

    print("\nEjecutando:\n ", " ".join(cmd))
    subprocess.run(cmd, check=True, env=env)


def main():
    print("=== DEMO Paralelo OneMax (OMP) ===")
    print("1) Compilar")
    try_make_targets()

    exe_elite = which_exec(EXEC_ELITE_CANDIDATES)
    exe_izhi  = which_exec(EXEC_IZHI_CANDIDATES)

    if not exe_elite and not exe_izhi:
        raise FileNotFoundError(
            "No encuentro ejecutables tras compilar.\n"
            f"Probé: {EXEC_ELITE_CANDIDATES + EXEC_IZHI_CANDIDATES}\n"
            "Revisa nombres/tags del Makefile o los binarios generados."
        )

    print("\n2) Parámetros de ejecución")
    threads = read_int("Número de hilos (threads) a usar: ", default=None, min_value=1)
    
    seed = read_first_seed(SEEDS_FILE)
    print(f"Seed fija (primera de {SEEDS_FILE}): {seed}")


    print("\n3) ¿Qué ejecutar?")
    print("  1) Solo cga_paral_onemax (elite)")
    print("  2) Solo cga_paral_izhi_onemax (izhi)")
    print("  3) Ambos")
    choice = read_int("Elige 1/2/3 [default=3]: ", default=3, min_value=1)
    if choice not in (1, 2, 3):
        choice = 3

    if choice in (1, 3):
        if not exe_elite:
            raise FileNotFoundError("No encuentro ejecutable elite paralelo (cga_paral_onemax).")
        run_program(exe_elite, seed=seed, threads=threads)

    if choice in (2, 3):
        if not exe_izhi:
            raise FileNotFoundError("No encuentro ejecutable izhi paralelo (cga_paral_izhi_onemax).")
        izhi_args = load_izhi_args()
        run_program(exe_izhi, seed=seed, threads=threads, extra_args=izhi_args)

    print("\n✅ Demo terminada.")


if __name__ == "__main__":
    main()
