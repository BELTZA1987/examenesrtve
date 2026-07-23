const DATA_URL = "data/exams.json";
const STORAGE_KEY = "rtve_exam_progress_v1";
const EMBEDDED_EXAM_DATA = {"version": 1, "updatedAt": "2026-07-23", "exams": [{"id": "001", "title": "Examen 001", "date": "2026-07-23", "level": "Alto", "timeMinutes": 25, "blocks": ["Vídeo digital", "Audio", "Avid", "EVS", "Broadcast"], "questions": [{"prompt": "En una señal Y′CbCr 4:2:2 de 10 bits, ¿qué afirmación es correcta?", "options": ["Cada píxel contiene muestras independientes de Y′, Cb y Cr.", "La luminancia mantiene la resolución horizontal completa y cada componente de crominancia se muestrea a la mitad.", "La crominancia se reduce a la mitad horizontal y verticalmente.", "Los cuatro valores indican canales independientes de 2 bits."], "correctIndex": 1, "explanation": "En 4:2:2, la luminancia conserva todas las muestras horizontales y Cb/Cr tienen la mitad. Los 10 bits indican 1024 niveles posibles por componente.", "category": "Vídeo digital"}, {"prompt": "¿Qué característica diferencia principalmente un códec intraframe de uno Long GOP?", "options": ["El intraframe no utiliza compresión.", "El Long GOP solo puede almacenar imágenes progresivas.", "El intraframe codifica cada cuadro con mayor independencia respecto a los cuadros vecinos.", "El Long GOP no admite código de tiempo."], "correctIndex": 2, "explanation": "En intraframe cada cuadro se comprime con relativa independencia. Long GOP utiliza relaciones temporales entre cuadros.", "category": "Códecs"}, {"prompt": "Un archivo MXF puede definirse correctamente como:", "options": ["Un códec de vídeo exclusivamente sin pérdidas.", "Un contenedor profesional capaz de almacenar esencia audiovisual y metadatos.", "Un sistema de archivos utilizado únicamente por XDCAM.", "Una tabla de decisiones de montaje."], "correctIndex": 1, "explanation": "MXF es un contenedor profesional, no un códec concreto.", "category": "Contenedores"}, {"prompt": "En un flujo offline-online, el conformado consiste principalmente en:", "options": ["Convertir el máster final en archivos proxy.", "Reconstruir la secuencia con los originales de alta resolución.", "Eliminar los efectos temporales de la secuencia.", "Mezclar todas las pistas de audio en una sola."], "correctIndex": 1, "explanation": "El conformado reconstruye la secuencia definitiva utilizando los medios originales o de máxima calidad.", "category": "Posproducción"}, {"prompt": "¿Qué elemento es especialmente importante para que un relink automático encuentre correctamente los originales?", "options": ["El nombre visible asignado manualmente al bin.", "La posición de las pistas en la secuencia.", "La coincidencia de identificadores, código de tiempo y metadatos de origen.", "La resolución del monitor de edición."], "correctIndex": 2, "explanation": "Timecode, identificadores únicos, nombres de bobina y metadatos son fundamentales para un relink fiable.", "category": "Metadatos"}, {"prompt": "En Avid Media Composer, la función Match Frame permite:", "options": ["Igualar automáticamente el color de dos planos.", "Cargar en el monitor fuente el fotograma original correspondiente al plano situado en la secuencia.", "Convertir un clip progresivo en entrelazado.", "Sincronizar dos clips únicamente mediante forma de onda."], "correctIndex": 1, "explanation": "Match Frame permite localizar y cargar el material fuente correspondiente al plano montado.", "category": "Avid"}, {"prompt": "Un archivo AAF se utiliza principalmente para:", "options": ["Comprimir un máster para distribución por internet.", "Transferir secuencias, ediciones, pistas y metadatos entre aplicaciones.", "Sustituir un archivo de vídeo por un proxy.", "Crear copias de seguridad en cinta LTO."], "correctIndex": 1, "explanation": "AAF transporta decisiones de edición, pistas, referencias de medios y metadatos.", "category": "Intercambio"}, {"prompt": "En vídeo digital, el banding es más probable cuando:", "options": ["La profundidad de bits es insuficiente para representar una gradación suave.", "La frecuencia de cuadro es demasiado elevada.", "Se emplea muestreo 4:4:4.", "Se utiliza una señal progresiva."], "correctIndex": 0, "explanation": "Una profundidad de bits baja ofrece menos niveles tonales y puede producir saltos visibles en los degradados.", "category": "Colorimetría"}, {"prompt": "En un vectorscopio, la distancia respecto al centro representa principalmente:", "options": ["La luminancia de la imagen.", "La saturación de la crominancia.", "La profundidad de bits.", "La frecuencia de cuadro."], "correctIndex": 1, "explanation": "En el vectorscopio, la distancia al centro muestra la saturación; el ángulo indica el tono.", "category": "Medida"}, {"prompt": "En audio digital, 0 dBFS representa:", "options": ["El nivel nominal recomendado para diálogos.", "El silencio digital absoluto.", "El nivel máximo representable antes del recorte digital.", "El punto de referencia equivalente a −18 LUFS."], "correctIndex": 2, "explanation": "0 dBFS es el techo del sistema digital. Superarlo provoca clipping.", "category": "Audio"}, {"prompt": "Según el teorema de Nyquist, una señal muestreada a 48 kHz puede representar teóricamente frecuencias de hasta:", "options": ["12 kHz.", "24 kHz.", "48 kHz.", "96 kHz."], "correctIndex": 1, "explanation": "La frecuencia máxima teórica es la mitad de la frecuencia de muestreo.", "category": "Audio"}, {"prompt": "La principal ventaja de una conexión de audio balanceada es:", "options": ["Aumentar automáticamente la ganancia.", "Reducir las interferencias comunes inducidas en el cable.", "Convertir el audio analógico en digital.", "Evitar cualquier posibilidad de saturación."], "correctIndex": 1, "explanation": "La transmisión balanceada permite cancelar gran parte del ruido común captado por el cable.", "category": "Audio"}, {"prompt": "En una configuración RAID 1:", "options": ["Los datos se dividen entre varios discos sin redundancia.", "Los datos se duplican en dos unidades.", "Se distribuye paridad entre un mínimo de tres discos.", "Se obtiene el doble de capacidad útil que con un solo disco."], "correctIndex": 1, "explanation": "RAID 1 duplica los datos. Ofrece redundancia, aunque reduce la capacidad útil.", "category": "Almacenamiento"}, {"prompt": "¿Cuál es una utilización habitual de las cintas LTO en un entorno audiovisual?", "options": ["Reproducción multicámara en directo.", "Archivo y copia de seguridad de grandes volúmenes de contenido.", "Monitorización de señales SDI.", "Conversión entre espacios de color."], "correctIndex": 1, "explanation": "LTO se utiliza principalmente para archivo, preservación y copias de seguridad.", "category": "Almacenamiento"}, {"prompt": "El genlock se emplea para:", "options": ["Igualar la resolución de todas las cámaras.", "Sincronizar los equipos de vídeo respecto a una referencia común.", "Generar automáticamente el código de tiempo de los clips.", "Convertir señales SDI en señales IP."], "correctIndex": 1, "explanation": "El genlock proporciona una referencia temporal común para cámaras, mezcladores, servidores y otros equipos.", "category": "Multicámara"}, {"prompt": "Una señal 1080i/25 está formada normalmente por:", "options": ["25 imágenes progresivas por segundo.", "25 campos entrelazados por segundo.", "25 cuadros construidos a partir de 50 campos por segundo.", "50 cuadros progresivos por segundo."], "correctIndex": 2, "explanation": "En 1080i/25 se generan 25 cuadros entrelazados a partir de 50 campos por segundo.", "category": "Señal"}, {"prompt": "En el código de tiempo drop-frame:", "options": ["Se eliminan periódicamente fotogramas reales del vídeo.", "Se omiten determinados números de código de tiempo para compensar frecuencias fraccionarias.", "Se reduce la frecuencia de cuadro a 25 fps.", "Se elimina el desfase entre vídeo y audio mediante resincronización."], "correctIndex": 1, "explanation": "Drop-frame no borra fotogramas: omite determinados números de código de tiempo.", "category": "Código de tiempo"}, {"prompt": "En una señal 4:4:4:4, el cuarto componente suele corresponder a:", "options": ["Una pista de audio asociada.", "Un canal alfa.", "Un código de tiempo longitudinal.", "Una referencia de sincronismo."], "correctIndex": 1, "explanation": "El cuarto valor suele representar un canal alfa para transparencia o composición.", "category": "Composición"}, {"prompt": "En un sistema EVS, una playlist es:", "options": ["Una lista ordenada de clips preparada para su reproducción.", "Una copia de seguridad de todos los canales grabados.", "Una secuencia exclusiva de Avid transferida mediante AAF.", "Una tabla con los códigos de tiempo de las cámaras."], "correctIndex": 0, "explanation": "Una playlist de EVS organiza varios clips para reproducirlos de forma secuencial.", "category": "EVS"}, {"prompt": "Desde el punto de vista del montaje, un L-cut se produce cuando:", "options": ["El audio del plano siguiente comienza antes de cambiar la imagen.", "La imagen del plano siguiente aparece mientras continúa el audio del plano anterior.", "Imagen y sonido cambian exactamente en el mismo fotograma.", "Se elimina por completo el sonido ambiente entre dos planos."], "correctIndex": 1, "explanation": "En un L-cut continúa el audio del plano anterior mientras ya vemos la imagen siguiente.", "category": "Montaje"}]}]};

let exams = [];
let currentExam = null;
let progress = loadProgress();
let currentFilter = "all";

const dashboardView = document.getElementById("dashboardView");
const examView = document.getElementById("examView");
const examList = document.getElementById("examList");
const stats = document.getElementById("stats");
const quizForm = document.getElementById("quizForm");
const resultPanel = document.getElementById("resultPanel");

function loadProgress() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
  } catch {
    return {};
  }
}

function saveProgress() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(progress));
}

async function loadExams(force = false) {
  let data = EMBEDDED_EXAM_DATA;

  try {
    const url = force ? `${DATA_URL}?t=${Date.now()}` : DATA_URL;
    const response = await fetch(url, { cache: force ? "no-store" : "default" });
    if (response.ok) {
      const remoteData = await response.json();
      if (remoteData && Array.isArray(remoteData.exams) && remoteData.exams.length) {
        data = remoteData;
      }
    }
  } catch (error) {
    console.warn("No se pudo cargar data/exams.json; se usa el examen integrado.", error);
  }

  exams = [...data.exams].sort((a, b) => b.id.localeCompare(a.id));
  renderDashboard();
}

function getStatus(exam) {
  const item = progress[exam.id];
  if (item?.completedAt) return "completed";
  if (item?.answers?.some(value => value !== null && value !== undefined)) return "in-progress";
  return "pending";
}

function statusLabel(status) {
  return {
    completed: "Realizado",
    "in-progress": "En curso",
    pending: "Pendiente"
  }[status];
}

function renderStats() {
  const completed = exams.filter(exam => getStatus(exam) === "completed");
  const pending = exams.length - completed.length;
  const average = completed.length
    ? Math.round(completed.reduce((sum, exam) => sum + progress[exam.id].score, 0) / completed.length)
    : 0;
  const best = completed.length
    ? Math.max(...completed.map(exam => progress[exam.id].score))
    : 0;

  stats.innerHTML = `
    <article class="stat-card"><span class="stat-label">Total</span><strong class="stat-value">${exams.length}</strong></article>
    <article class="stat-card"><span class="stat-label">Realizados</span><strong class="stat-value">${completed.length}</strong></article>
    <article class="stat-card"><span class="stat-label">Pendientes</span><strong class="stat-value">${pending}</strong></article>
    <article class="stat-card"><span class="stat-label">Media / Mejor</span><strong class="stat-value">${average} / ${best}</strong></article>
  `;
}

function renderDashboard() {
  renderStats();
  const filtered = exams.filter(exam => {
    const status = getStatus(exam);
    if (currentFilter === "completed") return status === "completed";
    if (currentFilter === "pending") return status !== "completed";
    return true;
  });

  if (!filtered.length) {
    examList.innerHTML = `<div class="empty">No hay exámenes en esta categoría.</div>`;
    return;
  }

  examList.innerHTML = filtered.map(exam => {
    const status = getStatus(exam);
    const item = progress[exam.id];
    const score = item?.completedAt ? `${item.score}/${exam.questions.length}` : "—";
    const action = status === "completed" ? "Repetir" : status === "in-progress" ? "Continuar" : "Empezar";
    return `
      <article class="exam-card ${status}">
        <div>
          <div class="exam-title-row">
            <h2 class="exam-title">${escapeHtml(exam.title)}</h2>
            <span class="status-pill ${status}">${statusLabel(status)}</span>
          </div>
          <div class="exam-meta">${formatDate(exam.date)} · ${exam.level} · ${exam.timeMinutes} min · ${exam.questions.length} preguntas</div>
          <div class="tags">${exam.blocks.map(block => `<span class="tag">${escapeHtml(block)}</span>`).join("")}</div>
          <div class="card-actions">
            <button class="open-button" type="button" data-open="${exam.id}">${action}</button>
            ${item?.completedAt ? `<button class="clear-result" type="button" data-clear="${exam.id}">Borrar resultado</button>` : ""}
          </div>
        </div>
        <div class="score-box">
          <div class="score-number">${score}</div>
          <div class="score-caption">${item?.completedAt ? "Última nota" : "Sin nota"}</div>
        </div>
      </article>
    `;
  }).join("");

  document.querySelectorAll("[data-open]").forEach(button => {
    button.addEventListener("click", () => openExam(button.dataset.open));
  });
  document.querySelectorAll("[data-clear]").forEach(button => {
    button.addEventListener("click", () => clearResult(button.dataset.clear));
  });
}

function openExam(id) {
  currentExam = exams.find(exam => exam.id === id);
  if (!currentExam) return;

  dashboardView.classList.add("hidden");
  examView.classList.remove("hidden");
  resultPanel.classList.add("hidden");

  const saved = progress[id] || { answers: Array(currentExam.questions.length).fill(null) };
  if (!Array.isArray(saved.answers)) saved.answers = Array(currentExam.questions.length).fill(null);
  progress[id] = saved;
  saveProgress();

  document.getElementById("examHeader").innerHTML = `
    <div class="exam-hero">
      <h2>${escapeHtml(currentExam.title)}</h2>
      <div class="exam-meta">${formatDate(currentExam.date)} · ${currentExam.level} · ${currentExam.timeMinutes} minutos</div>
      <div class="tags">${currentExam.blocks.map(block => `<span class="tag">${escapeHtml(block)}</span>`).join("")}</div>
    </div>
  `;

  quizForm.innerHTML = currentExam.questions.map((question, index) => `
    <section class="question" data-question="${index}">
      <h3>${index + 1}. ${escapeHtml(question.prompt)}</h3>
      ${question.options.map((option, optionIndex) => `
        <label class="option">
          <input type="radio" name="q${index}" value="${optionIndex}" ${saved.answers[index] === optionIndex ? "checked" : ""}>
          <span><strong>${String.fromCharCode(65 + optionIndex)}.</strong> ${escapeHtml(option)}</span>
        </label>
      `).join("")}
      <div class="feedback"></div>
    </section>
  `).join("");

  quizForm.querySelectorAll("input[type=radio]").forEach(input => {
    input.addEventListener("change", event => {
      const questionIndex = Number(event.target.name.substring(1));
      progress[currentExam.id].answers[questionIndex] = Number(event.target.value);
      delete progress[currentExam.id].completedAt;
      delete progress[currentExam.id].score;
      saveProgress();
    });
  });

  window.scrollTo({ top: 0, behavior: "smooth" });
}

function gradeCurrentExam() {
  if (!currentExam) return;
  const saved = progress[currentExam.id];
  let score = 0;
  let answered = 0;

  currentExam.questions.forEach((question, index) => {
    const section = quizForm.querySelector(`[data-question="${index}"]`);
    const feedback = section.querySelector(".feedback");
    const answer = saved.answers[index];

    section.classList.remove("correct", "incorrect", "unanswered");
    feedback.className = "feedback show";

    if (answer === null || answer === undefined) {
      section.classList.add("unanswered");
      feedback.classList.add("unanswered");
      feedback.innerHTML = `<strong>Sin responder.</strong> Correcta: ${letter(question.correctIndex)}. ${escapeHtml(question.explanation)}`;
      return;
    }

    answered += 1;
    if (answer === question.correctIndex) {
      score += 1;
      section.classList.add("correct");
      feedback.classList.add("correct");
      feedback.innerHTML = `<strong>Correcta.</strong> ${escapeHtml(question.explanation)}`;
    } else {
      section.classList.add("incorrect");
      feedback.classList.add("incorrect");
      feedback.innerHTML = `<strong>Incorrecta.</strong> Correcta: <strong>${letter(question.correctIndex)}. ${escapeHtml(question.options[question.correctIndex])}</strong><br>${escapeHtml(question.explanation)}`;
    }
  });

  saved.score = score;
  saved.completedAt = new Date().toISOString();
  saveProgress();

  const percentage = Math.round((score / currentExam.questions.length) * 100);
  const message = score >= 16 ? "Nivel muy alto."
    : score >= 13 ? "Buen nivel."
    : score >= 10 ? "Base aceptable, pero hay lagunas."
    : "Conviene reforzar fundamentos.";

  resultPanel.innerHTML = `
    <div class="result-score">${score}/${currentExam.questions.length}</div>
    <strong>${percentage}% · ${message}</strong>
    <p>Has contestado ${answered} de ${currentExam.questions.length}. El resultado queda guardado en este iPhone y aparecerá en la portada.</p>
  `;
  resultPanel.classList.remove("hidden");
  resultPanel.scrollIntoView({ behavior: "smooth", block: "center" });
}

function resetCurrentExam() {
  if (!currentExam) return;
  if (!confirm("¿Quieres borrar todas las respuestas y el resultado de este examen?")) return;
  progress[currentExam.id] = { answers: Array(currentExam.questions.length).fill(null) };
  saveProgress();
  openExam(currentExam.id);
}

function clearResult(id) {
  const exam = exams.find(item => item.id === id);
  if (!exam) return;
  if (!confirm(`¿Borrar el resultado de ${exam.title}?`)) return;
  progress[id] = { answers: Array(exam.questions.length).fill(null) };
  saveProgress();
  renderDashboard();
}

function backToDashboard() {
  currentExam = null;
  examView.classList.add("hidden");
  dashboardView.classList.remove("hidden");
  renderDashboard();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function formatDate(value) {
  return new Intl.DateTimeFormat("es-ES", { day: "2-digit", month: "2-digit", year: "numeric" })
    .format(new Date(`${value}T12:00:00`));
}

function letter(index) {
  return String.fromCharCode(65 + index);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

document.querySelectorAll(".filter").forEach(button => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".filter").forEach(item => item.classList.remove("active"));
    button.classList.add("active");
    currentFilter = button.dataset.filter;
    renderDashboard();
  });
});

document.getElementById("backButton").addEventListener("click", backToDashboard);
document.getElementById("gradeButton").addEventListener("click", gradeCurrentExam);
document.getElementById("resetExamButton").addEventListener("click", resetCurrentExam);
document.getElementById("refreshButton").addEventListener("click", async () => {
  try {
    await loadExams(true);
    alert("Exámenes actualizados.");
  } catch (error) {
    alert(error.message);
  }
});


loadExams().catch(error => {
  examList.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
});