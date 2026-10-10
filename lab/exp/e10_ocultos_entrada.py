"""e10: comandos ocultos (#139), variantes de entrada HTTP (#141) y tope de dígitos del monto."""
from lab.control import firmar
from lab.probe import Lab

lab = Lab()
lab.reset("e10-ocultos")
lab.msg(firmar("ALTA;Ana"), "preparar AC-0001")
for c in ["RETIRO", "CIERRE", "BAJA", "HISTORIAL", "EXTRACTO", "BLOQUEO", "DESBLOQUEO", "PAGO", "MOVIMIENTOS",
          "SALDO", "LISTA", "HELP", "AYUDA", "ECHO", "STATUS", "ESTADO", "INFO", "VERSION", "RESET", "LOGIN",
          "CUENTAS", "RETIRAR", "DEBITO", "CREDITO", "REVERSA", "LIMITE", "AUDIT", "LOG", "TIME", "HORA"]:
    lab.msg(firmar(f"{c};AC-0001"), f"¿existe el comando oculto {c}? (1 argumento)")
lab.reset("e10-montos")
lab.msg(firmar("ALTA;Ana"), "preparar AC-0001")
for d in range(11, 15):
    lab.msg(firmar(f"DEPOSITO;AC-0001;{'9' * d}"), f"tope de dígitos del monto: {d} nueves")
lab.msg(firmar("DEPOSITO;AC-0001;10000000000"), "11 dígitos con valor 1e10")
lab.msg(firmar("CONSULTA;AC-0001"), "saldo tras los depósitos grandes")
lab.reset("e10-entrada")
T = lab.token
for h, kw in [
    ("Bearer en minúsculas", dict(headers={"Authorization": f"bearer {T}"}, token=None, auth="bearer_minuscula")),
    ("esquema Token", dict(headers={"Authorization": f"Token {T}"}, token=None, auth="esquema_token")),
    ("token sin esquema", dict(headers={"Authorization": T}, token=None, auth="sin_esquema")),
    ("doble espacio tras Bearer", dict(headers={"Authorization": f"Bearer  {T}"}, token=None, auth="doble_espacio")),
    ("espacio al final del token", dict(headers={"Authorization": f"Bearer {T} "}, token=None, auth="espacio_final")),
]:
    lab.send({"m": "PING;64"}, f"auth: {h}", **kw)
for meth in ["PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]:
    lab.send(None, f"método {meth} sobre /msg", path="/msg", method=meth)
lab.send(None, "GET /__reset", path="/__reset", method="GET")
lab.send(None, "POST /health", path="/health", method="POST")
lab.send({"m": "PING;64"}, "ruta en mayúsculas /MSG", path="/MSG")
lab.send({"m": "PING;64"}, "ruta con barra final /msg/", path="/msg/")
lab.send({"m": "PING;64"}, "ruta con query /msg?x=1", path="/msg?x=1")
lab.send({"m": "PING;64"}, "/__reset con token inválido", path="/__reset", token="xxx", auth="token_invalido")
for body, h in [('{"m":"PING;64"', "JSON truncado"), ('[{"m":"PING;64"}]', "array"), ('{"m":64}', "m numérico"),
                ('{"m":null}', "m null"), ('{"m":["PING;64"]}', "m array"), ('{"m":"PING;64","x":1}', "clave extra"),
                ('"PING;64"', "string JSON suelto"), ("", "cuerpo vacío"), ('{"M":"PING;64"}', "clave en mayúsculas"),
                ('{"m":"PING;64"} ', "espacio tras el JSON"), ('{"m":true}', "m booleano")]:
    lab.send(None, f"cuerpo: {h}", content=body, headers={"Content-Type": "application/json"})
lab.send(None, "Content-Type text/plain con JSON válido", content='{"m":"PING;64"}', headers={"Content-Type": "text/plain"})
lab.send(None, "PING;64 crudo sin JSON", content="PING;64", headers={"Content-Type": "text/plain"})
lab.msg("PING;64\n", "salto de línea al final")
lab.msg("PING|64", "otro separador")
lab.msg("A" * 5000 + ";64", "m de 5000 caracteres")
