from __future__ import annotations

import json
import os
import random
import sys
from datetime import date
from pathlib import Path
from typing import Any

from openai import OpenAI, APIError, AuthenticationError, RateLimitError

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "exams.json"
REFERENCE_FILE = ROOT / "reference" / "rtve_topics.txt"

MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
FORCE_CREATE = os.getenv("FORCE_CREATE", "false").lower() in {"1", "true", "yes"}
TODAY = date.today().isoformat()


def load_data() -> dict[str, Any]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"No existe {DATA_FILE}")
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    if not isinstance(data.get("exams"), list):
        raise ValueError("data/exams.json no contiene una lista 'exams'.")
    return data


def validate_generated(exam: dict[str, Any]) -> None:
    questions = exam.get("questions")
    if not isinstance(questions, list) or len(questions) != 20:
        raise ValueError("El modelo no generó exactamente 20 preguntas.")

    seen_prompts: set[str] = set()
    for number, question in enumerate(questions, start=1):
        prompt = str(question.get("prompt", "")).strip()
        options = question.get("options")
        correct = question.get("correctIndex")
        explanation = str(question.get("explanation", "")).strip()
        category = str(question.get("category", "")).strip()

        if not prompt or prompt.casefold() in seen_prompts:
            raise ValueError(f"Pregunta {number} vacía o duplicada.")
        seen_prompts.add(prompt.casefold())

        if not isinstance(options, list) or len(options) != 4:
            raise ValueError(f"La pregunta {number} no tiene cuatro opciones.")
        if len({str(option).strip().casefold() for option in options}) != 4:
            raise ValueError(f"La pregunta {number} contiene opciones repetidas.")
        if not isinstance(correct, int) or correct not in range(4):
            raise ValueError(f"Índice de respuesta inválido en la pregunta {number}.")
        if not explanation or not category:
            raise ValueError(f"Falta explicación o categoría en la pregunta {number}.")


def rotate_options(exam: dict[str, Any], seed: int) -> None:
    """Distribuye las letras correctas para evitar que casi todas sean B."""
    rng = random.Random(seed)
    for question in exam["questions"]:
        options = list(question["options"])
        correct_text = options[question["correctIndex"]]
        rng.shuffle(options)
        question["options"] = options
        question["correctIndex"] = options.index(correct_text)


def main() -> int:
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: falta el secreto OPENAI_API_KEY.", file=sys.stderr)
        return 2

    data = load_data()
    existing: list[dict[str, Any]] = data["exams"]

    if not FORCE_CREATE and any(exam.get("date") == TODAY for exam in existing):
        print(f"Ya existe un examen con fecha {TODAY}; no se crea un duplicado.")
        return 0

    next_number = max([int(exam["id"]) for exam in existing if str(exam.get("id", "")).isdigit()] or [0]) + 1
    exam_id = f"{next_number:03d}"

    recent_questions: list[str] = []
    for exam in existing[:6]:
        recent_questions.extend(
            str(question.get("prompt", ""))
            for question in exam.get("questions", [])
        )

    reference = REFERENCE_FILE.read_text(encoding="utf-8")

    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "level": {"type": "string"},
            "timeMinutes": {"type": "integer", "minimum": 20, "maximum": 40},
            "blocks": {
                "type": "array",
                "minItems": 5,
                "maxItems": 8,
                "items": {"type": "string"},
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
                        "category": {"type": "string"},
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

    recent_text = "\n".join(f"- {question}" for question in recent_questions[-120:])

    prompt = f"""
Genera el examen {exam_id} para la oposición de Edición, Montaje y Procesos
Audiovisuales de RTVE.

REQUISITOS:
- Exactamente 20 preguntas tipo test.
- Cuatro opciones y una sola respuesta inequívocamente correcta.
- Nivel alto, equivalente a una oposición técnica.
- Mezcla fundamentos y operación broadcast.
- No copies literalmente un examen real.
- Evita repetir las preguntas recientes. Se pueden repetir conceptos con un
  enfoque distinto.
- Redacción en español de España.
- Explica con rigor por qué la respuesta correcta lo es.
- No uses opciones absurdas ni pistas gramaticales.
- Distribuye los temas de forma equilibrada.
- Devuelve únicamente el JSON solicitado.

REFERENCIA TEMÁTICA:
{reference}

PREGUNTAS RECIENTES:
{recent_text or "No hay preguntas anteriores."}
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
        print("ERROR: la clave OPENAI_API_KEY no es válida o no tiene acceso.", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 3
    except RateLimitError as exc:
        print("ERROR: falta saldo, cuota o se ha alcanzado un límite de la API.", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 4
    except APIError as exc:
        print(f"ERROR de OpenAI API: {exc}", file=sys.stderr)
        return 5

    if response.status not in {None, "completed"}:
        raise RuntimeError(f"La respuesta terminó con estado {response.status!r}.")

    generated = json.loads(response.output_text)
    validate_generated(generated)
    rotate_options(generated, seed=next_number)

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
        f"Creado {exam['title']} con {len(exam['questions'])} preguntas "
        f"usando {MODEL}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
