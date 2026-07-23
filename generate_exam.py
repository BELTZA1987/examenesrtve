import json
import os
from datetime import date
from pathlib import Path

from openai import OpenAI

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "exams.json"
REFERENCE_FILE = ROOT / "reference" / "rtve_topics.txt"

client = OpenAI()
model = os.getenv("OPENAI_MODEL", "gpt-5-mini")

data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
existing = data.get("exams", [])
next_number = max([int(exam["id"]) for exam in existing] or [0]) + 1
exam_id = f"{next_number:03d}"

recent_questions = []
for exam in existing[:5]:
    recent_questions.extend(question["prompt"] for question in exam["questions"])
recent_text = "\n".join(f"- {question}" for question in recent_questions[-100:])

reference = REFERENCE_FILE.read_text(encoding="utf-8")

schema = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "level": {"type": "string"},
        "timeMinutes": {"type": "integer", "minimum": 15, "maximum": 45},
        "blocks": {
            "type": "array",
            "minItems": 4,
            "maxItems": 8,
            "items": {"type": "string"}
        },
        "questions": {
            "type": "array",
            "minItems": 20,
            "maxItems": 20,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "prompt": {"type": "string"},
                    "options": {
                        "type": "array",
                        "minItems": 4,
                        "maxItems": 4,
                        "items": {"type": "string"}
                    },
                    "correctIndex": {"type": "integer", "minimum": 0, "maximum": 3},
                    "explanation": {"type": "string"},
                    "category": {"type": "string"}
                },
                "required": ["prompt", "options", "correctIndex", "explanation", "category"]
            }
        }
    },
    "required": ["level", "timeMinutes", "blocks", "questions"]
}

prompt = f"""
Genera el examen diario número {exam_id} para la oposición de Edición, Montaje y Procesos Audiovisuales de RTVE.

CONDICIONES:
- Exactamente 20 preguntas, cuatro opciones y una sola respuesta correcta.
- Nivel alto, pero sin preguntas capciosas ni respuestas ambiguas.
- Equilibrio entre fundamentos y operación broadcast.
- Inspírate en la referencia temática, no copies literalmente preguntas reales.
- Evita repetir las preguntas recientes; se pueden repetir conceptos importantes con otro enfoque.
- Todas las explicaciones deben justificar por qué la opción correcta lo es.
- Redacción en español de España.
- No incluyas Markdown.

REFERENCIA:
{reference}

PREGUNTAS RECIENTES QUE DEBES EVITAR REPETIR:
{recent_text or "Todavía no hay preguntas anteriores."}
"""

response = client.responses.create(
    model=model,
    input=prompt,
    text={
        "format": {
            "type": "json_schema",
            "name": "rtve_daily_exam",
            "strict": True,
            "schema": schema
        }
    }
)

generated = json.loads(response.output_text)
exam = {
    "id": exam_id,
    "title": f"Examen {exam_id}",
    "date": date.today().isoformat(),
    **generated
}

# Newest first; the web also sorts defensively.
data["exams"] = [exam] + existing
data["updatedAt"] = date.today().isoformat()
DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Creado {exam['title']} con {len(exam['questions'])} preguntas.")
