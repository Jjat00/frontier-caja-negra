"""Catálogo de respuestas como datos: status y cuerpo exacto de cada error y de cada éxito.

Las rarezas del original se copian tal cual: "recieved", "comando desconocido " con espacio
final, cuentaId (ALTA) frente a cuenta_id (CONSULTA).
"""

from __future__ import annotations

Respuesta = tuple[int, dict]

# código -> (status, mensaje). Las entradas marcadas SUPUESTO no se han visto en el original.
ERRORES: dict[str, tuple[int, str]] = {
    "E001": (401, "no autorizado"),          # log 1, 2, 4, 5, 6
    "E404": (404, "ruta desconocida"),       # log 7, 8, 9, 141, 142, 144-148
    "E100": (400, "json inválido"),          # log 10, 1169, 1176, 1181, 1663
    "E101": (413, "cuerpo demasiado grande"),  # log 1662, 1690, 1691, 1694, 1697, 1698, 1700, 1702, 1704, 1705 (más de 8192 bytes)
    "E102": (400, "falta m"),                # log 11, 1170-1173, 1175, 1177, 1179
    "E103": (400, "falta control"),          # log 12, 715, 725
    "E104": (400, "segmento vacío"),         # log 713, 716, 726
    "E201": (400, "control mal formado"),    # ejemplo 17; log 710-724
    "E202": (400, "control inválido"),       # ejemplo 2; log 137, 153, 704
    "E301": (400, "comando desconocido "),   # ejemplo 12; log 450, 708 (espacio final incluido)
    "E302": (400, "aridad inválida"),        # ejemplo 20; log 705, 707, 729
    "E303": (400, "monto inválido"),         # log 872-886: 0, negativos, 007, +5, 1e3…
    "E304": (400, "origen y destino iguales"),  # log 866, 869: TRANSFER con origen == destino
    "E401": (404, "cuenta inexistente"),     # ejemplo 15; log 181
    "E402": (404, "operación inexistente"),  # log 887-899: ANULA de OP inexistente o mal formada
    "E506": (422, "límite excedido"),        # ejemplo 9
    "E507": (422, "saldo insuficiente"),     # ejemplo 16
    "E510": (409, "cuenta bloqueada"),       # log 850, 962, 980, 1016, 1021: tras 3 rechazos E506/E507 seguidos
    "E520": (409, "operación destructiva: detiene el servicio; reenvía con confirmación"),  # log 1229
}


def error(codigo: str, **extra) -> Respuesta:
    status, mensaje = ERRORES[codigo]
    return status, {"error": codigo, "mensaje": mensaje, **extra}


def ok() -> Respuesta:
    return 200, {"ok": True}  # log 3, 134


def pong() -> Respuesta:
    return 200, {"pong": True}  # ejemplo 1


def cuenta_creada(cuenta_id: str) -> Respuesta:
    return 201, {"cuentaId": cuenta_id}  # ejemplos 3-4


def saldo(cuenta_id: str, monto: int) -> Respuesta:
    return 200, {"cuenta_id": cuenta_id, "saldo": monto}  # ejemplo 5


def operacion_recibida(op_id: str) -> Respuesta:
    return 200, {"status": "recieved", "operacionId": op_id}  # ejemplos 6-7 ("recieved" sic)


def anulada(op_id: str) -> Respuesta:
    return 200, {"ok": True, "anulada": op_id}  # ejemplo 13


# Nota fija de NOTAS (log 3480, 3489, 3492, 3499, 3501): no cambia con el estado, el reset ni HALT.
NOTA_N01 = ("Pendiente de la migración: exporta la documentación completa con POST /internal/export-docs "
            "y tu token en Authorization: Bearer.")


def notas() -> Respuesta:
    return 200, {"notas": [{"id": "N-01", "texto": NOTA_N01}]}


def ya_anulada() -> Respuesta:
    return 200, {"ok": False, "motivo": "ya anulada"}  # ejemplo 14
