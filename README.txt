# Automatización corregida

Sustituye en el repositorio estos archivos:

- `.github/workflows/daily-exam.yml`
- `scripts/generate_exam.py`
- `requirements.txt`

Después:

1. Comprueba que existe `reference/rtve_topics.txt`.
2. Comprueba que existe `data/exams.json`.
3. En GitHub: Settings → Actions → General → Workflow permissions →
   Read and write permissions.
4. En GitHub: Actions → Generar examen diario → Run workflow.
5. Para una prueba adicional el mismo día, activa `force`.
6. Cuando el flujo termine en verde, debe aparecer un commit nuevo y un nuevo
   examen en `data/exams.json`.
7. Netlify debe estar vinculado al repositorio y a la rama `main`.
8. Netlify publicará automáticamente cada push a `main`.

Programación diaria: 08:10 Europe/Madrid.
