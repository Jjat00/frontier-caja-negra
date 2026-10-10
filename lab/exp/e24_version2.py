"""e24: bordes de los tres cambios de la versión 2 (ticket #FR-0153, confirmada a las 16:00; canario-1600, filas 6040-6081).

1. Límite de TRANSFER: búsqueda binaria entre 40000 (pasa, 6058) y 100000 (E506, 6059). Tras cada E506 un DEPOSITO de 1 al
   origen reinicia el contador de rechazos (MEM-10) para no bloquear la cuenta.
2. Formato del saldo en CONSULTA: string con dos decimales del saldo en centésimas (6052, 6073, 6074). Valores de 1 dígito,
   2 dígitos, negativo (ANULA de un depósito gastado) y de 10+ dígitos.
3. E510: status 423 y campo "intentos" (6065-6067). ¿Sigue más allá de 3? ¿Cuentan E401/E303/E304 o CONSULTA? ¿Se reinicia
   tras desbloquear y volver a bloquear? ¿Es por cuenta?

Uso: uv run python -m lab.exp.e24_version2
"""

import json

from lab.control import firmar as f
from lab.probe import Lab

lab = Lab()


def s(m: str, h: str) -> dict:
    r = lab.msg(f(m), "e24 v2: " + h)
    print(r["id"], m, r["status"], json.dumps(r["response"], ensure_ascii=False))
    return r


def limite() -> None:
    lab.reset("e24-limite", "reset: límite de TRANSFER en la versión 2")
    s("ALTA;Lucia", "cuenta origen")
    s("ALTA;Mateo", "cuenta destino")
    s("DEPOSITO;AC-0001;9999999999", "saldo de sobra para que solo cuente el límite")
    lo, hi = 40000, 100000  # lo pasa (6058), hi da E506 (6059)
    while hi - lo > 1:
        mid = (lo + hi) // 2
        r = s(f"TRANSFER;AC-0001;AC-0002;{mid}", f"búsqueda binaria del límite: {mid} entre {lo} y {hi}")
        if r["status"] == 200:
            lo = mid
        else:
            hi = mid
            s("DEPOSITO;AC-0001;1", "depósito de 1: reinicia el contador de rechazos")
    print("LIMITE: pasa", lo, "· E506 desde", hi)


def saldo() -> None:
    lab.reset("e24-saldo", "reset: formato del saldo en la versión 2")
    s("ALTA;Lucia", "cuenta")
    s("CONSULTA;AC-0001", "saldo 0")
    s("DEPOSITO;AC-0001;5", "saldo de un dígito")
    s("CONSULTA;AC-0001", "saldo 5: ¿«0.05»?")
    s("DEPOSITO;AC-0001;95", "llega a 100")
    s("CONSULTA;AC-0001", "saldo 100: ¿«1.00»?")
    s("ALTA;Mateo", "destino")
    s("TRANSFER;AC-0001;AC-0002;60", "gasta parte del depósito")
    s("ANULA;OP-0002", "anula el depósito de 95: saldo negativo")
    s("CONSULTA;AC-0001", "saldo negativo -55: ¿«-0.55»?")
    s("CONSULTA;AC-0002", "saldo 60: ¿«0.60»?")
    s("DEPOSITO;AC-0002;9999999999", "saldo de 10 dígitos")
    s("CONSULTA;AC-0002", "saldo 10000000059: ¿«100000000.59»?")


def intentos() -> None:
    lab.reset("e24-intentos", "reset: campo intentos de E510 en la versión 2")
    s("ALTA;Lucia", "origen")
    s("ALTA;Mateo", "destino")
    s("ALTA;Ana", "otra cuenta")
    for i in range(3):
        s("TRANSFER;AC-0001;AC-0002;500000", f"rechazo E506 {i + 1} de 3")
    s("TRANSFER;AC-0001;AC-0002;5", "bloqueada: intentos 1")
    s("TRANSFER;AC-0001;AC-0009;5", "E401 con la cuenta bloqueada: ¿cuenta como intento?")
    s("TRANSFER;AC-0001;AC-0002;5", "¿intentos 2 o 3?")
    s("CONSULTA;AC-0001", "CONSULTA de la cuenta bloqueada: ¿cuenta como intento?")
    s("TRANSFER;AC-0001;AC-0002;5", "siguiente intento")
    s("TRANSFER;AC-0001;AC-0002;5", "más allá de 3: ¿sigue contando?")
    s("TRANSFER;AC-0001;AC-0002;5", "siguiente")
    for i in range(3):
        s("TRANSFER;AC-0003;AC-0002;500000", f"otra cuenta, rechazo {i + 1}")
    s("TRANSFER;AC-0003;AC-0002;5", "otra cuenta bloqueada: ¿intentos empieza en 1 (por cuenta)?")
    s("DEPOSITO;AC-0001;1", "desbloquea AC-0001")
    for i in range(3):
        s("TRANSFER;AC-0001;AC-0002;500000", f"re-bloqueo, rechazo {i + 1}")
    s("TRANSFER;AC-0001;AC-0002;5", "tras re-bloquear: ¿intentos vuelve a 1?")


def orden() -> None:
    # Hallazgo de fz3-97 (fila 6573): TRANSFER de 250000 sin saldo da E507 en la versión 2; en la 1, E506 (ERR-49).
    lab.reset("e24-orden", "reset: orden E506/E507 en la versión 2")
    s("ALTA;Lucia", "origen sin saldo")
    s("ALTA;Mateo", "destino")
    s("TRANSFER;AC-0001;AC-0002;60000", "sobre el límite y sin saldo: ¿E507 (saldo antes que límite) o E506?")
    s("DEPOSITO;AC-0001;30000", "saldo parcial")
    s("TRANSFER;AC-0001;AC-0002;60000", "sobre el límite y saldo insuficiente: ¿E507?")


def monto_250000() -> None:
    # fz3-97 (6573): 250000 sin saldo dio E507, pero 60000 sin saldo da E506 (6599). ¿Depende del monto?
    lab.reset("e24-250000", "reset: ¿E507 en vez de E506 según el monto?")
    s("ALTA;Lucia", "origen sin saldo")
    s("ALTA;Mateo", "destino")
    for m in (250000, 200000, 300000, 250001, 249999):
        s(f"TRANSFER;AC-0001;AC-0002;{m}", f"sin saldo, monto {m}: ¿E506 o E507?")
        s("DEPOSITO;AC-0001;1", "reinicia el contador de rechazos")


def mismo_titular() -> None:
    # fz3-97 (6573): origen y destino se llaman «Ana Maria» y 250000 sin saldo dio E507, no E506 (6605: E506 con
    # nombres distintos). Hipótesis: entre cuentas del mismo titular no aplica el límite.
    lab.reset("e24-titular", "reset: límite entre cuentas del mismo nombre")
    s("ALTA;Lucia", "AC-0001 de Lucia")
    s("ALTA;Lucia", "AC-0002 también de Lucia")
    s("ALTA;Mateo", "AC-0003 de Mateo")
    s("TRANSFER;AC-0001;AC-0002;250000", "mismo nombre, sin saldo: ¿E507 (sin límite) o E506?")
    s("DEPOSITO;AC-0001;300000", "saldo de sobra")
    s("TRANSFER;AC-0001;AC-0002;250000", "mismo nombre, con saldo, sobre el límite: ¿pasa?")
    s("TRANSFER;AC-0001;AC-0003;250000", "nombre distinto, con saldo: E506")
    s("DEPOSITO;AC-0001;1", "reinicia el contador")
    s("CONSULTA;AC-0002", "saldo de AC-0002 tras la transferencia entre cuentas propias")


def titular_igualdad() -> None:
    # ¿Cómo compara el nombre del titular? Sin saldo: E507 = sin límite (mismo titular), E506 = con límite.
    lab.reset("e24-titular-b", "reset: igualdad del nombre del titular")
    for n in ("Lucia", "lucia", "Lucia ", "Lucía", "LUCIA"):
        s(f"ALTA;{n}", f"cuenta de «{n}»")
    for i, n in enumerate(("lucia", "Lucia ", "Lucía", "LUCIA"), start=2):
        s(f"TRANSFER;AC-0001;AC-000{i};250000", f"«Lucia» -> «{n}» sin saldo: E507 si cuenta como mismo titular, E506 si no")
        s("DEPOSITO;AC-0001;1", "reinicia el contador de rechazos")


if __name__ == "__main__":
    import sys
    pasos = {"limite": limite, "saldo": saldo, "intentos": intentos, "orden": orden, "monto_250000": monto_250000, "mismo_titular": mismo_titular, "titular_igualdad": titular_igualdad}
    for nombre in sys.argv[1:] or ["limite", "saldo", "intentos"]:
        pasos[nombre]()
