// ───────── БАЗА: Telegram Mini App ─────────
const tg = window.Telegram ? window.Telegram.WebApp : null;

if (tg) {
  tg.ready();
  tg.expand();
}

const API_BASE = "/api";
const LESSONS_META = {};
const DEV_USER_ID = 445677777; // можешь заменить на свой Telegram ID

function getUserId() {
  if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
    return tg.initDataUnsafe.user.id;
  }
  return DEV_USER_ID;
}

// ───────── ВСПОМОГАТЕЛЬНОЕ ─────────
function $(selector) {
  return document.querySelector(selector);
}

function createEl(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}

// ───────── ПЕРЕКЛЮЧЕНИЕ ВКЛАДОК ─────────
function switchTab(tabName) {
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tabName);
  });

  document.querySelectorAll(".tab-content").forEach((block) => {
    block.classList.toggle("active", block.id === `tab-${tabName}`);
  });
}
window.switchTab = switchTab;

// ───────── МОДАЛКИ ─────────
function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add("hidden");
}
window.closeModal = closeModal;

// ───────── РЕНДЕР СОСТОЯНИЯ ПОЛЬЗОВАТЕЛЯ ─────────
function renderUserState(state) {
  $("#userName").textContent = state.name || "Трейдер";
  $("#userXP").textContent = state.xp ?? 0;
  $("#userLvl").textContent = state.level ?? 1;
  $("#userRank").textContent = state.rank || "🪨";

  const moduleIndex = (state.module_index ?? 0) + 1;
  $("#moduleName").textContent = `Модуль ${moduleIndex}`;

  const deadlineEl = $("#deadlineText");
  if (state.module_deadline) {
    const d = new Date(state.module_deadline);
    deadlineEl.textContent = `Дедлайн модуля: до ${d.toLocaleDateString("ru-RU")}`;
  } else {
    deadlineEl.textContent = "";
  }

  $("#progressBar").style.width = "0%";
}

// ───────── РЕНДЕР МОДУЛЕЙ И УРОКОВ ─────────
// /api/modules → {"modules": MODULES}
function renderModules(modulesResp) {
  const modules = modulesResp.modules || modulesResp;
  const container = $("#modulesList");
  container.innerHTML = "";

  modules.forEach((mod, idx) => {
    const card = createEl("div", "module-card");
    const header = createEl("div", "module-header");
    const title = createEl(
      "div",
      "module-title",
      `Модуль ${idx + 1}: ${mod.title}`
    );
    const chev = createEl("div", "module-chevron", "▼");

    header.appendChild(title);
    header.appendChild(chev);
    card.appendChild(header);

    const list = createEl("div", "lesson-list");
    mod.lessons.forEach((lessonKey) => {
      const meta = LESSONS_META[lessonKey];
      const displayTitle = meta ? meta.title : lessonKey;

      const item = createEl("div", "lesson-item");
      const name = createEl("div", "lesson-name", displayTitle);
      const arrow = createEl("div", "lesson-arrow", "›");
      item.appendChild(name);
      item.appendChild(arrow);

      item.addEventListener("click", () => openLesson(lessonKey));
      list.appendChild(item);
    });

    card.appendChild(list);

    header.addEventListener("click", () => {
      card.classList.toggle("open");
    });

    container.appendChild(card);
  });
}

// ───────── РЕНДЕР КВЕСТОВ ─────────
// /api/quests/{user_id} → {"quests": [...]}
function renderQuests(questsResp) {
  const container = $("#questsList");
  container.innerHTML = "";

  const quests = questsResp.quests || [];
  quests.forEach((q) => {
    const card = createEl("div", "quest-card");
    if (q.completed) card.classList.add("completed");

    const header = createEl("div", "quest-header");
    const title = createEl("div", "quest-title", q.title);
    const xp = createEl("div", "quest-xp", `+${q.xp_reward} XP`);
    header.appendChild(title);
    header.appendChild(xp);

    const typeBadge = createEl(
      "div",
      "quest-type-badge " +
        (q.type === "quiz" ? "quest-type-quiz" : "quest-type-task"),
      q.type === "quiz" ? "Квиз" : "Задание"
    );
    const desc = createEl("div", "quest-desc", q.description || "");

    const btn = createEl(
      "button",
      "btn-start-quest",
      q.type === "quiz" ? "Начать квиз" : "Открыть задание"
    );
    btn.disabled = q.completed;
    btn.addEventListener("click", () => {
      if (q.type === "quiz") {
        startQuiz(q.id);
      } else {
        startTask(q.id);
      }
    });

    card.appendChild(header);
    card.appendChild(typeBadge);
    card.appendChild(desc);
    card.appendChild(btn);

    container.appendChild(card);
  });
}

// ───────── РЕНДЕР ЛИДЕРБОРДА ─────────
// /api/leaderboard → {"leaderboard": [...]}
function renderLeaderboard(resp) {
  const list = resp.leaderboard || resp;
  const container = $("#leaderboardList");
  container.innerHTML = "";

  list.forEach((row, idx) => {
    const item = createEl("div", "lb-item");
    const rank = createEl("div", "lb-rank", idx + 1);
    const info = createEl("div", "lb-info");
    const name = createEl("div", "lb-name", row.name || `User ${row.user_id}`);
    const sub = createEl(
      "div",
      "lb-sub",
      `Lvl ${row.level} • ${row.rank} • Модуль ${row.module}`
    );
    const xp = createEl("div", "lb-xp", `${row.xp} XP`);

    info.appendChild(name);
    info.appendChild(sub);
    item.appendChild(rank);
    item.appendChild(info);
    item.appendChild(xp);
    container.appendChild(item);
  });
}

// ───────── ОТКРЫТИЕ УРОКА ─────────
// /api/lesson/{lesson_key} + /api/chart/{lesson_key}/png
async function openLesson(lessonKey) {
  try {
    const res = await fetch(`${API_BASE}/lesson/${lessonKey}`);
    if (!res.ok) throw new Error("lesson fetch failed");
    const data = await res.json();

    $("#lessonTitle").textContent = data.title;
    $("#lessonArticle").textContent = data.article || "";
    const link = $("#lessonVideo");
    link.href = data.video || "#";

    const loading = document.querySelector(".chart-loading");
    const img = $("#chartImg");
    loading.style.display = "block";
    img.style.display = "none";

    const chartRes = await fetch(`${API_BASE}/chart/${lessonKey}/png`);
    if (chartRes.ok) {
      const blob = await chartRes.blob();
      img.src = URL.createObjectURL(blob);
      img.onload = () => {
        loading.style.display = "none";
        img.style.display = "block";
      };
    } else {
      loading.textContent = "График недоступен";
    }

    $("#lessonModal").classList.remove("hidden");
  } catch (e) {
    console.error(e);
    alert("Ошибка загрузки урока");
  }
}
window.openLesson = openLesson;

// ───────── СТАРТ ЗАДАНИЯ / КВИЗА ─────────
// /api/quest/start
async function startTask(questId) {
  try {
    const userId = getUserId();
    const res = await fetch(`${API_BASE}/quest/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, quest_id: questId }),
    });
    const data = await res.json();
    if (!data.ok) {
      alert("Не удалось стартовать квест: " + (data.message || data.error));
      return;
    }
    alert("Квест начат. Логику проверки задания можно будет добавить позже.");
  } catch (e) {
    console.error(e);
    alert("Ошибка старта квеста");
  }
}

async function startQuiz(questId) {
  try {
    const userId = getUserId();
    const res = await fetch(`${API_BASE}/quest/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId, quest_id: questId }),
    });
    const data = await res.json();
    if (!data.ok) {
      alert("Не удалось стартовать квиз: " + (data.message || data.error));
      return;
    }
    alert("Квиз стартовал (фронт-часть квиза добавим отдельным шагом).");
  } catch (e) {
    console.error(e);
    alert("Ошибка старта квиза");
  }
}

// ───────── ИНИЦИАЛИЗАЦИЯ ПОЛЬЗОВАТЕЛЯ ─────────
// /api/user/init и /api/user/{user_id}
async function initUser() {
  const userId = getUserId();
  try {
    await fetch(`${API_BASE}/user/init`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: userId }),
    });
  } catch (e) {
    console.error("user init error", e);
  }
  return userId;
}

// ───────── ЗАГРУЗКА ДАННЫХ ПРИ СТАРТЕ ─────────
async function loadInitialData() {
  try {
    const userId = await initUser();

    const [stateRes, modulesRes, questsRes, lbRes, lessonsMetaRes] =
      await Promise.all([
        fetch(`${API_BASE}/user/${userId}`),
        fetch(`${API_BASE}/modules`),
        fetch(`${API_BASE}/quests/${userId}`),
        fetch(`${API_BASE}/leaderboard`),
        fetch(`${API_BASE}/lessons/meta`),
      ]);

    const state = await stateRes.json();
    const modules = await modulesRes.json();
    const quests = await questsRes.json();
    const lb = await lbRes.json();
    const lessonsMeta = await lessonsMetaRes.json();

    Object.assign(LESSONS_META, lessonsMeta);

    renderUserState(state);
    renderModules(modules);
    renderQuests(quests);
    renderLeaderboard(lb);
  } catch (e) {
    console.error("init error", e);
  }
}

document.addEventListener("DOMContentLoaded", loadInitialData);

// ───────── КНОПКА "Начать обучение" ─────────
document.addEventListener("DOMContentLoaded", () => {
  const btnStart = document.getElementById("btn-start");
  if (!btnStart) return;

  btnStart.addEventListener("click", () => {
    switchTab("lessons");
    openLesson("what_is_smc");
  });
});
