"""e04: orden de evaluación de errores con fallas simultáneas y formas raras del control.

Todos los mensajes salen del mismo estado (reset) y no crean nada, salvo que se diga.
"""
from lab.control import control, firmar
from lab.probe import Lab

lab = Lab()
lab.reset("e04-orden")
mal = lambda b: f"{b};{(int(control(b)) % 97) + 1}"  # control con valor incorrecto
casos = [
    # aridad vs valor del control
    (mal("ALTA;Lucia;Gomez"), "aridad mala + control incorrecto: ¿E302 o E202?"),
    (firmar("ALTA;Lucia;Gomez"), "aridad mala + control correcto: E302 esperado"),
    (mal("CONSULTA"), "CONSULTA sin argumentos + control incorrecto"),
    (firmar("CONSULTA"), "CONSULTA sin argumentos + control correcto"),
    # comando desconocido vs aridad
    (firmar("FOO;a;b;c;d"), "comando desconocido + muchos campos, control correcto"),
    (mal("FOO;a;b;c;d"), "comando desconocido + control incorrecto"),
    # formato del control vs comando y aridad
    ("FOO;x;5X", "comando desconocido + control mal formado: ¿E301 o E201?"),
    ("ALTA;a;b;5X", "aridad mala + control mal formado: ¿E302 o E201?"),
    ("CONSULTA;5X", "aridad mala (sin cuenta) + control mal formado"),
    # formas del control
    ("ALTA;Lucia;", "control vacío tras ;"),
    ("ALTA;Lucia", "sin control: el último campo es Lucia"),
    ("ALTA", "un solo campo"),
    (";82", "comando vacío con control"),
    ("ALTA;Lucia; 82", "control con espacio delante"),
    ("ALTA;Lucia;82 ", "control con espacio detrás"),
    ("ALTA;Lucia;+82", "control con signo +"),
    ("ALTA;Lucia;082", "control con cero a la izquierda (3 dígitos)"),
    ("ALTA;Lucia;182", "control de 3 dígitos"),
    ("ALTA;Lucia;-15", "control negativo"),
    ("ALTA;Lucia;8.2", "control decimal"),
    ("ALTA;Lucia;8a", "control alfanumérico distinto de 5X"),
    # PING
    ("PING", "PING sin control"),
    ("PING;", "PING con control vacío"),
    ("PING;5X", "PING con control mal formado: ¿valida el formato?"),
    ("PING;100", "PING con control de 3 dígitos"),
    ("PING;a;64", "PING con un argumento de más"),
    ("ping;64", "comando en minúsculas"),
    (" PING;64", "espacio antes del comando"),
    ("PING ;64", "espacio después del comando"),
]
for m, h in casos:
    lab.msg(m, h)
