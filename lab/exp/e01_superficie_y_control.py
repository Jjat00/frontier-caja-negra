"""e01: superficie oficial (Phase 1) y qué comandos validan el valor del control.

Hipótesis: solo algunos comandos validan el valor del control (PING no lo hace, ALTA sí).
Se manda cada comando de los ejemplos con su control conocido y con ese control +1,
siempre desde el mismo estado (reset + cuentas creadas como en los ejemplos).
"""
from lab.probe import Lab

lab = Lab()
lab.reset("e01-spec")
for p in ["/openapi.json", "/docs", "/swagger.json", "/llms.txt", "/"]:
    lab.send(None, f"Phase 1: ¿hay especificación oficial en GET {p}?", path=p, method="GET")

def base(seq):
    lab.reset(seq)
    lab.msg("ALTA;Lucia;82", "preparar AC-0001")
    lab.msg("ALTA;Mateo;3", "preparar AC-0002")
    lab.msg("DEPOSITO;AC-0001;250000;86", "preparar saldo y OP-0001")

casos = [
    ("CONSULTA;AC-0001", 14), ("CONSULTA;AC-0002", 11), ("DEPOSITO;AC-0002;700", 35),
    ("TRANSFER;AC-0001;AC-0002;40000", 86), ("ANULA;OP-0001", None),
]
for i, (m, c) in enumerate(casos):
    base(f"e01-valida-{i}")
    otro = 0 if c is None else (c + 1) % 100
    lab.msg(f"{m};{otro:02d}", f"¿{m.split(';')[0]} valida el valor del control? control alterado {otro:02d}")
    if c is not None:
        lab.msg(f"{m};{c}", f"control de los ejemplos ({c}) en el mismo estado")
