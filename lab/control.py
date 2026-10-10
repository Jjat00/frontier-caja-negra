"""Dígito de control del original (log 699-702 y e02): ISO 7064 MOD 97-10 con A=1.

Del mensaje sin el último campo se toman los alfanuméricos ASCII; las letras valen su posición
en el alfabeto (en decimal, J=10) y el control es 98 - (N*100 mod 97), sin ceros a la izquierda.
El resto se calcula dígito a dígito para aceptar mensajes de cualquier largo (log 1184).
"""


def control(cuerpo: str) -> str:
    resto = 0
    for ch in cuerpo:
        if not (ch.isascii() and ch.isalnum()):
            continue
        for d in ch if ch.isdigit() else str(ord(ch.upper()) - 64):
            resto = (resto * 10 + int(d)) % 97
    return str(98 - resto * 100 % 97)


def firmar(cuerpo: str) -> str:
    return f"{cuerpo};{control(cuerpo)}"
