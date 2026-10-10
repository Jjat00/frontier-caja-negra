"""e25: cómo se «reenvía con confirmación» HALT (E520). Autorizado por Jaime a las 16:45 tras la corrida 2 (99/100):
el único test largo con HALT (test 92 en los logs HTTP del reemplazo) tiene un 400 del reemplazo justo después del 409.
MATERIAL.md: «Cada token tiene su propio estado» y «Nada de lo que hagas con tu token es irreversible: POST /__reset lo
repara». De menos a más riesgo. Tras cada sonda que no responde 409 E520 (las de dos argumentos), PING y CONSULTA para ver
si el servicio sigue vivo; las que dan E520 no llevan comprobación intermedia. Reset, PING y ALTA al final.

Uso: uv run python -m lab.exp.e25_halt_confirmacion
"""

import json
import sys

from lab.control import firmar as f
from lab.probe import Lab

lab = Lab()


def ver(r: dict) -> None:
    print(r["id"], r.get("ruta", ""), repr(r["request"])[:70], r["status"], json.dumps(r["response"], ensure_ascii=False)[:150])


def vivo(etiqueta: str) -> bool:
    a = lab.msg("PING;64", f"e25: ¿el servicio sigue respondiendo tras {etiqueta}?")
    b = lab.msg(f("CONSULTA;AC-0001"), f"e25: ¿el estado sigue tras {etiqueta}?")
    ver(a); ver(b)
    return a["status"] == 200 and b["status"] == 200


def sonda_msg(m: str, h: str) -> bool:
    r = lab.msg(f(m), "e25 HALT: " + h); ver(r)
    return vivo(m) if r["status"] != 409 or "E520" not in json.dumps(r["response"]) else True


def sonda_cuerpo(cuerpo: dict, h: str, headers: dict | None = None) -> bool:
    r = lab.send(None, "e25 HALT: " + h, content=json.dumps(cuerpo).encode(),
                 headers={"Content-Type": "application/json", **(headers or {})}); ver(r)
    return vivo(h) if r["status"] != 409 or "E520" not in json.dumps(r["response"]) else True


lab.reset("e25-halt", "reset: confirmación de HALT")
ver(lab.msg(f("ALTA;Lucia"), "e25: cuenta para ver el estado"))
ver(lab.msg(f("HALT;AC-0001"), "e25: HALT normal, E520 como siempre"))
fases = [
    # 1. dos argumentos: lo más probable es E302 (aridad), sin efecto
    lambda: sonda_msg("HALT;AC-0001;CONFIRMAR", "segundo argumento CONFIRMAR"),
    lambda: sonda_msg("HALT;AC-0001;SI", "segundo argumento SI"),
    lambda: sonda_msg("HALT;AC-0001;CONFIRMO", "segundo argumento CONFIRMO"),
    # 2. la confirmación fuera de m: campo del JSON o header
    lambda: sonda_cuerpo({"m": f("HALT;AC-0001"), "confirmar": True}, "campo confirmar:true en el JSON"),
    lambda: sonda_cuerpo({"m": f("HALT;AC-0001"), "confirmacion": True}, "campo confirmacion:true en el JSON"),
    lambda: sonda_cuerpo({"m": f("HALT;AC-0001"), "confirm": True}, "campo confirm:true en el JSON"),
    lambda: sonda_cuerpo({"m": f("HALT;AC-0001")}, "header X-Confirm: true", {"X-Confirm": "true"}),
    lambda: sonda_cuerpo({"m": f("HALT;AC-0001")}, "header X-Confirmacion: true", {"X-Confirmacion": "true"}),
    # 3. un argumento con valor de confirmación: puede detener algo
    lambda: sonda_msg("HALT;CONFIRMAR", "argumento CONFIRMAR"),
    lambda: sonda_msg("HALT;CONFIRMO", "argumento CONFIRMO"),
    lambda: sonda_msg("HALT;SI", "argumento SI"),
    lambda: sonda_msg("HALT;CONFIRM", "argumento CONFIRM"),
    lambda: sonda_msg("HALT;YES", "argumento YES"),
]
for i, fase in enumerate(fases):
    if not fase():
        print(f"\n>>> cambio de comportamiento en la sonda {i + 1}: se detiene la serie")
        break
print("reset final:", lab.reset("e25-halt-fin", "reset tras las sondas de HALT: ¿repara el estado?"))
ver(lab.msg("PING;64", "e25: PING tras el reset final"))
ver(lab.msg(f("ALTA;Lucia"), "e25: ALTA tras el reset final: ¿AC-0001 y servicio normal?"))
sys.exit(0)
