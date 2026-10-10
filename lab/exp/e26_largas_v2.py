"""e26: diferencial de secuencias largas contra la versión 2 (corrida oficial 2: 99/100, la falla es un test difícil
con status distinto más adelante). Como e21, pero con lo nuevo de la versión 2: titulares repetidos (exención del
límite, CAM-07), montos en el borde de 50000 (CAM-04), CONSULTA en centésimas (CAM-05) y bloqueo con 423 e intentos
(CAM-06), intercalados con depósitos, anulaciones, transferencias entrantes y errores. Perfil v_tarde.

Uso: uv run python -m lab.exp.e26_largas_v2 SEMILLA [N=40]
"""

import json
import os
import random
import sys
import warnings

warnings.filterwarnings("ignore", message=".*httpx.*")
os.environ.setdefault("PERFIL", "v_tarde")

from lab.compare import comparar_paso, como_texto  # noqa: E402
from lab.control import firmar  # noqa: E402


def generar(r: random.Random) -> list[str]:
    nc = r.choice([2, 3, 3, 4])
    # nombres con repeticiones para que haya pares del mismo titular (exención del límite, CAM-07)
    nombres = [r.choice(["Lucia", "Lucia", "Mateo", "Ana Maria", "lucia"]) for _ in range(nc)]
    pasos = [firmar(f"ALTA;{n}") for n in nombres]
    pasos.append(firmar(f"DEPOSITO;AC-0001;{r.choice([1000, 50000, 100000, 150000, 300000])}"))
    ops = 1
    for _ in range(r.randint(6, 12)):
        a = f"AC-000{r.randint(1, nc)}"
        b = f"AC-000{r.randint(1, nc)}"
        while b == a:
            b = f"AC-000{r.randint(1, nc)}"
        k = r.random()
        if k < 0.30:
            m = f"TRANSFER;{a};{b};{r.choice([50001, 60000, 100001, 250000, 999999])}"
        elif k < 0.45:
            m = f"TRANSFER;{a};{b};{r.choice([999, 5000, 49999, 50000, 60000, 100000])}"
            ops += 1
        elif k < 0.55:
            m = f"DEPOSITO;{r.choice([a, b])};{r.choice([1, 5, 99, 700, 100000])}"
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
        if lab.reset(f"e26-{semilla}-{i}", "reset del diferencial largo de la versión 2 (e26)") != 200:
            raise SystemExit(f"e26-{semilla}-{i}: el reset del original falló; se aborta antes del primer paso")
        if cli.post("/__reset", headers=h).status_code != 200:
            raise SystemExit(f"e26-{semilla}-{i}: el reset del reemplazo falló")
        primero = None
        for m in pasos:
            f = lab.msg(m, f"e26 v2 (semilla {semilla}, test {i}): titulares repetidos, límite 50000, saldo en centésimas, 423 con intentos")
            rr = cli.post("/msg", headers=h, content=json.dumps({"m": m}).encode())
            motivo = comparar_paso(f["status"], como_texto(f["response"]), rr.status_code, rr.text)
            if motivo and primero is None:
                primero = (f["id"], m, motivo)
        if primero:
            malos += 1
            print("FALLA", i, primero)
    print(f"e26 semilla {semilla}: {n - malos}/{n} tests iguales")
    sys.exit(1 if malos else 0)


if __name__ == "__main__":
    main()
