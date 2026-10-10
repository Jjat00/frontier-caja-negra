"""e08: límite de TRANSFER con un reset por sonda y reglas del bloqueo E510."""
from lab.control import firmar
from lab.probe import Lab

lab = Lab()
prep = [("ALTA;Ana", "preparar AC-0001"), ("ALTA;Beto", "preparar AC-0002"),
        ("DEPOSITO;AC-0001;900000", "preparar saldo 900000 (OP-0001)")]
def seq(nombre, pasos, con_prep=True):
    lab.reset(nombre)
    # PING va tal cual: firmarlo lo convierte en PING;64;95 (E302, log 978; revisión 11)
    return [lab.msg(m if m.startswith("PING") else firmar(m), h) for m, h in (prep if con_prep else []) + pasos]

lo, hi = 100000, 102499
n = 0
while hi - lo > 1:
    mid = (lo + hi) // 2; n += 1
    r = seq(f"e08-limite-{n}", [(f"TRANSFER;AC-0001;AC-0002;{mid}", f"límite desde estado limpio: ¿{mid} pasa? (pasa {lo}, falla {hi})")])[-1]
    if r["response"].get("error") == "E506": hi = mid
    else: lo = mid
lab.conclude(f"límite por transferencia: {lo} pasa, {hi} da E506")
print("limite", lo, hi)
big = "TRANSFER;AC-0001;AC-0002;500000"
seq("e08-bloqueo-a", [(big, "E506 #1"), (big, "E506 #2"), (big, "E506 #3"),
    ("TRANSFER;AC-0001;AC-0002;10", "tras 3 E506: transferencia válida pequeña ¿E510?"),
    ("DEPOSITO;AC-0001;10", "¿depositar en cuenta bloqueada?"), ("CONSULTA;AC-0001", "¿consultar cuenta bloqueada?"),
    ("TRANSFER;AC-0002;AC-0001;1", "¿transferir HACIA la cuenta bloqueada? (AC-0002 sin saldo)"),
    ("DEPOSITO;AC-0002;100", "saldo para AC-0002 (OP-?)"), ("TRANSFER;AC-0002;AC-0001;1", "transferir hacia la bloqueada con saldo"),
    ("ANULA;OP-0001", "¿anular el depósito de la bloqueada?"), ("TRANSFER;AC-0001;AC-0001;10", "bloqueada + iguales: ¿E304 o E510?"),
    ("TRANSFER;AC-0001;AC-0002;0", "bloqueada + monto inválido"), ("TRANSFER;AC-0001;AC-0009;10", "bloqueada + destino inexistente")])
seq("e08-bloqueo-b", [(big, "E506 #1"), (big, "E506 #2"), ("PING;64", "un PING en medio"), (big, "E506 #3 tras PING"),
    ("TRANSFER;AC-0001;AC-0002;10", "¿bloqueada si el PING no reinicia el contador?")])
seq("e08-bloqueo-c", [(big, "E506 #1"), (big, "E506 #2"), ("DEPOSITO;AC-0001;5", "depósito en medio"), (big, "E506 #3 tras depósito"),
    ("TRANSFER;AC-0001;AC-0002;10", "¿bloqueada si el depósito no reinicia?")])
seq("e08-bloqueo-d", [(big, "E506 #1"), (big, "E506 #2"), ("TRANSFER;AC-0001;AC-0002;10", "transferencia exitosa en medio"),
    (big, "E506 #3 tras éxito"), ("TRANSFER;AC-0001;AC-0002;10", "¿bloqueada?")])
seq("e08-bloqueo-e", [("DEPOSITO;AC-0002;900000", "saldo AC-0002"), (big, "AC-0001 E506 #1"), (big, "AC-0001 E506 #2"),
    ("TRANSFER;AC-0002;AC-0001;500000", "AC-0002 E506: ¿contador por cuenta o global?"),
    ("TRANSFER;AC-0001;AC-0002;10", "AC-0001: ¿bloqueada?"), ("TRANSFER;AC-0002;AC-0001;10", "AC-0002: ¿bloqueada?")])
seq("e08-bloqueo-f", [("TRANSFER;AC-0002;AC-0001;10", "E507 #1"), ("TRANSFER;AC-0002;AC-0001;10", "E507 #2"),
    ("TRANSFER;AC-0002;AC-0001;10", "E507 #3"), ("TRANSFER;AC-0002;AC-0001;10", "¿E507 cuenta para bloquear?"),
    (big, "E506 #1"), (big, "E506 #2"), ("TRANSFER;AC-0001;AC-0009;10", "E401 en medio"), (big, "E506 #3"),
    ("TRANSFER;AC-0001;AC-0002;10", "¿bloqueada si E401 no reinicia?")])
