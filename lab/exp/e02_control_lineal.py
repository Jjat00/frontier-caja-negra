"""e02: ¿el control es lineal mod 97 en cada carácter? Peso por posición.

CONSULTA de una cuenta inexistente no cambia el estado: si el control es válido responde E401,
si no, E202. Así se barre sin preparar nada.
"""
import sys
from lab.probe import Lab

lab = Lab()

def ok(r):
    return r["response"].get("error") != "E202" and r["response"].get("error") != "E201"

def barrer(base, hip, desde=0):
    """Barre controles 00..99 hasta el primer válido. Devuelve el control o None."""
    for c in list(range(desde, 100)) + list(range(0, desde)):
        r = lab.msg(f"{base};{c}", f"{hip} (barrido, control {c})")
        if ok(r):
            lab.conclude(f"control válido de {base} = {c}")
            return c
    return None

if sys.argv[1] == "pred":
    lab.reset("e02-pred")
    for m, c, h in [("CONSULTA;AC-0003", 8, "lineal: +1 en el último dígito resta 3 → 14-6=8"),
                    ("CONSULTA;AC-0005", 2, "lineal: 14-12=2"),
                    ("CONSULTA;AC-0006", 96, "lineal mod 97: 14-15=-1 → 96"),
                    ("CONSULTA;AC-0007", 93, "lineal mod 97: 14-18 → 93"),
                    ("ALTA;Mateo;03", None, "¿'03' equivale a '3'? (ejemplo 4 usa '3')")]:
        lab.msg(f"{m};{c:02d}" if c is not None else m, h)
elif sys.argv[1] == "pos":
    lab.reset("e02-pos")
    for m in sys.argv[2:]:
        barrer(m, f"peso por posición: control de {m}")
