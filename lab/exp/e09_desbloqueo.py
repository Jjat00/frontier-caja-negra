"""e09: qué desbloquea una cuenta y qué reinicia el contador de rechazos."""
from lab.control import firmar
from lab.probe import Lab

lab = Lab()
prep = [("ALTA;Ana", "preparar AC-0001"), ("ALTA;Beto", "preparar AC-0002"),
        ("DEPOSITO;AC-0001;900000", "preparar saldo 900000 (OP-0001)")]
big = "TRANSFER;AC-0001;AC-0002;500000"
tres = [(big, "E506 #1"), (big, "E506 #2"), (big, "E506 #3")]
ok = ("TRANSFER;AC-0001;AC-0002;10", "transferencia válida: ¿bloqueada?")
def seq(nombre, pasos):
    lab.reset(nombre)
    for m, h in prep + pasos:
        lab.msg(firmar(m) if not m.startswith("PING") else m, h)

seq("e09-desbloqueo-deposito", tres + [ok, ("DEPOSITO;AC-0001;5", "depositar en la bloqueada"), ok])
seq("e09-desbloqueo-entrante", tres + [("DEPOSITO;AC-0002;100", "saldo a AC-0002"),
    ("TRANSFER;AC-0002;AC-0001;5", "transferencia entrante a la bloqueada"), ok])
seq("e09-desbloqueo-anula", tres + [("ANULA;OP-0001", "anular un depósito de la bloqueada"), ok])
seq("e09-e510-cuenta", tres + [ok, ok, ok, ok, ("DEPOSITO;AC-0001;5", "depósito tras 4 E510"), ok])
seq("e09-contador-consulta", [(big, "E506 #1"), (big, "E506 #2"), ("CONSULTA;AC-0001", "CONSULTA en medio"), (big, "E506 #3"), ok])
seq("e09-contador-anula", [("TRANSFER;AC-0001;AC-0002;10", "OP-0002"), (big, "E506 #1"), (big, "E506 #2"),
    ("ANULA;OP-0002", "ANULA de una transfer de AC-0001 en medio"), (big, "E506 #3"), ok])
seq("e09-contador-entrante", [("DEPOSITO;AC-0002;100", "saldo a AC-0002"), (big, "E506 #1"), (big, "E506 #2"),
    ("TRANSFER;AC-0002;AC-0001;5", "transferencia entrante en medio"), (big, "E506 #3"), ok])
seq("e09-contador-e304", [(big, "E506 #1"), (big, "E506 #2"), ("TRANSFER;AC-0001;AC-0001;5", "E304 en medio"),
    ("TRANSFER;AC-0001;AC-0002;0", "E303 en medio"), (big, "E506 #3"), ok])
seq("e09-alta", tres + [("ALTA;Caro", "ALTA tras bloqueo: ¿AC-0003?"), ok])
