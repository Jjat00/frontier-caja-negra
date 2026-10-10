"""e07: borde exacto del límite de TRANSFER, orden de errores dentro de TRANSFER y tope de montos."""
from lab.control import firmar
from lab.probe import Lab

lab = Lab()
def seq(nombre, pasos):
    lab.reset(nombre)
    return [lab.msg(firmar(m), h) for m, h in pasos]

prep = [("ALTA;Ana", "preparar AC-0001"), ("ALTA;Beto", "preparar AC-0002"),
        ("DEPOSITO;AC-0001;900000", "preparar saldo 900000 (OP-0001)")]
lo, hi = 100000, 119999  # 100000 pasa (ejemplo 10), 119999 da E506 (log 805)
lab.reset("e07-limite")
for m, h in prep:
    lab.msg(firmar(m), h)
while hi - lo > 1:
    mid = (lo + hi) // 2
    r = lab.msg(firmar(f"TRANSFER;AC-0001;AC-0002;{mid}"), f"búsqueda binaria del límite: ¿{mid} pasa? (pasa {lo}, falla {hi})")
    # Nota (revisión 11): esta búsqueda quedó INVALIDADA. Tras 3 E506 la cuenta se bloquea (E510) y
    # el else tomaba E510 como éxito. La medición limpia está en e08 (un reset por sonda).
    err = r["response"].get("error")
    if err == "E506":
        hi = mid
    elif "operacionId" in r["response"]:
        lo = mid
    else:
        raise SystemExit(f"respuesta inesperada {r['response']}: abortar (estado contaminado)")
lab.conclude(f"límite: {lo} pasa, {hi} da E506")
print("limite", lo, hi)
seq("e07-orden-transfer", prep + [
    ("TRANSFER;AC-0009;AC-0009;10", "iguales + inexistentes: ¿E304 o E401?"),
    ("TRANSFER;AC-0001;AC-0001;0", "iguales + monto inválido: ¿E304 o E303?"),
    ("TRANSFER;AC-0009;AC-0002;0", "origen inexistente + monto inválido: ¿E401 o E303?"),
    ("TRANSFER;AC-0001;AC-0001;500000", "iguales + límite: ¿E304 o E506?"),
    ("TRANSFER;XYZ;AC-0002;10", "origen sin formato"),
    ("TRANSFER;AC-0002;AC-0001;100000", "saldo 0 y monto en el límite permitido: E507"),
])
seq("e07-montos", prep + [
    ("DEPOSITO;AC-0002;999999999", "9 dígitos"), ("DEPOSITO;AC-0002;9999999999", "10 dígitos"),
    ("DEPOSITO;AC-0002;999999999999999", "15 dígitos"), ("DEPOSITO;AC-0002;9999999999999999", "16 dígitos"),
    ("DEPOSITO;AC-0002;+5", "signo +"), ("DEPOSITO;AC-0002; 5", "espacio delante"),
    ("DEPOSITO;AC-0002;5 ", "espacio detrás"), ("DEPOSITO;AC-0002;1,000", "coma de miles"),
    ("DEPOSITO;AC-0002;0x10", "hexadecimal"), ("DEPOSITO;AC-0002;５", "dígito de ancho completo"),
    ("CONSULTA;AC-0002", "saldo de AC-0002 tras los depósitos"),
])
seq("e07-anula", prep + [
    ("TRANSFER;AC-0001;AC-0002;50000", "OP-0002"), ("TRANSFER;AC-0002;AC-0001;50000", "OP-0003: AC-0002 queda en 0"),
    ("ANULA;OP-0002", "anular OP-0002 deja AC-0002 en -50000: ¿se permite?"), ("CONSULTA;AC-0002", "saldo de AC-0002"),
    ("ANULA;OP-0002", "anular otra vez"), ("ANULA;OP-0003", "anular la otra"),
    ("CONSULTA;AC-0001", "saldo AC-0001"), ("CONSULTA;AC-0002", "saldo AC-0002"),
    ("TRANSFER;AC-0002;AC-0001;1", "con saldo 0 tras anulaciones"),
])
