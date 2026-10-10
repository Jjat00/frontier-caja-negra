"""e16: cerrar supuestos de la especificación: tope del monto en TRANSFER, HALT en minúsculas y bloqueo con E506/E507 mezclados."""
from lab.control import firmar
from lab.probe import Lab

lab = Lab()
prep = [("ALTA;Ana", "preparar AC-0001"), ("ALTA;Beto", "preparar AC-0002"), ("DEPOSITO;AC-0001;900000", "saldo (OP-0001)")]
def seq(nombre, pasos):
    lab.reset(nombre)
    for m, h in prep + pasos:
        lab.msg(firmar(m), h)
seq("e16-monto-transfer", [("TRANSFER;AC-0001;AC-0002;10000000000", "TRANSFER con 11 dígitos: ¿E303 como en DEPOSITO o E506?"),
                           ("TRANSFER;AC-0001;AC-0002;9999999999", "TRANSFER con 10 dígitos: E506 (pasa el formato)"),
                           ("halt;AC-0001", "HALT en minúsculas: ¿E520 como HALT?")])
seq("e16-mixto-506-507", [("TRANSFER;AC-0002;AC-0001;500000", "AC-0002 E506 #1"), ("TRANSFER;AC-0002;AC-0001;5", "AC-0002 E507 #2 (saldo 0)"),
                          ("TRANSFER;AC-0002;AC-0001;500000", "AC-0002 E506 #3: ¿bloquea la mezcla?"),
                          ("DEPOSITO;AC-0002;100", "saldo a AC-0002 (desbloquea si estaba bloqueada)"),
                          ("TRANSFER;AC-0002;AC-0001;5", "¿pasa? (tras el depósito siempre debería)"),
                          ("TRANSFER;AC-0002;AC-0001;500000", "E506 #1"), ("TRANSFER;AC-0002;AC-0001;99999", "E507 #2"),
                          ("TRANSFER;AC-0002;AC-0001;500000", "E506 #3"), ("TRANSFER;AC-0002;AC-0001;5", "¿bloqueada por la mezcla E506/E507/E506?")])
