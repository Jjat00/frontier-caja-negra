"""e27: bloqueo y contador de rechazos en la versión 2, con eventos que nunca se observaron en la versión 2.

Tras la corrida 2 (99/100) la falla es un test difícil con status distinto más adelante. Las reglas de desbloqueo y de
reinicio del contador se midieron solo en la versión 1 (log 1040-1041, 1090-1092). Tres familias:
  A: AC-0001 bloqueada con tres E506, un evento X y una sonda (TRANSFER de 60000): 423 si sigue bloqueada.
  B: dos E506, un evento X, un E506 y la sonda: 423 si X no reinició el contador (o si X contó como rechazo).
  O: con AC-0001 bloqueada, TRANSFER con monto 0, origen = destino y destino inexistente: orden frente a E510.
Cada paso se compara con el reemplazo local (perfil v_tarde).

Uso: uv run python -m lab.exp.e27_bloqueo_v2 [familia ...]
"""

import json
import os
import sys
import warnings

warnings.filterwarnings("ignore", message=".*httpx.*")
os.environ.setdefault("PERFIL", "v_tarde")

from lab.compare import comparar_paso, como_texto  # noqa: E402
from lab.control import firmar  # noqa: E402

RECHAZO = "TRANSFER;AC-0001;AC-0002;60000"  # E506 en la versión 2 (límite 50000), con o sin saldo
PREP = ["ALTA;Lucia", "ALTA;Mateo", "DEPOSITO;AC-0002;100000"]  # nombres distintos: sin exención por titular

EVENTOS = {
    "entrante": ["TRANSFER;AC-0002;AC-0001;1000"],
    "entrante+anula": ["TRANSFER;AC-0002;AC-0001;1000", "ANULA;OP-0002"],
    "anula-otra": ["ANULA;OP-0001"],
    "deposito-otra": ["DEPOSITO;AC-0002;5"],
    "deposito-propia-e303": ["DEPOSITO;AC-0001;0"],
    "deposito-propia": ["DEPOSITO;AC-0001;5"],
    "consulta": ["CONSULTA;AC-0001"],
    "ping": ["PING"],
    "notas": ["NOTAS"],
    "halt": ["HALT;AC-0001"],
    "alta": ["ALTA;Ana"],
    "e302": ["TRANSFER;AC-0001;AC-0002"],
    "e303": ["TRANSFER;AC-0001;AC-0002;0"],
    "e304": ["TRANSFER;AC-0001;AC-0001;5"],
    "e401": ["TRANSFER;AC-0001;AC-0009;5"],
}
FAMILIA_A = ["entrante", "entrante+anula", "anula-otra", "deposito-otra", "deposito-propia-e303", "deposito-propia",
             "consulta", "ping", "notas", "halt", "alta", "e302"]
FAMILIA_B = ["entrante", "deposito-otra", "consulta", "anula-otra", "ping", "notas", "halt", "alta", "e303", "e304",
             "e401"]


def firmado(m: str) -> str:
    return "PING;1" if m == "PING" else firmar(m)


def secuencias(familias: list[str]) -> list[tuple[str, str, list[str]]]:
    out = []
    if "A" in familias:
        for x in FAMILIA_A:
            out.append((f"e27-A-{x}", f"bloqueada (3 E506) + {x}: ¿sigue bloqueada en la v2?",
                        PREP + [RECHAZO] * 3 + EVENTOS[x] + [RECHAZO]))
    if "B" in familias:
        for x in FAMILIA_B:
            out.append((f"e27-B-{x}", f"2 E506 + {x} + E506: ¿{x} reinicia o suma al contador en la v2?",
                        PREP + [RECHAZO] * 2 + EVENTOS[x] + [RECHAZO, RECHAZO]))
    if "O" in familias:
        out.append(("e27-O-orden", "bloqueada: ¿E303, E304 y E401 van antes que E510 en la v2 y suman intentos?",
                    PREP + [RECHAZO] * 3 + EVENTOS["e303"] + EVENTOS["e304"] + EVENTOS["e401"] + [RECHAZO]))
    return out


def main() -> None:
    from starlette.testclient import TestClient

    from app.main import CajaNegra
    from lab.probe import TOKEN, Lab

    familias = sys.argv[1:] or ["A", "B", "O"]
    lab, cli = Lab(), TestClient(CajaNegra())
    h = {"Authorization": f"Bearer {TOKEN}"}
    malos = 0
    for seq, hip, pasos in secuencias(familias):
        if lab.reset(seq, f"reset de e27: {hip}") != 200:
            raise SystemExit(f"{seq}: el reset del original falló; se aborta")
        if cli.post("/__reset", headers=h).status_code != 200:
            raise SystemExit(f"{seq}: el reset del reemplazo falló; se aborta")
        difs = []
        linea = []
        for m in map(firmado, pasos):
            f = lab.msg(m, f"e27 {hip}")
            rr = cli.post("/msg", headers=h, content=json.dumps({"m": m}).encode())
            motivo = comparar_paso(f["status"], como_texto(f["response"]), rr.status_code, rr.text)
            linea.append(str(f["status"]) + ("*" if motivo else ""))
            if motivo:
                difs.append((f["id"], m, f["status"], f["response"], rr.status_code, rr.text))
        print(("DIFERENCIA " if difs else "igual      ") + seq + "  " + " ".join(linea))
        for d in difs:
            print("    ", d)
        malos += bool(difs)
    print(f"e27: {malos} secuencias con diferencias")
    sys.exit(1 if malos else 0)


if __name__ == "__main__":
    main()
