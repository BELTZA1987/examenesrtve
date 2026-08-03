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
TOPIC_PLAN = [
    "Señal de vídeo",
    "Audio digital",
    "Colorimetría",
    "Espacios de color",
    "Codecs",
    "Contenedores",
    "Avid Media Composer",
    "Interplay / MediaCentral",
    "EVS / IPDirector",
    "XDCAM",
    "Código de tiempo",
    "Sincronismo",
    "Almacenamiento RAID",
    "LTO / LTFS",
    "Redes audiovisuales",
    "Medida y control",
    "Lenguaje audiovisual",
    "Realización multicámara",
    "Legislación RTVE",
    "Prevención de riesgos"
]

QUESTION_TYPES = [
    "definición",
    "comparación",
    "aplicación",
    "configuración",
    "compatibilidad",
    "flujo de trabajo",
    "diagnóstico",
    "normativa",
    "excepción",
    "procedimiento",
    "cálculo",
    "identificación"
]

recent_categories = []
for exam in existing[:15]:
    for q in exam["questions"]:
        recent_categories.append(q.get("category", ""))

recent_categories = recent_categories[-200:]

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
Actúa como el TRIBUNAL OFICIAL de las oposiciones de RTVE.

No eres un profesor.

No eres ChatGPT.

Eres un comité formado por:

- Editor Senior RTVE
- Responsable de Continuidad
- Ingeniero Broadcast
- Operador EVS
- Especialista Avid
- Responsable de Sistemas
- Responsable de Formación RTVE

Tu misión es redactar un examen que pueda confundirse con uno oficial.

=========================
OBJETIVO
=========================

Genera exactamente 20 preguntas.

Nivel ALTO.

Una única respuesta correcta.

Sin preguntas ambiguas.

Sin respuestas absurdas.

Las cuatro opciones deben parecer plausibles.

=========================
REDACCIÓN
=========================

Imita el examen oficial RTVE.

Preguntas cortas.

Muy técnicas.

Sin frases pedagógicas.

NO escribas nunca:

- Imagina...
- Supón...
- ¿Qué harías?
- Caso práctico.

=========================
DIFICULTAD
=========================

5 preguntas fáciles.

10 medias.

5 difíciles.

=========================
TIPOS DE PREGUNTA
=========================

Alterna continuamente:

{chr(10).join("- " + t for t in QUESTION_TYPES)}

Nunca hagas tres preguntas seguidas del mismo tipo.

=========================
PLAN OBLIGATORIO
=========================

La pregunta debe pertenecer exactamente a estos bloques:

{chr(10).join(f"{i+1}. {b}" for i,b in enumerate(TOPIC_PLAN))}

No cambies el reparto.

=========================
REPETICIONES
=========================

Estas categorías ya han aparecido recientemente:

{chr(10).join("- "+c for c in recent_categories[-80:])}

Evita volver a utilizar esas categorías salvo que sea imprescindible.

No repitas:

- Avid
- RAID
- LTO
- HDR
- Codecs

más de una vez en el mismo examen.

=========================
TEMARIO
=========================

{reference}

=========================
AUDITORÍA
=========================

Antes de responder revisa:

- ¿Estoy abusando de Avid?
- ¿Estoy abusando de codecs?
- ¿Estoy abusando de RAID?
- ¿Estoy recorriendo todo el programa?
- ¿Las preguntas parecen oficiales?

Si alguna respuesta es NO,

rehaz completamente el examen.

Devuelve únicamente el JSON solicitado.
"""

best = None
best_score = -1

for _ in range(3):

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

    candidate = json.loads(response.output_text)

    categories = [q["category"] for q in candidate["questions"]]

    score = len(set(categories))

    if score > best_score:
        best = candidate
        best_score = score

generated = best
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
