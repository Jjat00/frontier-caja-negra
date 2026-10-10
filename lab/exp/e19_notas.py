"""e19: comando oculto NOTAS (sugerido por TOTAL en e18, log 3301): aridad, respuesta, control y estado.
Filas 3478-3501. Uso: uv run python -m lab.exp.e19_notas
"""

# Parte 1 (seq e19-notas)
from lab.control import firmar
from lab.probe import Lab
import json
lab = Lab()
lab.reset("e19-notas", "reset: comando oculto NOTAS (sugerido por TOTAL, log 3301)")
for m, h in [
    (firmar("NOTAS;a;b;c;d;e"), "NOTAS con 5 argumentos: E302 si es comando"),
    (firmar("NOTAS"), "NOTAS con 0 argumentos"),
    (firmar("NOTAS;AC-0001"), "NOTAS con 1 argumento (cuenta inexistente)"),
    (firmar("NOTAS;AC-0001;hola"), "NOTAS con 2 argumentos"),
    (firmar("NOTAS;AC-0001;hola;x"), "NOTAS con 3 argumentos"),
    (firmar("NOTA;a;b;c;d;e"), "NOTA: ¿otro comando relacionado?"),
    (firmar("NOTE;a;b;c;d;e"), "NOTE"), (firmar("NOTES;a;b;c;d;e"), "NOTES"), (firmar("NOTAR;a;b;c;d;e"), "NOTAR"),
]:
    f = lab.msg(m, "e19: " + h); print(f["id"], m, f["status"], json.dumps(f["response"], ensure_ascii=False))

# Parte 2 (seq e19-notas-b)
lab = Lab()
def s(m,h):
    f = lab.msg(m, "e19: " + h); print(f["id"], repr(m), f["status"], json.dumps(f["response"], ensure_ascii=False))
lab.reset("e19-notas-b", "reset: NOTAS tras reset y con estado")
s(firmar("NOTAS"), "NOTAS justo tras reset: misma nota fija")
s("NOTAS;12", "NOTAS con control incorrecto: E202 si valida el control")
s("NOTAS;1X", "NOTAS con control mal formado: E201")
s(firmar("notas"), "notas en minúsculas")
s(firmar("ALTA;Lucia"), "ALTA para ver si NOTAS cambia con el estado")
s(firmar("DEPOSITO;AC-0001;500"), "depósito")
s(firmar("ANULA;OP-0001"), "anulación")
for i in range(3): s(firmar("TRANSFER;AC-0001;AC-0001;5" if i==9 else "TRANSFER;AC-0001;AC-0002;5"), "rechazo E401")
s(firmar("NOTAS"), "NOTAS con estado: ¿cambia?")
s(firmar("HALT;AC-0001"), "HALT E520 (sin confirmar)")
s(firmar("NOTAS"), "NOTAS tras HALT")
