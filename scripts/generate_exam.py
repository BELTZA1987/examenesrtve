from __future__ import annotations

import json
import os
import random
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from openai import APIError, AuthenticationError, OpenAI, RateLimitError

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "exams.json"
REFERENCE_FILE = ROOT / "reference" / "rtve_topics.txt"

MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
FORCE_CREATE = os.getenv("FORCE_CREATE", "false").lower() in {"1", "true", "yes"}
TODAY = date.today().isoformat()

BANNED_OPTION_PATTERNS = (
    "todas las anteriores",
    "ninguna de las anteriores",
    "a y b son correctas",
    "todas son correctas",
)

OFFICIAL_BLOCKS = (
    "Temario general y normativa RTVE",
    "Conocimientos básicos",
    "Tratamiento digital de la señal de televisión",
    "Equipos de medida y control",
    "Grabación y reproducción de vídeo",
    "Edición de vídeo",
    "Lenguaje audiovisual y teoría del montaje",
    "Prevención de riesgos laborales",
)


def load_data() -> dict[str, Any]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"No existe {DATA_FILE}")

    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    if not isinstance(data.get("exams"), list):
        raise ValueError("data/exams.json no contiene una lista 'exams'.")

    return data


def normalize_text(value: str) -> str:
    value = value.casefold().strip()
    value = re.sub(r"\s+", " ", value)
    return value


def validate_generated(exam: dict[str, Any]) -> None:
    questions = exam.get("questions")

    if not isinstance(questions, list) or len(questions) != 20:
        raise ValueError("El modelo no generó exactamente 20 preguntas.")

    seen_prompts: set[str] = set()
    category_counts: dict[str, int] = {}

    for number, question in enumerate(questions, start=1):
        prompt = str(question.get("prompt", "")).strip()
        options = question.get("options")
        correct = question.get("correctIndex")
        explanation = str(question.get("explanation", "")).strip()
        category = str(question.get("category", "")).strip()

        normalized_prompt = normalize_text(prompt)

        if len(prompt) < 25:
            raise ValueError(f"La pregunta {number} es demasiado breve.")
        if normalized_prompt in seen_prompts:
            raise ValueError(f"La pregunta {number} está duplicada.")
        seen_prompts.add(normalized_prompt)

        if not isinstance(options, list) or len(options) != 4:
            raise ValueError(f"La pregunta {number} no tiene cuatro opciones.")

        normalized_options = [normalize_text(str(option)) for option in options]
        if any(not option for option in normalized_options):
            raise ValueError(f"La pregunta {number} contiene una opción vacía.")
        if len(set(normalized_options)) != 4:
            raise ValueError(f"La pregunta {number} contiene opciones repetidas.")
        if any(
            banned in option
            for option in normalized_options
            for banned in BANNED_OPTION_PATTERNS
        ):
            raise ValueError(
                f"La pregunta {number} contiene una opción global no permitida."
            )

        if not isinstance(correct, int) or correct not in range(4):
            raise ValueError(
                f"Índice de respuesta inválido en la pregunta {number}."
            )

        if len(explanation) < 35:
            raise ValueError(
                f"La explicación de la pregunta {number} es insuficiente."
            )

        if category not in OFFICIAL_BLOCKS:
            raise ValueError(
                f"Categoría no válida en la pregunta {number}: {category!r}."
            )

        category_counts[category] = category_counts.get(category, 0) + 1

    if category_counts.get("Temario general y normativa RTVE", 0) != 3:
        raise ValueError("El examen debe contener exactamente 3 preguntas normativas.")

    missing_specific = [
        block
        for block in OFFICIAL_BLOCKS[1:]
        if category_counts.get(block, 0) < 1
    ]
    if missing_specific:
        raise ValueError(
            "Faltan bloques específicos: " + ", ".join(missing_specific)
        )

    overloaded = {
        block: count
        for block, count in category_counts.items()
        if block != "Temario general y normativa RTVE" and count > 4
    }
    if overloaded:
        raise ValueError(f"Hay bloques sobrerrepresentados: {overloaded}")


def balance_correct_answers(exam: dict[str, Any], seed: int) -> None:
    """Reparte las respuestas correctas: cinco A, cinco B, cinco C y cinco D."""
    rng = random.Random(seed)
    target_positions = [0, 1, 2, 3] * 5
    rng.shuffle(target_positions)

    for question, target_index in zip(exam["questions"], target_positions):
        options = list(question["options"])
        current_index = question["correctIndex"]

        options[current_index], options[target_index] = (
            options[target_index],
            options[current_index],
        )

        question["options"] = options
        question["correctIndex"] = target_index


def main() -> int:
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: falta el secreto OPENAI_API_KEY.", file=sys.stderr)
        return 2

    data = load_data()
    existing: list[dict[str, Any]] = data["exams"]

    if not FORCE_CREATE and any(exam.get("date") == TODAY for exam in existing):
        print(f"Ya existe un examen con fecha {TODAY}; no se crea un duplicado.")
        return 0

    numeric_ids = [
        int(str(exam.get("id", "")).strip())
        for exam in existing
        if str(exam.get("id", "")).strip().isdigit()
    ]
    next_number = max(numeric_ids, default=0) + 1
    exam_id = f"{next_number:03d}"

    recent_questions: list[str] = []
    recent_categories: list[str] = []

    for exam in existing[:10]:
        for question in exam.get("questions", []):
            recent_questions.append(str(question.get("prompt", "")).strip())
            recent_categories.append(str(question.get("category", "")).strip())

    reference = REFERENCE_FILE.read_text(encoding="utf-8")

    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "level": {
                "type": "string",
                "enum": ["Alto", "Muy alto"],
            },
            "timeMinutes": {
                "type": "integer",
                "minimum": 30,
                "maximum": 45,
            },
            "blocks": {
                "type": "array",
                "minItems": 6,
                "maxItems": 8,
                "items": {
                    "type": "string",
                    "enum": list(OFFICIAL_BLOCKS),
                },
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
                            "items": {"type": "string"},
                        },
                        "correctIndex": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 3,
                        },
                        "explanation": {"type": "string"},
                        "category": {
                            "type": "string",
                            "enum": list(OFFICIAL_BLOCKS),
                        },
                    },
                    "required": [
                        "prompt",
                        "options",
                        "correctIndex",
                        "explanation",
                        "category",
                    ],
                },
            },
        },
        "required": ["level", "timeMinutes", "blocks", "questions"],
    }

    recent_text = "\n".join(
        f"- {question}" for question in recent_questions[-200:] if question
    )
    category_text = ", ".join(
        category for category in recent_categories[-100:] if category
    )

    prompt = f"""
Actúa como miembro experto de un comité de valoración de una oposición técnica
de RTVE. Genera el EXAMEN {exam_id} para la ocupación tipo Edición, Montaje y
Procesos Audiovisuales.

JERARQUÍA DE REFERENCIAS
1. El temario oficial completo incluido más abajo. No salgas de su ámbito.
2. El estilo de exámenes reales anteriores de RTVE: preguntas objetivas,
   técnicas, precisas y con distractores verosímiles.
3. Normas técnicas y documentación primaria de fabricantes cuando sirvan para
   desarrollar un epígrafe oficial.
4. No inventes normas, funciones, artículos legales ni capacidades de equipos.

COMPOSICIÓN OBLIGATORIA
- Exactamente 20 preguntas.
- Exactamente 3 preguntas de “Temario general y normativa RTVE”.
- 17 preguntas del temario específico.
- Al menos una pregunta de cada uno de los siete bloques específicos.
- Ningún bloque específico puede superar 4 preguntas.
- Entre 7 y 10 preguntas deben ser casos prácticos breves: diagnóstico,
  elección de flujo, interpretación de medida o consecuencia técnica.
- Incluye contenidos de Avid Media Composer, gestión colaborativa
  Interplay/MediaCentral, EVS/IPDirector y XDCAM cuando encajen en los
  epígrafes oficiales, sin fingir que todos esos nombres aparecen literalmente
  en el Anexo 2.
- Alterna fundamento, operación, diagnóstico y lenguaje de montaje.

CALIDAD DE LAS PREGUNTAS
- Nivel alto o muy alto, pero evaluable con el temario.
- Cuatro opciones y una única respuesta inequívocamente correcta.
- Los tres distractores deben ser plausibles y pertenecer al mismo campo
  semántico que la respuesta correcta.
- Evita respuestas evidentes por longitud, gramática, precisión o tono.
- No uses “todas las anteriores”, “ninguna de las anteriores” ni combinaciones
  del tipo “A y B”.
- No plantees preguntas basadas en marcas salvo que evalúen una función o flujo
  profesional relevante.
- No conviertas preferencias de trabajo en verdades universales.
- En normativa, pregunta por contenido sustantivo y no por detalles triviales
  como números de BOE o fechas, salvo que sean jurídicamente relevantes.
- En la explicación, justifica la correcta y aclara brevemente por qué el
  distractor más próximo no lo es.
- Redacta en español de España.
- Devuelve únicamente el JSON exigido por el esquema.

CONTROL DE REPETICIONES
- No repitas literalmente ninguna pregunta reciente.
- No reformules superficialmente una pregunta reciente cambiando solo cifras,
  códec, marca o orden.
- Se puede volver sobre un concepto esencial únicamente desde otra competencia:
  aplicación, diagnóstico, comparación o consecuencia.
- Usa la distribución reciente de categorías para compensar temas poco usados.

TEMARIO Y MAPA DE DESARROLLO:
{reference}

PREGUNTAS RECIENTES QUE DEBES EVITAR:
{recent_text or "No hay preguntas anteriores."}

CATEGORÍAS RECIENTES:
{category_text or "No hay historial."}
""".strip()

    client = OpenAI()

    try:
        response = client.responses.create(
            model=MODEL,
            input=prompt,
            store=False,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "rtve_daily_exam",
                    "strict": True,
                    "schema": schema,
                }
            },
        )
    except AuthenticationError as exc:
        print(
            "ERROR: la clave OPENAI_API_KEY no es válida o no tiene acceso.",
            file=sys.stderr,
        )
        print(str(exc), file=sys.stderr)
        return 3
    except RateLimitError as exc:
        print(
            "ERROR: falta saldo, cuota o se ha alcanzado un límite de la API.",
            file=sys.stderr,
        )
        print(str(exc), file=sys.stderr)
        return 4
    except APIError as exc:
        print(f"ERROR de OpenAI API: {exc}", file=sys.stderr)
        return 5

    if response.status not in {None, "completed"}:
        raise RuntimeError(
            f"La respuesta terminó con estado {response.status!r}."
        )

    generated = json.loads(response.output_text)
    validate_generated(generated)
    balance_correct_answers(generated, seed=next_number)

    exam = {
        "id": exam_id,
        "title": f"Examen {exam_id}",
        "date": TODAY,
        **generated,
    }

    data["exams"] = [exam] + existing
    data["updatedAt"] = TODAY

    DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        f"Creado {exam['title']} con 20 preguntas usando {MODEL}. "
        "Respuestas equilibradas: 5 A, 5 B, 5 C y 5 D."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
