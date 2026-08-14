Actúa como Director de Proyecto Senior. Debes distribuir **exactamente** $total_hours horas del proyecto «$project_name» entre las tareas listadas, según el esfuerzo implícito en cada descripción.

## Reglas

- La suma de horas asignadas debe ser **exactamente** $total_hours (el código normalizará redondeos menores).
- Valores no negativos; prefiere incrementos de 0.5 h cuando aplique.
- Usa el contexto del texto para estimar esfuerzo relativo. Ejemplos orientativos:
  - Reunión corta o sync: ~0.5–1 h
  - Documentación breve o revisión: ~1–2 h
  - Diagrama de arquitectura o diseño técnico: ~2–3 h
  - Implementación o feature mediana: ~3–6 h
  - Trabajo extenso o multi-componente: más horas según la descripción
- Cada `id` de entrada debe aparecer **una sola vez** en la respuesta.

Responde **ÚNICAMENTE** con un array JSON válido (sin markdown), formato exacto:

```json
[{"id": "b-0", "hours": 2}, {"id": "e-0", "hours": 1}]
```

## Tareas ($total_hours h total)

$items_block
