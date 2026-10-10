# Cambios al diseño después de la corrida oficial 1

Anexo de [`diseno.md`](diseno.md), que queda congelado como se entregó a las 12:00 (etiqueta `diseno-12h`). Aquí se
registra qué cambió en el plan de medición, por qué y qué se descartó. La arquitectura (D1 a D8) no cambia.

## Qué lo motivó

La corrida oficial 1 (13:43) dio **83/100** con M1 al 100 % y M2 en 100/100 en las semillas 1 y 2. La puerta interna
para gastar una corrida (M2 ≥ 95 %) se cumplió y aun así fallaron 17 tests. Ese hueco entre M2 y el set oculto es la
evidencia de un punto ciego del plan.

**El punto ciego:** M2 genera secuencias con los comandos, argumentos y errores que mi modelo ya conoce. Mide bien si
el reemplazo reproduce lo conocido, pero los nombres de comando y los caracteres que no están en su generador nunca
aparecen en sus casos: NOTAS o `ı` no podían salir de M2.

Tres comportamientos de ese tipo se encontraron después con un diferencial que amplía las entradas conocidas (filas 2281 a
4467 del log; ver la especificación):

| Comportamiento | Cómo se encontró | Filas |
|---|---|---|
| Comando oculto NOTAS (aridad 0) | barrido de nombres con cinco argumentos (CMD-NOTAS-01, 07) | 3301, 3188-3477, 3541-3746 |
| Mayúsculas solo ASCII en el nombre del comando (CMD-GEN-05) | mutaciones de carácter (e17) y sondas dirigidas (e20) | 2444, 3505-3540 |
| `NaN` en el JSON da E100 (ENT-24) | variantes del cuerpo JSON (e17) | 2357, 2373 |

Cuántos de los 17 fallos explican no se sabe hasta la siguiente corrida.

## Cambio 1: nueva medición M6, diferencial exploratorio con el original como oráculo

| Medición | Qué es | Métrica |
|---|---|---|
| **M6. Diferencial exploratorio** | Casos que amplían las entradas conocidas, con el original como oráculo (la respuesta correcta es la suya, no la de mi modelo). Dependencias: parte de mensajes válidos conocidos, de una preparación fija (dos cuentas y un depósito), del algoritmo del control para recalcularlo y de listas explícitas de nombres: (a) mutaciones de carácter de mensajes válidos (insertar, borrar, reemplazar, cambiar mayúsculas, espacios y segmentos), con el control recalculado para llegar a las etapas de después (`lab/exp/e17_mutaciones.py`); (b) variantes del cuerpo JSON, de rutas y del header de auth (mismo script); (c) barrido de nombres de comando con una aridad que ningún comando tiene, para que un comando real responda E302 sin ejecutarse (`lab/exp/e18_comandos_ocultos.py`). Se corre contra el original y el reemplazo y se compara paso a paso. | 0 pasos distintos, y 0 comandos fuera del catálogo en el barrido. |

**Por qué M6 y no ampliar M2:** M2 sigue siendo la medición con la mezcla del set oficial. Si se le agregan
mutaciones al azar, su tasa deja de ser comparable con el set. Separadas, cada una responde una pregunta distinta:
M2, «¿reproduzco lo que conozco con la distribución del set?», y M6, «¿qué existe que no conozco?».

**Alternativa descartada:** pedir al set oculto la pista. Las corridas oficiales solo dicen cuántos tests pasan y son
tres; usarlas para buscar causas repite el error de Chofex (refutaciones, no diagnóstico).

**Límite:** el barrido de comandos solo encuentra nombres de su lista o a distancia de Levenshtein ≤ 2 de alguno
(la sugerencia de E301 delata a los cercanos). Un comando lejano a todo lo probado seguiría oculto.

## Cambio 2: M3 se mide sobre la especificación

El diseño definía M3 como una matriz comando × error × estado sin celdas vacías. En la práctica, cada celda quedó
como una fila de la especificación con su evidencia y su confianza, y nunca se contó. Ahora la cuenta
`lab/m3.py`, que lee las tablas de `docs/especificacion.md`. Resultado a las 15:55, sobre 184 comportamientos:

| Confianza | Filas | % |
|---|---|---|
| confirmado | 135 | 73,4 % |
| probable | 37 | 20,1 % |
| supuesto | 12 | 6,5 % |

La meta del diseño era ≥ 90 % de celdas confirmadas: **no se cumple**. El 93,5 % tiene evidencia del log (confirmado
o probable), pero la regla de «confirmado» exige dos observaciones en secuencias distintas, y la revisión de las 14:40
bajó varias filas a probable por tener una sola. Subirlas cuesta requests al original, que se reservan para la
versión 2 del incidente.

## Cierre de M5

`lab/m5.py` repite contra el reemplazo desplegado las secuencias de la semilla 1 del fuzzer (no llama al original).
Resultado a las 15:55: **325 pasos, p50 125 ms, p95 141 ms, p99 150 ms, máximo 185 ms**, medidos desde el cliente
(incluyen la red). Cumple la meta (p99 < 200 ms) con margen frente al límite de 5 s del set.

## Cambio 3: re-corrida del log por bloques

El diseño pedía re-correr el log **completo** contra el original tras el incidente. Con el presupuesto de la tarde
(8.000 requests por día, más de 6.000 usados a las 15:45), el log completo ya no cabe. `lab/recorrida.py` repite las
secuencias elegidas (incluidos cuerpos crudos y variantes de auth) y compara con lo registrado. Orden de uso cuando
el incidente esté en línea, de más barato a más caro: canario (42, incluido el reset), semilla 1 del fuzzer y los 20 ejemplos (446, incluidos 101 resets) y,
si faltan cambios, experimentos dirigidos solo de las zonas que no hayan salido, con una asignación de unas 500
requests (la re-corrida dirigida completa de las 15:42 costó 1084 con sus 85 resets: no cabe entera).

Referencia de la versión 1 ya registrada: canario de las 15:36 (41/41 iguales) y re-corridas de las 15:36 (345 pasos)
y 15:42 (999 pasos; 446 y 1084 requests con sus resets), todas sin diferencias.
