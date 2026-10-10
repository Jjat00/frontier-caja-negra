"""e21: diferencial de secuencias largas centradas en el bloqueo (E506/E507 -> E510), con depósitos, anulaciones,
transferencias entrantes, consultas y errores intercalados. En los logs HTTP de la corrida oficial 1 al menos 7 de
los 15 tests largos encadenan tres 422 y un 409. Cada test: reset, preparación y 6 a 12 pasos al azar.

Uso: uv run python -m lab.exp.e21_bloqueo SEMILLA [N=40]
"""

import json
import os
import random
import sys
import warnings

warnings.filterwarnings("ignore", message=".*httpx.*")
os.environ.setdefault("PERFIL", "v_manana")

from lab.compare import comparar_paso, como_texto  # noqa: E402
from lab.control import firmar  # noqa: E402


def generar(r: random.Random) -> list[str]:
    nc = r.choice([2, 3])
    pasos = [firmar(f"ALTA;{n}") for n in ["Lucia", "Mateo", "Ana"][:nc]]
    pasos.append(firmar(f"DEPOSITO;AC-0001;{r.choice([1000, 50000, 100000, 150000])}"))
    ops = 1
    for _ in range(r.randint(6, 12)):
        a = f"AC-000{r.randint(1, nc)}"
        b = f"AC-000{r.randint(1, nc)}"
        while b == a:
            b = f"AC-000{r.randint(1, nc)}"
        k = r.random()
        if k < 0.30:
            m = f"TRANSFER;{a};{b};{r.choice([100001, 120000, 999999])}"
        elif k < 0.45:
            m = f"TRANSFER;{a};{b};{r.choice([999, 5000, 60000, 100000])}"
            ops += 1
        elif k < 0.55:
            m = f"DEPOSITO;{r.choice([a, b])};{r.choice([1, 700, 100000])}"
            ops += 1
        elif k < 0.65:
            m = f"ANULA;OP-{r.randint(1, ops):04d}"
        elif k < 0.75:
            m = f"CONSULTA;{a}"
        elif k < 0.80:
            m = f"TRANSFER;{a};AC-0009;5"
        elif k < 0.84:
            m = f"TRANSFER;{a};{a};5"
        elif k < 0.88:
            m = f"TRANSFER;{a};{b};0"
        elif k < 0.91:
            pasos.append(f"TRANSFER;{a};{b};5;1")  # control casi siempre inválido: E202
            continue
        elif k < 0.94:
            m = r.choice(["NOTAS", f"HALT;{a}", "PING"])
        elif k < 0.97:
            m = f"TRANSFER;{a};{b}"  # aridad
        else:
            m = f"DEPOSITO;{a};-5"
        pasos.append(firmar(m) if not m.startswith("PING") else "PING;1")
    return pasos


def main() -> None:
    from starlette.testclient import TestClient

    from app.main import CajaNegra
    from lab.probe import TOKEN, Lab

    semilla = int(sys.argv[1])
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    r = random.Random(semilla)
    lab, cli = Lab(), TestClient(CajaNegra())
    h = {"Authorization": f"Bearer {TOKEN}"}
    malos = 0
    for i in range(n):
        pasos = generar(r)
        lab.reset(f"e21-{semilla}-{i}", "reset del diferencial de bloqueo e21")
        cli.post("/__reset", headers=h)
        primero = None
        for m in pasos:
            f = lab.msg(m, f"e21 bloqueo (semilla {semilla}, test {i}): rechazos, bloqueo E510, desbloqueo y anulaciones")
            rr = cli.post("/msg", headers=h, content=json.dumps({"m": m}).encode())
            motivo = comparar_paso(f["status"], como_texto(f["response"]), rr.status_code, rr.text)
            if motivo and primero is None:
                primero = (f["id"], m, motivo)
        if primero:
            malos += 1
            print("FALLA", i, primero)
    print(f"e21 semilla {semilla}: {n - malos}/{n} tests iguales")


if __name__ == "__main__":
    main()
