import os
import sys

from google import genai

# 1. Configurar cliente
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Error crítico: No se encontró la variable de entorno GEMINI_API_KEY.")
    sys.exit(1)

client = genai.Client(api_key=api_key)

# 2. Leer el diff global
try:
    with open("diff.txt", "r", encoding="utf-8") as f:
        diff_content = f.read().strip()
except FileNotFoundError:
    print("Error: No se encontró el archivo diff.txt.")
    sys.exit(1)

if not diff_content:
    print("No hay cambios de código para analizar.")
    sys.exit(0)

# 3. Leer qué archivos cambiaron en el push
changed_files = sys.argv[1:]

if not changed_files:
    print("No se especificaron archivos modificados.")
    sys.exit(0)

# 4. MAPEO INTELIGENTE ADAPTADO A NUESTRA ESTRUCTURA
docs_to_update = set()

for file_path in changed_files:
    file_path = file_path.lower().replace("\\", "/")

    # Regla para Infraestructura y Configuración Global (Raíz del proyecto)
    if "infra/" in file_path:
        docs_to_update.add("README.md")

    # Regla para Base de Datos (Migraciones de Alembic o modelos/esquemas dentro de domains)
    elif "backend/alembic/" in file_path or "model" in file_path or "database" in file_path:
        docs_to_update.add("docs/base-de-datos.md")

    # Regla para Endpoints de la API y Lógica del Servidor (Backend App)
    elif "backend/app/" in file_path:
        docs_to_update.add("docs/endpoints-api.md")

    # Regla para Arquitectura, UI y Features del Cliente (Todo el Frontend de React)
    elif "frontend/" in file_path:
        docs_to_update.add("docs/arquitectura.md")

if not docs_to_update:
    print("Los archivos modificados no alteran la documentación técnica indexada. Terminando.")
    sys.exit(0)

MODEL = "gemini-2.0-flash"

# 5. Iterar y actualizar cada .md afectado
errores = []
for docs_path in docs_to_update:
    print(f"Procesando actualización para: {docs_path}")

    try:
        with open(docs_path, "r", encoding="utf-8") as f:
            current_docs = f.read()
    except FileNotFoundError:
        current_docs = f"# Documentación: {os.path.basename(docs_path)}\n"

    prompt = f"""
    Eres un Tech Lead experto. Estamos desarrollando un sistema con FastAPI, Supabase y React.

    Analiza el siguiente diff de código de los cambios actuales:
    ```diff
    {diff_content}
    ```

    Debes actualizar ESPECÍFICAMENTE el archivo de documentación: '{docs_path}'
    La versión actual del archivo es:
    ```markdown
    {current_docs}
    ```

    Reglas:
    1. Modifica, elimina o agrega secciones SOLO si el git diff tiene relación directa con el propósito de '{docs_path}'.
    2. Si los cambios no afectan a este archivo en particular, devuelve exactamente el mismo texto de la versión actual.
    3. NO inventes datos. Devuelve ÚNICAMENTE el código Markdown resultante, sin saludos ni bloques de comentarios.
    """

    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
        new_docs = response.text.strip()

        if new_docs.startswith("```markdown"):
            new_docs = new_docs[11:]
        if new_docs.endswith("```"):
            new_docs = new_docs[:-3]

        dir_name = os.path.dirname(docs_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        with open(docs_path, "w", encoding="utf-8") as f:
            f.write(new_docs.strip())

        print(f"¡{docs_path} actualizado con éxito!")

    except Exception as e:
        print(f"Error procesando {docs_path} con Gemini: {e}")
        errores.append((docs_path, str(e)))

print("Proceso de documentación finalizado.")

# 6. Fallar fuerte si alguna generación falló: así el workflow se pone en rojo
# en vez de reportar success sin haber actualizado nada (falla silenciosa).
if errores:
    print(f"\n{len(errores)} archivo(s) fallaron:")
    for docs_path, err in errores:
        print(f"  - {docs_path}: {err}")
    sys.exit(1)
