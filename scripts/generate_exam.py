name: Examen diario RTVE

run-name: Generar y publicar examen RTVE #${{ github.run_number }}

on:
  # Permite generar un examen nuevo manualmente
  workflow_dispatch:

  # Generación automática todos los días a las 09:17
  # hora de Madrid
  schedule:
    - cron: "17 9 * * *"
      timezone: "Europe/Madrid"

# Impide que dos generaciones/publicaciones se solapen
concurrency:
  group: rtve-github-pages
  cancel-in-progress: true

jobs:

  # ============================================================
  # GENERAR EXAMEN
  # ============================================================
  generate:
    name: Generar examen
    runs-on: ubuntu-latest
    timeout-minutes: 20

    permissions:
      contents: write
      pages: write
      id-token: write

    steps:

      # 1. Descargar el repositorio
      - name: Descargar repositorio
        uses: actions/checkout@v6
        with:
          ref: ${{ github.event.repository.default_branch }}
          fetch-depth: 0

      # 2. Configurar Python
      - name: Configurar Python
        uses: actions/setup-python@v6
        with:
          python-version: "3.12"

      # 3. Instalar dependencias
      - name: Instalar dependencias
        shell: bash
        run: |
          python -m pip install --upgrade pip

          if [ -f "requirements.txt" ]; then
            python -m pip install -r requirements.txt
          else
            echo "No existe requirements.txt. Instalando OpenAI..."
            python -m pip install openai
          fi

      # 4. Comprobar que existe OPENAI_API_KEY
      - name: Comprobar clave de OpenAI
        shell: bash
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          if [ -z "${OPENAI_API_KEY:-}" ]; then
            echo "::error::No existe el secreto OPENAI_API_KEY."
            echo "::error::Añádelo en Settings > Secrets and variables > Actions."
            exit 1
          fi

          echo "OPENAI_API_KEY encontrada correctamente."

      # 5. Generar SIEMPRE un examen nuevo
      #
      # FORCE_CREATE=true hace que generate_exam.py cree
      # un examen aunque ya exista otro del mismo día.
      - name: Generar examen nuevo
        shell: bash
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          FORCE_CREATE: "true"
        run: |
          echo "Generando un examen nuevo..."
          python scripts/generate_exam.py

      # 6. Comprobar que el generador modificó exams.json
      - name: Comprobar examen generado
        shell: bash
        run: |
          if [ ! -f "data/exams.json" ]; then
            echo "::error::No existe data/exams.json."
            exit 1
          fi

          if git diff --quiet -- data/exams.json; then
            echo "::error::generate_exam.py terminó pero data/exams.json no cambió."
            exit 1
          fi

          echo "data/exams.json se ha actualizado correctamente."
          ls -lh data/exams.json

      # 7. Guardar el nuevo exams.json en GitHub
      - name: Guardar examen en GitHub
        shell: bash
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

          git add data/exams.json

          FECHA_MADRID="$(TZ=Europe/Madrid date +'%Y-%m-%d %H:%M:%S')"

          git commit -m "Nuevo examen RTVE - ${FECHA_MADRID}"

          git push origin HEAD:${{ github.event.repository.default_branch }}

      # 8. Comprobar que existe index.html
      - name: Comprobar página web
        shell: bash
        run: |
          if [ ! -f "index.html" ]; then
            echo "::error::No existe index.html."
            exit 1
          fi

          echo "index.html encontrado."

      # 9. Preparar los archivos que se publicarán
      - name: Preparar página web
        shell: bash
        run: |
          rm -rf "_site"
          mkdir -p "_site"

          rsync -av \
            --exclude=".git/" \
            --exclude=".github/" \
            --exclude="_site/" \
            --exclude="scripts/" \
            --exclude="requirements.txt" \
            --exclude="__pycache__/" \
            --exclude="*.py" \
            --exclude="*.pyc" \
            ./ "_site/"

          touch "_site/.nojekyll"

          if [ ! -f "_site/index.html" ]; then
            echo "::error::No existe _site/index.html."
            exit 1
          fi

          if [ ! -f "_site/data/exams.json" ]; then
            echo "::error::No existe _site/data/exams.json."
            exit 1
          fi

          echo "Página preparada correctamente."
          echo ""
          echo "Archivos que se publicarán:"
          find "_site" -maxdepth 4 -type f | sort

      # 10. Configurar GitHub Pages
      - name: Configurar GitHub Pages
        uses: actions/configure-pages@v5

      # 11. Crear el artefacto de GitHub Pages
      #
      # El nombre incluye run_id y run_attempt para evitar
      # el problema anterior de dos artefactos github-pages.
      - name: Subir página
        uses: actions/upload-pages-artifact@v5
        with:
          name: github-pages-${{ github.run_id }}-${{ github.run_attempt }}
          path: ./_site
          retention-days: 1


  # ============================================================
  # PUBLICAR GITHUB PAGES
  # ============================================================
  deploy:
    name: Publicar en GitHub Pages
    needs: generate
    runs-on: ubuntu-latest
    timeout-minutes: 20

    permissions:
      contents: read
      pages: write
      id-token: write

    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}

    steps:

      # 12. Publicar exactamente el artefacto creado arriba
      - name: Publicar en GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v5
        with:
          artifact_name: github-pages-${{ github.run_id }}-${{ github.run_attempt }}
          timeout: 1200000