# Oposición Editor RTVE — web interactiva

## Qué incluye

- Portada con todos los exámenes.
- Estados **Pendiente**, **En curso** y **Realizado**.
- Nota junto a cada examen terminado.
- Estadísticas de realizados, pendientes, media y mejor resultado.
- Guardado automático de respuestas y resultados en el navegador del iPhone.
- Instalación como icono en la pantalla de inicio.
- Generación diaria opcional mediante GitHub Actions y OpenAI API.
- Despliegue automático en Netlify al actualizar GitHub.

## Importante sobre los resultados

Los resultados se guardan con `localStorage` bajo el dominio de tu web de Netlify.

- Permanecen al cerrar Safari y al actualizar la web.
- Permanecen cuando se publican nuevos exámenes en el mismo dominio.
- Son locales a ese navegador y dispositivo.
- Se perderán si borras los datos de Safari, cambias de dominio o usas otro dispositivo.

Para sincronización entre iPhone, ordenador y otros dispositivos hace falta añadir una base de datos y un inicio de sesión, por ejemplo Supabase o Firebase.

## Publicación inicial

### Opción rápida

Arrastra toda esta carpeta a Netlify Drop.

### Opción recomendada para automatizar

1. Crea un repositorio en GitHub.
2. Sube el contenido de esta carpeta a la raíz del repositorio.
3. En Netlify, abre tu proyecto y vincúlalo al repositorio:
   `Project configuration → Build & deploy → Continuous deployment → Repository`.
4. Usa la rama `main` y el directorio de publicación `.`.
5. Cada cambio enviado a GitHub actualizará automáticamente la web.

## Activar un examen nuevo cada día

La automatización usa `.github/workflows/daily-exam.yml`.

1. Crea una clave de API en la plataforma de OpenAI.
2. En GitHub abre:
   `Settings → Secrets and variables → Actions → New repository secret`.
3. Crea el secreto:
   - Nombre: `OPENAI_API_KEY`
   - Valor: tu clave de API.
4. Abre la pestaña `Actions`.
5. Selecciona `Generar examen diario`.
6. Pulsa `Run workflow` para hacer una prueba manual.
7. El flujo está programado a las 08:10 en la zona `Europe/Madrid`.
8. El proceso genera un examen, actualiza `data/exams.json`, hace commit y Netlify lo publica.

La API de OpenAI se factura aparte de la suscripción de ChatGPT.

## Añadir a la pantalla de inicio del iPhone

1. Abre la URL de Netlify en Safari.
2. Pulsa Compartir.
3. Selecciona `Añadir a pantalla de inicio`.
4. Abre la app desde el nuevo icono.

## Actualizar desde el iPhone

Dentro de la web pulsa el botón `↻`. El archivo `exams.json` se descarga de nuevo sin caché.

## Personalizar contenidos

Edita `reference/rtve_topics.txt` para cambiar la mezcla de materias o añadir temas de nuevos exámenes oficiales.
