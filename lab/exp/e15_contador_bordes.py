"""e15: qué rechazos cuentan para el bloqueo y qué queda del contador tras desbloquear."""
from lab.control import firmar
from lab.probe import Lab

lab = Lab()
prep = [("ALTA;Ana", "preparar AC-0001"), ("ALTA;Beto", "preparar AC-0002"), ("DEPOSITO;AC-0001;900000", "saldo (OP-0001)")]
big = "TRANSFER;AC-0001;AC-0002;500000"
ok = ("TRANSFER;AC-0001;AC-0002;10", "transferencia válida: ¿bloqueada?")
def seq(nombre, pasos):
    lab.reset(nombre)
    for m, h in prep + pasos:
        lab.msg(m if m.startswith("PING") else firmar(m), h)
seq("e15-e303", [("TRANSFER;AC-0001;AC-0002;0", "E303 #1"), ("TRANSFER;AC-0001;AC-0002;0", "E303 #2"),
                 ("TRANSFER;AC-0001;AC-0002;0", "E303 #3: ¿cuenta para el bloqueo?"), ok])
seq("e15-e304", [("TRANSFER;AC-0001;AC-0001;5", "E304 #1"), ("TRANSFER;AC-0001;AC-0001;5", "E304 #2"),
                 ("TRANSFER;AC-0001;AC-0001;5", "E304 #3: ¿cuenta?"), ok])
seq("e15-e401", [("TRANSFER;AC-0001;AC-0009;5", "E401 #1 (destino inexistente)"), ("TRANSFER;AC-0001;AC-0009;5", "E401 #2"),
                 ("TRANSFER;AC-0001;AC-0009;5", "E401 #3: ¿cuenta?"), ok])
seq("e15-post-desbloqueo", [(big, "E506 #1"), (big, "E506 #2"), (big, "E506 #3"), ok, ("DEPOSITO;AC-0001;1", "desbloquear"),
                            (big, "E506 tras desbloquear #1"), ok, (big, "E506 #1 tras éxito"), (big, "E506 #2"),
                            ("DEPOSITO;AC-0001;1", "depósito"), (big, "E506 #1 tras depósito"), (big, "E506 #2"), ok])
seq("e15-mixto", [(big, "E506 #1"), ("TRANSFER;AC-0002;AC-0001;5", "AC-0002 sin saldo: E507 de OTRA cuenta"),
                  ("TRANSFER;AC-0001;AC-0002;9999999", "E506 #2"), ("TRANSFER;AC-0001;AC-0002;900000", "E506 #3 (900000 > límite)"), ok,
                  ("CONSULTA;AC-0002", "saldo AC-0002 tras todo")])
seq("e15-saldo-negativo", [("TRANSFER;AC-0001;AC-0002;100000", "OP-0002"), ("ANULA;OP-0001", "AC-0001 queda en -100000"),
                           ("TRANSFER;AC-0001;AC-0002;1", "E507 con saldo negativo"), ("DEPOSITO;AC-0001;100000", "vuelve a 0"),
                           ("TRANSFER;AC-0001;AC-0002;1", "E507 con saldo 0"), ("DEPOSITO;AC-0001;1", "saldo 1"),
                           ("TRANSFER;AC-0001;AC-0002;1", "saldo exacto 1"), ("CONSULTA;AC-0001", "saldo 0")])
