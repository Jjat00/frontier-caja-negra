"""e06: validación de argumentos y reglas de negocio por comando (matriz M3)."""
from lab.control import firmar
from lab.probe import Lab

lab = Lab()

def seq(nombre, pasos):
    lab.reset(nombre)
    for m, h in pasos:
        lab.msg(firmar(m), h)

prep = [("ALTA;Ana", "preparar AC-0001"), ("ALTA;Beto", "preparar AC-0002"),
        ("DEPOSITO;AC-0001;100000", "preparar saldo 100000 en AC-0001 (OP-0001)")]

seq("e06-alta", [
    ("ALTA;123", "nombre numérico"), ("ALTA;Ana Maria", "nombre con espacio"), ("ALTA;José", "nombre con tilde"),
    ("ALTA;" + "x" * 200, "nombre de 200 caracteres"), ("ALTA;a-b", "nombre con guion"),
    ("ALTA;Ana", "nombre repetido"), ("ALTA;Ana", "nombre repetido otra vez"),
    ("CONSULTA;AC-0002", "la cuenta del nombre con espacio existe"),
    ("CONSULTA;ac-0001", "id de cuenta en minúsculas"), ("CONSULTA;AC-1", "id sin ceros"),
    ("CONSULTA;AC-00001", "id con 5 dígitos"), ("CONSULTA;OP-0001", "id de operación como cuenta"),
    ("CONSULTA;XYZ", "id sin formato"), ("CONSULTA;AC-0000", "cuenta 0"),
])
seq("e06-deposito", prep + [
    ("DEPOSITO;AC-0001;0", "monto 0"), ("DEPOSITO;AC-0001;-5", "monto negativo"),
    ("DEPOSITO;AC-0001;5.5", "monto decimal"), ("DEPOSITO;AC-0001;007", "monto con ceros a la izquierda"),
    ("DEPOSITO;AC-0001;abc", "monto no numérico"), ("DEPOSITO;AC-0001;1e3", "monto en notación científica"),
    ("DEPOSITO;AC-0001;99999999999999999999", "monto enorme"), ("DEPOSITO;AC-0001;120000", "depósito igual al límite de transfer"),
    ("DEPOSITO;AC-0001;1000000", "depósito de un millón"), ("DEPOSITO;AC-0009;100", "depósito a cuenta inexistente"),
    ("DEPOSITO;XYZ;100", "depósito a cuenta sin formato"), ("DEPOSITO;AC-0009;abc", "cuenta inexistente + monto inválido: ¿cuál primero?"),
    ("CONSULTA;AC-0001", "saldo tras todo lo anterior"), ("DEPOSITO;AC-0001;1", "¿qué OP sale? ¿los fallidos consumen número?"),
])
seq("e06-transfer", prep + [
    ("TRANSFER;AC-0001;AC-0002;119999", "límite: 119999 (saldo 100000 insuficiente) ¿E506 o E507?"),
    ("DEPOSITO;AC-0001;200000", "subir saldo a 300000"),
    ("TRANSFER;AC-0001;AC-0002;119999", "119999 con saldo suficiente"),
    ("TRANSFER;AC-0001;AC-0002;120000", "120000: borde del límite"),
    ("TRANSFER;AC-0001;AC-0002;120001", "120001"),
    ("TRANSFER;AC-0001;AC-0001;10", "transferencia a la misma cuenta"),
    ("TRANSFER;AC-0001;AC-0009;10", "destino inexistente"), ("TRANSFER;AC-0009;AC-0001;10", "origen inexistente"),
    ("TRANSFER;AC-0008;AC-0009;10", "ambas inexistentes"),
    ("TRANSFER;AC-0001;AC-0002;0", "monto 0"), ("TRANSFER;AC-0001;AC-0002;-1", "monto negativo"),
    ("TRANSFER;AC-0001;AC-0002;1.5", "monto decimal"), ("TRANSFER;AC-0009;AC-0002;500000", "origen inexistente + límite"),
    ("TRANSFER;AC-0002;AC-0001;500000", "saldo insuficiente + límite: ¿E506 o E507?"),
    ("CONSULTA;AC-0001", "saldo origen"), ("CONSULTA;AC-0002", "saldo destino"),
])
seq("e06-transfer-saldo", prep + [
    ("TRANSFER;AC-0001;AC-0002;100000", "saldo exacto: transferir todo"),
    ("CONSULTA;AC-0001", "debe quedar 0"), ("TRANSFER;AC-0001;AC-0002;1", "sin saldo"),
])
seq("e06-anula", prep + [
    ("TRANSFER;AC-0001;AC-0002;30000", "OP-0002"),
    ("ANULA;OP-0001", "anular el depósito OP-0001 con saldo 70000 (dejaría -30000)"),
    ("CONSULTA;AC-0001", "¿saldo negativo?"), ("ANULA;OP-0009", "operación inexistente"),
    ("ANULA;XYZ", "id sin formato"), ("ANULA;op-0002", "id en minúsculas"), ("ANULA;AC-0001", "id de cuenta"),
    ("ANULA;OP-0002", "anular la transferencia"), ("CONSULTA;AC-0002", "destino tras anular"),
    ("CONSULTA;AC-0001", "origen tras anular"), ("DEPOSITO;AC-0002;5", "¿siguiente OP tras anulaciones?"),
])
