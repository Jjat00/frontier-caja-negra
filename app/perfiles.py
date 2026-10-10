"""Perfiles de comportamiento por versión del servicio (diseño D3 y D5).

Un perfil fija el orden de la tubería, los comandos activos con su aridad y los límites.
Se elige con la variable de entorno PERFIL (por defecto v_manana).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import partial
from typing import Callable

from app import comandos as c


@dataclass(frozen=True)
class Comando:
    aridad: int
    manejador: Callable
    valida_control: bool = True


@dataclass(frozen=True)
class Perfil:
    nombre: str
    etapas: tuple[str, ...]
    comandos: dict[str, Comando]
    distancia_sugerencia: int
    max_cuerpo: int
    max_anidamiento: int


# Orden de la tubería. Entrada: log 10-12, 1169-1183, 1662-1663, 1690-1707. Cruces de
# E103/E104/E201/E202/E301/E302: log 704-732, medidos sobre todo con ALTA, CONSULTA, FOO y PING;
# HALT, aparte, en log 1228-1233. Que el mismo orden valga para cada comando es inferencia.
ETAPAS_MANANA = (
    "tamano",            # E101
    "json",              # E100
    "campo_m",           # E102
    "control_presente",  # E103
    "segmento_vacio",    # E104
    "control_formato",   # E201
    "control_valor",     # E202
    "comando",           # E301
    "aridad",            # E302
)

LIMITE_TRANSFER_MANANA = 100000  # máximo permitido: 100000 pasa, 100001 da E506 (log 900-954)
RECHAZOS_BLOQUEO_MANANA = 3      # rechazos seguidos de TRANSFER que bloquean el origen (log 955-1021)

V_MANANA = Perfil(
    nombre="v_manana",
    etapas=ETAPAS_MANANA,
    comandos={
        "PING": Comando(0, c.ping, valida_control=False),   # log 13-127, 727-729
        "ALTA": Comando(1, c.alta),
        "CONSULTA": Comando(1, c.consulta),
        "DEPOSITO": Comando(2, c.deposito),
        "TRANSFER": Comando(3, partial(c.transfer, limite=LIMITE_TRANSFER_MANANA,
                                       rechazos_bloqueo=RECHAZOS_BLOQUEO_MANANA)),
        "ANULA": Comando(1, c.anula),
        # Oculto: aparece como sugerencia (log 1125, 1208, 1210), aridad 1 (log 1228-1231) y valida
        # el control (log 1232-1233). SUPUESTO: va último para los empates de la sugerencia.
        "HALT": Comando(1, c.halt),
    },
    max_cuerpo=8192,         # bytes; 8193 da E101 (log 1702-1704)
    max_anidamiento=20,      # 20 niveles se parsean y 21 dan E100, en arrays y objetos (log 1708-1720)
    distancia_sugerencia=2,  # Levenshtein <= 2 (log 733-755); empates SUPUESTO (ver tuberia.sugerir)
)

PERFILES = {p.nombre: p for p in (V_MANANA,)}


def activo() -> Perfil:
    return PERFILES[os.environ.get("PERFIL", "v_manana")]
