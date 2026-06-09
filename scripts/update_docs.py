import os
import re
import sys
import time

from google import genai

MAX_DIFF_CHARS = 3000
MAX_RETRIES = 3
RETRY_BASE_DELAY = 15
API_CALL_DELAY = 5

MODEL_FALLBACK_CHAIN = [
    "gemini-1.5-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash-8b",
    "gemini-2.0-flash",
]


def generate_with_retry(client, model, prompt, max_retries=MAX_RETRIES):
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            return response
        except Exception as e:
            last_error = e
            error_str = str(e)
            is_rate_limit = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str

            if attempt < max_retries:
                delay_raw = 20
                match = re.search(r"retryDelay['\": ]+(\d+)", error_str)
                if match:
                    delay_raw = int(match.group(1))
                delay = max(RETRY_BASE_DELAY * attempt, delay_raw * attempt)

                reason = "rate limit" if is_rate_limit else "error transitorio"
                print(f"  Reintento {attempt}/{max_retries} por {reason}, esperando {delay}s...")
                time.sleep(delay)
            else:
                print(f"  Agotados {max_retries} reintentos.")

    raise last_error


def extract_relevant_diff(full_diff, docs_path):
    docs_path_lower = docs_path.lower().replace("\\", "/")
    filtered_lines = []
    current_file = None
    include_current = False

    for line in full_diff.split("\n"):
        file_match = re.match(r"^diff --git a/(.+) b/(.+)", line)
        if file_match:
            file_a = file_match.group(1).lower().replace("\\", "/")
            current_file = file_a

            if "readme.md" in docs_path_lower:
                include_current = (
                    "infra/" in file_a
                    or "docker" in file_a
                    or not any(
                        prefix in file_a
                        for prefix in ("backend/", "frontend/", "docs/", ".github/")
                    )
                )
            elif "base-de-datos" in docs_path_lower:
                include_current = (
                    "backend/alembic/" in file_a
                    or "model" in file_a
                    or "database" in file_a
                    or "migration" in file_a
                    or "schema" in file_a
                )
            elif "endpoints-api" in docs_path_lower:
                include_current = (
                    "backend/app/" in file_a and "model" not in file_a
                )
            elif "arquitectura" in docs_path_lower:
                include_current = "frontend/" in file_a
            else:
                include_current = True

        if include_current:
            filtered_lines.append(line)

    result = "\n".join(filtered_lines)
    if len(result) > MAX_DIFF_CHARS:
        result = result[:MAX_DIFF_CHARS] + "\n... (diff truncado por tamaño)"
    return result


def try_generate(client, prompt):
    last_error = None
    for model in MODEL_FALLBACK_CHAIN:
        try:
            print(f"  Intentando con modelo {model}...")
            response = generate_with_retry(client, model, prompt)
            return response
        except Exception as e:
            error_str = str(e)
            is_quota = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str
            if is_quota:
                print(f"  {model} sin quota disponible, probando siguiente...")
                last_error = e
                continue
            raise
    raise last_error


def update_docs(client, full_diff, changed_files):
    docs_to_update = set()

    ROOT_FILES = {"readme.md", ".env.example", "docker-compose.yml", "claude.md", "makefile", "mvp-spec.md", ".gitignore", ".pre-commit-config.yaml", "opencode.json", "pyproject.toml"}

    for file_path in changed_files:
        file_path = file_path.lower().replace("\\", "/")
        base_name = os.path.basename(file_path)

        if "infra/" in file_path or base_name in ROOT_FILES:
            docs_to_update.add("README.md")

        elif "backend/alembic/" in file_path or "model" in file_path or "database" in file_path:
            docs_to_update.add("docs/base-de-datos.md")

        elif "backend/app/" in file_path:
            docs_to_update.add("docs/endpoints-api.md")

        elif "frontend/" in file_path:
            docs_to_update.add("docs/arquitectura.md")

    if not docs_to_update:
        print("Los archivos modificados no alteran la documentacion tecnica indexada. Terminando.")
        return 0, []

    docs_list = sorted(docs_to_update)
    errores = []

    for idx, docs_path in enumerate(docs_list):
        print(f"Procesando actualizacion para: {docs_path}")

        try:
            with open(docs_path, "r", encoding="utf-8") as f:
                current_docs = f.read()
        except FileNotFoundError:
            current_docs = f"# Documentacion: {os.path.basename(docs_path)}\n"

        relevant_diff = extract_relevant_diff(full_diff, docs_path)
        if not relevant_diff.strip():
            print(f"  Sin cambios relevantes para {docs_path}, omitiendo.")
            continue

        diff_char_count = len(relevant_diff)
        print(f"  Diff relevante: {diff_char_count} caracteres")

        prompt = f"""Eres un Tech Lead experto. Estamos desarrollando un sistema con FastAPI, Supabase y React.

Analiza el siguiente diff de codigo de los cambios actuales:
```diff
{relevant_diff}
```

Debes actualizar ESPECIFICAMENTE el archivo de documentacion: '{docs_path}'
La version actual del archivo es:
```markdown
{current_docs}
```

Reglas:
1. Modifica, elimina o agrega secciones SOLO si el git diff tiene relacion directa con el proposito de '{docs_path}'.
2. Si los cambios no afectan a este archivo en particular, devuelve exactamente el mismo texto de la version actual.
3. NO inventes datos. Devuelve UNICAMENTE el codigo Markdown resultante, sin saludos ni bloques de comentarios.
"""

        try:
            response = try_generate(client, prompt)
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

            print(f"  {docs_path} actualizado con exito!")

        except Exception as e:
            print(f"  Error procesando {docs_path} con Gemini: {e}")
            errores.append((docs_path, str(e)))

        if idx < len(docs_list) - 1:
            print(f"  Esperando {API_CALL_DELAY}s antes del siguiente documento...")
            time.sleep(API_CALL_DELAY)

    print("Proceso de documentacion finalizado.")
    return (1 if errores else 0, errores)


if __name__ == "__main__":
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error critico: No se encontro la variable de entorno GEMINI_API_KEY.")
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    try:
        with open("diff.txt", "r", encoding="utf-8") as f:
            full_diff = f.read().strip()
    except FileNotFoundError:
        print("Error: No se encontro el archivo diff.txt.")
        sys.exit(1)

    if not full_diff:
        print("No hay cambios de codigo para analizar.")
        sys.exit(0)

    changed_files = sys.argv[1:]
    if not changed_files:
        print("No se especificaron archivos modificados.")
        sys.exit(0)

    exit_code, errores = update_docs(client, full_diff, changed_files)

    if errores:
        print(f"\n{len(errores)} archivo(s) fallaron:")
        for docs_path, err in errores:
            print(f"  - {docs_path}: {err}")

    sys.exit(exit_code)
