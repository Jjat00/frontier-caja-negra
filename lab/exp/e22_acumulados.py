"""e22: reglas de riesgo por acumulación (huecos E501-E505, E508, E509 en la numeración). Escenarios largos con
repetición: transferencias de 100000 seguidas, transferencias idénticas, muchos depósitos, muchas cuentas, saldos
enormes y anulaciones encadenadas. Cada escenario va contra original y reemplazo; se imprime cada paso distinto.

Uso: uv run python -m lab.exp.e22_acumulados
"""

import json
import os
import warnings

warnings.filterwarnings("ignore", message=".*httpx.*")
os.environ.setdefault("PERFIL", "v_manana")

from lab.compare import comparar_paso, como_texto  # noqa: E402
from lab.control import firmar as f  # noqa: E402

A2 = [f("ALTA;Lucia"), f("ALTA;Mateo")]
ESCENARIOS = {
    "transferencias de 100000 seguidas (¿límite acumulado?)":
        A2 + [f("DEPOSITO;AC-0001;9999999999")] + [f("TRANSFER;AC-0001;AC-0002;100000")] * 14 + [f("CONSULTA;AC-0001")],
    "transferencia idéntica repetida (¿duplicado?)":
        A2 + [f("DEPOSITO;AC-0001;5000")] + [f("TRANSFER;AC-0001;AC-0002;10")] * 8 + [f("CONSULTA;AC-0002")],
    "depósito idéntico repetido":
        A2 + [f("DEPOSITO;AC-0001;777")] * 12 + [f("CONSULTA;AC-0001")],
    "depósitos de 10 dígitos (saldo enorme)":
        A2 + [f("DEPOSITO;AC-0001;9999999999")] * 6 + [f("CONSULTA;AC-0001"), f("TRANSFER;AC-0001;AC-0002;100000"), f("CONSULTA;AC-0002")],
    "muchas cuentas":
        [f(f"ALTA;N{i}") for i in range(25)] + [f("CONSULTA;AC-0025"), f("CONSULTA;AC-0026")],
    "ida y vuelta entre dos cuentas":
        A2 + [f("DEPOSITO;AC-0001;1000")] + [f("TRANSFER;AC-0001;AC-0002;1000"), f("TRANSFER;AC-0002;AC-0001;1000")] * 6,
    "anulaciones encadenadas y re-anulación":
        A2 + [f("DEPOSITO;AC-0001;1000"), f("TRANSFER;AC-0001;AC-0002;600"), f("ANULA;OP-0001"), f("CONSULTA;AC-0001"),
              f("TRANSFER;AC-0001;AC-0002;100"), f("ANULA;OP-0002"), f("ANULA;OP-0003"), f("CONSULTA;AC-0001"),
              f("CONSULTA;AC-0002"), f("ANULA;OP-0002"), f("DEPOSITO;AC-0002;5"), f("CONSULTA;AC-0002")],
    "rechazos alternando cuentas y tipos":
        A2 + [f("ALTA;Ana"), f("DEPOSITO;AC-0001;10")] + [f("TRANSFER;AC-0001;AC-0002;50"), f("TRANSFER;AC-0002;AC-0003;50"),
              f("TRANSFER;AC-0001;AC-0003;200000")] * 3 + [f("TRANSFER;AC-0001;AC-0002;5"), f("TRANSFER;AC-0002;AC-0001;1")],
    "muchas operaciones pequeñas":
        A2 + [f("DEPOSITO;AC-0001;100")] + [f("TRANSFER;AC-0001;AC-0002;1")] * 20 + [f("CONSULTA;AC-0001")],
}


def main() -> None:
    from starlette.testclient import TestClient

    from app.main import CajaNegra
    from lab.probe import TOKEN, Lab

    lab, cli = Lab(), TestClient(CajaNegra())
    h = {"Authorization": f"Bearer {TOKEN}"}
    for k, (nombre, pasos) in enumerate(ESCENARIOS.items()):
        lab.reset(f"e22-{k}", f"reset: {nombre}")
        cli.post("/__reset", headers=h)
        difs = 0
        for m in pasos:
            fo = lab.msg(m, f"e22 {nombre}: ¿aparece una regla de riesgo por acumulación?")
            rr = cli.post("/msg", headers=h, content=json.dumps({"m": m}).encode())
            motivo = comparar_paso(fo["status"], como_texto(fo["response"]), rr.status_code, rr.text)
            if motivo:
                difs += 1
                if difs <= 3:
                    print(f"  DIF log {fo['id']} {m}: {motivo}")
        print(f"{nombre}: {len(pasos)} pasos, {difs} distintos")


if __name__ == "__main__":
    main()
