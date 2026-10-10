"""Estado en memoria y comandos como manejadores puros (estado, args) -> (status, cuerpo, estado').

Ningún manejador muta el estado que recibe: devuelve uno nuevo (o el mismo si no hubo cambio).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from app import catalogo as cat


@dataclass(frozen=True)
class Operacion:
    tipo: str                 # "DEPOSITO" o "TRANSFER"
    destino: str              # cuenta que recibió el dinero
    monto: int
    origen: str | None = None  # solo en TRANSFER
    anulada: bool = False


@dataclass(frozen=True)
class Estado:
    cuentas: dict[str, int] = field(default_factory=dict)          # id -> saldo
    operaciones: dict[str, Operacion] = field(default_factory=dict)
    sig_cuenta: int = 1   # AC-0001 tras reset (ejemplo 3; log 135, 139)
    sig_op: int = 1       # OP-0001 tras reset (ejemplo 6; log 152)
    rechazos: dict[str, int] = field(default_factory=dict)  # rechazos seguidos de TRANSFER por origen
    bloqueadas: frozenset[str] = frozenset()                 # cuentas con E510


Resultado = tuple[int, dict, Estado]

# Monto: entero positivo sin ceros a la izquierda ni signo (log 872-886: 0, -5, 007, +5, 1e3,
# 1,000, 0x10, espacios y dígitos de ancho completo dan E303). 10 dígitos pasan (log 877) y 11 dan
# E303 en DEPOSITO (log 1146-1150, 1738). En TRANSFER, 11 dígitos dan E303 (log 2265)
# y 10 pasan el formato y llegan al límite E506 (log 2266).
MONTO = re.compile(r"[1-9][0-9]{0,9}")


def _monto(texto: str) -> int | None:
    return int(texto) if MONTO.fullmatch(texto) else None


def _nueva_op(estado: Estado, op: Operacion, cuentas: dict[str, int]) -> Resultado:
    op_id = f"OP-{estado.sig_op:04d}"
    nuevo = replace(estado, cuentas=cuentas, operaciones={**estado.operaciones, op_id: op},
                    sig_op=estado.sig_op + 1)
    return (*cat.operacion_recibida(op_id), nuevo)


def ping(estado: Estado, args: list[str]) -> Resultado:
    return (*cat.pong(), estado)  # ejemplo 1


def alta(estado: Estado, args: list[str]) -> Resultado:
    # Nombres aceptados en el log: numérico, con espacios, con tilde (José), 200 caracteres, con
    # guion, repetidos y un espacio solo (log 767-782). Que no haya otras restricciones es SUPUESTO.
    # Ids secuenciales con relleno a 4 dígitos (ejemplos 3-4); más allá de AC-9999, SUPUESTO.
    cuenta_id = f"AC-{estado.sig_cuenta:04d}"
    nuevo = replace(estado, cuentas={**estado.cuentas, cuenta_id: 0}, sig_cuenta=estado.sig_cuenta + 1)
    return (*cat.cuenta_creada(cuenta_id), nuevo)


def consulta(estado: Estado, args: list[str]) -> Resultado:
    cuenta = args[0]
    if cuenta not in estado.cuentas:  # ejemplo 15; texto exacto, sin validar formato (log 1447, 870)
        return (*cat.error("E401"), estado)
    return (*cat.saldo(cuenta, estado.cuentas[cuenta]), estado)  # ejemplos 5, 8, 11, 19


def deposito(estado: Estado, args: list[str]) -> Resultado:
    cuenta, texto = args
    monto = _monto(texto)
    if monto is None:  # E303 antes que E401 (log 783-800)
        return (*cat.error("E303"), estado)
    if cuenta not in estado.cuentas:
        return (*cat.error("E401"), estado)
    cuentas = {**estado.cuentas, cuenta: estado.cuentas[cuenta] + monto}
    # Sin el límite de 100000 de TRANSFER, pero sujeto al formato y tope del monto: aceptados
    # 120000, 1000000, 9 y 10 dígitos (log 794-795, 876-877); rechazados 11 a 20 dígitos
    # (log 793, 1146-1150). Un depósito reinicia el contador de rechazos de la
    # cuenta (log 1009-1021) y la desbloquea (log 1029-1031, 1061-1063). Una transferencia
    # entrante o una ANULA no la desbloquean (log 1040-1041, 1049-1050).
    rechazos = {k: v for k, v in estado.rechazos.items() if k != cuenta}
    estado = replace(estado, rechazos=rechazos, bloqueadas=estado.bloqueadas - {cuenta})
    return _nueva_op(estado, Operacion("DEPOSITO", cuenta, monto), cuentas)  # ejemplos 6, 18


def _rechazo(estado: Estado, origen: str, codigo: str, umbral: int) -> Resultado:
    """E506/E507 cuentan como rechazo seguido de la cuenta de origen; al llegar al umbral la
    cuenta queda bloqueada para las siguientes TRANSFER (log 955-1021, 1055-1061) hasta un
    DEPOSITO a esa cuenta o un __reset. No reinician el contador un PING exitoso (log 1675-1677),
    un E302 (log 978), un E401, una ANULA (log 1078-1082) ni los rechazos de otra cuenta."""
    n = estado.rechazos.get(origen, 0) + 1
    bloqueadas = estado.bloqueadas | {origen} if n >= umbral else estado.bloqueadas
    nuevo = replace(estado, rechazos={**estado.rechazos, origen: n}, bloqueadas=bloqueadas)
    return (*cat.error(codigo), nuevo)


def transfer(estado: Estado, args: list[str], *, limite: int, rechazos_bloqueo: int) -> Resultado:
    origen, destino, texto = args
    # Orden E303 -> E304 -> E401 -> E510 -> E506 -> E507.
    monto = _monto(texto)
    if monto is None:  # antes que E304 (log 867), E401 (log 868) y E510 (log 1686)
        return (*cat.error("E303"), estado)
    if origen == destino:  # texto exacto, aunque no existan (log 866); antes de E506 (869) y E510 (1685)
        return (*cat.error("E304"), estado)
    if origen not in estado.cuentas or destino not in estado.cuentas:
        # Antes del límite (log 817) y de E510 (log 1687); no cuenta como rechazo.
        return (*cat.error("E401"), estado)
    if origen in estado.bloqueadas:  # antes de E506 (log 850-861) y de E507 (log 1016, 1050)
        return (*cat.error("E510"), estado)
    if monto > limite:  # 100000 pasa, 100001 da E506 (log 900-954); antes de E507 (log 805, 818)
        return _rechazo(estado, origen, "E506", rechazos_bloqueo)
    if estado.cuentas[origen] < monto:  # ejemplo 16
        return _rechazo(estado, origen, "E507", rechazos_bloqueo)
    cuentas = dict(estado.cuentas)
    cuentas[origen] -= monto
    cuentas[destino] += monto
    # Una TRANSFER exitosa reinicia el contador de su origen (log 955-1021).
    estado = replace(estado, rechazos={k: v for k, v in estado.rechazos.items() if k != origen})
    return _nueva_op(estado, Operacion("TRANSFER", destino, monto, origen), cuentas)  # ejemplos 7, 10


def anula(estado: Estado, args: list[str]) -> Resultado:
    op_id = args[0]
    op = estado.operaciones.get(op_id)
    if op is None:  # texto exacto; inexistente o mal formada (log 887-899)
        return (*cat.error("E402"), estado)
    if op.anulada:  # ejemplo 14
        return (*cat.ya_anulada(), estado)
    # Revierte los saldos (ejemplos 13, 16, 19) aunque queden negativos (log 828-842, 887-899).
    # No consume número OP- (log 828-842) ni reinicia el contador de bloqueo (log 1078-1082).
    cuentas = dict(estado.cuentas)
    cuentas[op.destino] -= op.monto
    if op.origen is not None:
        cuentas[op.origen] += op.monto
    nuevo = replace(estado, cuentas=cuentas,
                    operaciones={**estado.operaciones, op_id: replace(op, anulada=True)})
    return (*cat.anulada(op_id), nuevo)  # ejemplo 13


def halt(estado: Estado, args: list[str]) -> Resultado:
    # Comando oculto: con 1 argumento responde 409 E520 y no cambia el estado (log 1229, 1234-1235).
    # Visto con AC-0001, AC-1, ac-0001, AC-0002 y AC-0003 (log 1229, 1253, 1563, 1345, 1407). El reenvío
    # «con confirmación» no se probó a propósito (servicio compartido): SUPUESTO que todo HALT da E520.
    return (*cat.error("E520"), estado)
