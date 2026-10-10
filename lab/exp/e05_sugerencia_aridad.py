"""e05: regla de la sugerencia de E301, segmentos vacíos y aridad de cada comando (todo con control correcto)."""
from lab.control import firmar
from lab.probe import Lab

lab = Lab()
lab.reset("e05-sugerencia")
for cmd, h in [
    ("CONSUL", "distancia 2 de CONSULTA (faltan 2)"), ("CONSULTAS", "distancia 1 (sobra 1)"),
    ("CONSUTLA", "transposición"), ("CONSULTXX", "distancia 2 (sustitución + inserción)"),
    ("CONSULTXY", "sustitución x2"), ("DEPOSIT", "distancia 1 de DEPOSITO"), ("DEPOS", "distancia 3"),
    ("TRANSFERENCIA", "prefijo TRANSFER + sufijo"), ("TRANS", "distancia 3 de TRANSFER"),
    ("ANULAR", "distancia 1 de ANULA"), ("ALT", "distancia 1 de ALTA"), ("AL", "distancia 2 de ALTA"),
    ("A", "distancia 3 de ALTA"), ("PIN", "distancia 1 de PING"), ("PONG", "distancia 1 de PING"),
    ("PINGPONG", "contiene PING"), ("consultb", "minúsculas y distancia 1"), ("SALDO", "SALDOS sin S"),
    ("XXXX", "4 letras sin relación"), ("ALTX", "distancia 1 de ALTA, misma longitud"),
    ("ALZZ", "distancia 2 de ALTA, misma longitud"), ("AÑTA", "carácter no ASCII"),
]:
    lab.msg(firmar(f"{cmd};AC-0001"), f"sugerencia de E301 para '{cmd}': {h}")
lab.reset("e05-aridad")
for m, h in [
    ("ALTA", "ALTA sin nombre (solo comando + control)"), ("ALTA;a;b", "ALTA con 2 argumentos"),
    ("CONSULTA;AC-0001;x", "CONSULTA con 2 argumentos"),
    ("DEPOSITO;AC-0001", "DEPOSITO sin monto"), ("DEPOSITO;AC-0001;5;5", "DEPOSITO con 3 argumentos"),
    ("TRANSFER;AC-0001;AC-0002", "TRANSFER sin monto"), ("TRANSFER;AC-0001;AC-0002;5;5", "TRANSFER con 4 argumentos"),
    ("ANULA", "ANULA sin operación"), ("ANULA;OP-0001;x", "ANULA con 2 argumentos"),
    ("ALTA;;Lucia", "segmento vacío en medio"), ("ALTA; ", "segmento de un espacio"),
]:
    lab.msg(firmar(m), f"aridad o segmentos: {h}")
