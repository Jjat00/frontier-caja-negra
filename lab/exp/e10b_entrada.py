"""e10b: resto de la entrada HTTP (#141); e10 se cortó por un header ilegal en el cliente."""
from lab.probe import Lab

lab = Lab()
lab.reset("e10b-entrada")
T = lab.token
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
