"""Re-corrida contra el original de secuencias ya registradas (riesgo del diseño: «el incidente cambia algo que no
detecta el canario»). Repite cada secuencia elegida tras un reset, la registra como seq rc<HHMM>-<seq original> y
compara cada respuesta con la registrada. Una divergencia indica que algo cambió desde esa fila (el original, la
reconstrucción del request o el entorno): la causa se atribuye después, con experimentos.

Uso: uv run python -m lab.recorrida PREFIJO [PREFIJO …] [--ejemplos]
  p. ej. `lab.recorrida fz1- --ejemplos` repite la semilla 1 del fuzzer y los 20 ejemplos oficiales.
"""

from __future__ import annotations

import json
import sys
import time
from collections import OrderedDict
from pathlib import Path

from lab.compare import comparar_paso, como_texto
from lab.m1 import TOKEN_INVALIDO, VARIANTES_AUTH
from lab.probe import Lab

ROOT = Path(__file__).resolve().parents[1]


def cargar(prefijos: list[str], ejemplos: bool) -> OrderedDict[str, list[dict]]:
    seqs: OrderedDict[str, list[dict]] = OrderedDict()
    if ejemplos:
        with open(ROOT / "pruebas" / "ejemplos.jsonl", encoding="utf-8") as f:
            seqs["ejemplos"] = [{**json.loads(l), "id": f"ej{json.loads(l)['n']}"} for l in f if l.strip()]
    with open(ROOT / "experimentos.jsonl", encoding="utf-8") as f:
        for linea in f:
            r = json.loads(linea)
            if "infra" in r or not any(r["seq"].startswith(p) for p in prefijos):
                continue
            if r.get("ruta") == "POST /__reset":
                continue
            auth = r.get("auth", "propio")
            if not (auth in VARIANTES_AUTH or auth.startswith("variante: ")):
                # igual que M1: una variante que no se sabe reconstruir aborta antes de mandar nada
                raise SystemExit(f"fila {r['id']} ({r['seq']}): variante de auth desconocida {auth!r}")
            seqs.setdefault(r["seq"], []).append(r)
    return seqs


def reenviar(lab: Lab, r: dict, metodo: str, ruta: str, hip: str) -> dict:
    """Reconstruye el request como M1: variante de auth desde `auth` (nunca desde el header redactado) y cuerpo
    JSON, crudo o vacío según `body_mode`."""
    auth = r.get("auth", "propio")
    plantilla = auth.removeprefix("variante: ") if auth.startswith("variante: ") else VARIANTES_AUTH[auth]
    headers = {k: v for k, v in (r.get("headers") or {}).items() if k.lower() != "authorization"}
    if plantilla is not None:
        headers["Authorization"] = plantilla.format(t=lab.token, otro=TOKEN_INVALIDO)
    req = r.get("request")
    modo = r.get("body_mode") or ("none" if req is None else "raw" if isinstance(req, str) else "json")
    kw = {"path": ruta, "method": metodo, "token": None, "headers": headers, "auth": auth}
    if modo == "raw":
        return lab.send(None, hip, content=req.encode("utf-8"), **kw)
    if modo == "json":
        headers.setdefault("Content-Type", "application/json")
        return lab.send(None, hip, content=json.dumps(req, ensure_ascii=False).encode("utf-8"), **kw)
    return lab.send(None, hip, **kw)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    seqs = cargar(args, "--ejemplos" in sys.argv)
    hhmm = time.strftime("%H%M")
    lab = Lab()
    pasos = difs = 0
    for seq, filas in seqs.items():
        if lab.reset(f"rc{hhmm}-{seq}", f"re-corrida {hhmm} de {seq}: ¿el original cambió desde que se registró?") != 200:
            raise SystemExit(f"rc{hhmm}-{seq}: el reset del original falló; se aborta antes del primer paso")
        for r in filas:
            metodo, ruta = r.get("ruta", "POST /msg").split(" ", 1)
            f = reenviar(lab, r, metodo, ruta, f"re-corrida {hhmm} de la fila {r['id']}: misma respuesta que entonces")
            pasos += 1
            motivo = comparar_paso(r["status"], como_texto(r["response"]), f["status"], como_texto(f["response"]))
            if motivo:
                difs += 1
                print(f"DIVERGENCIA fila {r['id']} -> {f['id']} {r['request']}: {motivo}")
    print(f"\nre-corrida {hhmm}: {len(seqs)} secuencias, {pasos} pasos, {difs} distintos")
    sys.exit(1 if difs else 0)


if __name__ == "__main__":
    main()
