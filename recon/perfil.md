# Perfil del terreno (surface-recon, Phase 0)

```yaml
access: granted            # token personal del reto, 8.000 req/día, 10 req/s
planes: [network, command] # HTTP + protocolo de texto "CMD;args;control" dentro de POST /msg
primary-plane: command
acceptance: [contract-conformance, state-transition, replay]
maximum-consequence: reversible  # POST /__reset restaura el estado del token
```

- Cada afirmación necesita una fila del log (`experimentos.jsonl`) como recibo.
- Conformidad: el reemplazo reproduce status y cuerpo exactos (fuzzer diferencial, M2 del diseño).
