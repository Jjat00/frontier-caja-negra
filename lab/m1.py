"""M1: regresión del log contra el reemplazo LOCAL (nunca contra el original).

Re-ejecuta cada `seq` de experimentos.jsonl y la secuencia de pruebas/ejemplos.jsonl:
reset al inicio de cada seq y luego cada fila con su método, ruta, variante de auth y cuerpo
(json, texto crudo o sin cuerpo). Las filas `infra` (rate limit) se ignoran y X-Req no se compara.

Uso: uv run python -m lab.m1 [-v]   (-v lista también las filas que pasan)
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import warnings

warnings.filterwarnings("ignore", message=".*httpx.*")  # aviso de deprecación del TestClient
from starlette.testclient import TestClient  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("PERFIL", "v_manana")

from app.main import CajaNegra  # noqa: E402
from app.perfiles import PERFILES  # noqa: E402
from lab.compare import comparar_paso, como_texto  # noqa: E402

TOKEN_INVALIDO = "token-invalido-m1"
PRIMERA_FILA_V2 = 6040  # canario-1600: primera secuencia registrada con la versión 2
TOKEN_FICTICIO = "token-ficticio-m1"  # M1 no necesita el token real

# Variante de auth del log -> header que se manda (None = sin header).
VARIANTES_AUTH = {
    "propio": "Bearer {t}",
    "sin_token": None,
    "token_invalido": "Bearer {otro}",
    "bearer_minuscula": "bearer {t}",
    "esquema_token": "Token {t}",
    "sin_esquema": "{t}",
    "doble_espacio": "Bearer  {t}",
    "token_equipo": "Bearer {otro}",  # log 4467: el original no acepta el token del equipo; localmente es otro token
}


def cargar() -> dict[str, list[dict]]:
    """Secuencias en orden de aparición; los ejemplos van como una sola seq."""
    seqs: dict[str, list[dict]] = defaultdict(list)
    with open(ROOT / "experimentos.jsonl", encoding="utf-8") as f:
        for linea in f:
            if linea.strip():
                fila = json.loads(linea)
                if "infra" not in fila:
                    seqs[fila["seq"]].append(fila)
    with open(ROOT / "pruebas" / "ejemplos.jsonl", encoding="utf-8") as f:
        for linea in f:
            if linea.strip():
                fila = json.loads(linea)
                seqs["ejemplos"].append({**fila, "id": f"ej{fila['n']}"})
    return seqs


def enviar(cliente: TestClient, token: str, fila: dict):
    metodo, ruta = fila.get("ruta", "POST /msg").split(" ", 1)
    # El Authorization guardado en el log se ignora (está redactado): se reconstruye desde `auth`.
    headers = {k: v for k, v in (fila.get("headers") or {}).items() if k.lower() != "authorization"}
    auth = fila.get("auth", "propio")
    if auth.startswith("variante: "):  # e17: la plantilla del header va en el propio campo
        valor = auth.removeprefix("variante: ")
    elif auth not in VARIANTES_AUTH:
        raise ValueError(f"fila {fila['id']}: variante de auth desconocida {auth!r}")
    else:
        valor = VARIANTES_AUTH[auth]
    if valor is not None:
        headers["Authorization"] = valor.format(t=token, otro=TOKEN_INVALIDO)
    request = fila.get("request")
    modo = fila.get("body_mode") or ("none" if request is None else "raw" if isinstance(request, str) else "json")
    if modo == "json":
        headers.setdefault("Content-Type", "application/json")
        contenido = json.dumps(request, ensure_ascii=False).encode("utf-8")
    elif modo == "raw":
        contenido = request.encode("utf-8")
    else:
        contenido = None
    return cliente.request(metodo, ruta, content=contenido, headers=headers)


def main() -> None:
    verbose = "-v" in sys.argv
    app = CajaNegra()
    token = app.token = TOKEN_FICTICIO
    cliente = TestClient(app)
    total = iguales = 0
    fallos = []
    for seq, filas in cargar().items():
        # Cada secuencia se repite con la versión del servicio vigente cuando se registró: hasta la fila 6039 la 1
        # (v_manana, incluidos los 20 ejemplos) y desde el canario de las 16:00 (fila 6040) la 2 (v_tarde).
        primera = filas[0]["id"]
        app.perfil = PERFILES["v_tarde" if isinstance(primera, int) and primera >= PRIMERA_FILA_V2 else "v_manana"]
        cliente.post("/__reset", headers={"Authorization": f"Bearer {token}"})
        for fila in filas:
            r = enviar(cliente, token, fila)
            motivo = comparar_paso(fila["status"], como_texto(fila["response"]), r.status_code, r.text)
            total += 1
            if motivo is None:
                iguales += 1
                if verbose:
                    print(f"ok    {seq} #{fila['id']}")
            else:
                fallos.append((seq, fila, motivo))
    for seq, fila, motivo in fallos:
        print(f"FALLA {seq} #{fila['id']} {fila.get('ruta', 'POST /msg')} {fila.get('request')!r}: {motivo}")
    print(f"\nM1: {iguales}/{total} pasos iguales ({100 * iguales / total:.1f} %)")
    sys.exit(0 if not fallos else 1)


if __name__ == "__main__":
    main()
