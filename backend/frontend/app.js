/* ═══════════════════════════════════════════════════════════════════════
   SMC Quest — app.js v4.0  |  EPIC REDESIGN
   Candlestick BG · Confetti · XP Floats · Level-up · Onboarding · SVG Ranks
   ═══════════════════════════════════════════════════════════════════════ */

// ── CONFIG ────────────────────────────────────────────────────────────────
const API     = "/api";
const tg      = window.Telegram?.WebApp ?? null;
const DEV_UID = 445677777;

// ── GLOBAL STATE ─────────────────────────────────────────────────────────
const state = {
  userId: null,
  userState: null,
  quizData: null,
  currentQuestId: null,
  lessonsMetaCache: {},
  quizStreak: 0,
};

// ── RANK CONFIG ───────────────────────────────────────────────────────────
const RANKS = {
  "🪨": { name: "Камень",    color: "#78716c", glow: "rgba(120,113,108,0.4)" },
  "🥉": { name: "Бронза",   color: "#cd7f32", glow: "rgba(205,127,50,0.4)"  },
  "🥈": { name: "Серебро",  color: "#94a3b8", glow: "rgba(148,163,184,0.4)" },
  "🥇": { name: "Золото",   color: "#fbbf24", glow: "rgba(251,191,36,0.5)"  },
  "💎": { name: "Бриллиант",color: "#00d4ff", glow: "rgba(0,212,255,0.5)"  },
};

// ── SVG RANK ICONS ────────────────────────────────────────────────────────
const RANK_SVGS = {
  "🪨": `<svg viewBox="0 0 40 40" fill="none">
    <polygon points="20,4 36,14 36,26 20,36 4,26 4,14" fill="#1a1918" stroke="#78716c" stroke-width="2"/>
    <polygon points="20,10 30,17 30,23 20,30 10,23 10,17" fill="#78716c" opacity="0.6"/>
    <line x1="20" y1="4" x2="20" y2="36" stroke="#78716c" stroke-width="0.5" opacity="0.3"/>
    <line x1="4" y1="14" x2="36" y2="26" stroke="#78716c" stroke-width="0.5" opacity="0.3"/>
    <line x1="36" y1="14" x2="4" y2="26" stroke="#78716c" stroke-width="0.5" opacity="0.3"/>
  </svg>`,
  "🥉": `<svg viewBox="0 0 40 40" fill="none">
    <circle cx="20" cy="20" r="16" fill="#1a1410" stroke="#cd7f32" stroke-width="2"/>
    <circle cx="20" cy="20" r="10" fill="#cd7f32" opacity="0.25"/>
    <path d="M20 10 L22.5 17H30L24 21.5L26.5 29L20 24.5L13.5 29L16 21.5L10 17H17.5Z" fill="#cd7f32"/>
  </svg>`,
  "🥈": `<svg viewBox="0 0 40 40" fill="none">
    <circle cx="20" cy="20" r="16" fill="#111418" stroke="#94a3b8" stroke-width="2"/>
    <circle cx="20" cy="20" r="10" fill="#94a3b8" opacity="0.2"/>
    <path d="M20 10 L22.5 17H30L24 21.5L26.5 29L20 24.5L13.5 29L16 21.5L10 17H17.5Z" fill="#94a3b8"/>
    <circle cx="20" cy="20" r="4" fill="white" opacity="0.3"/>
  </svg>`,
  "🥇": `<svg viewBox="0 0 40 40" fill="none">
    <defs>
      <radialGradient id="rg_gold" cx="40%" cy="35%" r="60%">
        <stop offset="0%" stop-color="#fde68a"/>
        <stop offset="100%" stop-color="#b45309"/>
      </radialGradient>
    </defs>
    <circle cx="20" cy="20" r="16" fill="#1a1505" stroke="#fbbf24" stroke-width="2"/>
    <circle cx="20" cy="20" r="12" fill="url(#rg_gold)" opacity="0.3"/>
    <path d="M20 8 L23 16H32L25 21L28 30L20 25L12 30L15 21L8 16H17Z" fill="url(#rg_gold)"/>
    <circle cx="20" cy="18" r="3" fill="white" opacity="0.4"/>
  </svg>`,
  "💎": `<svg viewBox="0 0 40 40" fill="none">
    <defs>
      <linearGradient id="lg_dia" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#7dd3fc"/>
        <stop offset="50%" stop-color="#00d4ff"/>
        <stop offset="100%" stop-color="#0099cc"/>
      </linearGradient>
    </defs>
    <circle cx="20" cy="20" r="16" fill="#050d12" stroke="#00d4ff" stroke-width="2"/>
    <polygon points="20,8 30,16 26,32 14,32 10,16" fill="url(#lg_dia)" opacity="0.8"/>
    <polygon points="20,8 30,16 20,18" fill="white" opacity="0.25"/>
    <polygon points="20,18 30,16 26,32" fill="url(#lg_dia)" opacity="0.6"/>
    <polygon points="20,18 10,16 14,32" fill="#005f7a" opacity="0.7"/>
  </svg>`,
};

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

  const candleW = 12;
  const gap     = 8;
  const step    = candleW + gap;
  const cols    = Math.ceil(window.innerWidth / step) + 4;

  // Generate candles
  const candles = [];
  let price = 180 + Math.random() * 100;

  for (let i = 0; i < cols; i++) {
    const change = (Math.random() - 0.46) * 18;
    const open   = price;
    price        = Math.max(60, Math.min(380, price + change));
    const close  = price;
    const high   = Math.max(open, close) + Math.random() * 12;
    const low    = Math.min(open, close) - Math.random() * 12;
    candles.push({ open, close, high, low, x: i * step });
  }

  let offset = 0;

  function draw() {
    const W = canvas.width;
    const H = canvas.height;

    // Clear
    ctx.clearRect(0, 0, W, H);

    // Grid lines
    ctx.strokeStyle = "rgba(255,255,255,0.025)";
    ctx.lineWidth = 1;
    for (let y = 0; y < H; y += 60) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(W, y);
      ctx.stroke();
    }

    const maxH  = Math.max(...candles.map(c => c.high));
    const minL  = Math.min(...candles.map(c => c.low));
    const range = maxH - minL || 1;
    const scale = (H * 0.7) / range;

    const toY = v => H * 0.15 + (maxH - v) * scale;

    candles.forEach((c, i) => {
      const x = c.x - offset;

      // Wrap around
      const wx = ((x % (W + step * 2)) + W + step * 2) % (W + step * 2) - step;

      const isBull = c.close >= c.open;
      const bodyCol = isBull ? "rgba(0,232,122," : "rgba(255,77,109,";

      const oY = toY(c.open);
      const cY = toY(c.close);
      const hY = toY(c.high);
      const lY = toY(c.low);

      // Wick
      ctx.strokeStyle = bodyCol + "0.5)";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(wx + candleW / 2, hY);
      ctx.lineTo(wx + candleW / 2, lY);
      ctx.stroke();

      // Body
      const bodyY = Math.min(oY, cY);
      const bodyH = Math.max(Math.abs(cY - oY), 2);

      // Glow
      ctx.shadowColor = isBull ? "#00e87a" : "#ff4d6d";
      ctx.shadowBlur = 4;
      ctx.fillStyle = bodyCol + "0.7)";
      ctx.fillRect(wx, bodyY, candleW, bodyH);
      ctx.shadowBlur = 0;
    });

    offset += 0.4;
    requestAnimationFrame(draw);
  }

  draw();
}

// ── RANK SVG ──────────────────────────────────────────────────────────────
function getRankSVG(rankEmoji) {
  return RANK_SVGS[rankEmoji] || RANK_SVGS["🪨"];
}

// ── ONBOARDING ────────────────────────────────────────────────────────────
let obCurrentSlide = 0;
const OB_TOTAL = 3;

function initOnboarding() {
  const overlay = $("#onboardingOverlay");
  if (!overlay) return;

  const seen = localStorage.getItem("smc_onboarding_done");
  if (seen) return;

  overlay.classList.remove("hidden");

  const nextBtn = $("#ob-next-btn");
  const skipBtn = $("#ob-skip-btn");

  nextBtn.addEventListener("click", () => {
    if (obCurrentSlide < OB_TOTAL - 1) {
      goToSlide(obCurrentSlide + 1);
    } else {
      closeOnboarding();
    }
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
  if (overlay) {
    overlay.style.animation = "fadeOut 0.3s ease forwards";
    setTimeout(() => overlay.classList.add("hidden"), 300);
  }
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

    const x     = Math.random() * 100;
    const dur   = 1.8 + Math.random() * 1.5;
    const delay = Math.random() * 0.8;
    const color = CONFETTI_COLORS[Math.floor(Math.random() * CONFETTI_COLORS.length)];
    const size  = 6 + Math.random() * 8;
    const rot   = Math.random() * 360;

    piece.style.cssText = `
      left: ${x}%;
      animation-duration: ${dur}s;
      animation-delay: ${delay}s;
      background: ${color};
      width: ${size}px;
      height: ${size}px;
      border-radius: ${Math.random() > 0.5 ? "50%" : "2px"};
      transform: rotate(${rot}deg);
    `;

    layer.appendChild(piece);
    setTimeout(() => piece.remove(), (dur + delay) * 1000 + 100);
  }
}

// ── XP FLOAT ──────────────────────────────────────────────────────────────
function floatXP(amount, sourceEl) {
  const layer = $("#xpFloatLayer");
  if (!layer) return;

  const rect = sourceEl
    ? sourceEl.getBoundingClientRect()
    : { left: window.innerWidth / 2, top: window.innerHeight / 2 };

  const el = document.createElement("div");
  el.className = "xp-float";
  el.textContent = `+${amount} XP`;
  el.style.left = (rect.left + (rect.width || 0) / 2) + "px";
  el.style.top  = (rect.top)  + "px";

  layer.appendChild(el);
  setTimeout(() => el.remove(), 1700);

  if (tg?.HapticFeedback) {
    tg.HapticFeedback.notificationOccurred("success");
  }
}

// ── LEVEL UP SCREEN ───────────────────────────────────────────────────────
function showLevelUp(level, rankEmoji) {
  const overlay = $("#levelUpOverlay");
  if (!overlay) return;

  const rankInfo = RANKS[rankEmoji] || RANKS["🪨"];

  $("#levelupNum").textContent      = level;
  $("#levelupRankName").textContent = rankInfo.name;
  $("#levelupRankIcon").innerHTML   = getRankSVG(rankEmoji);

  // Burst particles
  const container = $("#levelupParticles");
  container.innerHTML = "";
  for (let i = 0; i < 24; i++) {
    const p    = document.createElement("div");
    p.className = "levelup-particle";
    const angle = (i / 24) * 360;
    const dist  = 80 + Math.random() * 80;
    const tx    = Math.cos(angle * Math.PI / 180) * dist;
    const ty    = Math.sin(angle * Math.PI / 180) * dist;
    const color = CONFETTI_COLORS[Math.floor(Math.random() * CONFETTI_COLORS.length)];
    const dur   = 0.8 + Math.random() * 0.6;
    p.style.cssText = `
      --tx: ${tx}px; --ty: ${ty}px; --dur: ${dur}s;
      background: ${color};
      left: 50%; top: 50%;
      box-shadow: 0 0 6px ${color};
    `;
    container.appendChild(p);
  }

  overlay.classList.remove("hidden");
  launchConfetti(120);

  if (tg?.HapticFeedback) {
    tg.HapticFeedback.notificationOccurred("success");
  }
}

document.getElementById("levelupCloseBtn")?.addEventListener("click", () => {
  $("#levelUpOverlay").classList.add("hidden");
});

// ── TABS ──────────────────────────────────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll(".tab").forEach(b => b.classList.toggle("active", b.dataset.tab === name));
  document.querySelectorAll(".tab-content").forEach(c => c.classList.toggle("active", c.id === `tab-${name}`));
  if (name === "quests")       loadQuests();
  if (name === "leaderboard")  loadLeaderboard();

  if (tg?.HapticFeedback) {
    tg.HapticFeedback.selectionChanged();
  }
}
window.switchTab = switchTab;

// ── MODALS ────────────────────────────────────────────────────────────────
function openModal(id)  {
  $(id)?.classList.remove("hidden");
  if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred("light");
}
function closeModal(id) { $(id)?.classList.add("hidden"); }
window.closeModal = closeModal;

// ── MARKDOWN RENDERER ─────────────────────────────────────────────────────
function renderMarkdown(text) {
  if (!text) return "";
  const div  = document.createElement("div");
  const lines = text.split("\n");
  lines.forEach((line, idx) => {
    if (!line.trim()) {
      if (idx > 0) div.appendChild(document.createElement("br"));
      return;
    }
    const p = document.createElement("span");
    p.style.display = "block";
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
    if (line.startsWith("• ") || line.match(/^[1-9][️⃣)\\.] /)) {
      p.className = "bullet";
    }
    div.appendChild(p);
  });
  return div.innerHTML;
}

// ── RENDER USER STATE ─────────────────────────────────────────────────────
function renderHeader(s) {
  state.userState = s;
  const rankEmoji = s.rank || "🪨";

  $("#userName").textContent = s.name || "Трейдер";
  $("#userXP").textContent   = s.xp ?? 0;
  $("#userLvl").textContent  = s.level ?? 1;
  $("#moduleName").textContent = `Модуль ${(s.module_index ?? 0) + 1}`;

  // Inject SVG rank icon
  const rankWrap = $("#rankIconWrap");
  if (rankWrap) rankWrap.innerHTML = getRankSVG(rankEmoji);

  if (s.module_deadline) {
    const d       = new Date(s.module_deadline);
    const now     = new Date();
    const daysLeft = Math.ceil((d - now) / 86400000);
    const txt = daysLeft > 0
      ? `⏰ ${daysLeft} дн.`
      : `⚠️ Просрочен!`;
    $("#deadlineText").textContent = txt;
    $("#deadlineText").style.color = daysLeft <= 2 ? "var(--bear)" : "var(--gold)";
  }
}

function setProgress(completed, total) {
  const pct = total > 0 ? Math.round(completed / total * 100) : 0;
  const bar  = $("#progressBar");
  const glow = $("#progressGlow");

  bar.style.width = pct + "%";
  if (glow) glow.style.left = pct + "%";

  if ($("#progressLabel")) $("#progressLabel").textContent = `${completed}/${total} квестов`;
  if ($("#progressPct"))   $("#progressPct").textContent = pct + "%";
}

// ── RENDER MODULES ────────────────────────────────────────────────────────
function renderModules(modules) {
  const container = $("#modulesList");
  container.innerHTML = "";
  modules.forEach((mod, idx) => {
    const card   = el("div", "module-card");
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
    header.addEventListener("click", () => {
      card.classList.toggle("open");
      if (tg?.HapticFeedback) tg.HapticFeedback.selectionChanged();
    });
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

  setProgress(resp.completed_count || 0, resp.total_count || 0);

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

    // Quest type icon SVG
    const iconWrap = el("div", `quest-type-icon ${q.type === "quiz" ? "quiz-icon" : isBoss ? "boss-icon" : "task-icon"}`);
    if (q.type === "quiz") {
      iconWrap.innerHTML = `<svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <circle cx="10" cy="7" r="4" stroke="#00d4ff" stroke-width="1.5"/>
        <path d="M10 11V13M10 15V15.5" stroke="#00d4ff" stroke-width="1.5" stroke-linecap="round"/>
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
        approved: ["✅ Принято",      "approved"],
        rejected: ["❌ Отклонено",    "rejected"],
      };
      const [txt, cls] = statuses[hw] || [];
      if (txt) {
        badges.appendChild(el("div", `quest-status-badge status-${cls}`, txt));
      }
    }

    const desc = el("div", "quest-desc", q.description || "");

    const btn = el("button", "btn-quest",
      q.completed
        ? "✓ Выполнено"
        : q.type === "quiz"
          ? "▶ Начать квиз"
          : "📋 Открыть задание");
    btn.disabled = q.completed;
    btn.addEventListener("click", (e) => {
      if (q.type === "quiz") startQuiz(q.id, q.title, q.xp_reward, e.currentTarget);
      else openTask(q.id, q.title, q.xp_reward, q.description);
    });

    card.append(headerRow, badges, desc, btn);
    container.appendChild(card);
  });
}

// ── RENDER LEADERBOARD ─────────────────────────────────────────────────────
function renderLeaderboard(resp) {
  const list      = resp.leaderboard || [];
  const container = $("#leaderboardList");
  container.innerHTML = "";

  if (!list.length) {
    container.innerHTML = `<div class="empty-state"><span class="es-icon">🏆</span><div class="es-title">Пока никого нет</div><p>Стань первым!</p></div>`;
    return;
  }

  list.forEach((row, i) => {
    const item = el("div", "lb-item");
    const rank = el("div", "lb-rank", i < 3 ? ["🥇","🥈","🥉"][i] : `${i+1}`);
    const info = el("div", "lb-info");
    const name = el("div", "lb-name", row.name || `User ${row.user_id}`);
    const sub  = el("div", "lb-sub", `Lvl ${row.level} · ${row.module ? `Модуль ${row.module}` : ""}`);
    const xp   = el("div", "lb-xp", `${row.xp} XP`);
    info.append(name, sub);
    item.append(rank, info, xp);

    if (row.user_id === state.userId) {
      item.style.borderColor = "rgba(0,212,255,0.25)";
      item.style.background  = "rgba(0,212,255,0.04)";
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

    const chartRes = await fetch(`${API}/chart/${key}/png`);
    if (chartRes.ok) {
      const blob = await chartRes.blob();
      img.onload = () => { loading.style.display = "none"; img.style.display = "block"; };
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
async function startQuiz(questId, questTitle, xpReward, btnEl) {
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
  if (wrap) {
    wrap.classList.toggle("hidden", state.quizStreak < 2);
  }
}

function renderQuizQuestion() {
  const { questions, current } = state.quizData;
  const total = questions.length;
  const q     = questions[current];

  const pct = Math.round(current / total * 100);
  $("#quizProgressBar").style.width = pct + "%";
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

  if (tg?.HapticFeedback) {
    tg.HapticFeedback.notificationOccurred(isCorrect ? "success" : "error");
  }

  document.querySelectorAll(".quiz-option").forEach((b, i) => {
    b.disabled = true;
    if (i === correctIdx) b.classList.add("correct");
    if (i === chosen && !isCorrect) b.classList.add("wrong");
  });

  if (isCorrect) {
    state.quizData.correct++;
    state.quizStreak++;
    updateStreakDisplay();
    // Mini XP float
    floatXP(5, clickedBtn);
  } else {
    state.quizStreak = 0;
    updateStreakDisplay();
  }

  const fb = $("#quizFeedback");
  if (isCorrect) {
    fb.className = "quiz-feedback correct-fb";
    fb.textContent = state.quizStreak >= 3
      ? `🔥 ${state.quizStreak} в ряд! Правильно!`
      : "✅ Правильно!";
  } else {
    fb.className = "quiz-feedback wrong-fb";
    fb.textContent = `❌ Неверно. Правильный ответ: ${questions[current].options[correctIdx]}`;
  }

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
      setTimeout(() => { closeModal("#quizModal"); onQuizFinished(data); }, 1200);
      return;
    }
  } catch (e) { console.error("quiz answer:", e); }

  state.quizData.current++;
  if (state.quizData.current >= questions.length) {
    setTimeout(() => closeModal("#quizModal"), 1200);
    return;
  }

  const nextBtn = $("#quizNext");
  const isLast  = state.quizData.current >= questions.length - 1;
  nextBtn.textContent = isLast ? "Завершить →" : "Следующий вопрос →";
  nextBtn.classList.remove("hidden");
}

function quizNextQuestion() { renderQuizQuestion(); }
window.quizNextQuestion = quizNextQuestion;

function abortQuiz() { state.quizData = null; closeModal("#quizModal"); }
window.abortQuiz = abortQuiz;

function onQuizFinished(data) {
  if (data.passed) {
    // XP float from center
    floatXP(data.xp_earned || data.xp_reward || 0, null);

    let msg = `Результат: ${data.correct}/${data.total} (${data.score}%)`;
    if (data.module_advanced) msg += "\n🎉 Новый модуль разблокирован!";

    showResult("🏆", "Квиз пройден!", msg, data.xp_earned);
    launchConfetti(80);

    if (data.leveled_up) {
      setTimeout(() => {
        showLevelUp(data.new_level, state.userState?.rank || "🪨");
      }, 1500);
    }

    loadQuests();
    refreshHeader();
  } else {
    showResult("😤", "Попробуй снова",
      `Результат: ${data.correct}/${data.total} (${data.score}%)\nНужно набрать ${data.required}%`,
      null);
    if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred("error");
  }
}

// ── TASK ──────────────────────────────────────────────────────────────────
function openTask(questId, title, xpReward, description) {
  state.currentQuestId = questId;
  $("#taskTitle").textContent = title;
  $("#taskXp").textContent    = `+${xpReward} XP`;
  $("#taskDesc").textContent  = description || "";

  const statusEl = $("#taskStatus");
  statusEl.className = "task-status hidden";

  const submitBtn = $("#taskSubmitBtn");
  submitBtn.disabled = false;
  submitBtn.textContent = "Отправить на проверку";

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
      statusEl.textContent = "⏳ Задание отправлено! Ожидай проверки.";
      btn.textContent = "✓ Отправлено";
      showToast("Задание отправлено на проверку!", "success");
      loadQuests();
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
  if (xp) {
    xpEl.textContent = `+${xp} XP`;
    xpEl.classList.remove("hidden");
  } else {
    xpEl.classList.add("hidden");
  }
  openModal("#resultModal");
}

function onResultClose() { closeModal("#resultModal"); }
window.onResultClose = onResultClose;

// ── TOAST ─────────────────────────────────────────────────────────────────
function showToast(msg, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
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

// ── INITIAL LOAD ──────────────────────────────────────────────────────────
async function init() {
  // Start canvas immediately
  initCanvas();
  // Check onboarding
  initOnboarding();

  const info = getUserInfo();
  state.userId = info.id;

  try {
    await fetch(`${API}/user/init`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: info.id,
        username: info.username,
        first_name: info.first_name,
        last_name: info.last_name,
      }),
    });

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
    setTimeout(() => {
      const firstLesson = document.querySelector(".lesson-item");
      if (firstLesson) {
        document.querySelector(".module-header")?.click();
        setTimeout(() => firstLesson?.click(), 200);
      }
    }, 100);
  });
});
