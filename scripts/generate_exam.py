from __future__ import annotations

import json
import os
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from openai import APIError, AuthenticationError, OpenAI, RateLimitError

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "exams.json"
REFERENCE_FILE = ROOT / "reference" / "rtve_topics.txt"

MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
FORCE_CREATE = os.getenv("FORCE_CREATE", "false").lower() in {"1", "true", "yes"}
TODAY = date.today().isoformat()

# Umbrales y reintentos de robustez.
# Una pregunta histórica solo se rechaza si es prácticamente una reformulación.
EXAM_SIMILARITY_THRESHOLD = 0.92
HISTORY_SIMILARITY_THRESHOLD = 0.94
MAX_FULL_ATTEMPTS = 3
MAX_REPAIR_ROUNDS = 8

BANNED_OPTION_PATTERNS = (
    "todas las anteriores",
    "ninguna de las anteriores",
    "a y b son correctas",
    "todas son correctas",
)

BANNED_PROMPT_PREFIXES = (
    "caso práctico:",
    "fundamento:",
    "concepto:",
    "operación práctica:",
    "operación/diagnóstico:",
    "medida/diagnóstico:",
    "operativa/servidores:",
    "lenguaje del montaje:",
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

SPECIFIC_BLOCKS = OFFICIAL_BLOCKS[1:]

# Cada concepto es deliberadamente más concreto que un bloque del temario. La
# selección se hace en Python; el modelo solo redacta la pregunta asignada.
CONCEPTS: tuple[dict[str, Any], ...] = (
    # ------------------------------------------------------------------
    # TEMARIO GENERAL Y NORMATIVA RTVE
    # ------------------------------------------------------------------
    {
        "id": "norm_constitucion_derechos",
        "family": "norm_constitucion",
        "category": OFFICIAL_BLOCKS[0],
        "label": "Constitución: derechos fundamentales y libertad de información",
        "focus": "distinguir libertad de expresión, información veraz, límites y garantías constitucionales",
        "keywords": ("constitución", "información veraz", "libertad de expresión", "artículo 20"),
    },
    {
        "id": "norm_constitucion_igualdad",
        "family": "norm_constitucion",
        "category": OFFICIAL_BLOCKS[0],
        "label": "Constitución: igualdad y no discriminación",
        "focus": "contenido sustantivo del principio de igualdad y prohibición de discriminación",
        "keywords": ("constitución", "igualdad", "discriminación", "artículo 14"),
    },
    {
        "id": "norm_ley17_servicio_publico",
        "family": "norm_ley17",
        "category": OFFICIAL_BLOCKS[0],
        "label": "Ley 17/2006: función de servicio público",
        "focus": "misión, principios y obligaciones de servicio público de la Corporación RTVE",
        "keywords": ("ley 17/2006", "servicio público", "misión"),
    },
    {
        "id": "norm_ley17_organizacion",
        "family": "norm_ley17",
        "category": OFFICIAL_BLOCKS[0],
        "label": "Ley 17/2006: naturaleza y organización de la Corporación RTVE",
        "focus": "naturaleza jurídica, órganos y estructura básica; no repetir la pregunta genérica sobre carácter jurídico",
        "keywords": ("ley 17/2006", "corporación rtve", "naturaleza jurídica", "consejo de administración"),
    },
    {
        "id": "norm_ley5_independencia",
        "family": "norm_ley5",
        "category": OFFICIAL_BLOCKS[0],
        "label": "Ley 5/2017: independencia y pluralismo de RTVE",
        "focus": "finalidad de la reforma y elección parlamentaria de los órganos de RTVE",
        "keywords": ("ley 5/2017", "independencia", "pluralismo"),
    },
    {
        "id": "norm_ley8_financiacion",
        "family": "norm_ley8",
        "category": OFFICIAL_BLOCKS[0],
        "label": "Ley 8/2009: sistema de financiación de RTVE",
        "focus": "fuentes, restricciones y principios generales del modelo de financiación",
        "keywords": ("ley 8/2009", "financiación", "publicidad"),
    },
    {
        "id": "norm_convenio_clasificacion",
        "family": "norm_convenio",
        "category": OFFICIAL_BLOCKS[0],
        "label": "III Convenio Colectivo: clasificación y organización profesional",
        "focus": "clasificación profesional, ocupaciones tipo y organización del trabajo; no preguntar qué regula genéricamente el convenio",
        "keywords": ("convenio colectivo", "clasificación profesional", "ocupación tipo"),
    },
    {
        "id": "norm_convenio_jornada",
        "family": "norm_convenio",
        "category": OFFICIAL_BLOCKS[0],
        "label": "III Convenio Colectivo: jornada, descansos y turnos",
        "focus": "regulación laboral sustantiva sobre jornada, descanso o turnicidad",
        "keywords": ("convenio colectivo", "jornada", "descanso", "turno"),
    },
    {
        "id": "norm_igualdad_plan",
        "family": "norm_igualdad",
        "category": OFFICIAL_BLOCKS[0],
        "label": "II Plan de Igualdad y Guía de Igualdad de RTVE",
        "focus": "medidas de igualdad, prevención del acoso y lenguaje o representación no sexista",
        "keywords": ("plan de igualdad", "guía de igualdad", "acoso", "no sexista"),
    },
    {
        "id": "norm_ley13_accesibilidad",
        "family": "norm_ley13",
        "category": OFFICIAL_BLOCKS[0],
        "label": "Ley 13/2022: accesibilidad audiovisual",
        "focus": "obligaciones concretas de accesibilidad; evitar la pregunta genérica repetida sobre si la ley contempla accesibilidad",
        "keywords": ("ley 13/2022", "accesibilidad", "subtitulado", "audiodescripción"),
    },
    {
        "id": "norm_ley13_menores",
        "family": "norm_ley13",
        "category": OFFICIAL_BLOCKS[0],
        "label": "Ley 13/2022: protección de menores",
        "focus": "obligaciones de protección de menores y clasificación o acceso a contenidos",
        "keywords": ("ley 13/2022", "menores", "protección"),
    },
    {
        "id": "norm_prl_principios",
        "family": "norm_prl",
        "category": OFFICIAL_BLOCKS[0],
        "label": "Ley 31/1995: principios de la acción preventiva",
        "focus": "principios generales y obligaciones preventivas, sin repetir la fórmula genérica de garantizar seguridad y salud",
        "keywords": ("ley 31/1995", "acción preventiva", "evaluación de riesgos"),
    },

    # ------------------------------------------------------------------
    # CONOCIMIENTOS BÁSICOS
    # ------------------------------------------------------------------
    {
        "id": "basic_ohm_potencia",
        "family": "basic_electronica",
        "category": OFFICIAL_BLOCKS[1],
        "label": "Ley de Ohm y potencia eléctrica",
        "focus": "relación operativa entre tensión, corriente, resistencia y potencia en equipos audiovisuales",
        "keywords": ("ley de ohm", "tensión", "corriente", "potencia"),
    },
    {
        "id": "basic_impedancia_adaptacion",
        "family": "basic_electronica",
        "category": OFFICIAL_BLOCKS[1],
        "label": "Impedancia y adaptación de señales",
        "focus": "consecuencias de una adaptación incorrecta de impedancias en una cadena audiovisual",
        "keywords": ("impedancia", "adaptación"),
    },
    {
        "id": "basic_audio_balanceado",
        "family": "basic_audio_conexion",
        "category": OFFICIAL_BLOCKS[1],
        "label": "Audio balanceado y rechazo de modo común",
        "focus": "principio de la conexión balanceada y rechazo de interferencias; evitar repetir el caso del zumbido de 50 Hz",
        "keywords": ("balanceada", "modo común", "zumbido", "50 hz"),
    },
    {
        "id": "basic_masa_bucle",
        "family": "basic_audio_conexion",
        "category": OFFICIAL_BLOCKS[1],
        "label": "Bucles de masa y aislamiento eléctrico",
        "focus": "causa y diagnóstico de bucles de masa, sin reutilizar la solución literal de una caja DI",
        "keywords": ("bucle de masa", "ground loop", "aislamiento"),
    },
    {
        "id": "basic_cpu_gpu_ram",
        "family": "basic_informatica",
        "category": OFFICIAL_BLOCKS[1],
        "label": "CPU, GPU y RAM en postproducción",
        "focus": "diferenciar las funciones y cuellos de botella de CPU, GPU y memoria en edición y efectos",
        "keywords": ("cpu", "gpu", "ram", "efectos en tiempo real"),
    },
    {
        "id": "basic_filesystem_archivos",
        "family": "basic_informatica",
        "category": OFFICIAL_BLOCKS[1],
        "label": "Sistemas de archivos y tamaño máximo de fichero",
        "focus": "compatibilidad y limitaciones de sistemas de archivos en soportes audiovisuales",
        "keywords": ("sistema de archivos", "fat32", "ntfs", "exfat"),
    },
    {
        "id": "basic_red_ip",
        "family": "basic_redes",
        "category": OFFICIAL_BLOCKS[1],
        "label": "Direccionamiento IP, máscara y puerta de enlace",
        "focus": "diagnóstico básico de conectividad en una red de edición",
        "keywords": ("dirección ip", "máscara", "puerta de enlace"),
    },
    {
        "id": "basic_ancho_banda",
        "family": "basic_redes",
        "category": OFFICIAL_BLOCKS[1],
        "label": "Cálculo de ancho de banda para flujos audiovisuales",
        "focus": "relación entre bitrate agregado, concurrencia y margen de red",
        "keywords": ("ancho de banda", "bitrate agregado", "gigabit"),
    },
    {
        "id": "basic_rgb_ycbcr",
        "family": "basic_color",
        "category": OFFICIAL_BLOCKS[1],
        "label": "Diferencia entre RGB y YCbCr",
        "focus": "componentes y uso de RGB frente a luminancia y diferencias de color",
        "keywords": ("rgb", "ycbcr", "luminancia", "crominancia"),
    },
    {
        "id": "basic_submuestreo",
        "family": "basic_color",
        "category": OFFICIAL_BLOCKS[1],
        "label": "Submuestreo 4:4:4, 4:2:2 y 4:2:0",
        "focus": "consecuencias visuales y operativas del submuestreo; no repetir la relación numérica básica de 4:2:2",
        "keywords": ("4:4:4", "4:2:2", "4:2:0", "submuestreo"),
    },
    {
        "id": "basic_bit_depth",
        "family": "basic_color",
        "category": OFFICIAL_BLOCKS[1],
        "label": "Profundidad de bits y cuantificación de color",
        "focus": "niveles disponibles, banding y margen de procesamiento",
        "keywords": ("profundidad de bits", "10 bits", "banding"),
    },
    {
        "id": "basic_audio_muestreo",
        "family": "basic_sonido",
        "category": OFFICIAL_BLOCKS[1],
        "label": "Frecuencia de muestreo y teorema de Nyquist",
        "focus": "relación entre frecuencia de muestreo, banda audible y aliasing",
        "keywords": ("frecuencia de muestreo", "nyquist", "aliasing"),
    },
    {
        "id": "basic_dbfs",
        "family": "basic_sonido",
        "category": OFFICIAL_BLOCKS[1],
        "label": "Escala dBFS y techo digital",
        "focus": "significado y consecuencias de 0 dBFS, evitando repetir la definición literal ya usada",
        "keywords": ("0 dbfs", "dbfs", "clipping digital"),
    },
    {
        "id": "basic_fase_audio",
        "family": "basic_sonido",
        "category": OFFICIAL_BLOCKS[1],
        "label": "Fase, polaridad y cancelación en audio",
        "focus": "detección y consecuencias de problemas de fase o polaridad",
        "keywords": ("fase", "polaridad", "cancelación"),
    },

    # ------------------------------------------------------------------
    # TRATAMIENTO DIGITAL DE LA SEÑAL DE TELEVISIÓN
    # ------------------------------------------------------------------
    {
        "id": "digital_entrelazado_progresivo",
        "family": "digital_formato",
        "category": OFFICIAL_BLOCKS[2],
        "label": "Exploración entrelazada y progresiva",
        "focus": "diferencias temporales y artefactos de movimiento",
        "keywords": ("entrelazado", "progresivo", "campos"),
    },
    {
        "id": "digital_frame_rate",
        "family": "digital_formato",
        "category": OFFICIAL_BLOCKS[2],
        "label": "Frame rate y conversión de cadencia",
        "focus": "efectos de mezclar cadencias y métodos de conversión",
        "keywords": ("frame rate", "cadencia", "25p", "50p"),
    },
    {
        "id": "digital_bitrate_cbr_vbr",
        "family": "digital_compresion",
        "category": OFFICIAL_BLOCKS[2],
        "label": "Bitrate constante y variable",
        "focus": "ventajas, limitaciones y adecuación de CBR y VBR",
        "keywords": ("cbr", "vbr", "bitrate"),
    },
    {
        "id": "digital_intra_longgop",
        "family": "digital_compresion",
        "category": OFFICIAL_BLOCKS[2],
        "label": "Compresión intraframe frente a Long-GOP",
        "focus": "comparar acceso aleatorio, eficiencia, carga de decodificación y robustez de edición",
        "keywords": ("intraframe", "long-gop", "gop"),
    },
    {
        "id": "digital_gop_ipb",
        "family": "digital_compresion",
        "category": OFFICIAL_BLOCKS[2],
        "label": "Estructura GOP y fotogramas I, P y B",
        "focus": "dependencias de predicción y consecuencias de errores; no repetir cuántos frames hay que decodificar para acceso aleatorio",
        "keywords": ("gop", "fotogramas i", "fotogramas p", "fotogramas b"),
    },
    {
        "id": "digital_codec_avc_hevc",
        "family": "digital_codecs",
        "category": OFFICIAL_BLOCKS[2],
        "label": "AVC/H.264 frente a HEVC/H.265",
        "focus": "eficiencia, complejidad y compatibilidad en flujos audiovisuales",
        "keywords": ("h.264", "avc", "h.265", "hevc"),
    },
    {
        "id": "digital_codec_prores_dnx",
        "family": "digital_codecs",
        "category": OFFICIAL_BLOCKS[2],
        "label": "Códecs intermedios ProRes y DNxHR",
        "focus": "uso como códecs de postproducción, perfiles y compatibilidad",
        "keywords": ("prores", "dnxhr", "dnxhd"),
    },
    {
        "id": "digital_xavc",
        "family": "digital_codecs",
        "category": OFFICIAL_BLOCKS[2],
        "label": "Familia XAVC y sus variantes",
        "focus": "diferenciar Intra y Long-GOP, perfiles y aplicaciones",
        "keywords": ("xavc", "xavc intra", "xavc long"),
    },
    {
        "id": "digital_mxf_op1a_opatom",
        "family": "digital_contenedores",
        "category": OFFICIAL_BLOCKS[2],
        "label": "MXF OP1a frente a OP-Atom",
        "focus": "diferencia estructural y adecuación a entrega o edición; no repetir la definición aislada de OP1a",
        "keywords": ("mxf op1a", "op-atom", "op1a"),
    },
    {
        "id": "digital_mov_mp4_mxf",
        "family": "digital_contenedores",
        "category": OFFICIAL_BLOCKS[2],
        "label": "Contenedor frente a códec: MOV, MP4 y MXF",
        "focus": "distinguir encapsulado de compresión y compatibilidades",
        "keywords": ("contenedor", "mov", "mp4", "mxf"),
    },
    {
        "id": "digital_metadatos",
        "family": "digital_catalogacion",
        "category": OFFICIAL_BLOCKS[2],
        "label": "Metadatos técnicos y descriptivos",
        "focus": "función en catalogación, búsqueda e intercambio",
        "keywords": ("metadatos", "catalogación", "descriptivos"),
    },
    {
        "id": "digital_umid",
        "family": "digital_catalogacion",
        "category": OFFICIAL_BLOCKS[2],
        "label": "Identificación persistente de material mediante UMID",
        "focus": "función de identificadores únicos; no repetir la pregunta de relink proxy-alta resolución",
        "keywords": ("umid", "identificador", "proxy", "alto-res", "relink dinámico"),
    },
    {
        "id": "digital_checksum",
        "family": "digital_integridad",
        "category": OFFICIAL_BLOCKS[2],
        "label": "Checksums y verificación de integridad",
        "focus": "comparación antes/después y límites de un checksum; no repetir solo su función principal en ingesta",
        "keywords": ("checksum", "hash", "integridad"),
    },
    {
        "id": "digital_proxy_diseno",
        "family": "digital_proxy",
        "category": OFFICIAL_BLOCKS[2],
        "label": "Diseño de proxies para edición",
        "focus": "criterios de resolución, bitrate y códec; prohibido volver a preguntar qué proxy facilita scrubbing con CPU limitada",
        "keywords": ("proxy", "scrubbing", "frame-accurate", "baja latencia"),
    },
    {
        "id": "digital_hdr_sdr",
        "family": "digital_color_hdr",
        "category": OFFICIAL_BLOCKS[2],
        "label": "HDR frente a SDR",
        "focus": "rango dinámico, luminancia y compatibilidad de visualización",
        "keywords": ("hdr", "sdr", "rango dinámico"),
    },
    {
        "id": "digital_pq_hlg",
        "family": "digital_color_hdr",
        "category": OFFICIAL_BLOCKS[2],
        "label": "Curvas PQ y HLG",
        "focus": "diferencias de principio y compatibilidad de distribución",
        "keywords": ("pq", "hlg", "bt.2100"),
    },
    {
        "id": "digital_lut_log",
        "family": "digital_color_hdr",
        "category": OFFICIAL_BLOCKS[2],
        "label": "Señales logarítmicas y LUT",
        "focus": "distinguir transformación de visualización de corrección creativa",
        "keywords": ("log", "lut", "look-up table"),
    },

    # ------------------------------------------------------------------
    # EQUIPOS DE MEDIDA Y CONTROL
    # ------------------------------------------------------------------
    {
        "id": "measure_waveform_luma",
        "family": "measure_waveform",
        "category": OFFICIAL_BLOCKS[3],
        "label": "Monitor de forma de onda: luminancia y niveles",
        "focus": "uso para medir nivel y legalidad; prohibido repetir qué representa la traza vertical",
        "keywords": ("waveform", "forma de onda", "traza vertical"),
    },
    {
        "id": "measure_waveform_rgb_parade",
        "family": "measure_waveform",
        "category": OFFICIAL_BLOCKS[3],
        "label": "RGB Parade y equilibrio de canales",
        "focus": "diagnóstico de dominantes y niveles por canal",
        "keywords": ("rgb parade", "parade", "canales rgb"),
    },
    {
        "id": "measure_vectorscope",
        "family": "measure_vectorscope",
        "category": OFFICIAL_BLOCKS[3],
        "label": "Vectorscopio: fase, saturación y tono",
        "focus": "interpretación de ángulo y distancia al centro, no una definición genérica",
        "keywords": ("vectorscopio", "saturación", "fase de crominancia"),
    },
    {
        "id": "measure_skin_tone",
        "family": "measure_vectorscope",
        "category": OFFICIAL_BLOCKS[3],
        "label": "Línea de tono de piel en vectorscopio",
        "focus": "uso y límites para evaluar tonos de piel",
        "keywords": ("tono de piel", "skin tone", "vectorscopio"),
    },
    {
        "id": "measure_gamut_legalizer",
        "family": "measure_legalidad",
        "category": OFFICIAL_BLOCKS[3],
        "label": "Legalidad de señal y gamut",
        "focus": "diferencia entre niveles legales, gamut y limitación automática",
        "keywords": ("legalizer", "gamut", "niveles legales"),
    },
    {
        "id": "measure_lufs_integrated",
        "family": "measure_loudness",
        "category": OFFICIAL_BLOCKS[3],
        "label": "Loudness integrado, short-term y momentary",
        "focus": "diferenciar ventanas y aplicaciones; prohibido repetir el ajuste de -16 a -23 LUFS",
        "keywords": ("lufs", "integrado", "short-term", "momentary", "-16", "-23"),
    },
    {
        "id": "measure_true_peak",
        "family": "measure_loudness",
        "category": OFFICIAL_BLOCKS[3],
        "label": "True Peak frente a sample peak",
        "focus": "picos entre muestras y control de entrega",
        "keywords": ("true peak", "sample peak", "dbtp"),
    },
    {
        "id": "measure_correlacion_fase",
        "family": "measure_audio",
        "category": OFFICIAL_BLOCKS[3],
        "label": "Medidor de correlación de fase",
        "focus": "interpretación de compatibilidad mono y relación estéreo",
        "keywords": ("correlación", "compatibilidad mono", "fase"),
    },
    {
        "id": "measure_router_crosspoint",
        "family": "measure_matrices",
        "category": OFFICIAL_BLOCKS[3],
        "label": "Matrices: fuentes, destinos y crosspoints",
        "focus": "identificar y verificar un punto de cruce sin repetir el caso de audio enviado a cabina equivocada",
        "keywords": ("matriz", "router", "crosspoint", "enrutamiento"),
    },
    {
        "id": "measure_sdi_ancillary",
        "family": "measure_interfaces",
        "category": OFFICIAL_BLOCKS[3],
        "label": "SDI, audio embebido y datos auxiliares",
        "focus": "transporte de vídeo, audio y ANC en la interfaz",
        "keywords": ("sdi", "audio embebido", "anc"),
    },
    {
        "id": "measure_blackburst_trilevel",
        "family": "measure_sync",
        "category": OFFICIAL_BLOCKS[3],
        "label": "Black burst y tri-level sync",
        "focus": "señales de referencia y adecuación a SD/HD",
        "keywords": ("black burst", "tri-level", "sincronismo"),
    },
    {
        "id": "measure_genlock_timing",
        "family": "measure_sync",
        "category": OFFICIAL_BLOCKS[3],
        "label": "Genlock y temporización de fuentes",
        "focus": "consecuencias de fuentes no sincronizadas y corrección mediante frame sync",
        "keywords": ("genlock", "frame synchronizer", "temporización"),
    },

    # ------------------------------------------------------------------
    # GRABACIÓN Y REPRODUCCIÓN DE VÍDEO
    # ------------------------------------------------------------------
    {
        "id": "record_soportes_estado_solido",
        "family": "record_soportes",
        "category": OFFICIAL_BLOCKS[4],
        "label": "Soportes de estado sólido y su gestión",
        "focus": "ventajas, riesgos y prácticas de descarga o formateo",
        "keywords": ("tarjeta", "estado sólido", "sxs", "p2"),
    },
    {
        "id": "record_xdcam_estructura",
        "family": "record_xdcam",
        "category": OFFICIAL_BLOCKS[4],
        "label": "Estructura y metadatos de soportes XDCAM",
        "focus": "aspectos distintos de conservar carpetas e índices; por ejemplo spanning, metadatos o acceso mediante herramienta compatible",
        "keywords": ("xdcam", "estructura de carpetas", "ficheros de índice"),
    },
    {
        "id": "record_xdcam_proxy_essence",
        "family": "record_xdcam",
        "category": OFFICIAL_BLOCKS[4],
        "label": "Proxy y esencia de alta resolución en XDCAM",
        "focus": "relación y usos durante visionado, selección e ingesta",
        "keywords": ("xdcam", "proxy", "esencia"),
    },
    {
        "id": "record_ingest_capture_import",
        "family": "record_ingesta",
        "category": OFFICIAL_BLOCKS[4],
        "label": "Diferencia entre captura, importación, enlace e ingesta",
        "focus": "distinguir operaciones; prohibido volver a preguntar qué es genéricamente ingest",
        "keywords": ("ingest", "ingesta", "captura", "importación", "link"),
    },
    {
        "id": "record_ingest_verificacion",
        "family": "record_ingesta",
        "category": OFFICIAL_BLOCKS[4],
        "label": "Ingesta verificada y control de calidad",
        "focus": "secuencia de copia, checksum, validación de estructura y registro",
        "keywords": ("ingesta", "verificada", "checksum", "control de calidad"),
    },
    {
        "id": "record_servidor_concurrencia",
        "family": "record_servidores",
        "category": OFFICIAL_BLOCKS[4],
        "label": "Servidores de vídeo y acceso concurrente",
        "focus": "capacidad, ancho de banda y concurrencia de canales",
        "keywords": ("servidor de vídeo", "concurrencia", "canales"),
    },
    {
        "id": "record_raid_niveles",
        "family": "record_almacenamiento",
        "category": OFFICIAL_BLOCKS[4],
        "label": "Niveles RAID y tolerancia a fallos",
        "focus": "comparar niveles y reconstrucción, no repetir que RAID no es backup",
        "keywords": ("raid 5", "raid 6", "raid 10", "paridad"),
    },
    {
        "id": "record_backup_321",
        "family": "record_almacenamiento",
        "category": OFFICIAL_BLOCKS[4],
        "label": "Política 3-2-1 y copia de seguridad",
        "focus": "copias independientes, soportes y ubicación; prohibido repetir solo RAID frente a backup",
        "keywords": ("3-2-1", "backup", "copia de seguridad", "raid no"),
    },
    {
        "id": "record_lto_ltfs",
        "family": "record_archivo",
        "category": OFFICIAL_BLOCKS[4],
        "label": "LTO, LTFS y archivo a largo plazo",
        "focus": "acceso, catálogo, verificación y limitaciones de cinta",
        "keywords": ("lto", "ltfs", "cinta"),
    },
    {
        "id": "record_migracion_archivo",
        "family": "record_archivo",
        "category": OFFICIAL_BLOCKS[4],
        "label": "Migración y preservación de archivos",
        "focus": "obsolescencia, verificación periódica y migración de soportes",
        "keywords": ("migración", "preservación", "obsolescencia"),
    },
    {
        "id": "record_evs_loop",
        "family": "record_evs",
        "category": OFFICIAL_BLOCKS[4],
        "label": "Grabación en bucle y canales de servidor EVS",
        "focus": "principio operativo de grabación continua, canales y recuperación de acciones",
        "keywords": ("evs", "grabación en bucle", "loop"),
    },
    {
        "id": "record_evs_playlist",
        "family": "record_evs",
        "category": OFFICIAL_BLOCKS[4],
        "label": "Clips y playlists en EVS/IPDirector",
        "focus": "edición, orden, transiciones o publicación de una playlist; prohibido volver a preguntar qué es una playlist",
        "keywords": ("evs", "ipdirector", "playlist"),
    },

    # ------------------------------------------------------------------
    # EDICIÓN DE VÍDEO
    # ------------------------------------------------------------------
    {
        "id": "edit_lineal_abroll",
        "family": "edit_lineal",
        "category": OFFICIAL_BLOCKS[5],
        "label": "Edición lineal y A/B Roll",
        "focus": "función de las fuentes A/B, prelectura y mezclador en edición lineal",
        "keywords": ("a/b roll", "edición lineal", "prelectura"),
    },
    {
        "id": "edit_mezclador_key",
        "family": "edit_lineal",
        "category": OFFICIAL_BLOCKS[5],
        "label": "Mezclador de vídeo, buses y key",
        "focus": "programa, previo, key y transición en un mezclador",
        "keywords": ("mezclador de vídeo", "bus de programa", "key"),
    },
    {
        "id": "edit_offline_online",
        "family": "edit_conformado",
        "category": OFFICIAL_BLOCKS[5],
        "label": "Flujo offline/online y conformado",
        "focus": "relación entre montaje proxy, lista de decisiones y reconformado a originales",
        "keywords": ("offline", "online", "conformado"),
    },
    {
        "id": "edit_edl_aaf",
        "family": "edit_intercambio",
        "category": OFFICIAL_BLOCKS[5],
        "label": "EDL frente a AAF en intercambio de proyectos",
        "focus": "alcance, pistas, efectos y metadatos transferibles",
        "keywords": ("edl", "aaf", "intercambio"),
    },
    {
        "id": "edit_timecode_dropframe",
        "family": "edit_timecode",
        "category": OFFICIAL_BLOCKS[5],
        "label": "Código de tiempo drop-frame y non-drop-frame",
        "focus": "corrección de numeración frente a tiempo real, sin confundir con eliminación de fotogramas",
        "keywords": ("drop-frame", "non-drop", "código de tiempo"),
    },
    {
        "id": "edit_timecode_aux",
        "family": "edit_timecode",
        "category": OFFICIAL_BLOCKS[5],
        "label": "Código de tiempo auxiliar y sincronización",
        "focus": "uso de source, record o auxiliary timecode",
        "keywords": ("auxiliary timecode", "aux tc", "source timecode"),
    },
    {
        "id": "edit_multicam_timecode",
        "family": "edit_multicam",
        "category": OFFICIAL_BLOCKS[5],
        "label": "Sincronización multicámara mediante código de tiempo",
        "focus": "condiciones y tratamiento de cámaras con TC común",
        "keywords": ("multicámara", "código de tiempo común", "sync"),
    },
    {
        "id": "edit_multicam_waveform",
        "family": "edit_multicam",
        "category": OFFICIAL_BLOCKS[5],
        "label": "Sincronización multicámara por forma de onda de audio",
        "focus": "condiciones de fiabilidad y limitaciones; no repetir la pregunta genérica sobre qué método automático se usa",
        "keywords": ("multicámara", "forma de onda de audio", "sincronizar ángulos"),
    },
    {
        "id": "edit_alpha_premult",
        "family": "edit_composicion",
        "category": OFFICIAL_BLOCKS[5],
        "label": "Canal alpha premultiplicado y straight",
        "focus": "halos, interpretación y composición de gráficos",
        "keywords": ("alpha", "premultiplicado", "straight"),
    },
    {
        "id": "edit_chromakey",
        "family": "edit_composicion",
        "category": OFFICIAL_BLOCKS[5],
        "label": "Chromakey: matte, spill y bordes",
        "focus": "orden y diagnóstico del proceso de incrustación",
        "keywords": ("chromakey", "spill", "matte"),
    },
    {
        "id": "edit_color_primaries",
        "family": "edit_color",
        "category": OFFICIAL_BLOCKS[5],
        "label": "Corrección primaria y secundaria de color",
        "focus": "diferenciar ajustes globales y selectivos",
        "keywords": ("corrección primaria", "secundaria", "colorización"),
    },
    {
        "id": "edit_color_order",
        "family": "edit_color",
        "category": OFFICIAL_BLOCKS[5],
        "label": "Orden de operaciones en colorización",
        "focus": "normalización, balance, contraste, matching y look",
        "keywords": ("orden de nodos", "balance", "matching", "look"),
    },
    {
        "id": "edit_project_media",
        "family": "edit_avid_media",
        "category": OFFICIAL_BLOCKS[5],
        "label": "Proyecto, bins y media en un NLE",
        "focus": "diferenciar metadatos de proyecto y archivos de esencia",
        "keywords": ("bin", "proyecto", "media files"),
    },
    {
        "id": "edit_matchframe",
        "family": "edit_avid_commands",
        "category": OFFICIAL_BLOCKS[5],
        "label": "Match Frame y localización de fuente",
        "focus": "variantes o límites del comando; prohibido volver a preguntar qué realiza esencialmente Match Frame",
        "keywords": ("match frame", "fuente original", "fotograma en la secuencia"),
    },
    {
        "id": "edit_trim_modes",
        "family": "edit_avid_commands",
        "category": OFFICIAL_BLOCKS[5],
        "label": "Trim: ripple, roll y slip/slide",
        "focus": "efectos sobre duración, sincronía y puntos de corte",
        "keywords": ("trim", "ripple", "roll", "slip", "slide"),
    },
    {
        "id": "edit_consolidate_transcode",
        "family": "edit_avid_media",
        "category": OFFICIAL_BLOCKS[5],
        "label": "Consolidate frente a Transcode",
        "focus": "diferencias de copia, handles y cambio de códec; prohibido repetir qué realiza la operación de forma genérica",
        "keywords": ("consolidate", "transcode", "handles"),
    },
    {
        "id": "edit_relink",
        "family": "edit_avid_media",
        "category": OFFICIAL_BLOCKS[5],
        "label": "Criterios de relink y gestión de versiones",
        "focus": "criterios de coincidencia y resolución de enlaces incorrectos, sin repetir UMID proxy-alta resolución",
        "keywords": ("relink", "desvinculado", "offline media"),
    },
    {
        "id": "edit_shared_bins",
        "family": "edit_colaborativa",
        "category": OFFICIAL_BLOCKS[5],
        "label": "Bloqueo de bins y trabajo colaborativo",
        "focus": "concurrencia, permisos y prevención de sobrescrituras",
        "keywords": ("bin locking", "bloqueo de bin", "colaborativo"),
    },
    {
        "id": "edit_nexis_bandwidth",
        "family": "edit_colaborativa",
        "category": OFFICIAL_BLOCKS[5],
        "label": "Almacenamiento compartido y reservas de ancho de banda",
        "focus": "rendimiento concurrente en NEXIS/SAN sin convertir una marca en epígrafe oficial",
        "keywords": ("nexis", "ancho de banda", "almacenamiento compartido"),
    },
    {
        "id": "edit_directos_growing",
        "family": "edit_directos",
        "category": OFFICIAL_BLOCKS[5],
        "label": "Edición de ficheros en crecimiento durante directos",
        "focus": "flujo de growing files, disponibilidad y cierre de esencia",
        "keywords": ("growing file", "fichero en crecimiento", "directo"),
    },
    {
        "id": "edit_evs_exchange",
        "family": "edit_directos",
        "category": OFFICIAL_BLOCKS[5],
        "label": "Intercambio entre EVS y sistema de edición",
        "focus": "transferencia, handles, códec y disponibilidad durante retransmisión",
        "keywords": ("evs", "intercambio", "edición", "transferencia"),
    },
    {
        "id": "edit_export_qc",
        "family": "edit_export",
        "category": OFFICIAL_BLOCKS[5],
        "label": "Exportación y control de calidad técnico",
        "focus": "verificación de formato, niveles, sincronía, campos y metadatos",
        "keywords": ("exportación", "control de calidad", "qc"),
    },

    # ------------------------------------------------------------------
    # LENGUAJE AUDIOVISUAL Y TEORÍA DEL MONTAJE
    # ------------------------------------------------------------------
    {
        "id": "language_eje_180",
        "family": "language_continuidad",
        "category": OFFICIAL_BLOCKS[6],
        "label": "Eje de acción y regla de 180 grados",
        "focus": "continuidad espacial y cambio de eje",
        "keywords": ("eje", "180 grados", "salto de eje"),
    },
    {
        "id": "language_raccord_mirada",
        "family": "language_continuidad",
        "category": OFFICIAL_BLOCKS[6],
        "label": "Raccord de mirada y dirección",
        "focus": "coherencia espacial entre planos",
        "keywords": ("raccord de mirada", "dirección"),
    },
    {
        "id": "language_match_action",
        "family": "language_continuidad",
        "category": OFFICIAL_BLOCKS[6],
        "label": "Raccord de movimiento o match on action",
        "focus": "continuidad perceptiva del movimiento; no repetir su definición esencial",
        "keywords": ("match on action", "raccord de movimiento"),
    },
    {
        "id": "language_elipsis",
        "family": "language_tiempo",
        "category": OFFICIAL_BLOCKS[6],
        "label": "Elipsis y compresión temporal",
        "focus": "eliminación de tiempo narrativo manteniendo comprensión",
        "keywords": ("elipsis", "compresión temporal"),
    },
    {
        "id": "language_paralelo_alterno",
        "family": "language_estructuras",
        "category": OFFICIAL_BLOCKS[6],
        "label": "Montaje paralelo y alterno",
        "focus": "diferencias de simultaneidad, convergencia y asociación temática",
        "keywords": ("montaje paralelo", "montaje alterno"),
    },
    {
        "id": "language_intelectual",
        "family": "language_estructuras",
        "category": OFFICIAL_BLOCKS[6],
        "label": "Montaje intelectual y asociación de ideas",
        "focus": "creación de significado por yuxtaposición",
        "keywords": ("montaje intelectual", "yuxtaposición"),
    },
    {
        "id": "language_jcut_lcut",
        "family": "language_audio_cuts",
        "category": OFFICIAL_BLOCKS[6],
        "label": "J-cut y L-cut",
        "focus": "comparar entrada o permanencia del audio; prohibido repetir qué describe un L-cut",
        "keywords": ("l-cut", "j-cut"),
    },
    {
        "id": "language_ritmo",
        "family": "language_ritmo",
        "category": OFFICIAL_BLOCKS[6],
        "label": "Ritmo interno y externo del montaje",
        "focus": "duración de planos, movimiento interno y estructura",
        "keywords": ("ritmo interno", "ritmo externo", "duración de planos"),
    },
    {
        "id": "language_music_sync",
        "family": "language_ritmo",
        "category": OFFICIAL_BLOCKS[6],
        "label": "Sincronización del montaje con música y sonido",
        "focus": "frase musical, acentos, contrapunto y continuidad sonora",
        "keywords": ("música", "acento", "sincronización"),
    },
    {
        "id": "language_news",
        "family": "language_genres",
        "category": OFFICIAL_BLOCKS[6],
        "label": "Edición de noticias y coordinación con redacción",
        "focus": "prioridad informativa, locución, totales, recursos y tiempos",
        "keywords": ("noticias", "redacción", "totales"),
    },
    {
        "id": "language_fiction",
        "family": "language_genres",
        "category": OFFICIAL_BLOCKS[6],
        "label": "Edición de ficción y coordinación con realización",
        "focus": "continuidad dramática, interpretación y cobertura",
        "keywords": ("ficción", "realización", "continuidad dramática"),
    },
    {
        "id": "language_target",
        "family": "language_genres",
        "category": OFFICIAL_BLOCKS[6],
        "label": "Estilo de edición según género y público objetivo",
        "focus": "adaptación de ritmo, densidad y recursos al target",
        "keywords": ("target", "público objetivo", "género"),
    },
    {
        "id": "language_transition_motivation",
        "family": "language_transitions",
        "category": OFFICIAL_BLOCKS[6],
        "label": "Corte, fundido y encadenado según función narrativa",
        "focus": "elección motivada de transición y significado temporal",
        "keywords": ("fundido", "encadenado", "transición"),
    },

    # ------------------------------------------------------------------
    # PREVENCIÓN DE RIESGOS LABORALES
    # ------------------------------------------------------------------
    {
        "id": "prl_derechos_obligaciones",
        "family": "prl_general",
        "category": OFFICIAL_BLOCKS[7],
        "label": "Derechos y obligaciones en prevención",
        "focus": "información, formación, cooperación y uso correcto de medios",
        "keywords": ("derechos", "obligaciones", "prevención"),
    },
    {
        "id": "prl_pvd_pantalla",
        "family": "prl_pvd",
        "category": OFFICIAL_BLOCKS[7],
        "label": "Pantallas de visualización: colocación y reflejos",
        "focus": "distancia, altura, orientación, iluminación y reflejos; no repetir la obligación genérica del empleador",
        "keywords": ("pantallas de visualización", "reflejos", "distancia", "altura"),
    },
    {
        "id": "prl_pvd_pausas",
        "family": "prl_pvd",
        "category": OFFICIAL_BLOCKS[7],
        "label": "Pantallas de visualización: pausas y alternancia",
        "focus": "organización de tareas para reducir fatiga visual y postural",
        "keywords": ("pausas", "alternancia", "fatiga visual"),
    },
    {
        "id": "prl_musculoesqueletico",
        "family": "prl_ergonomia",
        "category": OFFICIAL_BLOCKS[7],
        "label": "Trastornos musculoesqueléticos de extremidad superior",
        "focus": "factores de riesgo y medidas preventivas en teclado, ratón y tableta",
        "keywords": ("musculoesquelético", "extremidad superior", "ratón"),
    },
    {
        "id": "prl_postura",
        "family": "prl_ergonomia",
        "category": OFFICIAL_BLOCKS[7],
        "label": "Ergonomía postural del puesto de edición",
        "focus": "ajuste de silla, apoyo lumbar, antebrazos y pies",
        "keywords": ("postura", "silla", "apoyo lumbar"),
    },
    {
        "id": "prl_incendio",
        "family": "prl_emergencias",
        "category": OFFICIAL_BLOCKS[7],
        "label": "Prevención y actuación ante incendios",
        "focus": "clases de fuego, evacuación, extintores y seguridad eléctrica",
        "keywords": ("incendio", "extintor", "evacuación"),
    },
    {
        "id": "prl_in_itinere",
        "family": "prl_desplazamientos",
        "category": OFFICIAL_BLOCKS[7],
        "label": "Accidente in itinere",
        "focus": "elementos que caracterizan el desplazamiento habitual domicilio-trabajo",
        "keywords": ("in itinere", "domicilio", "trabajo"),
    },
    {
        "id": "prl_en_mision",
        "family": "prl_desplazamientos",
        "category": OFFICIAL_BLOCKS[7],
        "label": "Accidente en misión y desplazamientos profesionales",
        "focus": "riesgos y prevención durante tareas fuera del centro habitual",
        "keywords": ("en misión", "desplazamiento profesional"),
    },
)

CONCEPT_BY_ID = {concept["id"]: concept for concept in CONCEPTS}

QUESTION_TYPES = (
    "directa",
    "comparación",
    "aplicación",
    "diagnóstico",
    "interpretación",
    "procedimiento",
    "compatibilidad",
    "excepción",
)

DIFFICULTY_PLAN = ("fácil",) * 5 + ("media",) * 10 + ("difícil",) * 5


def load_data() -> dict[str, Any]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"No existe {DATA_FILE}")

    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    if not isinstance(data.get("exams"), list):
        raise ValueError("data/exams.json no contiene una lista 'exams'.")
    return data


def normalize_text(value: str) -> str:
    value = value.casefold().strip()
    value = re.sub(r"[^a-záéíóúüñ0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def keyword_score(prompt: str, concept: dict[str, Any]) -> int:
    normalized = normalize_text(prompt)
    score = 0
    for keyword in concept["keywords"]:
        key = normalize_text(keyword)
        if key and key in normalized:
            score += 3 + len(key.split())
    return score


def infer_concept_id(question: dict[str, Any]) -> str | None:
    stored = str(question.get("conceptId", "")).strip()
    if stored in CONCEPT_BY_ID:
        return stored

    prompt = str(question.get("prompt", ""))
    if not prompt:
        return None

    ranked = sorted(
        ((keyword_score(prompt, concept), concept["id"]) for concept in CONCEPTS),
        reverse=True,
    )
    if ranked and ranked[0][0] >= 4:
        return ranked[0][1]
    return None


def build_history(existing: list[dict[str, Any]]) -> tuple[Counter[str], Counter[str], dict[str, int]]:
    concept_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    last_seen: dict[str, int] = {}

    # index 0 = examen más reciente. La penalización por recencia se calcula aparte.
    for exam_age, exam in enumerate(existing):
        for question in exam.get("questions", []):
            concept_id = infer_concept_id(question)
            if not concept_id:
                continue
            concept = CONCEPT_BY_ID[concept_id]
            concept_counts[concept_id] += 1
            family_counts[concept["family"]] += 1
            last_seen.setdefault(concept_id, exam_age)
            last_seen.setdefault(f"family:{concept['family']}", exam_age)

    return concept_counts, family_counts, last_seen


def category_targets(rng: random.Random, family_counts: Counter[str]) -> dict[str, int]:
    # Distribución estable basada en la amplitud de los epígrafes oficiales.
    # La variedad se obtiene rotando conceptos, no alterando cada día el peso del
    # examen hasta producir cuatro preguntas de PRL o de un bloque menor.
    return {
        "Conocimientos básicos": 2,
        "Tratamiento digital de la señal de televisión": 3,
        "Equipos de medida y control": 2,
        "Grabación y reproducción de vídeo": 3,
        "Edición de vídeo": 3,
        "Lenguaje audiovisual y teoría del montaje": 2,
        "Prevención de riesgos laborales": 2,
    }


def concept_priority(
    concept: dict[str, Any],
    concept_counts: Counter[str],
    family_counts: Counter[str],
    last_seen: dict[str, int],
    selected_families: set[str],
    rng: random.Random,
) -> float:
    concept_id = concept["id"]
    family = concept["family"]
    age = last_seen.get(concept_id, 999)
    family_age = last_seen.get(f"family:{family}", 999)

    score = 100.0
    score -= concept_counts[concept_id] * 15
    score -= family_counts[family] * 4

    # Bloqueos fuertes: la misma familia en los últimos exámenes casi nunca entra.
    if age == 0:
        score -= 1000
    elif age == 1:
        score -= 500
    elif age == 2:
        score -= 250
    elif age <= 4:
        score -= 90
    elif age <= 8:
        score -= 30

    if family_age == 0:
        score -= 350
    elif family_age == 1:
        score -= 180
    elif family_age == 2:
        score -= 90
    elif family_age <= 4:
        score -= 35

    if family in selected_families:
        score -= 1000

    # Pequeño desempate reproducible para no elegir siempre el primer concepto.
    score += rng.random() * 8
    return score


def choose_concepts(existing: list[dict[str, Any]], exam_number: int) -> list[dict[str, Any]]:
    rng = random.Random(f"rtve-{TODAY}-{exam_number}")
    concept_counts, family_counts, last_seen = build_history(existing)
    targets = category_targets(rng, family_counts)
    targets[OFFICIAL_BLOCKS[0]] = 3

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    selected_families: set[str] = set()

    for category, amount in targets.items():
        pool = [concept for concept in CONCEPTS if concept["category"] == category]
        for _ in range(amount):
            available = [c for c in pool if c["id"] not in selected_ids]
            if not available:
                raise RuntimeError(f"No hay suficientes conceptos para {category}.")

            ranked = sorted(
                available,
                key=lambda c: concept_priority(
                    c,
                    concept_counts,
                    family_counts,
                    last_seen,
                    selected_families,
                    rng,
                ),
                reverse=True,
            )
            chosen = ranked[0]
            selected.append(chosen)
            selected_ids.add(chosen["id"])
            selected_families.add(chosen["family"])

    # Mezcla manteniendo normativa distribuida y sin agrupar categorías iguales.
    normative = [c for c in selected if c["category"] == OFFICIAL_BLOCKS[0]]
    specific = [c for c in selected if c["category"] != OFFICIAL_BLOCKS[0]]
    rng.shuffle(normative)
    rng.shuffle(specific)

    ordered: list[dict[str, Any]] = []
    norm_positions = {0, 7, 14}
    for position in range(20):
        source = normative if position in norm_positions else specific
        if not source:
            source = specific or normative

        # Evita dos categorías consecutivas cuando sea posible.
        previous_category = ordered[-1]["category"] if ordered else None
        choices = [c for c in source if c["category"] != previous_category] or source
        chosen = rng.choice(choices)
        source.remove(chosen)
        ordered.append(chosen)

    difficulties = list(DIFFICULTY_PLAN)
    rng.shuffle(difficulties)
    types = list(QUESTION_TYPES) * 3
    rng.shuffle(types)

    plan: list[dict[str, Any]] = []
    for index, concept in enumerate(ordered, start=1):
        item = dict(concept)
        item["planIndex"] = index
        item["difficulty"] = difficulties[index - 1]
        item["questionType"] = types[index - 1]
        plan.append(item)

    return plan


def build_schema(plan: list[dict[str, Any]]) -> dict[str, Any]:
    allowed_ids = [item["id"] for item in plan]
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "level": {"type": "string", "enum": ["Alto", "Muy alto"]},
            "timeMinutes": {"type": "integer", "minimum": 30, "maximum": 45},
            "blocks": {
                "type": "array",
                "minItems": 6,
                "maxItems": 8,
                "items": {"type": "string", "enum": list(OFFICIAL_BLOCKS)},
            },
            "questions": {
                "type": "array",
                "minItems": 20,
                "maxItems": 20,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "planIndex": {"type": "integer", "minimum": 1, "maximum": 20},
                        "conceptId": {"type": "string", "enum": allowed_ids},
                        "difficulty": {"type": "string", "enum": ["fácil", "media", "difícil"]},
                        "questionType": {"type": "string", "enum": list(QUESTION_TYPES)},
                        "prompt": {"type": "string"},
                        "options": {
                            "type": "array",
                            "minItems": 4,
                            "maxItems": 4,
                            "items": {"type": "string"},
                        },
                        "correctIndex": {"type": "integer", "minimum": 0, "maximum": 3},
                        "explanation": {"type": "string"},
                        "category": {"type": "string", "enum": list(OFFICIAL_BLOCKS)},
                    },
                    "required": [
                        "planIndex",
                        "conceptId",
                        "difficulty",
                        "questionType",
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



def build_single_question_schema(item: dict[str, Any]) -> dict[str, Any]:
    """Esquema estricto para regenerar solo una pregunta del plan."""
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "planIndex": {"type": "integer", "enum": [item["planIndex"]]},
            "conceptId": {"type": "string", "enum": [item["id"]]},
            "difficulty": {"type": "string", "enum": [item["difficulty"]]},
            "questionType": {"type": "string", "enum": [item["questionType"]]},
            "prompt": {"type": "string"},
            "options": {
                "type": "array",
                "minItems": 4,
                "maxItems": 4,
                "items": {"type": "string"},
            },
            "correctIndex": {"type": "integer", "minimum": 0, "maximum": 3},
            "explanation": {"type": "string"},
            "category": {"type": "string", "enum": [item["category"]]},
        },
        "required": [
            "planIndex",
            "conceptId",
            "difficulty",
            "questionType",
            "prompt",
            "options",
            "correctIndex",
            "explanation",
            "category",
        ],
    }


def request_structured_json(
    client: OpenAI,
    prompt: str,
    schema: dict[str, Any],
    schema_name: str,
) -> dict[str, Any]:
    """Llama a OpenAI y devuelve el JSON estructurado."""
    response = client.responses.create(
        model=MODEL,
        input=prompt,
        store=False,
        text={
            "format": {
                "type": "json_schema",
                "name": schema_name,
                "strict": True,
                "schema": schema,
            }
        },
    )

    if response.status not in {None, "completed"}:
        raise RuntimeError(f"La respuesta terminó con estado {response.status!r}.")

    try:
        parsed = json.loads(response.output_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"OpenAI devolvió JSON no válido: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("OpenAI no devolvió un objeto JSON.")
    return parsed

def recent_prompt_list(existing: list[dict[str, Any]], limit: int = 320) -> list[str]:
    prompts: list[str] = []
    for exam in existing:
        for question in exam.get("questions", []):
            prompt = str(question.get("prompt", "")).strip()
            if prompt:
                prompts.append(prompt)
            if len(prompts) >= limit:
                return prompts
    return prompts


def similarity(a: str, b: str) -> float:
    na = normalize_text(a)
    nb = normalize_text(b)
    if not na or not nb:
        return 0.0

    sequence = SequenceMatcher(None, na, nb).ratio()
    sa = set(na.split())
    sb = set(nb.split())
    jaccard = len(sa & sb) / max(1, len(sa | sb))
    return max(sequence, jaccard)


def question_validation_error(
    question: dict[str, Any],
    assigned: dict[str, Any],
    accepted_prompts: list[str],
    recent_prompts: list[str],
) -> str | None:
    """Devuelve el motivo de rechazo de una pregunta o None si es válida."""
    if not isinstance(question, dict):
        return "la pregunta no es un objeto JSON"

    index = question.get("planIndex")
    concept_id = str(question.get("conceptId", ""))
    prompt = str(question.get("prompt", "")).strip()
    options = question.get("options")
    correct = question.get("correctIndex")
    explanation = str(question.get("explanation", "")).strip()
    category = str(question.get("category", "")).strip()
    difficulty = str(question.get("difficulty", "")).strip()
    question_type = str(question.get("questionType", "")).strip()

    if index != assigned["planIndex"]:
        return f"planIndex incorrecto: {index!r} != {assigned['planIndex']!r}"
    if concept_id != assigned["id"]:
        return f"conceptId incorrecto: {concept_id!r} != {assigned['id']!r}"
    if category != assigned["category"]:
        return "categoría incorrecta"
    if difficulty != assigned["difficulty"]:
        return "dificultad incorrecta"
    if question_type != assigned["questionType"]:
        return "tipo de pregunta incorrecto"

    normalized_prompt = normalize_text(prompt)
    if len(prompt) < 22:
        return "el enunciado es demasiado breve"
    if any(
        normalized_prompt.startswith(normalize_text(prefix))
        for prefix in BANNED_PROMPT_PREFIXES
    ):
        return "el enunciado usa una etiqueta artificial"

    if accepted_prompts:
        nearest_exam_prompt, nearest_exam = max(
            ((old, similarity(prompt, old)) for old in accepted_prompts),
            key=lambda pair: pair[1],
        )
        if nearest_exam >= EXAM_SIMILARITY_THRESHOLD:
            return (
                "se parece demasiado a otra pregunta del mismo examen "
                f"(similitud {nearest_exam:.2f}): {nearest_exam_prompt[:220]}"
            )

    if recent_prompts:
        nearest_history_prompt, nearest_history = max(
            ((old, similarity(prompt, old)) for old in recent_prompts),
            key=lambda pair: pair[1],
        )
        if nearest_history >= HISTORY_SIMILARITY_THRESHOLD:
            return (
                "se parece demasiado a una pregunta histórica "
                f"(similitud {nearest_history:.2f}): {nearest_history_prompt[:220]}"
            )

    if not isinstance(options, list) or len(options) != 4:
        return "no tiene exactamente cuatro opciones"

    normalized_options = [normalize_text(str(option)) for option in options]
    if any(not option for option in normalized_options):
        return "contiene una opción vacía"
    if len(set(normalized_options)) != 4:
        return "contiene opciones repetidas"
    if any(
        banned in option
        for option in normalized_options
        for banned in BANNED_OPTION_PATTERNS
    ):
        return "contiene una opción global no permitida"
    if not isinstance(correct, int) or correct not in range(4):
        return "el índice de respuesta correcta es inválido"
    if len(explanation) < 45:
        return "la explicación es insuficiente"

    return None


def classify_questions(
    exam: dict[str, Any],
    plan: list[dict[str, Any]],
    recent_prompts: list[str],
) -> tuple[dict[int, dict[str, Any]], dict[int, str]]:
    """
    Separa preguntas válidas e inválidas por planIndex.

    Las válidas se conservan. Las inválidas o ausentes se pueden regenerar
    individualmente sin tirar el resto del examen.
    """
    questions = exam.get("questions")
    if not isinstance(questions, list):
        questions = []

    grouped: defaultdict[int, list[dict[str, Any]]] = defaultdict(list)
    for question in questions:
        if isinstance(question, dict):
            index = question.get("planIndex")
            if isinstance(index, int):
                grouped[index].append(question)

    valid: dict[int, dict[str, Any]] = {}
    invalid: dict[int, str] = {}
    accepted_prompts: list[str] = []

    for assigned in sorted(plan, key=lambda item: item["planIndex"]):
        index = assigned["planIndex"]
        candidates = grouped.get(index, [])

        if not candidates:
            invalid[index] = "falta la pregunta correspondiente a este planIndex"
            continue
        if len(candidates) > 1:
            invalid[index] = "hay varias preguntas con el mismo planIndex"
            continue

        question = candidates[0]
        error = question_validation_error(
            question,
            assigned,
            accepted_prompts,
            recent_prompts,
        )
        if error is not None:
            invalid[index] = error
            continue

        valid[index] = question
        accepted_prompts.append(str(question.get("prompt", "")).strip())

    return valid, invalid


def validate_generated(
    exam: dict[str, Any],
    plan: list[dict[str, Any]],
    recent_prompts: list[str],
) -> None:
    valid, invalid = classify_questions(exam, plan, recent_prompts)

    if invalid:
        index = min(invalid)
        raise ValueError(f"La pregunta {index} no es válida: {invalid[index]}.")

    if len(valid) != 20:
        raise ValueError(f"Solo hay {len(valid)}/20 preguntas válidas.")

    ordered_questions = [valid[index] for index in sorted(valid)]
    category_counts = Counter(question["category"] for question in ordered_questions)
    difficulty_counts = Counter(question["difficulty"] for question in ordered_questions)

    if category_counts[OFFICIAL_BLOCKS[0]] != 3:
        raise ValueError("El examen debe contener exactamente 3 preguntas normativas.")
    if any(category_counts[block] < 1 for block in SPECIFIC_BLOCKS):
        raise ValueError("Falta al menos un bloque específico.")
    if any(category_counts[block] > 4 for block in SPECIFIC_BLOCKS):
        raise ValueError("Un bloque específico supera cuatro preguntas.")
    if difficulty_counts != Counter({"media": 10, "fácil": 5, "difícil": 5}):
        raise ValueError(f"Distribución de dificultad incorrecta: {difficulty_counts}.")

    exam["questions"] = ordered_questions


def build_repair_prompt(
    exam_id: str,
    item: dict[str, Any],
    reference: str,
    recent_prompts: list[str],
    accepted_prompts: list[str],
    rejected_prompt: str,
    rejection_reason: str,
) -> str:
    recent_text = "\n".join(f"- {prompt}" for prompt in recent_prompts[:220])
    accepted_text = "\n".join(f"- {prompt}" for prompt in accepted_prompts[:40])

    return f"""
Actúas como tribunal técnico de una oposición de RTVE para Edición, Montaje y
Procesos Audiovisuales.

Debes regenerar ÚNICAMENTE la pregunta {item['planIndex']} del examen {exam_id}.
No redactes el examen completo.

ASIGNACIÓN CERRADA
- planIndex: {item['planIndex']}
- conceptId: {item['id']}
- categoría: {item['category']}
- concepto: {item['label']}
- enfoque obligatorio: {item['focus']}
- tipo: {item['questionType']}
- dificultad: {item['difficulty']}

MOTIVO POR EL QUE SE RECHAZÓ LA VERSIÓN ANTERIOR
{rejection_reason}

ENUNCIADO RECHAZADO
{rejected_prompt or "No había una pregunta utilizable para esta posición."}

REGLAS
- Conserva exactamente planIndex, conceptId, categoría, tipo y dificultad.
- Evalúa el mismo concepto, pero cambia de verdad el ángulo de la pregunta.
- No hagas una simple paráfrasis del enunciado rechazado.
- Redacción sobria, directa y técnica, semejante a un test oficial de oposición.
- No uses etiquetas como «Caso práctico», «Fundamento», «Concepto»,
  «Operación» o «Diagnóstico».
- Exactamente cuatro opciones y una sola correcta.
- Distractores verosímiles, próximos y técnicamente distinguibles.
- No uses «todas las anteriores», «ninguna de las anteriores» ni combinaciones A+B.
- La explicación debe justificar la correcta y distinguirla del distractor más próximo.
- No inventes normas, artículos, formatos, prestaciones ni datos.

OTRAS PREGUNTAS YA ACEPTADAS EN ESTE EXAMEN
No redactes una pregunta que se parezca demasiado a estas:
{accepted_text or "Todavía no hay otras preguntas aceptadas."}

HISTÓRICO RECIENTE
No copies ni reformules de forma casi literal estas preguntas:
{recent_text or "No hay historial."}

TEMARIO OFICIAL Y DESARROLLO ORIENTATIVO
{reference}

Devuelve únicamente el objeto JSON de esta pregunta.
""".strip()


def repair_candidate(
    client: OpenAI,
    exam_id: str,
    candidate: dict[str, Any],
    plan: list[dict[str, Any]],
    reference: str,
    recent_prompts: list[str],
) -> dict[str, Any]:
    """
    Conserva las preguntas válidas y regenera únicamente las rechazadas.
    Repite el proceso hasta que las 20 sean válidas o se agoten las rondas.
    """
    candidate = dict(candidate)
    plan_by_index = {item["planIndex"]: item for item in plan}

    for repair_round in range(1, MAX_REPAIR_ROUNDS + 1):
        valid, invalid = classify_questions(candidate, plan, recent_prompts)

        if not invalid:
            candidate["questions"] = [valid[index] for index in sorted(valid)]
            validate_generated(candidate, plan, recent_prompts)
            return candidate

        print(
            f"Ronda de reparación {repair_round}: "
            f"{len(invalid)} pregunta(s) a sustituir."
        )

        # Conservamos todas las válidas y generamos únicamente las rechazadas.
        repaired: dict[int, dict[str, Any]] = dict(valid)
        accepted_prompts = [
            str(question.get("prompt", "")).strip()
            for _, question in sorted(repaired.items())
        ]

        old_questions = candidate.get("questions")
        if not isinstance(old_questions, list):
            old_questions = []

        for index in sorted(invalid):
            item = plan_by_index[index]
            old_candidates = [
                question
                for question in old_questions
                if isinstance(question, dict) and question.get("planIndex") == index
            ]
            rejected_prompt = ""
            if old_candidates:
                rejected_prompt = str(old_candidates[0].get("prompt", "")).strip()

            print(
                f"  - Sustituyendo pregunta {index}: {invalid[index]}"
            )

            repair_prompt = build_repair_prompt(
                exam_id=exam_id,
                item=item,
                reference=reference,
                recent_prompts=recent_prompts,
                accepted_prompts=accepted_prompts,
                rejected_prompt=rejected_prompt,
                rejection_reason=invalid[index],
            )

            replacement = request_structured_json(
                client=client,
                prompt=repair_prompt,
                schema=build_single_question_schema(item),
                schema_name=f"rtve_repair_q{index:02d}",
            )
            repaired[index] = replacement
            accepted_prompts.append(str(replacement.get("prompt", "")).strip())

        candidate["questions"] = [
            repaired[index]
            for index in sorted(repaired)
            if index in plan_by_index
        ]

    valid, invalid = classify_questions(candidate, plan, recent_prompts)
    details = "; ".join(
        f"P{index}: {reason}" for index, reason in sorted(invalid.items())
    )
    raise ValueError(
        f"No se pudieron reparar todas las preguntas tras {MAX_REPAIR_ROUNDS} rondas. "
        f"Quedan {len(invalid)} inválidas. {details}"
    )


def balance_correct_answers(exam: dict[str, Any], seed: int) -> None:
    rng = random.Random(seed)
    target_positions = [0, 1, 2, 3] * 5
    rng.shuffle(target_positions)

    questions = sorted(exam["questions"], key=lambda q: q["planIndex"])
    for question, target_index in zip(questions, target_positions):
        options = list(question["options"])
        current_index = question["correctIndex"]
        options[current_index], options[target_index] = options[target_index], options[current_index]
        question["options"] = options
        question["correctIndex"] = target_index

    exam["questions"] = questions


def build_prompt(
    exam_id: str,
    plan: list[dict[str, Any]],
    reference: str,
    recent_prompts: list[str],
) -> str:
    plan_text = "\n".join(
        (
            f"{item['planIndex']:02d}. conceptId={item['id']} | "
            f"categoría={item['category']} | concepto={item['label']} | "
            f"enfoque obligatorio={item['focus']} | "
            f"tipo={item['questionType']} | dificultad={item['difficulty']}"
        )
        for item in plan
    )

    recent_text = "\n".join(f"- {prompt}" for prompt in recent_prompts[:220])

    return f"""
Actúas como tribunal técnico de una oposición de RTVE para Edición, Montaje y
Procesos Audiovisuales. Redacta el examen {exam_id}.

REGLA PRINCIPAL
Python ya ha seleccionado los veinte conceptos. No puedes sustituirlos por otros,
aunque te parezcan más habituales. Cada pregunta debe evaluar exactamente el
conceptId y el enfoque indicados en su posición. Devuelve el planIndex, conceptId,
categoría, tipo y dificultad exactamente como figuran en el plan.

PLAN CERRADO DEL EXAMEN
{plan_text}

ESTILO
- Redacción sobria, directa y técnica, semejante a un test oficial.
- No antepongas etiquetas como «Caso práctico», «Fundamento», «Concepto»,
  «Operación» o «Diagnóstico».
- Alterna preguntas interrogativas y, de forma ocasional, enunciados terminados
  en dos puntos. No conviertas todas las preguntas en casos narrativos.
- No menciones el plan, el conceptId, la dificultad, el tipo de pregunta ni el
  proceso de generación dentro del enunciado.
- No uses «imagina», «supón», «qué harías», «seleccione la mejor» ni lenguaje de
  academia.
- Los enunciados deben ser normalmente concisos. Añade contexto solo cuando sea
  imprescindible para aplicar o diagnosticar.

CONTENIDO Y DIFICULTAD
- La pregunta debe salir del concepto y del enfoque asignados, no de otro concepto
  relacionado que resulte más fácil de redactar.
- Si el enfoque prohíbe repetir una formulación habitual, respeta esa prohibición.
- Una pregunta fácil comprueba un fundamento concreto.
- Una pregunta media exige distinguir, relacionar o aplicar.
- Una pregunta difícil exige diagnóstico, compatibilidad, interpretación o una
  distinción técnica fina, pero debe ser resoluble con el temario.
- No inventes artículos, normas, funciones, formatos ni prestaciones.

OPCIONES
- Exactamente cuatro y una sola correcta.
- Las cuatro deben pertenecer a la misma clase: cuatro operaciones, cuatro
  magnitudes, cuatro normas, cuatro formatos o cuatro afirmaciones comparables.
- Los distractores deben ser técnicamente verosímiles y próximos, pero claramente
  incorrectos por una razón comprobable.
- Evita que la correcta sea identificable por longitud o precisión.
- No uses «todas», «ninguna», combinaciones A+B ni opciones humorísticas.

EXPLICACIÓN
- Explica por qué la correcta lo es y señala la diferencia decisiva respecto al
  distractor más próximo.
- No añadas información ajena al concepto evaluado.

CONTROL DE REPETICIONES
Las preguntas siguientes ya se han utilizado. No copies su competencia evaluada
ni su estructura, aunque cambies palabras, cifras, marcas o contexto. El plan ha
seleccionado conceptos distintos precisamente para evitarlo:
{recent_text or "No hay historial."}

TEMARIO OFICIAL Y DESARROLLO ORIENTATIVO
{reference}

Devuelve únicamente el JSON del esquema.
""".strip()

def main() -> int:
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: falta el secreto OPENAI_API_KEY.", file=sys.stderr)
        return 2

    data = load_data()
    existing: list[dict[str, Any]] = data["exams"]

    numeric_ids = [
        int(str(exam.get("id", "")).strip())
        for exam in existing
        if str(exam.get("id", "")).strip().isdigit()
    ]
    next_number = max(numeric_ids, default=0) + 1
    exam_id = f"{next_number:03d}"

    reference = REFERENCE_FILE.read_text(encoding="utf-8")
    recent_prompts = recent_prompt_list(existing)
    plan = choose_concepts(existing, next_number)
    schema = build_schema(plan)
    prompt = build_prompt(exam_id, plan, reference, recent_prompts)

    print("Plan temático seleccionado:")
    for item in plan:
        print(
            f"{item['planIndex']:02d}. {item['category']} — {item['label']} — "
            f"{item['questionType']} — {item['difficulty']}"
        )

    print(
        "Control de similitud: "
        f"mismo examen >= {EXAM_SIMILARITY_THRESHOLD:.2f}; "
        f"histórico >= {HISTORY_SIMILARITY_THRESHOLD:.2f}."
    )

    client = OpenAI(max_retries=2, timeout=180.0)

    generated: dict[str, Any] | None = None
    last_validation_error: Exception | None = None

    try:
        for attempt in range(1, MAX_FULL_ATTEMPTS + 1):
            attempt_prompt = prompt
            if last_validation_error is not None:
                attempt_prompt += (
                    "\n\nLa propuesta completa anterior no pudo quedar validada incluso "
                    "después de reparar las preguntas problemáticas. Motivo final: "
                    f"{last_validation_error}. Genera una nueva propuesta completa "
                    "manteniendo exactamente el mismo plan cerrado."
                )

            print(
                f"Generando propuesta completa "
                f"{attempt}/{MAX_FULL_ATTEMPTS}..."
            )

            candidate = request_structured_json(
                client=client,
                prompt=attempt_prompt,
                schema=schema,
                schema_name="rtve_daily_exam_v4",
            )

            try:
                candidate = repair_candidate(
                    client=client,
                    exam_id=exam_id,
                    candidate=candidate,
                    plan=plan,
                    reference=reference,
                    recent_prompts=recent_prompts,
                )
                validate_generated(candidate, plan, recent_prompts)
            except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                last_validation_error = exc
                print(
                    f"Propuesta completa {attempt} rechazada tras reparaciones: {exc}",
                    file=sys.stderr,
                )
                continue

            generated = candidate
            break

    except AuthenticationError as exc:
        print("ERROR: OPENAI_API_KEY no es válida o no tiene acceso.", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 3
    except RateLimitError as exc:
        print("ERROR: falta saldo, cuota o se alcanzó un límite de API.", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 4
    except APIError as exc:
        print(f"ERROR de OpenAI API: {exc}", file=sys.stderr)
        return 5

    if generated is None:
        raise RuntimeError(
            "No se obtuvo un examen válido después de "
            f"{MAX_FULL_ATTEMPTS} propuestas completas y hasta "
            f"{MAX_REPAIR_ROUNDS} rondas de reparación por propuesta. "
            f"Último error: {last_validation_error}"
        )

    generated["blocks"] = [
        block
        for block in OFFICIAL_BLOCKS
        if any(question["category"] == block for question in generated["questions"])
    ]
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

    print(f"Creado {exam['title']} y guardado en {DATA_FILE}")
    
    return 0

if __name__ == "__main__":
    raise SystemExit(main())