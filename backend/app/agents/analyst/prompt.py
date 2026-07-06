"""Construcción del prompt para el Analyst Agent.

La función `build_prompt` genera un prompt en español que le pide al LLM
analizar un diff detectado por el Scout y devolver un JSON estricto con los
cuatro campos requeridos por el producto.
"""

from app.domains.auth.models import INDUSTRY_VALUES
from app.domains.changes.models import SECTION_VALUES

# Niveles de urgencia válidos (sincronizado con app.domains.insights.models)
URGENCY_LEVELS = ("alta", "media", "baja")


def build_prompt(
    diff_text: str,
    competitor_name: str,
    industry: str,
    section: str,
) -> str:
    """
    Construye el prompt que se envía al LLM para generar un insight.

    Args:
        diff_text: Texto del diff detectado por el Scout.
        competitor_name: Nombre del competidor.
        industry: Rubro de la empresa del usuario (food, tech, construction, other).
        section: Sección donde ocurrió el cambio (pricing, home, features, jobs, pdf, general).

    Returns:
        Prompt completo en español listo para enviar al LLM.

    Raises:
        ValueError: Si `industry` o `section` no son valores válidos.
    """
    if industry not in INDUSTRY_VALUES:
        raise ValueError(f"industry inválido: {industry!r}. Valores válidos: {INDUSTRY_VALUES}")

    if section not in SECTION_VALUES:
        raise ValueError(f"section inválida: {section!r}. Valores válidos: {SECTION_VALUES}")

    return f"""Sos un analista senior de inteligencia competitiva para distribuidoras argentinas.
Tu trabajo es interpretar un cambio detectado en un competidor y generar un insight accionable en español.

### Contexto

    - **Competidor:** {competitor_name}
- **Rubro de la empresa:** {industry}
- **Sección del cambio:** {section}

### Diff detectado

```diff
{diff_text}
```

### Tu tarea

Analizá el diff de arriba y generá un JSON estricto con exactamente estos 4 campos:

1. `what_changed` (string): ¿Qué cambió exactamente? Describí el cambio en 1-3 oraciones concretas.
2. `why_it_matters` (string): ¿Por qué es relevante para el negocio del cliente? Explicá el impacto competitivo.
3. `what_to_do` (string): ¿Qué acción concreta debería tomar el cliente? Sé específico y accionable.
4. `urgency` (string): Nivel de urgencia, uno de: alta, media, baja.

### Guía de urgencia

Usá estos criterios para asignar la urgencia:

- **alta**: cambios de precios, nuevos productos/servicios, expansiones geográficas, lanzamientos agresivos, promociones que pueden robar cuota de mercado.
- **media**: cambios de messaging o posicionamiento, contrataciones relevantes, cambios de equipo directivo, alianzas.
- **baja**: cambios de diseño, contenido menor, actualizaciones estéticas, correcciones de texto.

### Reglas importantes

- Respondé **solo** con el JSON, sin markdown, sin comentarios, sin texto adicional.
- Todos los campos deben ser strings no vacíos (después de quitar espacios).
- El campo `urgency` debe ser exactamente "alta", "media" o "baja".
- El contenido debe estar en español y ser útil para un equipo comercial o de producto.

### Formato esperado

{{"what_changed": "...", "why_it_matters": "...", "what_to_do": "...", "urgency": "..."}}
"""
