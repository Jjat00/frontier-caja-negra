"""e29: ¿el original normaliza el nombre del titular (NFC/NFKC) antes de aplicar la exención por mismo titular (CAM-07)?

Pista: en la corrida 2, el test 83 (índice 0 en los logs HTTP de Railway) hace dos ALTA con nombres cuyo request difiere
en un byte (452 y 453), un depósito y una TRANSFER de 6 cifras; el reemplazo respondió E506. Mayúsculas, tildes y
espacios ya se midieron (log 6626-6637: no exentos), pero no la forma compuesta (NFC) frente a la descompuesta (NFD).
AC-0001 recibe saldo suficiente: si son el mismo titular, la TRANSFER de 100000 da 200; si no, E506.

Uso: uv run python -m lab.exp.e29_titular_unicode
"""

import os
import sys
import unicodedata

os.environ.setdefault("PERFIL", "v_tarde")

from lab.exp import e27_bloqueo_v2 as e27  # noqa: E402

NFC = unicodedata.normalize("NFC", "José Pérez")
NFD = unicodedata.normalize("NFD", "José Pérez")
DEP = "DEPOSITO;AC-0001;200000"
T = "TRANSFER;AC-0001;AC-0002;100000"

SECUENCIAS = [
    ("e29-nfc-nfd", "titular NFC frente a NFD («José Pérez»): ¿mismo titular para la exención?",
     [f"ALTA;{NFC}", f"ALTA;{NFD}", DEP, T, "CONSULTA;AC-0002"]),
    ("e29-nfd-nfc", "titular NFD frente a NFC, orden inverso: ¿mismo titular?",
     [f"ALTA;{NFD}", f"ALTA;{NFC}", DEP, T]),
    ("e29-ligadura", "titular con ligadura «ﬁ» frente a «fi» (NFKC): ¿mismo titular?",
     ["ALTA;Soﬁa", "ALTA;Sofia", DEP, T]),
]


def main() -> None:
    e27.secuencias = lambda _familias: SECUENCIAS
    sys.argv = sys.argv[:1] + ["X"]
    e27.main()


if __name__ == "__main__":
    main()
