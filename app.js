const DATA_URL = "data/exams.json";
const STORAGE_KEY = "rtve_exam_progress_v1";

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
  const url = force ? `${DATA_URL}?t=${Date.now()}` : DATA_URL;
  const response = await fetch(url, { cache: force ? "no-store" : "default" });
  if (!response.ok) throw new Error("No se pudieron cargar los exámenes.");
  const data = await response.json();
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

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("sw.js"));
}

loadExams().catch(error => {
  examList.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
});