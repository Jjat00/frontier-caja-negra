"""Perfiles de comportamiento por versión del servicio (diseño D3 y D5).

Un perfil fija el orden de la tubería, los comandos activos con su aridad y los límites.
Se elige con la variable de entorno PERFIL (por defecto v_tarde, la versión vigente desde las 16:00; v_manana es la
versión 1 y la usa M1 para las filas del log anteriores a la 6040).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
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
        # el control (log 1232-1233). SUPUESTO: va después de los seis visibles en los empates de la sugerencia.
        "HALT": Comando(1, c.halt),
        # Oculto: TOTAL, NOTA, NOTE, NOTES y NOTAR lo sugieren (log 3301, 3484-3487). Aridad 0 (log 3479-3483).
        # SUPUESTO: su lugar en los empates de la sugerencia (va después de HALT).
        "NOTAS": Comando(0, c.notas),
    },
    max_cuerpo=8192,         # bytes; 8193 da E101 (log 1702-1704)
    max_anidamiento=20,      # 20 niveles se parsean y 21 dan E100, en arrays y objetos (log 1708-1720)
    distancia_sugerencia=2,  # Levenshtein <= 2 (log 733-755); empates SUPUESTO (ver tuberia.sugerir)
)

# Versión 2 (incidente, ticket #FR-0153; en línea confirmada a las 16:00, canario-1600, log 6040-6081). Cuatro
# diferencias frente a v_manana: límite, formato del saldo y E510 (los cambios del ticket) y la exención por titular,
# hallada en la versión 2 sin evidencia de si ya existía en la 1 (ver comandos.transfer).
LIMITE_TRANSFER_TARDE = 50000  # 50000 pasa y 50001 da E506 (log 6106-6109); en la versión 1, 100000 pasaba (825, 1740) y 100001 daba E506 (954)
V_TARDE = replace(
    V_MANANA,
    nombre="v_tarde",
    comandos={
        **V_MANANA.comandos,
        # saldo como texto con dos decimales, en centésimas (log 6052, 6112-6123)
        "CONSULTA": Comando(1, partial(c.consulta, saldo_centesimas=True)),
        # límite 50000 y E510 con status 423 y "intentos" (log 6065-6067, 6131-6146)
        "TRANSFER": Comando(3, partial(c.transfer, limite=LIMITE_TRANSFER_TARDE,
                                       rechazos_bloqueo=RECHAZOS_BLOQUEO_MANANA, e510_intentos=True,
                                       sin_limite_mismo_titular=True)),
    },
)

PERFILES = {p.nombre: p for p in (V_MANANA, V_TARDE)}
# El set oficial corre contra la versión vigente a las 20:00 (MATERIAL.md): la versión 2 por defecto.
PERFIL_POR_DEFECTO = "v_tarde"


def activo() -> Perfil:
    return PERFILES[os.environ.get("PERFIL", PERFIL_POR_DEFECTO)]
