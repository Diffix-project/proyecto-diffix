Flujo diario

1. Todo trabajo nace en Linear

Antes de tocar código, tiene que existir un issue en Linear. Sin issue → sin rama.

2. Crear la rama desde Linear

En el issue → "Copy git branch name" → crear la rama localmente:
git checkout -b eng/DIX-42-implementar-scout-agent

Esto solo ya sincroniza el issue a "In Progress" automáticamente.

3. Commits durante el desarrollo

Referenciar el issue en cada commit:
git commit -m "feat(scout): agregar hash SHA256 por fuente [DIX-42]"
No es obligatorio en cada commit, pero ayuda a rastrear el historial.

4. PR hacia dev

Cuando el feature está listo, PR a dev. El template se precarga, completás el número y listo. El CI corre automáticamente.

5. Merge de dev a staging periódicamente

Una vez al día o cuando acumulan features estables. El workflow de migrate corre las migraciones contra Supabase staging automáticamente.

6. Merge de staging a main para releases

Solo cuando staging está validado. Linear cierra los issues automáticamente por el Closes DIX-X del PR.

---
Flujo de ramas

feature/DIX-42  →  dev  →  staging  →  main
feature/DIX-55  →  dev  ↗