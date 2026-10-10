"""M5: latencia por paso del reemplazo desplegado (diseño, sección 4: p99 < 200 ms; el límite del set es 5 s).

Repite contra el reemplazo las secuencias de una semilla ya registrada del fuzzer (no llama al original), mide el
tiempo de cada request visto desde el cliente (incluye la red) y reporta p50, p95, p99 y máximo. Deja el reemplazo
reseteado al terminar. No correr mientras haya una corrida oficial en curso: comparte el estado del reemplazo.

Uso: TOKEN=<token del equipo> uv run python -m lab.m5 URL [SEMILLA=1]
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def pasos(semilla: int) -> list[list[dict]]:
    seqs: dict[str, list[dict]] = {}
    with open(ROOT / "experimentos.jsonl", encoding="utf-8") as f:
        for linea in f:
            r = json.loads(linea)
            if r["seq"].startswith(f"fz{semilla}-") and "infra" not in r and r.get("ruta") != "POST /__reset":
                seqs.setdefault(r["seq"], []).append(r)
    return list(seqs.values())


def percentil(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1))))]


def main() -> None:
    url = sys.argv[1]
    semilla = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    h = {"Authorization": f"Bearer {os.environ['TOKEN']}"}
    cli = httpx.Client(base_url=url, timeout=10)
    tiempos = []
    for filas in pasos(semilla):
        cli.post("/__reset", headers=h)
        for r in filas:
            metodo, ruta = r.get("ruta", "POST /msg").split(" ", 1)
            cuerpo = json.dumps(r["request"], ensure_ascii=False).encode() if r.get("request") is not None else None
            t = time.perf_counter()
            cli.request(metodo, ruta, headers={**h, "Content-Type": "application/json"}, content=cuerpo)
            tiempos.append((time.perf_counter() - t) * 1000)
    cli.post("/__reset", headers=h)
    print(f"M5 {url} semilla {semilla}: {len(tiempos)} pasos · p50 {percentil(tiempos, 50):.0f} ms · "
          f"p95 {percentil(tiempos, 95):.0f} ms · p99 {percentil(tiempos, 99):.0f} ms · máx {max(tiempos):.0f} ms")


if __name__ == "__main__":
    main()
