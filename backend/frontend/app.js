/* ═══════════════════════════════════════════════════════════════════════
   SMC Quest — app.js v3.0
   Полная реализация: квиз, задания, уроки, лидерборд
   ═══════════════════════════════════════════════════════════════════════ */

// ── CONFIG ────────────────────────────────────────────────────────────────
const API   = "/api";
const tg    = window.Telegram?.WebApp ?? null;
const DEV_UID = 445677777; // fallback для браузера

// ── GLOBAL STATE ─────────────────────────────────────────────────────────
const state = {
  userId: null,
  userState: null,
  quizData: null,       // { questions, questId, current, correct }
  currentQuestId: null, // активное задание
  lessonsMetaCache: {},
};

// ── INIT ──────────────────────────────────────────────────────────────────
if (tg) { tg.ready(); tg.expand(); }

function getUserInfo() {
  if (tg?.initDataUnsafe?.user) {
    const u = tg.initDataUnsafe.user;
    return { id: u.id, username: u.username || null, first_name: u.first_name || null, last_name: u.last_name || null };
  }
  return { id: DEV_UID, username: "dev_user", first_name: "Dev", last_name: null };
}

// ── DOM HELPERS ───────────────────────────────────────────────────────────
const $ = s => document.querySelector(s);
function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls)  e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

// ── MARKDOWN RENDERER ─────────────────────────────────────────────────────
// Парсит *bold*, форматирует буллеты (• и 1️⃣ и т.д.)
function renderMarkdown(text) {
  if (!text) return "";
  const div = document.createElement("div");
  const lines = text.split("\n");
  lines.forEach((line, idx) => {
    if (!line.trim()) {
      if (idx > 0) div.appendChild(document.createElement("br"));
      return;
    }
    const p = document.createElement("span");
    p.style.display = "block";
    // Рендерим *bold* → <strong>
    const parts = line.split(/\*([^*]+)\*/g);
    parts.forEach((part, i) => {
      if (i % 2 === 1) {
        const s = document.createElement("strong");
        s.textContent = part;
        p.appendChild(s);
      } else if (part) {
        p.appendChild(document.createTextNode(part));
      }
    });
    // Буллеты
    if (line.startsWith("• ") || line.match(/^[1-9][️⃣)\.] /)) {
      p.className = "bullet";
    }
    div.appendChild(p);
  });
  return div.innerHTML;
}

// ── TABS ──────────────────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll(".tab").forEach(b => b.classList.toggle("active", b.dataset.tab === name));
  document.querySelectorAll(".tab-content").forEach(c => c.classList.toggle("active", c.id === `tab-${name}`));
  if (name === "quests")       loadQuests();
  if (name === "leaderboard")  loadLeaderboard();
}
window.switchTab = switchTab;

// ── MODALS ────────────────────────────────────────────────────────────────
function openModal(id)  { $(id)?.classList.remove("hidden"); }
function closeModal(id) { $(id)?.classList.add("hidden"); }
window.closeModal = closeModal;

// ── RENDER USER STATE ─────────────────────────────────────────────────────
function renderHeader(s) {
  state.userState = s;
  $("#userName").textContent  = s.name || "Трейдер";
  $("#userXP").textContent    = s.xp ?? 0;
  $("#userLvl").textContent   = s.level ?? 1;
  $("#userRank").textContent  = s.rank || "🪨";
  $("#moduleName").textContent = `Модуль ${(s.module_index ?? 0) + 1}`;
  if (s.module_deadline) {
    const d = new Date(s.module_deadline);
    const now = new Date();
    const daysLeft = Math.ceil((d - now) / 86400000);
    const txt = daysLeft > 0
      ? `⏰ ${daysLeft} дн. до дедлайна`
      : `⚠️ Дедлайн просрочен!`;
    $("#deadlineText").textContent = txt;
    $("#deadlineText").style.color = daysLeft <= 2 ? "var(--bear)" : "var(--gold)";
  }
}

function setProgress(completed, total) {
  const pct = total > 0 ? Math.round(completed / total * 100) : 0;
  const bar = $("#progressBar");
  bar.style.width = pct + "%";
  if (pct > 5) bar.classList.add("active");
  $("#progressLabel") && ($("#progressLabel").textContent = `${completed}/${total}`);
}

// ── RENDER MODULES ────────────────────────────────────────────────────────
function renderModules(modules) {
  const container = $("#modulesList");
  container.innerHTML = "";
  modules.forEach((mod, idx) => {
    const card = el("div", "module-card");
    const header = el("div", "module-header");
    const title  = el("div", "module-title", `Модуль ${idx + 1}: ${mod.title}`);
    const chev   = el("div", "module-chevron", "▼");
    header.append(title, chev);
    card.append(header);

    const list = el("div", "lesson-list");
    (mod.lessons || []).forEach(key => {
      const meta  = state.lessonsMetaCache[key];
      const name  = meta ? meta.title : key;
      const item  = el("div", "lesson-item");
      const lname = el("div", "lesson-name", name);
      const arr   = el("div", "lesson-arrow", "›");
      item.append(lname, arr);
      item.addEventListener("click", () => openLesson(key));
      list.appendChild(item);
    });

    card.appendChild(list);
    header.addEventListener("click", () => card.classList.toggle("open"));
    container.appendChild(card);
  });
}

// ── RENDER QUESTS ─────────────────────────────────────────────────────────
function renderQuests(resp) {
  const quests = resp.quests || [];
  const container = $("#questsList");
  container.innerHTML = "";

  // Шапка модуля
  const hdr = $("#questsHeader");
  hdr.innerHTML = "";
  const statDiv = el("div", "q-stat");
  const val = el("div", "q-stat-val", `${resp.completed_count || 0}/${resp.total_count || 0}`);
  const lbl = el("div", "q-stat-lbl", "квестов завершено");
  statDiv.append(val, lbl);

  const modDiv = el("div", "q-stat");
  modDiv.style.marginLeft = "auto";
  const mval = el("div", "q-stat-val", `#${(resp.module_index ?? 0) + 1}`);
  const mlbl = el("div", "q-stat-lbl", resp.module_title || "");
  modDiv.append(mval, mlbl);
  hdr.append(statDiv, modDiv);

  setProgress(resp.completed_count || 0, resp.total_count || 0);

  if (!quests.length) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="es-icon">⚔️</div>
        <div class="es-title">Нет активных квестов</div>
        <div>Выполни все задания чтобы открыть следующий модуль</div>
      </div>`;
    return;
  }

  quests.forEach(q => {
    const isBoss = q.id.endsWith("_boss");
    const card   = el("div", `quest-card ${q.type}${isBoss ? " boss" : ""}${q.completed ? " completed" : ""}`);

    const hdrRow = el("div", "quest-header");
    const title  = el("div", "quest-title", q.title);
    const xp     = el("div", "quest-xp", `+${q.xp_reward} XP`);
    hdrRow.append(title, xp);

    const badges = el("div", "quest-badges");
    const typeBadge = el("div", `quest-type-badge quest-type-${isBoss ? "boss" : q.type}`,
      q.type === "quiz" ? "КВИЗ" : isBoss ? "👑 БОСС" : "ЗАДАНИЕ");
    badges.appendChild(typeBadge);

    // Статус задания
    const hw = state.userState?.homework_status;
    if (q.is_active && q.type === "task") {
      const statuses = { pending: ["⏳ На проверке", "pending"], approved: ["✅ Принято", "approved"], rejected: ["❌ Отклонено", "rejected"] };
      const [txt, cls] = statuses[hw] || [];
      if (txt) {
        const sb = el("div", `quest-status-badge status-${cls}`, txt);
        badges.appendChild(sb);
      }
    }

    const desc = el("div", "quest-desc", q.description || "");
    const btn  = el("button", "btn-quest", q.completed ? "✅ Выполнено" : q.type === "quiz" ? "▶ Начать квиз" : "📋 Открыть задание");
    btn.disabled = q.completed;
    btn.addEventListener("click", () => q.type === "quiz" ? startQuiz(q.id, q.title, q.xp_reward) : openTask(q.id, q.title, q.xp_reward, q.description));

    card.append(hdrRow, badges, desc, btn);
    container.appendChild(card);
  });
}

// ── RENDER LEADERBOARD ────────────────────────────────────────────────────
function renderLeaderboard(resp) {
  const list = resp.leaderboard || [];
  const container = $("#leaderboardList");
  container.innerHTML = "";

  if (!list.length) {
    container.innerHTML = `<div class="empty-state"><div class="es-icon">🏆</div><div class="es-title">Пока никого нет</div><div>Стань первым!</div></div>`;
    return;
  }

  list.forEach((row, i) => {
    const item  = el("div", "lb-item");
    const rank  = el("div", "lb-rank", i < 3 ? ["🥇","🥈","🥉"][i] : `${i+1}`);
    const info  = el("div", "lb-info");
    const name  = el("div", "lb-name", row.name || `User ${row.user_id}`);
    const sub   = el("div", "lb-sub", `Lvl ${row.level} · ${row.rank} · Модуль ${row.module}`);
    const xp    = el("div", "lb-xp", `${row.xp} XP`);
    info.append(name, sub);
    item.append(rank, info, xp);

    // Подсветить себя
    if (row.user_id === state.userId) {
      item.style.borderColor = "var(--accent)";
      item.style.background  = "rgba(79,142,247,0.05)";
    }
    container.appendChild(item);
  });
}

// ── OPEN LESSON ───────────────────────────────────────────────────────────
async function openLesson(key) {
  try {
    const res  = await fetch(`${API}/lesson/${key}`);
    if (!res.ok) throw new Error("404");
    const data = await res.json();

    $("#lessonTitle").textContent = data.title;
    $("#lessonArticle").innerHTML = renderMarkdown(data.article || "");

    const videoEl = $("#lessonVideo");
    if (data.video) {
      videoEl.href = data.video;
      videoEl.style.display = "flex";
    } else {
      videoEl.style.display = "none";
    }

    // Chart
    const loading = $(".chart-loading");
    const img     = $("#chartImg");
    loading.innerHTML = `<div class="spinner"></div><span>Генерирую график...</span>`;
    loading.style.display = "flex";
    img.style.display = "none";

    openModal("#lessonModal");

    // Загружаем chart асинхронно
    const chartRes = await fetch(`${API}/chart/${key}/png`);
    if (chartRes.ok) {
      const blob = await chartRes.blob();
      img.onload = () => {
        loading.style.display = "none";
        img.style.display = "block";
      };
      img.src = URL.createObjectURL(blob);
    } else {
      loading.innerHTML = "<span>График недоступен</span>";
    }
  } catch (e) {
    console.error("openLesson:", e);
    showToast("Ошибка загрузки урока", "error");
  }
}
window.openLesson = openLesson;

// ── QUIZ ──────────────────────────────────────────────────────────────────
async function startQuiz(questId, questTitle, xpReward) {
  try {
    const res  = await fetch(`${API}/quest/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: state.userId, quest_id: questId }),
    });
    const data = await res.json();

    if (!data.ok) {
      showResult("⚠️", "Квиз недоступен", data.message || data.error, null);
      return;
    }

    const questions = data.quiz?.questions || [];
    if (!questions.length) {
      showToast("Нет вопросов для этого квиза", "error"); return;
    }

    state.quizData = { questions, questId, xpReward, current: 0, correct: 0 };
    renderQuizQuestion();
    openModal("#quizModal");
  } catch (e) {
    console.error("startQuiz:", e);
    showToast("Ошибка запуска квиза", "error");
  }
}

function renderQuizQuestion() {
  const { questions, current } = state.quizData;
  const total = questions.length;
  const q     = questions[current];

  // Progress bar
  const pct = Math.round(current / total * 100);
  $("#quizProgressBar").style.width = pct + "%";
  $("#quizCounter").textContent = `${current + 1} / ${total}`;
  $("#quizQuestion").textContent = q.question;

  // Hide feedback/next
  const fb = $("#quizFeedback");
  fb.className = "quiz-feedback hidden";
  fb.textContent = "";
  $("#quizNext").classList.add("hidden");

  // Options
  const opts = $("#quizOptions");
  opts.innerHTML = "";
  q.options.forEach((opt, i) => {
    const btn = el("button", "quiz-option", opt);
    btn.addEventListener("click", () => onQuizAnswer(i, q.correct_index, btn));
    opts.appendChild(btn);
  });
}

async function onQuizAnswer(chosen, correctIdx, clickedBtn) {
  const { questions, questId, current, correct } = state.quizData;
  const isCorrect = chosen === correctIdx;

  // Disable all options
  document.querySelectorAll(".quiz-option").forEach((b, i) => {
    b.disabled = true;
    if (i === correctIdx) b.classList.add("correct");
    if (i === chosen && !isCorrect) b.classList.add("wrong");
  });

  if (isCorrect) state.quizData.correct++;

  // Show feedback
  const fb = $("#quizFeedback");
  if (isCorrect) {
    fb.className = "quiz-feedback correct-fb";
    fb.textContent = "✅ Правильно!";
  } else {
    fb.className = "quiz-feedback wrong-fb";
    const correct = questions[current].options[correctIdx];
    fb.textContent = `❌ Неверно. Правильный ответ: ${correct}`;
  }

  // Send to backend
  try {
    const res = await fetch(`${API}/quiz/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: state.userId,
        quest_id: questId,
        question_index: current,
        is_correct: isCorrect,
      }),
    });
    const data = await res.json();

    if (data.finished) {
      setTimeout(() => {
        closeModal("#quizModal");
        onQuizFinished(data);
      }, 1200);
      return;
    }
  } catch (e) {
    console.error("quiz answer:", e);
  }

  state.quizData.current++;
  if (state.quizData.current >= questions.length) {
    // Фронт думал что ещё не финиш, но на самом деле закончили
    setTimeout(() => closeModal("#quizModal"), 1200);
    return;
  }

  // Показываем кнопку Следующий
  const nextBtn = $("#quizNext");
  const isLast  = state.quizData.current >= questions.length - 1;
  nextBtn.textContent = isLast ? "Завершить квиз" : "Следующий вопрос →";
  nextBtn.classList.remove("hidden");
}

function quizNextQuestion() {
  renderQuizQuestion();
}
window.quizNextQuestion = quizNextQuestion;

function abortQuiz() {
  state.quizData = null;
  closeModal("#quizModal");
}
window.abortQuiz = abortQuiz;

function onQuizFinished(data) {
  if (data.passed) {
    showResult(
      "🏆",
      "Квиз пройден!",
      `Результат: ${data.correct}/${data.total} (${data.score}%)${data.leveled_up ? `\n⬆️ Уровень ${data.new_level}!` : ""}${data.module_advanced ? "\n🎉 Новый модуль разблокирован!" : ""}`,
      data.xp_earned
    );
    loadQuests(); // обновляем список
    refreshHeader();
  } else {
    showResult(
      "😤",
      "Попробуй снова",
      `Результат: ${data.correct}/${data.total} (${data.score}%)\nНужно набрать ${data.required}%`,
      null
    );
  }
}

// ── TASK ──────────────────────────────────────────────────────────────────
function openTask(questId, title, xpReward, description) {
  state.currentQuestId = questId;
  $("#taskTitle").textContent = title;
  $("#taskXp").textContent = `+${xpReward} XP`;
  $("#taskDesc").textContent = description || "";

  const statusEl = $("#taskStatus");
  statusEl.className = "task-status hidden";

  const submitBtn = $("#taskSubmitBtn");
  submitBtn.disabled = false;
  submitBtn.textContent = "✅ Отправить на проверку";

  openModal("#taskModal");
}

async function submitCurrentTask() {
  if (!state.currentQuestId) return;
  const btn = $("#taskSubmitBtn");
  btn.disabled = true;
  btn.textContent = "⏳ Отправляю...";

  try {
    const res = await fetch(`${API}/quest/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: state.userId, quest_id: state.currentQuestId }),
    });
    const data = await res.json();

    if (data.ok) {
      const statusEl = $("#taskStatus");
      statusEl.className = "task-status pending";
      statusEl.textContent = "⏳ Задание отправлено! Ожидай проверки администратора.";
      btn.textContent = "✅ Отправлено";
      loadQuests();
    } else {
      btn.disabled = false;
      btn.textContent = "✅ Отправить на проверку";
      showToast(data.message || "Ошибка отправки", "error");
    }
  } catch (e) {
    console.error("submitTask:", e);
    btn.disabled = false;
    btn.textContent = "✅ Отправить на проверку";
    showToast("Ошибка сети", "error");
  }
}
window.submitCurrentTask = submitCurrentTask;

// ── RESULT MODAL ──────────────────────────────────────────────────────────
function showResult(emoji, title, text, xp) {
  $("#resultEmoji").textContent = emoji;
  $("#resultTitle").textContent = title;
  $("#resultText").textContent  = text;
  const xpEl = $("#resultXp");
  if (xp) {
    xpEl.textContent = `+${xp} XP`;
    xpEl.classList.remove("hidden");
  } else {
    xpEl.classList.add("hidden");
  }
  openModal("#resultModal");
}

function onResultClose() {
  closeModal("#resultModal");
}
window.onResultClose = onResultClose;

// ── TOAST ─────────────────────────────────────────────────────────────────
function showToast(msg, type = "info") {
  const toast = document.createElement("div");
  toast.textContent = msg;
  toast.style.cssText = `
    position:fixed; bottom:24px; left:50%; transform:translateX(-50%);
    background:${type === "error" ? "var(--bear)" : "var(--panel2)"};
    color:white; padding:10px 18px; border-radius:8px; font-size:12px;
    font-weight:600; z-index:9999; animation:fadeIn 0.3s ease;
    white-space:nowrap; max-width:90vw;
  `;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

// ── API CALLS ─────────────────────────────────────────────────────────────
async function loadQuests() {
  try {
    const res  = await fetch(`${API}/quests/${state.userId}`);
    const data = await res.json();
    renderQuests(data);
  } catch (e) {
    console.error("loadQuests:", e);
  }
}

async function loadLeaderboard() {
  try {
    const res  = await fetch(`${API}/leaderboard?limit=20`);
    const data = await res.json();
    renderLeaderboard(data);
  } catch (e) {
    console.error("loadLeaderboard:", e);
  }
}

async function refreshHeader() {
  try {
    const res = await fetch(`${API}/user/${state.userId}`);
    const s   = await res.json();
    renderHeader(s);
  } catch (e) {}
}

// ── INITIAL LOAD ──────────────────────────────────────────────────────────
async function init() {
  const info = getUserInfo();
  state.userId = info.id;

  try {
    // 1. Инициализация пользователя
    await fetch(`${API}/user/init`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: info.id, username: info.username, first_name: info.first_name, last_name: info.last_name }),
    });

    // 2. Параллельно грузим все данные
    const [userRes, modulesRes, questsRes, metaRes, lbRes] = await Promise.all([
      fetch(`${API}/user/${info.id}`),
      fetch(`${API}/modules`),
      fetch(`${API}/quests/${info.id}`),
      fetch(`${API}/lessons/meta`),
      fetch(`${API}/leaderboard`),
    ]);

    const [userData, modulesData, questsData, metaData, lbData] = await Promise.all([
      userRes.json(), modulesRes.json(), questsRes.json(), metaRes.json(), lbRes.json(),
    ]);

    // 3. Кэшируем meta
    Object.assign(state.lessonsMetaCache, metaData);

    // 4. Рендерим
    renderHeader(userData);
    renderModules(modulesData.modules || []);
    renderQuests(questsData);
    renderLeaderboard(lbData);

    // 5. Прогресс бар сразу из квестов
    setProgress(questsData.completed_count || 0, questsData.total_count || 0);

  } catch (e) {
    console.error("init error:", e);
    showToast("Ошибка загрузки данных", "error");
  }
}

// ── BTN START ─────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  init();

  document.getElementById("btn-start")?.addEventListener("click", () => {
    switchTab("lessons");
    // Открываем первый урок
    setTimeout(() => {
      const firstLesson = document.querySelector(".lesson-item");
      if (firstLesson) {
        document.querySelector(".module-header")?.click();
        setTimeout(() => firstLesson?.click(), 200);
      }
    }, 100);
  });
});
