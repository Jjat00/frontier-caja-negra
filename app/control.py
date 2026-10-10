"""Dígito de control del original (ISO 7064 MOD 97-10 con A=1). Copia de lab/control.py.

Del mensaje sin el último campo se toman los alfanuméricos (comando incluido; ';', '-' y
espacios se ignoran). Los dígitos quedan igual y cada letra vale su posición en el alfabeto
en decimal (A=1 … Z=26, J -> "10"). Todo se concatena como un número N y el control es
98 - (N*100 mod 97), en decimal sin ceros a la izquierda.
Evidencia: ejemplos 2-19, log 135-140, 153-187, 450, 699-702 (borde 98 frente a 1 y 97 frente a 0).
"""

from __future__ import annotations

import re

# Formato aceptado: uno o dos dígitos ASCII (log 717-724: " 82", "82 ", "+82", "082", "182",
# "-15", "8.2" y "8a" dan E201; ejemplo 17: "5X").
FORMATO = re.compile(r"[0-9]{1,2}")


def calcular(cuerpo: str) -> str:
    # Los caracteres no ASCII se ignoran: medido con "AÑTA" (log 755), "José" (log 771) y "Ñandú"
    # (log 1341); para el resto de Unicode es probable, no medido. Mensaje de 5000 caracteres: log 1184.
    # Resto mod 97 dígito a dígito: equivale a int(N) % 97 sin el límite de 4300 dígitos de
    # int(str) (mensajes largos) y en tiempo lineal.
    resto = 0
    for ch in cuerpo:
        if ch.isascii() and ch.isalnum():
            for d in ch if ch.isdigit() else str(ord(ch.upper()) - 64):
                resto = (resto * 10 + int(d)) % 97
    return str(98 - resto * 100 % 97)


def formato_valido(control: str) -> bool:
    return FORMATO.fullmatch(control) is not None


def valor_valido(cuerpo: str, control: str) -> bool:
    # Comparación de texto: "03" es inválido cuando el correcto es "3" (log 183).
    return calcular(cuerpo) == control
