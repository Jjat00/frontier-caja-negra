# Fricción de surface-recon (reto 2, caja negra)

Una línea por fricción, en el momento en que ocurre.

- 2026-10-10 12:10 · Phase 0: el terreno es un protocolo de texto dentro de HTTP; la skill no tiene playbook para «adivinar un checksum» ni para «orden de validación». Se cubre con experimentos diferenciales propios.
- 2026-10-10 12:20 · Phase 3: para un checksum desconocido sirvió más medir el peso de cada posición (variar un carácter, barrer 0-99) que probar familias de hashes offline. La linealidad mod 97 salió en 3 barridos; la búsqueda de familias no encontró nada en 4 intentos. Falta en la skill un playbook de «checksum por diferencias».
- 2026-10-10 12:25 · Las búsquedas binarias contra un servicio con estado se contaminan: tres rechazos bloquearon la cuenta y E510 se tomó como éxito (log 850-861). Regla: estado limpio por sonda y abortar ante una respuesta inesperada.
- 2026-10-10 12:28 · La sugerencia de E301 («¿quisiste decir…?») sirve de oráculo para enumerar comandos ocultos (HELP → HALT). Patrón reutilizable: cualquier mensaje de error con sugerencias revela el catálogo interno.
- 2026-10-10 12:30 · Gate de consecuencia: HALT pide confirmación porque «detiene el servicio». No se confirmó (servicio compartido); decisión del usuario. La skill debería decir explícitamente que un «reenvía con confirmación» es un límite de maximum-consequence.
- 2026-10-10 12:45 · El registrador copiaba los headers enviados, incluido Authorization con el token, al log que se publica. Lo detectó la revisión de Codex. Regla para la skill: redactar las credenciales en el momento de registrar, no después.
