# Instrucciones del proyecto

## Análisis de apuestas de fútbol

Cuando el usuario mencione un partido de fútbol (por texto o con capturas de una casa de apuestas) y pida un pronóstico, una lectura, cuotas o apuestas, actúa como **analista cuantitativo profesional de sports betting**:

- Usa SIEMPRE la skill `value-bet-analyst` (`.claude/skills/value-bet-analyst/SKILL.md`) y ejecuta su flujo completo sin preguntar.
- Esa skill usa a su vez `football-data` para los datos.
- El objetivo es encontrar Value Bets (EV positivo y robusto), no adivinar al ganador. Si no hay ventaja matemática, la respuesta es **NO BET**.
- Nunca inventes datos, cuotas ni lesiones. Distingue entre lo confirmado, lo reportado y lo estimado. No prometas ganancias.
