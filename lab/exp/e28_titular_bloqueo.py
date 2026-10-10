"""e28: exención por mismo titular (CAM-07) frente al bloqueo en la versión 2. Ninguna fila anterior lo cubre:
no hay transferencias desde una cuenta bloqueada hacia otra del mismo titular, ni tres rechazos entre cuentas del mismo
titular seguidos de una sonda, ni una exenta exitosa seguida de los rechazos que muestren si reinició el contador.
AC-0001 y AC-0002 son de Lucia; AC-0003, de Mateo. Cada paso se compara con el reemplazo local (perfil v_tarde).

Uso: uv run python -m lab.exp.e28_titular_bloqueo
"""

import os
import sys

os.environ.setdefault("PERFIL", "v_tarde")

from lab.exp import e27_bloqueo_v2 as e27  # noqa: E402

ALTAS = ["ALTA;Lucia", "ALTA;Lucia", "ALTA;Mateo"]
DEP = "DEPOSITO;AC-0001;200000"
E506_OTRO = "TRANSFER;AC-0001;AC-0003;60000"  # E506: titular distinto, sobre el límite

SECUENCIAS = [
    ("e28-e507-mismo-pequeno", "3 E507 entre cuentas del mismo titular (montos pequeños): ¿bloquean?",
     ALTAS + ["TRANSFER;AC-0001;AC-0002;999"] * 3 + ["TRANSFER;AC-0001;AC-0002;999", E506_OTRO]),
    ("e28-e507-mismo-grande", "3 E507 exentos del límite (más de 50000, mismo titular): ¿bloquean?",
     ALTAS + ["TRANSFER;AC-0001;AC-0002;60000"] * 3 + ["TRANSFER;AC-0001;AC-0002;60000", E506_OTRO]),
    ("e28-bloq-exenta-grande", "bloqueada por E506 a otro titular: ¿puede transferir más de 50000 al mismo titular?",
     ALTAS + [DEP] + [E506_OTRO] * 3 + ["TRANSFER;AC-0001;AC-0002;60000", "TRANSFER;AC-0001;AC-0002;10"]),
    ("e28-bloq-mismo-pequeno", "bloqueada: ¿puede transferir 10 al mismo titular?",
     ALTAS + [DEP] + [E506_OTRO] * 3 + ["TRANSFER;AC-0001;AC-0002;10", "TRANSFER;AC-0001;AC-0003;10"]),
    ("e28-exenta-reinicia", "2 E506 + exenta exitosa (60000 al mismo titular) + E506: ¿la exenta reinicia el contador?",
     ALTAS + [DEP] + [E506_OTRO] * 2 + ["TRANSFER;AC-0001;AC-0002;60000", E506_OTRO, E506_OTRO]),
    ("e28-mezcla", "2 E506 a otro titular + 1 E507 al mismo titular: ¿suman al mismo contador?",
     ALTAS + [E506_OTRO] * 2 + ["TRANSFER;AC-0001;AC-0002;999", E506_OTRO]),
]


def main() -> None:
    e27.secuencias = lambda _familias: SECUENCIAS
    sys.argv = sys.argv[:1] + ["X"]
    e27.main()


if __name__ == "__main__":
    main()
