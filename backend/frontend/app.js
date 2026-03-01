/* ═══════════════════════════════════════════════════════════════════════
   CHM Smart Money Academy — app.js v5.0
   72h Deadlines · SMC Levels · Streak · Penalty Flow · Countdown Timer
   ═══════════════════════════════════════════════════════════════════════ */

// ── CONFIG ────────────────────────────────────────────────────────────────
const API     = "/api";
const tg      = window.Telegram?.WebApp ?? null;
const DEV_UID = 445677777;

// ── GLOBAL STATE ──────────────────────────────────────────────────────────
const state = {
  userId: null,
  userState: null,
  quizData: null,
  currentQuestId: null,
  lessonsMetaCache: {},
  quizStreak: 0,
  countdownInterval: null,
  deadlineInfo: null,
};

// ── SMC TRADER LEVELS (7 levels) ──────────────────────────────────────────
const SMC_LEVELS = [
  { xp: 0,    level: 1, name: "Наблюдатель рынка",       color: "#78716c", glow: "rgba(120,113,108,0.4)" },
  { xp: 300,  level: 2, name: "Охотник за ликвидностью", color: "#00d4ff", glow: "rgba(0,212,255,0.4)"  },
  { xp: 700,  level: 3, name: "Снайпер ордер-блоков",    color: "#a78bfa", glow: "rgba(167,139,250,0.4)" },
  { xp: 1300, level: 4, name: "SMC Практик",             color: "#00e87a", glow: "rgba(0,232,122,0.4)"  },
  { xp: 2100, level: 5, name: "Smart Money Инсайдер",    color: "#f59e0b", glow: "rgba(245,158,11,0.5)"  },
  { xp: 3200, level: 6, name: "Институциональный призрак",color: "#fbbf24", glow: "rgba(251,191,36,0.5)" },
  { xp: 5000, level: 7, name: "Архитектор рынка",        color: "#ff4d6d", glow: "rgba(255,77,109,0.6)"  },
];

const LEVEL_QUOTES = [
  "",
  "Биткоин не ждал тебя в 2017. Не будет ждать и сейчас.",
  "Ты видишь ликвидность там, где другие видят поддержку.",
  "Каждый OB — это след Smart Money. Ты научился его читать.",
  "Рынок манипулятивен. Ты знаешь, как.",
  "Ты торгуешь не по индикаторам — ты торгуешь по логике SM.",
  "Институциональные трейдеры не знают, что ты за ними следишь.",
  "Архитектор рынка — ты понимаешь структуру, которую другие не видят.",
];

function getLevelInfo(xp) {
  let info = SMC_LEVELS[0];
  for (const lvl of SMC_LEVELS) {
    if (xp >= lvl.xp) info = lvl;
  }
  return info;
}

// ── SVG RANK ICONS ────────────────────────────────────────────────────────
function getRankSVG(rankName) {
  const lvl = SMC_LEVELS.find(l => l.name === rankName) || SMC_LEVELS[0];
  const c = lvl.color;
  if (lvl.level === 7) {
    return `<svg viewBox="0 0 40 40" fill="none">
      <defs><radialGradient id="rg7" cx="40%" cy="35%" r="60%">
        <stop offset="0%" stop-color="#ff8fa3"/><stop offset="100%" stop-color="#cc1133"/>
      </radialGradient></defs>
      <circle cx="20" cy="20" r="16" fill="#150508" stroke="${c}" stroke-width="2"/>
      <circle cx="20" cy="20" r="12" fill="url(#rg7)" opacity="0.2"/>
      <path d="M20 8L23 16H32L25 21L28 30L20 25L12 30L15 21L8 16H17Z" fill="url(#rg7)"/>
      <circle cx="20" cy="18" r="3" fill="white" opacity="0.4"/>
    </svg>`;
  }
  if (lvl.level >= 5) {
    return `<svg viewBox="0 0 40 40" fill="none">
      <circle cx="20" cy="20" r="16" fill="#0a0c10" stroke="${c}" stroke-width="2"/>
      <circle cx="20" cy="20" r="10" fill="${c}" opacity="0.15"/>
      <path d="M20 8 L23 16H32L25 21L28 30L20 25L12 30L15 21L8 16H17Z" fill="${c}" opacity="0.9"/>
      <circle cx="20" cy="19" r="3" fill="white" opacity="0.3"/>
    </svg>`;
  }
  return `<svg viewBox="0 0 40 40" fill="none">
    <circle cx="20" cy="20" r="16" fill="#111420" stroke="${c}" stroke-width="2"/>
    <circle cx="20" cy="20" r="10" fill="${c}" opacity="0.2"/>
    <path d="M20 10 L22.5 17H30L24 21.5L26.5 29L20 24.5L13.5 29L16 21.5L10 17H17.5Z" fill="${c}"/>
  </svg>`;
}

// ── INIT ──────────────────────────────────────────────────────────────────
if (tg) { tg.ready(); tg.expand(); tg.setHeaderColor("#060810"); }

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

// ── CANDLESTICK CANVAS BACKGROUND ────────────────────────────────────────
function initCanvas() {
  const canvas = document.getElementById("bgCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  function resize() {
    canvas.width  = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener("resize", resize);

  const candleW = 12, gap = 8, step = candleW + gap;
  const cols = Math.ceil(window.innerWidth / step) + 4;
  const candles = [];
  let price = 180 + Math.random() * 100;

  for (let i = 0; i < cols; i++) {
    const change = (Math.random() - 0.46) * 18;
    const open  = price;
    price = Math.max(60, Math.min(380, price + change));
    const close = price;
    const high  = Math.max(open, close) + Math.random() * 12;
    const low   = Math.min(open, close) - Math.random() * 12;
    candles.push({ open, close, high, low, x: i * step });
  }

  let offset = 0;
  function draw() {
    const W = canvas.width, H = canvas.height;
    ctx.clearRect(0, 0, W, H);
    ctx.strokeStyle = "rgba(255,255,255,0.025)";
    ctx.lineWidth = 1;
    for (let y = 0; y < H; y += 60) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
    }
    const maxH = Math.max(...candles.map(c => c.high));
    const minL = Math.min(...candles.map(c => c.low));
    const range = maxH - minL || 1;
    const scale = (H * 0.7) / range;
    const toY = v => H * 0.15 + (maxH - v) * scale;

    candles.forEach((c) => {
      const x = c.x - offset;
      const wx = ((x % (W + step * 2)) + W + step * 2) % (W + step * 2) - step;
      const isBull = c.close >= c.open;
      const bodyCol = isBull ? "rgba(0,232,122," : "rgba(255,77,109,";
      const oY = toY(c.open), cY = toY(c.close), hY = toY(c.high), lY = toY(c.low);
      ctx.strokeStyle = bodyCol + "0.5)";
      ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(wx + candleW/2, hY); ctx.lineTo(wx + candleW/2, lY); ctx.stroke();
      ctx.shadowColor = isBull ? "#00e87a" : "#ff4d6d";
      ctx.shadowBlur = 4;
      ctx.fillStyle = bodyCol + "0.7)";
      ctx.fillRect(wx, Math.min(oY, cY), candleW, Math.max(Math.abs(cY - oY), 2));
      ctx.shadowBlur = 0;
    });
    offset += 0.4;
    requestAnimationFrame(draw);
  }
  draw();
}

// ── ONBOARDING ────────────────────────────────────────────────────────────
let obCurrentSlide = 0;
const OB_TOTAL = 3;

function initOnboarding() {
  const overlay = $("#onboardingOverlay");
  if (!overlay || localStorage.getItem("smc_onboarding_done")) return;
  overlay.classList.remove("hidden");
  const nextBtn = $("#ob-next-btn");
  const skipBtn = $("#ob-skip-btn");
  nextBtn.addEventListener("click", () => {
    if (obCurrentSlide < OB_TOTAL - 1) goToSlide(obCurrentSlide + 1);
    else closeOnboarding();
  });
  skipBtn.addEventListener("click", closeOnboarding);
  document.querySelectorAll(".ob-dot").forEach(dot => {
    dot.addEventListener("click", () => goToSlide(parseInt(dot.dataset.dot)));
  });
}

function goToSlide(idx) {
  const slides = document.querySelectorAll(".ob-slide");
  const dots   = document.querySelectorAll(".ob-dot");
  const nextBtn = $("#ob-next-btn");
  slides[obCurrentSlide].classList.add("exit-left");
  slides[obCurrentSlide].classList.remove("active");
  setTimeout(() => slides[obCurrentSlide]?.classList.remove("exit-left"), 400);
  obCurrentSlide = idx;
  slides[idx].classList.add("active");
  dots.forEach((d, i) => d.classList.toggle("active", i === idx));
  nextBtn.textContent = idx === OB_TOTAL - 1 ? "Начать →" : "Далее";
}

function closeOnboarding() {
  const overlay = $("#onboardingOverlay");
  if (overlay) { overlay.style.animation = "fadeOut 0.3s ease forwards"; setTimeout(() => overlay.classList.add("hidden"), 300); }
  localStorage.setItem("smc_onboarding_done", "1");
}

// ── CONFETTI ──────────────────────────────────────────────────────────────
const CONFETTI_COLORS = ["#00d4ff", "#fbbf24", "#00e87a", "#a78bfa", "#ff4d6d", "#f97316"];

function launchConfetti(count = 80) {
  const layer = $("#confettiLayer");
  if (!layer) return;
  for (let i = 0; i < count; i++) {
    const piece = document.createElement("div");
    piece.className = "confetti-piece";
    const dur = 1.8 + Math.random() * 1.5;
    const delay = Math.random() * 0.8;
    piece.style.cssText = `
      left: ${Math.random() * 100}%;
      animation-duration: ${dur}s; animation-delay: ${delay}s;
      background: ${CONFETTI_COLORS[Math.floor(Math.random() * CONFETTI_COLORS.length)]};
      width: ${6 + Math.random() * 8}px; height: ${6 + Math.random() * 8}px;
      border-radius: ${Math.random() > 0.5 ? "50%" : "2px"};
      transform: rotate(${Math.random() * 360}deg);
    `;
    layer.appendChild(piece);
    setTimeout(() => piece.remove(), (dur + delay) * 1000 + 100);
  }
}

// ── XP FLOAT ──────────────────────────────────────────────────────────────
function floatXP(amount, sourceEl) {
  const layer = $("#xpFloatLayer");
  if (!layer) return;
  const rect = sourceEl ? sourceEl.getBoundingClientRect() : { left: window.innerWidth/2, top: window.innerHeight/2, width: 0 };
  const e = document.createElement("div");
  e.className = "xp-float";
  e.textContent = `+${amount} XP`;
  e.style.left = (rect.left + (rect.width||0)/2) + "px";
  e.style.top  = rect.top + "px";
  layer.appendChild(e);
  setTimeout(() => e.remove(), 1700);
  if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
}

// ── LEVEL UP SCREEN ───────────────────────────────────────────────────────
function showLevelUp(level, rankName) {
  const overlay = $("#levelUpOverlay");
  if (!overlay) return;
  const lvlInfo = getLevelInfo(state.userState?.xp || 0);
  $("#levelupNum").textContent      = level;
  $("#levelupRankName").textContent = rankName || lvlInfo.name;
  $("#levelupRankIcon").innerHTML   = getRankSVG(rankName || lvlInfo.name);
  $("#levelupQuote").textContent    = LEVEL_QUOTES[level] || "";

  const container = $("#levelupParticles");
  container.innerHTML = "";
  for (let i = 0; i < 24; i++) {
    const p = document.createElement("div");
    p.className = "levelup-particle";
    const angle = (i / 24) * 360;
    const dist  = 80 + Math.random() * 80;
    const color = CONFETTI_COLORS[Math.floor(Math.random() * CONFETTI_COLORS.length)];
    p.style.cssText = `
      --tx: ${Math.cos(angle*Math.PI/180)*dist}px;
      --ty: ${Math.sin(angle*Math.PI/180)*dist}px;
      --dur: ${0.8 + Math.random()*0.6}s;
      background: ${color}; left:50%; top:50%; box-shadow:0 0 6px ${color};
    `;
    container.appendChild(p);
  }
  overlay.classList.remove("hidden");
  launchConfetti(120);
  if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
}

document.getElementById("levelupCloseBtn")?.addEventListener("click", () => {
  $("#levelUpOverlay").classList.add("hidden");
});

// ── COUNTDOWN TIMER ───────────────────────────────────────────────────────
function startCountdown(deadlineISO) {
  if (state.countdownInterval) {
    clearInterval(state.countdownInterval);
    state.countdownInterval = null;
  }
  if (!deadlineISO) {
    $("#deadlineCountdown")?.classList.add("hidden");
    return;
  }

  const cdEl = $("#deadlineCountdown");
  const timerEl = $("#countdownTimer");
  if (!cdEl || !timerEl) return;
  cdEl.classList.remove("hidden");

  function update() {
    const now = Date.now();
    const end = new Date(deadlineISO).getTime();
    const diff = end - now;

    if (diff <= 0) {
      timerEl.textContent = "00:00:00";
      cdEl.className = "deadline-countdown urgency-expired";
      clearInterval(state.countdownInterval);
      state.countdownInterval = null;
      showDeadlineExpiredScreen();
      return;
    }

    const hours = Math.floor(diff / 3600000);
    const mins  = Math.floor((diff % 3600000) / 60000);
    const secs  = Math.floor((diff % 60000) / 1000);
    timerEl.textContent = `${String(hours).padStart(2,"0")}:${String(mins).padStart(2,"0")}:${String(secs).padStart(2,"0")}`;

    // Urgency classes
    const hoursLeft = diff / 3600000;
    if (hoursLeft <= 1) {
      cdEl.className = "deadline-countdown urgency-critical";
    } else if (hoursLeft <= 6) {
      cdEl.className = "deadline-countdown urgency-danger";
    } else if (hoursLeft <= 24) {
      cdEl.className = "deadline-countdown urgency-warning";
    } else {
      cdEl.className = "deadline-countdown urgency-normal";
    }
  }

  update();
  state.countdownInterval = setInterval(update, 1000);
}

// ── DEADLINE EXPIRED SCREEN ───────────────────────────────────────────────
function showDeadlineExpiredScreen() {
  const overlay = $("#deadlineExpiredOverlay");
  if (!overlay) return;

  const dlInfo = state.deadlineInfo;
  const moduleIdx = state.userState?.module_index ?? 0;

  // Set penalty amounts from deadline info
  const penaltyAmount = dlInfo?.penalty_amount ?? 5;
  const repurchaseAmount = dlInfo?.repurchase_amount ?? 15;

  const penaltyTxt = $("#penaltyAmountText");
  const repurchaseTxt = $("#repurchaseAmountText");
  if (penaltyTxt) penaltyTxt.textContent = `$${penaltyAmount}`;
  if (repurchaseTxt) repurchaseTxt.textContent = `$${repurchaseAmount}`;

  // Show repurchase option if extensions exhausted
  const canExtend = dlInfo?.can_extend ?? true;
  const penaltyOpt = $("#penaltyOption");
  const repurchaseOpt = $("#repurchaseOption");
  if (canExtend) {
    penaltyOpt?.classList.remove("hidden");
    repurchaseOpt?.classList.add("hidden");
  } else {
    penaltyOpt?.classList.add("hidden");
    repurchaseOpt?.classList.remove("hidden");
  }

  overlay.classList.remove("hidden");
  if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred("error");
}

// Pay penalty handler
document.getElementById("payPenaltyBtn")?.addEventListener("click", async () => {
  const btn = $("#payPenaltyBtn");
  btn.disabled = true;
  btn.textContent = "⏳ Обработка...";

  try {
    const res = await fetch(`${API}/deadline/penalty`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: state.userId,
        module_index: state.userState?.module_index ?? 0,
        payment_type: "penalty",
      }),
    });
    const data = await res.json();
    if (data.ok) {
      $("#deadlineExpiredOverlay").classList.add("hidden");
      state.deadlineInfo = data.deadline_info;
      startCountdown(data.new_deadline_iso);
      showToast("Штраф оплачен. У тебя 48 часов. Не теряй их.", "success");
      await refreshHeader();
      await loadQuests();
    } else {
      showToast(data.message || "Ошибка", "error");
      btn.disabled = false;
      btn.textContent = "Оплатить и продолжить →";
    }
  } catch (e) {
    console.error("payPenalty:", e);
    showToast("Ошибка сети", "error");
    btn.disabled = false;
    btn.textContent = "Оплатить и продолжить →";
  }
});

// Repurchase handler
document.getElementById("repurchaseBtn")?.addEventListener("click", async () => {
  const btn = $("#repurchaseBtn");
  btn.disabled = true;
  btn.textContent = "⏳ Обработка...";

  try {
    const res = await fetch(`${API}/deadline/penalty`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: state.userId,
        module_index: state.userState?.module_index ?? 0,
        payment_type: "repurchase",
      }),
    });
    const data = await res.json();
    if (data.ok) {
      $("#deadlineExpiredOverlay").classList.add("hidden");
      state.deadlineInfo = data.deadline_info;
      startCountdown(data.deadline_info?.deadline_iso);
      showToast("Модуль перекуплен. Новый дедлайн: 72 часа.", "success");
      await refreshHeader();
      await loadQuests();
    } else {
      showToast(data.message || "Ошибка", "error");
      btn.disabled = false;
      btn.textContent = "Перекупить доступ →";
    }
  } catch (e) {
    showToast("Ошибка сети", "error");
    btn.disabled = false;
    btn.textContent = "Перекупить доступ →";
  }
});

// ── TABS ──────────────────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll(".tab").forEach(b => b.classList.toggle("active", b.dataset.tab === name));
  document.querySelectorAll(".tab-content").forEach(c => c.classList.toggle("active", c.id === `tab-${name}`));
  if (name === "quests")       loadQuests();
  if (name === "leaderboard")  loadLeaderboard();
  if (tg?.HapticFeedback) tg.HapticFeedback.selectionChanged();
}
window.switchTab = switchTab;

// ── MODALS ────────────────────────────────────────────────────────────────
function openModal(id)  { const sel = id.startsWith('#') ? id : '#'+id; $(sel)?.classList.remove("hidden"); if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred("light"); }
function closeModal(id) { const sel = id.startsWith('#') ? id : '#'+id; $(sel)?.classList.add("hidden"); }
window.closeModal = closeModal;

// ── MARKDOWN RENDERER ─────────────────────────────────────────────────────
function renderMarkdown(text) {
  if (!text) return "";
  const div   = document.createElement("div");
  const lines = text.split("\n");
  lines.forEach((line, idx) => {
    if (!line.trim()) { if (idx > 0) div.appendChild(document.createElement("br")); return; }
    const p = document.createElement("span");
    p.style.display = "block";
    const parts = line.split(/\*([^*]+)\*/g);
    parts.forEach((part, i) => {
      if (i % 2 === 1) { const s = document.createElement("strong"); s.textContent = part; p.appendChild(s); }
      else if (part) p.appendChild(document.createTextNode(part));
    });
    if (line.startsWith("• ") || line.match(/^[1-9][️⃣)\\.] /)) p.className = "bullet";
    div.appendChild(p);
  });
  return div.innerHTML;
}

// ── RENDER USER STATE ─────────────────────────────────────────────────────
function renderHeader(s) {
  state.userState = s;
  const rankName = s.rank || "Наблюдатель рынка";
  const lvlInfo  = getLevelInfo(s.xp || 0);

  $("#userName").textContent = s.name || "Трейдер";
  $("#userXP").textContent   = s.xp ?? 0;
  $("#userLvl").textContent  = s.level ?? 1;
  $("#moduleName").textContent = `Модуль ${(s.module_index ?? 0) + 1}`;

  const rankWrap = $("#rankIconWrap");
  if (rankWrap) rankWrap.innerHTML = getRankSVG(rankName);

  // Streak badge
  const streak = s.streak || 0;
  const streakBadge = $("#streakBadge");
  const streakCount = $("#streakCount");
  if (streakBadge && streakCount) {
    streakCount.textContent = streak;
    streakBadge.classList.toggle("hidden", streak < 2);
    if (streak >= 7) streakBadge.classList.add("streak-hot");
    else streakBadge.classList.remove("streak-hot");
  }
}

function setProgress(completed, total) {
  const pct = total > 0 ? Math.round(completed / total * 100) : 0;
  const bar  = $("#progressBar");
  const glow = $("#progressGlow");
  if (bar)  bar.style.width = pct + "%";
  if (glow) glow.style.left = pct + "%";
  if ($("#progressLabel")) $("#progressLabel").textContent = `${completed}/${total} квестов`;
  if ($("#progressPct"))   $("#progressPct").textContent = pct + "%";
}

function applyDeadlineInfo(dlInfo) {
  if (!dlInfo) return;
  state.deadlineInfo = dlInfo;

  // Show module subtitle if available
  const subEl = $("#moduleSubtitle");
  if (subEl && state.userState) {
    // Will be set from quests response
  }

  if (dlInfo.deadline_expired) {
    showDeadlineExpiredScreen();
    return;
  }

  if (dlInfo.deadline_iso) {
    startCountdown(dlInfo.deadline_iso);
  } else {
    $("#deadlineCountdown")?.classList.add("hidden");
  }
}

// ── RENDER MODULES ────────────────────────────────────────────────────────
function renderModules(modules) {
  const container = $("#modulesList");
  container.innerHTML = "";
  const currentModuleIdx = state.userState?.module_index ?? 0;

  modules.forEach((mod, idx) => {
    const isCurrentOrPast = idx <= currentModuleIdx;
    const isFree = mod.is_free;
    const isLocked = !isFree && idx > currentModuleIdx;

    const card   = el("div", `module-card${isLocked ? " locked" : ""}${idx === currentModuleIdx ? " current" : ""}`);
    const header = el("div", "module-header");

    const titleWrap = el("div", "module-title-wrap");
    const numBadge  = el("div", `module-num-badge${idx < currentModuleIdx ? " done" : idx === currentModuleIdx ? " active" : ""}`,
      idx < currentModuleIdx ? "✓" : `${idx + 1}`
    );
    const titleInfo = el("div", "module-title-info");
    const title     = el("div", "module-title", `${mod.title}`);
    const subtitle  = el("div", "module-subtitle-small", mod.subtitle || "");
    titleInfo.append(title, subtitle);
    titleWrap.append(numBadge, titleInfo);

    const right = el("div", "module-header-right");
    if (isFree) right.appendChild(el("div", "module-free-badge", "БЕСПЛАТНО"));
    if (isLocked) right.appendChild(el("div", "module-lock-icon", "🔒"));
    const chev = el("div", "module-chevron", "▼");
    right.append(chev);
    header.append(titleWrap, right);
    card.append(header);

    const list = el("div", "lesson-list");
    (mod.lessons || []).forEach(key => {
      const meta  = state.lessonsMetaCache[key];
      const name  = meta ? meta.title : key;
      const item  = el("div", `lesson-item${isLocked ? " lesson-locked" : ""}`);
      const lname = el("div", "lesson-name", name);
      const arr   = el("div", "lesson-arrow", isLocked ? "🔒" : "›");
      item.append(lname, arr);
      if (!isLocked) {
        item.addEventListener("click", () => openLesson(key));
      } else {
        item.addEventListener("click", () => showToast("Пройди текущий модуль чтобы открыть этот", "info"));
      }
      list.appendChild(item);
    });

    card.appendChild(list);
    header.addEventListener("click", () => {
      if (!isLocked) {
        card.classList.toggle("open");
        if (tg?.HapticFeedback) tg.HapticFeedback.selectionChanged();
      }
    });

    // Auto-open current module
    if (idx === currentModuleIdx) card.classList.add("open");

    container.appendChild(card);
  });
}

// ── RENDER QUESTS ─────────────────────────────────────────────────────────
function renderQuests(resp) {
  const quests    = resp.quests || [];
  const container = $("#questsList");
  container.innerHTML = "";

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

  // Update module subtitle
  const subEl = $("#moduleSubtitle");
  if (subEl) subEl.textContent = resp.module_subtitle || "";

  setProgress(resp.completed_count || 0, resp.total_count || 0);

  // Apply deadline info from quests response
  if (resp.deadline_info) {
    applyDeadlineInfo(resp.deadline_info);
  }

  if (resp.deadline_expired) {
    const expiredBanner = el("div", "deadline-expired-banner");
    expiredBanner.innerHTML = `
      <div class="deb-icon">🔴</div>
      <div class="deb-text">
        <strong>Дедлайн истёк</strong>
        <span>Модуль заблокирован — оплати штраф для продолжения</span>
      </div>
      <button class="deb-btn" onclick="showDeadlineExpiredScreen()">Разблокировать</button>
    `;
    container.appendChild(expiredBanner);
    return;
  }

  if (!quests.length) {
    container.innerHTML = `
      <div class="empty-state">
        <span class="es-icon">⚔️</span>
        <div class="es-title">Нет активных квестов</div>
        <p>Выполни все задания чтобы открыть следующий модуль</p>
      </div>`;
    return;
  }

  quests.forEach(q => {
    const isBoss = q.id.endsWith("_boss");
    const card   = el("div", `quest-card ${q.type}${isBoss ? " boss" : ""}${q.completed ? " completed" : ""}`);

    const iconWrap = el("div", `quest-type-icon ${q.type === "quiz" ? "quiz-icon" : isBoss ? "boss-icon" : "task-icon"}`);
    if (q.type === "quiz") {
      iconWrap.innerHTML = `<svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <circle cx="10" cy="7" r="4" stroke="#00d4ff" stroke-width="1.5"/>
        <path d="M3 17C3 14.8 6.1 13 10 13C13.9 13 17 14.8 17 17" stroke="#00d4ff" stroke-width="1.5" stroke-linecap="round"/>
      </svg>`;
    } else if (isBoss) {
      iconWrap.innerHTML = `<svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M10 2L12.5 8H19L13.5 11.5L16 18L10 14.5L4 18L6.5 11.5L1 8H7.5Z" stroke="#fbbf24" stroke-width="1.5" stroke-linejoin="round" fill="rgba(251,191,36,0.15)"/>
      </svg>`;
    } else {
      iconWrap.innerHTML = `<svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <rect x="4" y="3" width="12" height="14" rx="2" stroke="#a78bfa" stroke-width="1.5"/>
        <line x1="7" y1="7" x2="13" y2="7" stroke="#a78bfa" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="7" y1="10" x2="13" y2="10" stroke="#a78bfa" stroke-width="1.5" stroke-linecap="round" opacity="0.6"/>
        <line x1="7" y1="13" x2="10" y2="13" stroke="#a78bfa" stroke-width="1.5" stroke-linecap="round" opacity="0.4"/>
      </svg>`;
    }

    const headerRow  = el("div", "quest-header");
    const headerInfo = el("div", "quest-header-info");
    const title  = el("div", "quest-title", q.title);
    const xp     = el("div", "quest-xp", `+${q.xp_reward} XP`);
    headerInfo.append(title, xp);
    headerRow.append(iconWrap, headerInfo);

    const badges = el("div", "quest-badges");
    const typeBadge = el("div", `quest-type-badge quest-type-${isBoss ? "boss" : q.type}`,
      q.type === "quiz" ? "КВИЗ" : isBoss ? "👑 БОСС" : "ЗАДАНИЕ");
    badges.appendChild(typeBadge);

    const hw = state.userState?.homework_status;
    if (q.is_active && q.type === "task") {
      const statuses = {
        pending:  ["⏳ На проверке", "pending"],
        approved: ["✅ Принято",    "approved"],
        revision: ["🔄 На доработке","revision"],
        rejected: ["❌ Не принято", "rejected"],
      };
      const [txt, cls] = statuses[hw] || [];
      if (txt) badges.appendChild(el("div", `quest-status-badge status-${cls}`, txt));
    }

    const desc = el("div", "quest-desc", q.description || "");

    const canResubmit = q.is_active && q.type === "task" && (hw === "revision" || hw === "rejected");
    const btnLabel = q.completed
      ? "✓ Выполнено"
      : q.type === "quiz"
        ? "▶ Начать квиз"
        : canResubmit
          ? "🔄 Отправить повторно"
          : "📋 Открыть задание";
    const btn = el("button", "btn-quest", btnLabel);
    btn.disabled = q.completed && !canResubmit;
    btn.addEventListener("click", (e) => {
      if (q.type === "quiz") startQuiz(q.id, q.title, q.xp_reward, e.currentTarget);
      else openTask(q.id, q.title, q.xp_reward, q.description);
    });

    card.append(headerRow, badges, desc, btn);
    container.appendChild(card);
  });
}

// ── RENDER LEADERBOARD ────────────────────────────────────────────────────
function renderLeaderboard(resp) {
  const list      = resp.leaderboard || [];
  const container = $("#leaderboardList");
  const podium    = $("#leaderboardPodium");
  container.innerHTML = "";
  if (podium) podium.innerHTML = "";

  if (!list.length) {
    container.innerHTML = `<div class="empty-state"><span class="es-icon">🏆</span><div class="es-title">Пока никого нет</div><p>Стань первым!</p></div>`;
    return;
  }

  // ── Podium for top-3 ──
  if (podium && list.length >= 1) {
    // order: 2nd (left) | 1st (center) | 3rd (right)
    const podiumOrder = [1, 0, 2]; // indices into list
    const barHeights  = [64, 48, 40]; // index 0=1st place, 1=2nd, 2=3rd
    const crowns      = ["👑", "", ""];
    const medals      = ["🥇", "🥈", "🥉"];

    podiumOrder.forEach((listIdx) => {
      const row = list[listIdx];
      if (!row) return;
      const place = listIdx + 1; // 1, 2, or 3
      const nameShort = (row.name || `User ${row.user_id}`).split(" ")[0].slice(0, 10);
      const initials  = nameShort.slice(0, 2).toUpperCase();

      const div = document.createElement("div");
      div.className = "podium-place";

      div.innerHTML = `
        <div class="podium-avatar">
          ${listIdx === 0 ? `<span class="podium-crown">👑</span>` : ""}
          ${initials}
        </div>
        <div class="podium-name">${nameShort}</div>
        <div class="podium-xp">${row.xp} XP</div>
        <div class="podium-bar">${medals[listIdx]}</div>
      `;
      podium.appendChild(div);
    });
  }

  // ── Full list (all entries, starting from rank 1) ──
  list.forEach((row, i) => {
    const item = el("div", "lb-item");
    const rank = el("div", "lb-rank", i < 3 ? ["🥇","🥈","🥉"][i] : `${i+1}`);
    const info = el("div", "lb-info");
    const name = el("div", "lb-name", row.name || `User ${row.user_id}`);
    const sub  = el("div", "lb-sub", `${row.rank || "Наблюдатель рынка"} · Модуль ${row.module || 1}`);
    const xp   = el("div", "lb-xp", `${row.xp} XP`);
    if (row.streak >= 3) xp.appendChild(el("span", "lb-streak", `🔥${row.streak}`));
    info.append(name, sub);
    item.append(rank, info, xp);
    if (row.user_id === state.userId) {
      item.style.borderColor = "rgba(201,168,76,0.30)";
      item.style.background  = "rgba(201,168,76,0.05)";
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
    if (data.video) { videoEl.href = data.video; videoEl.style.display = "flex"; }
    else              { videoEl.style.display = "none"; }

    const loading = $(".chart-loading");
    const img     = $("#chartImg");
    loading.innerHTML = `<div class="spinner"></div><span>Генерирую график...</span>`;
    loading.style.display = "flex";
    img.style.display = "none";

    openModal("#lessonModal");

    const chartRes = await fetch(`${API}/chart/${key}`);
    if (chartRes.ok) {
      const chartData = await chartRes.json();
      img.onload = () => { loading.style.display = "none"; img.style.display = "block"; };
      img.onerror = () => { loading.innerHTML = "<span>График для этого урока недоступен</span>"; };
      img.src = `data:${chartData.mime};base64,${chartData.image_base64}`;
    } else {
      loading.innerHTML = "<span>График для этого урока недоступен</span>";
    }
  } catch (e) {
    console.error("openLesson:", e);
    showToast("Ошибка загрузки урока", "error");
  }
}
window.openLesson = openLesson;

// ── QUIZ ──────────────────────────────────────────────────────────────────
async function startQuiz(questId, questTitle, xpReward, btnEl) {
  try {
    const res  = await fetch(`${API}/quest/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: state.userId, quest_id: questId }),
    });
    const data = await res.json();

    if (!data.ok) {
      if (data.error === "deadline_expired") {
        showDeadlineExpiredScreen();
        return;
      }
      showResult("⚠️", "Квиз недоступен", data.message || data.error, null);
      return;
    }

    const questions = data.quiz?.questions || [];
    if (!questions.length) { showToast("Нет вопросов для этого квиза", "error"); return; }

    state.quizData  = { questions, questId, xpReward, current: 0, correct: 0 };
    state.quizStreak = 0;
    renderQuizQuestion();
    openModal("#quizModal");
  } catch (e) {
    console.error("startQuiz:", e);
    showToast("Ошибка запуска квиза", "error");
  }
}

function updateStreakDisplay() {
  const el = $("#quizStreakNum");
  const wrap = $("#quizStreak");
  if (el) el.textContent = state.quizStreak;
  if (wrap) wrap.classList.toggle("hidden", state.quizStreak < 2);
}

function renderQuizQuestion() {
  const { questions, current } = state.quizData;
  const total = questions.length;
  const q     = questions[current];

  $("#quizProgressBar").style.width = Math.round(current / total * 100) + "%";
  $("#quizCounter").textContent = `${current + 1} / ${total}`;
  $("#quizQuestion").textContent = q.question;

  const fb = $("#quizFeedback");
  fb.className = "quiz-feedback hidden";
  fb.textContent = "";
  $("#quizNext").classList.add("hidden");

  updateStreakDisplay();

  const opts = $("#quizOptions");
  opts.innerHTML = "";
  q.options.forEach((opt, i) => {
    const btn = el("button", "quiz-option", opt);
    btn.addEventListener("click", () => onQuizAnswer(i, q.correct_index, btn));
    opts.appendChild(btn);
  });
}

async function onQuizAnswer(chosen, correctIdx, clickedBtn) {
  const { questions, questId, current } = state.quizData;
  const isCorrect = chosen === correctIdx;

  if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred(isCorrect ? "success" : "error");

  document.querySelectorAll(".quiz-option").forEach((b, i) => {
    b.disabled = true;
    if (i === correctIdx) b.classList.add("correct");
    if (i === chosen && !isCorrect) b.classList.add("wrong");
  });

  if (isCorrect) {
    state.quizData.correct++;
    state.quizStreak++;
    updateStreakDisplay();
    floatXP(5, clickedBtn);
  } else {
    state.quizStreak = 0;
    updateStreakDisplay();
  }

  const fb = $("#quizFeedback");
  if (isCorrect) {
    fb.className = "quiz-feedback correct-fb";
    fb.textContent = state.quizStreak >= 3 ? `🔥 ${state.quizStreak} в ряд! Правильно!` : "✅ Правильно!";
  } else {
    fb.className = "quiz-feedback wrong-fb";
    fb.textContent = `❌ Неверно. Правильный ответ: ${questions[current].options[correctIdx]}`;
  }

  try {
    const res = await fetch(`${API}/quiz/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: state.userId, quest_id: questId, question_index: current, is_correct: isCorrect }),
    });
    const data = await res.json();

    if (data.finished) {
      setTimeout(() => { closeModal("#quizModal"); onQuizFinished(data); }, 1200);
      return;
    }
  } catch (e) { console.error("quiz answer:", e); }

  state.quizData.current++;
  if (state.quizData.current >= questions.length) { setTimeout(() => closeModal("#quizModal"), 1200); return; }

  const nextBtn = $("#quizNext");
  nextBtn.textContent = state.quizData.current >= questions.length - 1 ? "Завершить →" : "Следующий вопрос →";
  nextBtn.classList.remove("hidden");
}

function quizNextQuestion() { renderQuizQuestion(); }
window.quizNextQuestion = quizNextQuestion;
function abortQuiz() { state.quizData = null; closeModal("#quizModal"); }
window.abortQuiz = abortQuiz;

function onQuizFinished(data) {
  if (data.passed) {
    floatXP(data.xp_earned || 0, null);
    let msg = `Результат: ${data.correct}/${data.total} (${data.score}%)`;
    if (data.module_advanced) msg += "\n🎉 Новый модуль разблокирован!";
    showResult("🏆", "Квиз пройден!", msg, data.xp_earned);
    launchConfetti(80);
    if (data.leveled_up) {
      setTimeout(() => showLevelUp(data.new_level, data.rank), 1500);
    }
    loadQuests();
    refreshHeader();
  } else {
    showResult("😤", "Попробуй снова", `Результат: ${data.correct}/${data.total} (${data.score}%)\nНужно набрать ${data.required}%`, null);
    if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred("error");
  }
}

// ── PHOTO UPLOAD ───────────────────────────────────────────────────────────
let _hwPhotoBase64 = null;

function onPhotoSelected(input) {
  const file = input.files[0];
  if (!file) return;
  if (file.size > 8 * 1024 * 1024) { showToast("Файл слишком большой (макс 8MB)", "error"); return; }
  const reader = new FileReader();
  reader.onload = (e) => {
    _hwPhotoBase64 = e.target.result; // data:image/...;base64,...
    const wrap = $("#photoPreviewWrap");
    const img  = $("#photoPreviewImg");
    img.onload = () => {
      wrap?.classList.remove("hidden");
      $("#photoDropArea")?.classList.add("hidden");
    };
    img.onerror = () => { showToast("Не удалось загрузить фото", "error"); };
    img.src = _hwPhotoBase64;
  };
  reader.readAsDataURL(file);
}

function removePhoto() {
  _hwPhotoBase64 = null;
  const wrap = $("#photoPreviewWrap");
  wrap?.classList.add("hidden");
  $("#photoDropArea")?.classList.remove("hidden");
  const input = $("#hwPhotoInput");
  if (input) input.value = "";
}

window.onPhotoSelected = onPhotoSelected;
window.removePhoto = removePhoto;

// ── TASK ──────────────────────────────────────────────────────────────────
function openTask(questId, title, xpReward, description) {
  state.currentQuestId = questId;
  _hwPhotoBase64 = null;

  $("#taskTitle").textContent = title;
  $("#taskXp").textContent    = `+${xpReward} XP`;
  $("#taskDesc").textContent  = description || "";

  // Reset status
  const statusEl = $("#taskStatus");
  statusEl.className = "task-status hidden";

  // Reset submit button
  const submitBtn = $("#taskSubmitBtn");
  submitBtn.disabled = false;
  submitBtn.textContent = "Отправить на проверку";
  submitBtn.classList.remove("hidden");

  // Reset photo upload
  removePhoto();
  const hwInput = $("#hwPhotoInput");
  if (hwInput) hwInput.value = "";

  // Reset checkboxes
  ["check1","check2","check3","check4"].forEach(id => {
    const cb = $(`#${id}`);
    if (cb) cb.checked = false;
  });

  // Show/hide teacher comment based on current homework status
  const hw = state.userState?.homework_status;
  const commentBlock = $("#teacherCommentBlock");
  const commentText  = $("#teacherCommentText");
  const hwComment    = state.userState?.homework_comment || "";

  if (commentBlock) {
    if ((hw === "revision" || hw === "rejected") && hwComment) {
      commentText.textContent = hwComment;
      commentBlock.classList.remove("hidden");
    } else {
      commentBlock.classList.add("hidden");
    }
  }

  // Show/hide upload section based on status
  const uploadSection = $("#taskPhotoUpload");
  const selfCheck     = $("#taskSelfCheck");
  if (hw === "pending") {
    // Already submitted, waiting
    if (uploadSection) uploadSection.classList.add("hidden");
    if (selfCheck)     selfCheck.classList.add("hidden");
    statusEl.className = "task-status pending";
    statusEl.textContent = "⏳ Ожидает проверки преподавателем";
    submitBtn.classList.add("hidden");
  } else if (hw === "approved") {
    if (uploadSection) uploadSection.classList.add("hidden");
    if (selfCheck)     selfCheck.classList.add("hidden");
    statusEl.className = "task-status approved";
    statusEl.textContent = "✅ Задание принято!";
    submitBtn.classList.add("hidden");
  } else {
    if (uploadSection) uploadSection.classList.remove("hidden");
    if (selfCheck)     selfCheck.classList.remove("hidden");
  }

  openModal("#taskModal");
}

async function submitCurrentTask() {
  if (!state.currentQuestId) return;
  const btn = $("#taskSubmitBtn");
  btn.disabled = true;
  btn.textContent = "⏳ Отправляю...";

  try {
    const body = {
      user_id:  state.userId,
      quest_id: state.currentQuestId,
    };
    if (_hwPhotoBase64) body.photo = _hwPhotoBase64;

    const res = await fetch(`${API}/quest/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();

    if (data.ok) {
      const statusEl = $("#taskStatus");
      statusEl.className = "task-status pending";
      statusEl.textContent = "⏳ Задание отправлено! Преподаватель проверит в течение 24 часов.";
      btn.textContent = "✓ Отправлено";
      // Hide upload UI after submit
      $("#taskPhotoUpload")?.classList.add("hidden");
      $("#taskSelfCheck")?.classList.add("hidden");
      showToast("Задание отправлено на проверку!", "success");
      if (state.userState) state.userState.homework_status = "pending";
      loadQuests();
    } else if (data.error === "deadline_expired") {
      closeModal("#taskModal");
      showDeadlineExpiredScreen();
    } else {
      btn.disabled = false;
      btn.textContent = "Отправить на проверку";
      showToast(data.message || "Ошибка отправки", "error");
    }
  } catch (e) {
    console.error("submitTask:", e);
    btn.disabled = false;
    btn.textContent = "Отправить на проверку";
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
  if (xp) { xpEl.textContent = `+${xp} XP`; xpEl.classList.remove("hidden"); }
  else      xpEl.classList.add("hidden");
  openModal("#resultModal");
}

function onResultClose() { closeModal("#resultModal"); }
window.onResultClose = onResultClose;

// ── CHART LIGHTBOX ────────────────────────────────────────────────────────
const cl = { scale: 1, panX: 0, panY: 0, startPanX: 0, startPanY: 0,
             startDist: 0, startScale: 1, lastTap: 0, dragging: false };

function openChartLightbox(src) {
  const lb  = document.getElementById("chartLightbox");
  const img = document.getElementById("clImg");
  if (!lb || !img || !src) return;
  img.src = src;
  cl.scale = 1; cl.panX = 0; cl.panY = 0;
  applyClTransform();
  lb.classList.remove("hidden");
  document.body.style.overflow = "hidden";
}

function closeChartLightbox() {
  document.getElementById("chartLightbox")?.classList.add("hidden");
  document.body.style.overflow = "";
}

function applyClTransform() {
  const img = document.getElementById("clImg");
  if (img) img.style.transform = `translate(${cl.panX}px, ${cl.panY}px) scale(${cl.scale})`;
}

function initChartLightbox() {
  const vp = document.getElementById("clViewport");
  if (!vp) return;

  document.getElementById("clCloseBtn")?.addEventListener("click", closeChartLightbox);

  // Permanent click handler on chart preview image
  document.getElementById("chartImg")?.addEventListener("click", function () {
    if (this.src && !this.src.endsWith("#")) openChartLightbox(this.src);
  });

  vp.addEventListener("touchstart", (e) => {
    if (e.touches.length === 2) {
      cl.startDist  = Math.hypot(e.touches[0].clientX - e.touches[1].clientX,
                                 e.touches[0].clientY - e.touches[1].clientY);
      cl.startScale = cl.scale;
    } else if (e.touches.length === 1) {
      const now = Date.now();
      if (now - cl.lastTap < 280) {                // double-tap
        cl.scale = cl.scale > 1.05 ? 1 : 2.5;
        cl.panX  = 0; cl.panY = 0;
        applyClTransform();
        cl.lastTap = 0;
        return;
      }
      cl.lastTap   = now;
      cl.startPanX = e.touches[0].clientX - cl.panX;
      cl.startPanY = e.touches[0].clientY - cl.panY;
      cl.dragging  = true;
    }
  }, { passive: true });

  vp.addEventListener("touchmove", (e) => {
    e.preventDefault();
    if (e.touches.length === 2) {
      const dist = Math.hypot(e.touches[0].clientX - e.touches[1].clientX,
                              e.touches[0].clientY - e.touches[1].clientY);
      cl.scale = Math.min(5, Math.max(1, cl.startScale * dist / cl.startDist));
      if (cl.scale <= 1) { cl.panX = 0; cl.panY = 0; }
      applyClTransform();
    } else if (e.touches.length === 1 && cl.dragging && cl.scale > 1.05) {
      cl.panX = e.touches[0].clientX - cl.startPanX;
      cl.panY = e.touches[0].clientY - cl.startPanY;
      applyClTransform();
    }
  }, { passive: false });

  vp.addEventListener("touchend", () => {
    cl.dragging = false;
    if (cl.scale <= 1) { cl.scale = 1; cl.panX = 0; cl.panY = 0; applyClTransform(); }
  });

  // Tap backdrop (un-zoomed state) → close
  vp.addEventListener("click", (e) => {
    if (e.target === vp && cl.scale <= 1.05) closeChartLightbox();
  });

  // Mouse wheel zoom (desktop)
  vp.addEventListener("wheel", (e) => {
    e.preventDefault();
    cl.scale = Math.min(5, Math.max(1, cl.scale + (e.deltaY > 0 ? -0.2 : 0.2)));
    if (cl.scale <= 1) { cl.panX = 0; cl.panY = 0; }
    applyClTransform();
  }, { passive: false });
}

// ── TOAST ─────────────────────────────────────────────────────────────────
function showToast(msg, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
}

// ── DAILY BONUS DISPLAY ───────────────────────────────────────────────────
function showDailyBonus(xp, streak) {
  if (!xp) return;
  const textEl = $("#dailyBonusText");
  const streakEl = $("#dailyStreakDisplay");
  if (textEl) textEl.textContent = `+${xp} XP за вход сегодня`;
  if (streakEl) {
    if (streak >= 2) {
      streakEl.innerHTML = `<div class="streak-info">🔥 Стрик: <strong>${streak} дней</strong></div>`;
      if (streak === 7) streakEl.innerHTML += `<div class="streak-milestone">🏅 Бейдж «Неделя без пропусков» получен!</div>`;
      if (streak === 30) streakEl.innerHTML += `<div class="streak-milestone">🏆 Бейдж «Железная воля» получен!</div>`;
    }
  }
  setTimeout(() => openModal("#dailyBonusModal"), 800);
}

// ── API CALLS ─────────────────────────────────────────────────────────────
async function loadQuests() {
  try {
    const res  = await fetch(`${API}/quests/${state.userId}`);
    const data = await res.json();
    renderQuests(data);
  } catch (e) { console.error("loadQuests:", e); }
}

async function loadLeaderboard() {
  try {
    const res  = await fetch(`${API}/leaderboard?limit=20`);
    const data = await res.json();
    renderLeaderboard(data);
  } catch (e) { console.error("loadLeaderboard:", e); }
}

async function refreshHeader() {
  try {
    const res = await fetch(`${API}/user/${state.userId}`);
    const s   = await res.json();
    renderHeader(s);
  } catch (e) {}
}
window.showDeadlineExpiredScreen = showDeadlineExpiredScreen;

// ── INITIAL LOAD ──────────────────────────────────────────────────────────
async function init() {
  initCanvas();
  initOnboarding();

  const info = getUserInfo();
  state.userId = info.id;

  try {
    const initRes = await fetch(`${API}/user/init`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: info.id, username: info.username, first_name: info.first_name, last_name: info.last_name }),
    });
    const initData = await initRes.json();

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

    Object.assign(state.lessonsMetaCache, metaData);

    renderHeader(userData);
    renderModules(modulesData.modules || []);
    renderQuests(questsData);
    renderLeaderboard(lbData);
    setProgress(questsData.completed_count || 0, questsData.total_count || 0);

    // Apply deadline info
    if (questsData.deadline_info) {
      applyDeadlineInfo(questsData.deadline_info);
    }

    // Show daily bonus if applicable
    if (initData.daily_bonus_xp > 0) {
      showDailyBonus(initData.daily_bonus_xp, initData.streak);
    }

  } catch (e) {
    console.error("init error:", e);
    showToast("Ошибка загрузки данных", "error");
  }
}

// ── BTN START ─────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  init();
  initChartLightbox();

  document.getElementById("btn-start")?.addEventListener("click", () => {
    switchTab("lessons");
    setTimeout(() => {
      const firstOpen = document.querySelector(".module-card.open .lesson-item");
      if (firstOpen) firstOpen.click();
    }, 200);
  });
});
