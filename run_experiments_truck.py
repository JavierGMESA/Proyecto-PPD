#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import csv
import json
import glob
import time
import subprocess
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple

# ============================================================
# CONFIG (según tu proyecto)
# ============================================================

# Directorios reales del proyecto (según capturas)
CSV_DIR = "./CSVsTruck"
PARAM_DIR = "./MejoresParametrosTruck"
SEEDS_FILE = "./seeds.txt"

os.makedirs(CSV_DIR, exist_ok=True)
os.makedirs(PARAM_DIR, exist_ok=True)

# Runs
N_RUNS_MAIN = 5
N_RUNS_PERF = 3

THREAD_SET = [1, 2, 4, 6, 8, 12, 16, 24, 32]

# Timeout por ejecución (ajústalo si hace falta)
TIMEOUT_SEC = 12000

# MPI config
N_PROCESOS = 6
HOSTFILE = "hosts.txt"
IFACE = "tailscale0"

# OpenMP runtime hints (para evitar spin-wait en híbrido/oversubscription)
OMP_WAIT_POLICY = "PASSIVE"     # ACTIVE|PASSIVE [web:460]
OMP_PROC_BIND   = "true"        # true/false/master/close/spread [web:414]
OMP_PLACES      = "cores"       # threads/cores/sockets o lista explícita [web:480]
OMP_DYNAMIC     = "false"

# Binarios (tal como indicaste)
EXEC_TRUCK_ELITE_SEQ   = "./cga_truck"
EXEC_TRUCK_IZHI_SEQ    = "./cga_izhi_truck"
EXEC_TRUCK_ELITE_PARAL = "./cga_paral_truck"
EXEC_TRUCK_IZHI_PARAL  = "./cga_paral_izhi_truck"
EXEC_TRUCK_ELITE_DIST  = "./cga_distrib_truck"
EXEC_TRUCK_IZHI_DIST   = "./cga_distrib_izhi_truck"
EXEC_TRUCK_ELITE_HIBR  = "./cga_hibrid_truck"
EXEC_TRUCK_IZHI_HIBR   = "./cga_hibrid_izhi_truck"

# Base names EXACTOS como en optimize_param_truck.py
BASE_NAMES = {
    "izhi_seq":   "mejores_parametros_izhi_truck",
    "izhi_paral": "mejores_parametros_paral_izhi_truck",
    "izhi_dist":  "mejores_parametros_distrib_izhi_truck",
    "izhi_hibr":  "mejores_parametros_hibrid_izhi_truck",
}

# Orden parámetros Izhi (igual que optimize_param_truck.py)
PARAM_ORDER = [
    "IniI", "IncMutI", "IncPosI", "IncNegI", "IncPicI",
    "IniA",
    "IniB", "IncPosB", "IncNegB", "IncPicB",
    "IniC", "IncPosC", "IncNegC", "IncPicC",
    "IniD", "IncPosD", "IncNegD", "IncPicD",
    "MAX_ULT_PICO", "MAX_PIC_SEG"
]

# Tags para extraer fitness global final (mismo criterio que optimize)
FINAL_FITNESS_TAGS = [
    "Mejor fitness global:",
    "Mejor fitness encontrado:",
    "Best global fitness:",
    "Global best fitness:"
]

# ============================================================
# (Opcional) Energía con pyRAPL
# ============================================================

HAVE_PYRAPL = False
try:
    import pyRAPL  # type: ignore
    pyRAPL.setup()
    HAVE_PYRAPL = True
except Exception:
    HAVE_PYRAPL = False
    raise ValueError("Falta instalar pyRAPL")


def measure_energy_joules(fn):
    """Devuelve (energy_j, result_dict). energy_j=None si no hay pyRAPL."""
    if not HAVE_PYRAPL:
        return None, fn()

    m = pyRAPL.Measurement("run")
    m.begin()
    result = fn()
    m.end()

    energy_j = None
    try:
        # Normalmente microJ -> J
        if hasattr(m, "result") and hasattr(m.result, "pkg"):
            energy_j = sum(m.result.pkg) / 1e6
    except Exception:
        energy_j = None

    return energy_j, result


# ============================================================
# Parseo stdout -> filas por generación (según tu printf)
# ============================================================

RE_GEN = re.compile(r"^\s*Generación\s+(\d+)\s*$")
RE_GLOBAL = re.compile(
    r"Mejor fitness global:\s*([-\d\.eE]+)\s*(?:\|\s*Picos presentados:\s*([-\d]+))?"
)
RE_FIT = re.compile(
    r"Mejor fitness:\s*([-\d\.eE]+)\s*\|\s*Peor fitness:\s*([-\d\.eE]+)\s*\|\s*Promedio de fitness:\s*([-\d\.eE]+)"
)
RE_GREEN = re.compile(
    r"Mejor green kms:\s*([-\d\.eE]+)\s*\|\s*Peor green kms:\s*([-\d\.eE]+)\s*\|\s*Promedio de green kms:\s*([-\d\.eE]+)"
)
RE_EMIS = re.compile(
    r"Mejor emissions:\s*([-\d\.eE]+)\s*\|\s*Peor emissions:\s*([-\d\.eE]+)\s*\|\s*Promedio de emissions:\s*([-\d\.eE]+)"
)


def parse_fitness_global_final(output_text: str) -> Optional[float]:
    # Igual que en optimize_param_truck.py: buscar tags desde el final
    for line in output_text.splitlines()[::-1]:
        for tag in FINAL_FITNESS_TAGS:
            if tag in line:
                try:
                    return float(line.split(tag, 1)[1].strip().split()[0])
                except Exception:
                    pass

    # Fallback suave
    for line in output_text.splitlines()[::-1]:
        if "Mejor fitness global" in line:
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


def parse_generation_rows(output_text: str, seed: int, threads: Optional[int]) -> List[Dict]:
    rows = []
    cur = None
    cur_gen = None

    for raw in output_text.splitlines():
        line = raw.strip()

        m = RE_GEN.match(line)
        if m:
            cur_gen = int(m.group(1))
            cur = {
                "gen": cur_gen,
                "seed": seed,
                "threads": (threads if threads is not None else ""),
                "best_global": "",
                "picos": "",
                "fit_best": "", "fit_worst": "", "fit_mean": "",
                "green_best": "", "green_worst": "", "green_mean": "",
                "emis_best": "", "emis_worst": "", "emis_mean": "",
            }
            continue

        if cur is None:
            continue

        m = RE_GLOBAL.search(line)
        if m:
            cur["best_global"] = float(m.group(1))
            if m.group(2) is not None:
                try:
                    cur["picos"] = int(m.group(2))
                except Exception:
                    cur["picos"] = ""
            continue

        m = RE_FIT.search(line)
        if m:
            cur["fit_best"] = float(m.group(1))
            cur["fit_worst"] = float(m.group(2))
            cur["fit_mean"] = float(m.group(3))
            continue

        m = RE_GREEN.search(line)
        if m:
            cur["green_best"] = float(m.group(1))
            cur["green_worst"] = float(m.group(2))
            cur["green_mean"] = float(m.group(3))
            continue

        m = RE_EMIS.search(line)
        if m:
            cur["emis_best"] = float(m.group(1))
            cur["emis_worst"] = float(m.group(2))
            cur["emis_mean"] = float(m.group(3))
            # Esta línea cierra el bloque => guardamos fila
            rows.append(cur)
            cur = None
            cur_gen = None
            continue

    return rows


GEN_COLS = [
    "gen", "seed", "threads",
    "best_global", "picos",
    "fit_best", "fit_worst", "fit_mean",
    "green_best", "green_worst", "green_mean",
    "emis_best", "emis_worst", "emis_mean",
]

RUN_SUMMARY_FILE = os.path.join(CSV_DIR, "runs_summary.csv")
RUN_SUMMARY_COLS = [
    "suite", "variant", "kind", "threads", "run_id", "seed",
    "wall_time_s", "energy_j", "avg_power_w",
    "final_best_global", "return_code"
]


# ============================================================
# Helpers: seeds, params, incremental
# ============================================================

def read_seeds(path: str) -> List[int]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"No existe {path}")
    seeds = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            seeds.append(int(s))
    if not seeds:
        raise ValueError("seeds.txt está vacío")
    return seeds


def check_exec(path: str) -> bool:
    ok = os.path.exists(path)
    if not ok:
        print(f"❌ No existe el ejecutable: {path}")
    return ok


def ensure_summary_header():
    if not os.path.exists(RUN_SUMMARY_FILE):
        with open(RUN_SUMMARY_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(RUN_SUMMARY_COLS)


def existing_run_ids(pattern_glob: str) -> List[int]:
    out = []
    for p in glob.glob(pattern_glob):
        m = re.search(r"_run(\d+)\.csv$", p)
        if m:
            out.append(int(m.group(1)))
    return sorted(set(out))


def missing_run_ids(prefix: str, target: int, tag: str) -> List[int]:
    pattern = os.path.join(CSV_DIR, f"{prefix}{tag}_run*.csv")
    have = set(existing_run_ids(pattern))
    return [k for k in range(1, target + 1) if k not in have]


def load_izhi_params_for(key: str) -> Optional[List[str]]:
    base = BASE_NAMES[key]
    json_path = os.path.join(PARAM_DIR, base + ".json")
    txt_path = os.path.join(PARAM_DIR, base + ".txt")

    # 1) JSON (preferido)
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            params = data.get("parametros", {})
            args = []
            for k in PARAM_ORDER:
                if k not in params:
                    print(f"⚠️ Falta {k} en {json_path}")
                    return None
                args.append(str(params[k]))
            return args
        except Exception as e:
            print(f"⚠️ Error leyendo {json_path}: {e}")

    # 2) TXT (fallback)
    if os.path.exists(txt_path):
        try:
            params = {}
            with open(txt_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "=" not in line or line.startswith("==="):
                        continue
                    k, v = [x.strip() for x in line.split("=", 1)]
                    params[k] = v
            args = []
            for k in PARAM_ORDER:
                if k not in params:
                    print(f"⚠️ Falta {k} en {txt_path}")
                    return None
                args.append(str(params[k]))
            return args
        except Exception as e:
            print(f"⚠️ Error leyendo {txt_path}: {e}")

    return None


# ============================================================
# Construcción de comandos
# ============================================================

@dataclass(frozen=True)
class Variant:
    label: str
    exe: str
    kind: str  # seq, omp, mpi, hybrid
    izhi_key: Optional[str] = None  # izhi_seq, izhi_paral, izhi_dist, izhi_hibr


def build_cmd(var: Variant, seed: int, threads: Optional[int], izhi_args: Optional[List[str]]) -> Tuple[List[str], Dict[str, str]]:
    env_extra = {}

    args = [str(seed)]
    #if var.kind in ("omp", "hybrid"):
    #    if threads is None:
    #        raise ValueError(f"{var.label} requiere threads")
    #    args.append(str(threads))
    #    env_extra["OMP_NUM_THREADS"] = str(threads)
    if var.kind in ("omp", "hybrid"):
        if threads is None:
            raise ValueError(f"{var.label} requiere threads")
        args.append(str(threads))

        # Variables OpenMP para el runtime
        env_extra["OMP_NUM_THREADS"] = str(threads)
        env_extra["OMP_DYNAMIC"] = OMP_DYNAMIC
        env_extra["OMP_WAIT_POLICY"] = OMP_WAIT_POLICY
        env_extra["OMP_PROC_BIND"] = OMP_PROC_BIND
        env_extra["OMP_PLACES"] = OMP_PLACES

    if var.izhi_key is not None:
        if not izhi_args:
            raise RuntimeError(f"No hay parámetros Izhi para {var.label}")
        args.extend(izhi_args)

    if var.kind in ("seq", "omp"):
        return [var.exe] + args, env_extra

    mpicmd = [
        "mpirun",
        "-np", str(N_PROCESOS),
        "--hostfile", HOSTFILE,
        "--mca", "btl_tcp_if_include", IFACE,
        var.exe
    ] + args
    return mpicmd, env_extra


# ============================================================
# Ejecución
# ============================================================

def run_one(
    suite: str,
    var: Variant,
    run_id: int,
    seed: int,
    threads: Optional[int],
    izhi_args: Optional[List[str]],
    out_csv_path: str
):
    ensure_summary_header()

    cmd, env_extra = build_cmd(var, seed, threads, izhi_args)
    env = os.environ.copy()
    env.update(env_extra)

    print(f"\n🔄 [{suite}] {var.label} run={run_id} seed={seed} threads={threads}")
    print("   CMD:", " ".join(cmd))

    def _do():
        t0 = time.perf_counter()
        try:
            out = subprocess.check_output(
                cmd, stderr=subprocess.STDOUT, timeout=TIMEOUT_SEC, text=True, env=env
            )
            rc = 0
        except subprocess.TimeoutExpired:
            return {"rc": 124, "out": "", "wall": time.perf_counter() - t0}
        except subprocess.CalledProcessError as e:
            return {"rc": e.returncode, "out": e.output or "", "wall": time.perf_counter() - t0}

        wall = time.perf_counter() - t0
        return {"rc": rc, "out": out, "wall": wall}

    energy_j, res = measure_energy_joules(_do)
    rc = res["rc"]
    out = res["out"]
    wall_s = res["wall"]

    rows = parse_generation_rows(out, seed=seed, threads=threads)
    final_best = parse_fitness_global_final(out)

    # Guardar CSV por generación
    with open(out_csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=GEN_COLS)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    avg_power_w = ""
    if energy_j is not None and wall_s > 0:
        avg_power_w = f"{(energy_j / wall_s):.6f}"

    with open(RUN_SUMMARY_FILE, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            suite, var.label, var.kind,
            (threads if threads is not None else ""),
            run_id, seed,
            f"{wall_s:.6f}",
            (f"{energy_j:.6f}" if energy_j is not None else ""),
            avg_power_w,
            (f"{final_best:.6f}" if final_best is not None else ""),
            rc
        ])

    if rc != 0:
        print(f"  ⚠️ return_code={rc} (revisa runs_summary.csv)")
    print(f"  ✅ CSV: {out_csv_path} | wall={wall_s:.2f}s | energy_j={energy_j}")


def ask_yes_no(prompt: str, default: str = "n") -> bool:
    default = default.lower().strip()
    while True:
        ans = input(f"{prompt} [{'Y/n' if default=='y' else 'y/N'}]: ").strip().lower()
        if not ans:
            ans = default
        if ans in ("y", "yes", "s", "si"):
            return True
        if ans in ("n", "no"):
            return False


def delete_csvs():
    for p in glob.glob(os.path.join(CSV_DIR, "*.csv")):
        os.remove(p)
    print(f"🧹 CSVs eliminados en {CSV_DIR}")


def main():
    print("=" * 70)
    print("RUN EXPERIMENTS TRUCK")
    print("=" * 70)

    # 0) Limpieza
    if ask_yes_no(f"¿Eliminar CSVs existentes en {CSV_DIR}?", default="n"):
        delete_csvs()

    # 1) Comprobar binarios
    print("\nComprobando ejecutables...")
    ok = True
    for exe in [
        EXEC_TRUCK_ELITE_SEQ, EXEC_TRUCK_IZHI_SEQ,
        EXEC_TRUCK_ELITE_PARAL, EXEC_TRUCK_IZHI_PARAL,
        EXEC_TRUCK_ELITE_DIST, EXEC_TRUCK_IZHI_DIST,
        EXEC_TRUCK_ELITE_HIBR, EXEC_TRUCK_IZHI_HIBR,
    ]:
        ok = check_exec(exe) and ok
    if not ok:
        print("❌ Faltan ejecutables. Compila con make y reintenta.")
        return 1

    # 2) Seeds
    seeds = read_seeds(SEEDS_FILE)
    if len(seeds) < max(N_RUNS_MAIN, N_RUNS_PERF):
        raise ValueError(f"{SEEDS_FILE} debe tener al menos {max(N_RUNS_MAIN, N_RUNS_PERF)} seeds.")

    # 3) Cargar params Izhi (4 variantes)
    izhi_args = {
        "izhi_seq": load_izhi_params_for("izhi_seq"),
        "izhi_paral": load_izhi_params_for("izhi_paral"),
        "izhi_dist": load_izhi_params_for("izhi_dist"),
        "izhi_hibr": load_izhi_params_for("izhi_hibr"),
    }

    for k, v in izhi_args.items():
        if v is None:
            print(f"⚠️ No se encontraron parámetros para {k} en {PARAM_DIR}. Se omitirá esa variante Izhi.")

    # 4) Threads para suite MAIN (un único valor)
    default_threads_main = 12
    try:
        s = input(f"\nNum threads para ejecuciones MAIN en OMP/híbrida [default={default_threads_main}]: ").strip()
        threads_main = int(s) if s else default_threads_main
    except Exception:
        threads_main = default_threads_main

    variants_main = [
        Variant("truck_elite_seq",   EXEC_TRUCK_ELITE_SEQ,   "seq",    None),
        Variant("truck_elite_paral", EXEC_TRUCK_ELITE_PARAL, "omp",    None),
        Variant("truck_elite_dist",  EXEC_TRUCK_ELITE_DIST,  "mpi",    None),
        Variant("truck_elite_hibr",  EXEC_TRUCK_ELITE_HIBR,  "hybrid", None),

        Variant("truck_izhi_seq",    EXEC_TRUCK_IZHI_SEQ,    "seq",    "izhi_seq"),
        Variant("truck_izhi_paral",  EXEC_TRUCK_IZHI_PARAL,  "omp",    "izhi_paral"),
        Variant("truck_izhi_dist",   EXEC_TRUCK_IZHI_DIST,   "mpi",    "izhi_dist"),
        Variant("truck_izhi_hibr",   EXEC_TRUCK_IZHI_HIBR,   "hybrid", "izhi_hibr"),
    ]

    # ========================================================
    # SUITE MAIN (5 runs)
    # ========================================================
    print("\n" + "=" * 70)
    print("SUITE MAIN (5 runs): 8 variantes")
    print("=" * 70)

    for var in variants_main:
        if var.izhi_key is not None and izhi_args.get(var.izhi_key) is None:
            print(f"\n⏭️  Omitiendo {var.label} (sin params Izhi).")
            continue

        miss = missing_run_ids(prefix="genstats_", target=N_RUNS_MAIN, tag=var.label)
        if not miss:
            print(f"\n✅ {var.label}: ya hay {N_RUNS_MAIN} runs, se omite.")
            continue

        for run_id in miss:
            seed = seeds[run_id - 1]
            th = threads_main if var.kind in ("omp", "hybrid") else None
            out_csv = os.path.join(CSV_DIR, f"genstats_{var.label}_run{run_id}.csv")
            run_one(
                suite="main",
                var=var,
                run_id=run_id,
                seed=seed,
                threads=th,
                izhi_args=(izhi_args.get(var.izhi_key) if var.izhi_key else None),
                out_csv_path=out_csv
            )

    # ========================================================
    # SUITE PERF (3 runs) - SOLO SIN IZHI (para speedup/efic/paralec)
    # ========================================================
    print("\n" + "=" * 70)
    print("SUITE PERF (3 runs): solo sin-Izhi + barrido de hilos")
    print("=" * 70)

    perf_variants = [
        Variant("truck_elite_seq",   EXEC_TRUCK_ELITE_SEQ,   "seq",    None),
        Variant("truck_elite_dist",  EXEC_TRUCK_ELITE_DIST,  "mpi",    None),
        Variant("truck_elite_paral", EXEC_TRUCK_ELITE_PARAL, "omp",    None),
        Variant("truck_elite_hibr",  EXEC_TRUCK_ELITE_HIBR,  "hybrid", None),
    ]

    # Baselines seq y dist: 3 runs (threads vacío, pero usamos sufijo _t1 para uniformidad)
    for var in perf_variants:
        if var.kind in ("seq", "mpi"):
            tag = f"{var.label}_t1"
            miss = missing_run_ids(prefix="perf_", target=N_RUNS_PERF, tag=tag)
            for run_id in miss:
                seed = seeds[0]
                out_csv = os.path.join(CSV_DIR, f"perf_{tag}_run{run_id}.csv")
                run_one(
                    suite="perf",
                    var=var,
                    run_id=run_id,
                    seed=seed,
                    threads=None,
                    izhi_args=None,
                    out_csv_path=out_csv
                )

    # OMP e híbrida: 3 runs por cada threads
    for var in perf_variants:
        if var.kind not in ("omp", "hybrid"):
            continue
        for t in THREAD_SET:
            tag = f"{var.label}_t{t}"
            miss = missing_run_ids(prefix="perf_", target=N_RUNS_PERF, tag=tag)
            for run_id in miss:
                seed = seeds[0]
                out_csv = os.path.join(CSV_DIR, f"perf_{tag}_run{run_id}.csv")
                run_one(
                    suite="perf",
                    var=var,
                    run_id=run_id,
                    seed=seed,
                    threads=t,
                    izhi_args=None,
                    out_csv_path=out_csv
                )

    print("\n✅ FIN")
    print("CSVs:", CSV_DIR)
    print("Resumen (tiempo/energía):", RUN_SUMMARY_FILE)
    if not HAVE_PYRAPL:
        print("ℹ️ pyRAPL no está disponible; energía/potencia quedarán vacías (solo tiempos).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
