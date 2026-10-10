"""e12: bordes de entrada que la revisión 11 marcó sin evidencia: JSON muy anidado y saltos de línea."""
from lab.control import firmar
from lab.probe import Lab

lab = Lab()
lab.reset("e12-bordes")
lab.send(None, "JSON anidado 10000 niveles: ¿E100, E102 o 500?", content="[" * 10000 + "0" + "]" * 10000,
         headers={"Content-Type": "application/json"})
lab.send(None, "JSON objeto anidado 1000 niveles dentro de m", content='{"m":' + '{"a":' * 1000 + '1' + '}' * 1000 + '}',
         headers={"Content-Type": "application/json"})
lab.msg("PING;64", "el servicio sigue respondiendo tras el anidado")
lab.msg(firmar("ALTA;Lucia") + "\n", "ALTA con salto de línea tras el control")
lab.msg("ALTA;Lu\ncia;" + firmar("ALTA;Lucia").rsplit(";", 1)[1], "salto de línea dentro de un argumento")
lab.msg(firmar("PING;x").replace("PING;x;", "PING;"), "PING con control calculado (control normal)")
lab.msg("PING;64", "PING exitoso intercalado (para la regla del contador, ver e12-contador)")
big = firmar("TRANSFER;AC-0001;AC-0002;500000")
lab.reset("e12-contador")
for m, h in [(firmar("ALTA;Ana"), "preparar AC-0001"), (firmar("ALTA;Beto"), "preparar AC-0002"),
             (firmar("DEPOSITO;AC-0001;900000"), "saldo"), (big, "E506 #1"), (big, "E506 #2"),
             ("PING;64", "PING exitoso en medio"), (big, "E506 #3"), (firmar("TRANSFER;AC-0001;AC-0002;10"), "¿bloqueada pese al PING?")]:
    lab.msg(m, h)
lab.reset("e12-orden-e510")
for m, h in [(firmar("ALTA;Ana"), "preparar AC-0001"), (firmar("ALTA;Beto"), "preparar AC-0002"),
             (firmar("DEPOSITO;AC-0001;900000"), "saldo"), (big, "E506 #1"), (big, "E506 #2"), (big, "E506 #3"),
             (firmar("TRANSFER;AC-0001;AC-0001;10"), "bloqueada + iguales: ¿E304 o E510?"),
             (firmar("TRANSFER;AC-0001;AC-0002;0"), "bloqueada + monto inválido: ¿E303 o E510?"),
             (firmar("TRANSFER;AC-0001;AC-0009;10"), "bloqueada + destino inexistente: ¿E401 o E510?"),
             (firmar("TRANSFER;AC-0001;AC-0002;10"), "sigue bloqueada (control)")]:
    lab.msg(m, h)
