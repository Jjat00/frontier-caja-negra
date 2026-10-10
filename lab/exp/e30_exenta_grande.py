"""e30: transferencias exentas (mismo titular, CAM-07) de montos grandes. La exención solo se ha visto funcionar hasta
250000 (log 6621, 7343). En la corrida 2, el test 95 (índice 0 en los logs HTTP de Railway) hace dos ALTA del mismo
tamaño, dos depósitos y dos TRANSFER cuyo request mide lo de un monto de 10 cifras, dos ANULA y dos CONSULTA.
Se imita esa forma y se buscan topes en escalones (1e6, 1e7, 1e9, 10 dígitos).

Uso: uv run python -m lab.exp.e30_exenta_grande
"""

import os
import sys

os.environ.setdefault("PERFIL", "v_tarde")

from lab.exp import e27_bloqueo_v2 as e27  # noqa: E402

MISMOS = ["ALTA;Ana", "ALTA;Ana"]
SECUENCIAS = [
    ("e30-forma-test95", "mismo titular, depósitos y TRANSFER de 10 cifras, ANULA de ambas: ¿algún tope?",
     MISMOS + ["DEPOSITO;AC-0001;9999999999", "DEPOSITO;AC-0002;9999999999",
               "TRANSFER;AC-0001;AC-0002;9999999999", "TRANSFER;AC-0002;AC-0001;9999999999",
               "ANULA;OP-0003", "ANULA;OP-0004", "CONSULTA;AC-0001", "CONSULTA;AC-0002"]),
    ("e30-escalones", "mismo titular con saldo de 10 cifras: exentas de 1e6, 1e7 y 1e9",
     MISMOS + ["DEPOSITO;AC-0001;9999999999", "TRANSFER;AC-0001;AC-0002;1000000",
               "TRANSFER;AC-0001;AC-0002;10000000", "TRANSFER;AC-0001;AC-0002;1000000000", "CONSULTA;AC-0002"]),
]


def main() -> None:
    e27.secuencias = lambda _familias: SECUENCIAS
    sys.argv = sys.argv[:1] + ["X"]
    e27.main()


if __name__ == "__main__":
    main()
