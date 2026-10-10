"""Tubería de validación de POST /msg: etapas independientes cuyo orden fija el perfil.

Cada etapa recibe el contexto y devuelve None (sigue) o una Respuesta de error (corta).
Al final se despacha al manejador del comando.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

from app import catalogo as cat
from app import control
from app.catalogo import Respuesta

if TYPE_CHECKING:
    from app.perfiles import Comando, Perfil


@dataclass
class Ctx:
    cuerpo: bytes
    perfil: Perfil
    datos: object = None
    m: str = ""
    segmentos: list[str] = field(default_factory=list)
    nombre: str = ""             # comando tal como llegó
    comando: Comando | None = None


def tamano(ctx: Ctx) -> Respuesta | None:
    # Más de 8192 bytes -> 413 E101: 8192 pasa y 8193 no (log 1702-1704). Va antes que el JSON
    # (log 1705) y después de la ruta y la auth (log 1706, 1707).
    if len(ctx.cuerpo) > ctx.perfil.max_cuerpo:
        return cat.error("E101")
    return None


def _profundidad(texto: str) -> int:
    """Anidamiento máximo de [ y { fuera de strings, sin recursión."""
    actual = maximo = 0
    en_string = escape = False
    for ch in texto:
        if en_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                en_string = False
        elif ch == '"':
            en_string = True
        elif ch in "[{":
            actual += 1
            maximo = max(maximo, actual)
        elif ch in "]}":
            actual -= 1
    return maximo


def _constante(nombre: str):
    raise ValueError(nombre)


def json_valido(ctx: Ctx) -> Respuesta | None:
    try:
        texto = ctx.cuerpo.decode("utf-8")
        # Más de perfil.max_anidamiento niveles (20) dan E100 (log 1708-1720), también dentro de m (1663).
        # La profundidad se mide sin recursión antes de parsear.
        if _profundidad(texto) > ctx.perfil.max_anidamiento:
            return cat.error("E100")
        # JSON estricto: NaN da E100 en el original (medido, log 2357, 2373); Infinity y -Infinity se rechazan
        # por la misma regla (inferido, no medido).
        ctx.datos = json.loads(texto, parse_constant=_constante)
    except Exception:
        # log 10, 1169, 1176, 1181. Anidamiento extremo (RecursionError) también es E100 (log 1663);
        # SUPUESTO: cualquier otra excepción del parseo, igual, para que ningún cuerpo dé 500.
        return cat.error("E100")
    return None


def campo_m(ctx: Ctx) -> Respuesta | None:
    # {} -> E102 (log 11); también un JSON que no es objeto (log 1170, 1175), la clave "M"
    # (log 1177) y un m que no es string: número, null, array, booleano (log 1171-1173, 1179).
    if not isinstance(ctx.datos, dict) or not isinstance(ctx.datos.get("m"), str):
        return cat.error("E102")
    ctx.m = ctx.datos["m"]
    return None


def control_presente(ctx: Ctx) -> Respuesta | None:
    # Sin ';' no hay control: "" (log 12), "ALTA" (log 715), "PING" (log 725), "PING|64" (log 1183).
    ctx.segmentos = ctx.m.split(";")
    if len(ctx.segmentos) < 2:
        return cat.error("E103")
    ctx.nombre = ctx.segmentos[0]
    # Sin distinguir mayúsculas: medido en CONSULTA (ejemplo 11; log 1447), PING (log 730),
    # TRANSFER (log 1404, 1550), ANULA (log 1655), DEPOSITO (log 1768), ALTA (log 2139) y HALT (log 2267).
    # El nombre no se recorta (log 731-732).
    ctx.comando = ctx.perfil.comandos.get(mayus_ascii(ctx.nombre))
    return None


def mayus_ascii(texto: str) -> str:
    """Mayúsculas solo en ASCII, sin expandir: «PıNG» no es PING (log 3516) y «AßNG» queda a distancia 2 de
    PING (log 2444, 3521), mientras que str.upper() daría «PING» y «ASSNG»."""
    return "".join(ch.upper() if ch.isascii() else ch for ch in texto)


def segmento_vacio(ctx: Ctx) -> Respuesta | None:
    # log 713 ("ALTA;Lucia;"), 716 (";82"), 726 ("PING;"); también aplica a PING.
    # Un segmento de un espacio no es vacío (log 767: "ALTA; ;85" -> 201).
    if any(s == "" for s in ctx.segmentos):
        return cat.error("E104")
    return None


def _salta_control(ctx: Ctx) -> bool:
    # PING no valida ni el formato ni el valor del control (log 13-127, 727, 728).
    return ctx.comando is not None and not ctx.comando.valida_control


def control_formato(ctx: Ctx) -> Respuesta | None:
    # Antes que el comando y la aridad (log 710-712); ejemplo 17; log 714, 717-724.
    # fullmatch no admite un salto de línea final: "ALTA;Lucia;82\n" -> E201 (log 1665).
    if not _salta_control(ctx) and not control.formato_valido(ctx.segmentos[-1]):
        return cat.error("E201")
    return None


def control_valor(ctx: Ctx) -> Respuesta | None:
    # Antes que el comando (log 450 frente a 449; 708-709) y que la aridad (log 704-707).
    if _salta_control(ctx):
        return None
    if not control.valor_valido(";".join(ctx.segmentos[:-1]), ctx.segmentos[-1]):
        return cat.error("E202")
    return None


def comando_conocido(ctx: Ctx) -> Respuesta | None:
    if ctx.comando is not None:
        return None
    sugerencia = sugerir(ctx.nombre, ctx.perfil.comandos, ctx.perfil.distancia_sugerencia)
    if sugerencia:  # log 450 (CONSULTB), 731-732 (" PING", "PING ")
        return cat.error("E301", sugerencia=sugerencia)
    return cat.error("E301")  # ejemplo 12 (SALDOS), log 708 (FOO)


def aridad(ctx: Ctx) -> Respuesta | None:
    # Argumentos = segmentos sin comando ni control (ejemplo 20; log 705, 707, 729).
    if len(ctx.segmentos) - 2 != ctx.comando.aridad:
        return cat.error("E302")
    return None


def _levenshtein(a: str, b: str) -> int:
    previa = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        actual = [i]
        for j, cb in enumerate(b, 1):
            actual.append(min(previa[j] + 1, actual[j - 1] + 1, previa[j - 1] + (ca != cb)))
        previa = actual
    return previa[-1]


def sugerir(nombre: str, comandos: dict, distancia: int) -> str | None:
    """Sugiere el comando conocido más cercano por distancia de Levenshtein, sin distinguir
    mayúsculas y con el nombre tal cual (espacios incluidos), si es <= `distancia`.
    Log 450, 731-732 (distancia 1), 734-738 (distancia 2), 740-742 (3 o más: sin sugerencia).
    SUPUESTO: en empate gana el primero en el orden del perfil (no medido).
    """
    candidatos = [(_levenshtein(mayus_ascii(nombre), c), c) for c in comandos]
    d, mejor = min(candidatos, key=lambda x: x[0])
    return mejor if d <= distancia else None


ETAPAS: dict[str, Callable[[Ctx], Respuesta | None]] = {
    "tamano": tamano,
    "json": json_valido,
    "campo_m": campo_m,
    "control_presente": control_presente,
    "segmento_vacio": segmento_vacio,
    "control_formato": control_formato,
    "control_valor": control_valor,
    "comando": comando_conocido,
    "aridad": aridad,
}


def procesar(cuerpo: bytes, perfil, estado):
    """Corre las etapas en el orden del perfil y despacha. Devuelve (status, cuerpo, estado')."""
    ctx = Ctx(cuerpo=cuerpo, perfil=perfil)
    for nombre in perfil.etapas:
        respuesta = ETAPAS[nombre](ctx)
        if respuesta is not None:
            return (*respuesta, estado)
    return ctx.comando.manejador(estado, ctx.segmentos[1:-1])

