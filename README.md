# frontier-caja-negra

Reto 2 («La caja negra») del AI Builders Hackathon Frontier BOG / 26 (Lab10, 2026-10-10). Autor: Jaime Aza.

Un servicio sin código ni documentación recibe mensajes por HTTP y responde. Este repo contiene un
reemplazo que responde exactamente igual, errores incluidos, junto con la especificación y el log de
experimentos que permitieron descubrir su comportamiento.

## Entregables

| Entregable | Dónde |
| --- | --- |
| Reemplazo desplegado | `https://caja-negra-reemplazo-production.up.railway.app` (Railway, 1 réplica, despliegue automático desde `main`) |
| Especificación | [`docs/especificacion.md`](docs/especificacion.md): siete secciones, cada comportamiento con su evidencia y su confianza |
| Log de experimentos | [`experimentos.jsonl`](experimentos.jsonl): una fila por request al original, con su hipótesis |
| Systems design (12:00) | [`docs/diseno.md`](docs/diseno.md) y [`docs/arquitectura.png`](docs/arquitectura.png), congelados en la etiqueta `diseno-12h` |

## Qué es el servicio

Es un libro mayor bancario mínimo que se maneja con mensajes `POST /msg {"m": "CMD;arg;…;control"}`. Tiene
estos comandos: PING, ALTA, CONSULTA, DEPOSITO, TRANSFER, ANULA y dos ocultos, HALT y NOTAS. Lo más difícil fue:

- **El dígito de control.** Es ISO 7064 MOD 97-10 (el del IBAN) sobre los caracteres alfanuméricos, con las
  letras como A=1 … Z=26. Se descubrió midiendo el peso de cada posición, no adivinando el algoritmo.
- **El orden de los errores.** Va así: ruta, auth, tamaño (8192 bytes), JSON (20 niveles), estructura,
  control, comando (con sugerencia por distancia de Levenshtein), aridad y negocio.
- **La memoria.** Abarca las cuentas, las operaciones, las anulaciones (que pueden dejar saldos negativos) y
  un bloqueo por tres rechazos seguidos que solo un depósito levanta.

La especificación documenta también los riesgos que un cliente nuevo no debería heredar. El comando HALT
pide confirmación porque «detiene el servicio»: a propósito **no se confirmó nunca** contra el original,
porque es un servicio compartido.

## Cómo está hecho

```
lab/       laboratorio: habla con el original y mide
  probe.py     cliente del original; registra cada request en experimentos.jsonl (redacta credenciales)
  exp/         un script por experimento (e01-e23), cada uno con su hipótesis
  control.py   el dígito de control
  fuzz.py      M2: fuzzer diferencial, tests inéditos con la mezcla del set oficial
  canario.py   M4: secuencia fija contra el original para detectar cambios
  m1.py        M1: regresión del log completo contra el reemplazo local
  compare.py   el comparador oficial (JSON sin orden de claves, texto exacto si no es JSON)
app/       reemplazo: motor determinista, sin llamadas al original
  main.py      ASGI con ruta comodín (router antes de auth), bytes exactos
  tuberia.py   etapas de validación ordenadas como configuración
  perfiles.py  perfil de comportamiento por versión del servicio (PERFIL=v_manana)
  catalogo.py  códigos de error y textos exactos
  comandos.py  manejadores puros (estado, args) -> (status, cuerpo, estado')
recon/     perfil del terreno y registro de fricción de la exploración
```

Para medir se usan tres herramientas:

- **M1** repite el log completo contra el reemplazo.
- **M2** corre secuencias nuevas, con semilla guardada, contra el original y el reemplazo.
- **M4**, el canario, avisa si el original cambia durante el día.

Cada bloque de trabajo pasó por una revisión adversarial con Codex antes de entrar a `main`.

```bash
uv sync
uv run python -m lab.m1                        # regresión local (no llama al original)
uv run python -m lab.fuzz 1 --solo-reemplazo   # replay de la semilla 1 contra el reemplazo local
TOKEN=<token> uv run uvicorn app.main:app      # reemplazo en local
```

Material de la organización: [`MATERIAL.md`](MATERIAL.md) (enunciado y contrato) y
`pruebas/ejemplos.jsonl` (20 ejemplos).
