import os
import io
import json
import logging
import random
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, Rectangle
import matplotlib.gridspec as gridspec

from dotenv import load_dotenv
import telebot
from telebot import types

# ─────────────────────────────────────────────────────
# НАСТРОЙКИ
# ─────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "8505971843:AAHJDrETopJ8D_Ww9avB6MWbtpO_rnXXJqk")
ADMIN_ID = int(os.getenv("ADMIN_ID", "445677777"))
DEFAULT_DEADLINE_DAYS = int(os.getenv("DEFAULT_DEADLINE_DAYS", "7"))
MAX_EXTENSIONS = int(os.getenv("MAX_EXTENSIONS", "3"))
PROGRESS_FILE = Path("progress_smc.json")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ─────────────────────────────────────────────────────
# СТИЛЬ ГРАФИКОВ
# ─────────────────────────────────────────────────────
CHART_STYLE = {
    "bg": "#0d1117",
    "panel": "#161b22",
    "grid": "#21262d",
    "bull": "#26a641",
    "bear": "#f85149",
    "accent": "#58a6ff",
    "gold": "#e3b341",
    "purple": "#bc8cff",
    "text": "#c9d1d9",
    "muted": "#8b949e",
}


def set_dark_style(fig, ax_list=None):
    fig.patch.set_facecolor(CHART_STYLE["bg"])
    if ax_list is None:
        ax_list = fig.get_axes()
    for ax in ax_list:
        ax.set_facecolor(CHART_STYLE["panel"])
        ax.tick_params(colors=CHART_STYLE["text"], labelsize=8)
        ax.xaxis.label.set_color(CHART_STYLE["text"])
        ax.yaxis.label.set_color(CHART_STYLE["text"])
        ax.title.set_color(CHART_STYLE["text"])
        for spine in ax.spines.values():
            spine.set_edgecolor(CHART_STYLE["grid"])
        ax.grid(True, color=CHART_STYLE["grid"], linewidth=0.5, alpha=0.7)


def fig_to_bytes(fig) -> io.BytesIO:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight",
                facecolor=CHART_STYLE["bg"])
    buf.seek(0)
    plt.close(fig)
    return buf


# ─────────────────────────────────────────────────────
# ГЕНЕРАЦИЯ ГРАФИКОВ — по одному на урок
# ─────────────────────────────────────────────────────

def chart_what_is_smc() -> io.BytesIO:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))
    set_dark_style(fig, [ax1, ax2])
    fig.suptitle("Smart Money vs Розничные трейдеры", color=CHART_STYLE["text"], fontsize=13, fontweight="bold")

    # Pie chart — участники рынка
    labels = ["Банки\n(~40%)", "Хедж-фонды\n(~25%)", "Маркет-мейкеры\n(~20%)", "Розничные\nтрейдеры (~15%)"]
    sizes = [40, 25, 20, 15]
    colors = [CHART_STYLE["accent"], CHART_STYLE["bull"], CHART_STYLE["purple"], CHART_STYLE["bear"]]
    wedges, texts, autotexts = ax1.pie(sizes, labels=labels, colors=colors, autopct="%1.0f%%",
                                       startangle=90, textprops={"color": CHART_STYLE["text"], "fontsize": 8})
    for at in autotexts:
        at.set_color(CHART_STYLE["bg"])
        at.set_fontweight("bold")
    ax1.set_title("Участники рынка", color=CHART_STYLE["text"])

    # Bar chart — влияние на цену
    categories = ["Банки", "Хедж-фонды", "Маркет-мейкеры", "Розничные"]
    influence = [40, 25, 20, 15]
    clrs = [CHART_STYLE["accent"], CHART_STYLE["bull"], CHART_STYLE["purple"], CHART_STYLE["bear"]]
    bars = ax2.barh(categories, influence, color=clrs, height=0.55, edgecolor="none")
    for bar, val in zip(bars, influence):
        ax2.text(val + 0.5, bar.get_y() + bar.get_height() / 2,
                 f"{val}%", va="center", color=CHART_STYLE["text"], fontsize=9, fontweight="bold")
    ax2.set_xlim(0, 50)
    ax2.set_xlabel("Доля влияния на рынок (%)")
    ax2.set_title("Влияние на движение цены", color=CHART_STYLE["text"])
    ax2.invert_yaxis()

    plt.tight_layout()
    return fig_to_bytes(fig)


def chart_timeframes() -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(10, 6))
    set_dark_style(fig, [ax])
    fig.suptitle("Top-Down Анализ: Иерархия таймфреймов", color=CHART_STYLE["text"], fontsize=13, fontweight="bold")

    tfs = ["W1/MN — Глобальный тренд", "D1 — Основное направление", "H4 — Swing-структура",
           "H1 — Рабочая структура", "M15 — Сетапы и зоны", "M5/M1 — Точка входа"]
    purposes = ["Где мы находимся глобально?", "Покупки или продажи?", "HTF зоны & Order Blocks",
                 "BOS, CHoCH, Inducement", "OB, FVG, OTE", "Триггер, SL, TP"]
    colors = [CHART_STYLE["purple"], CHART_STYLE["accent"], CHART_STYLE["bull"],
              CHART_STYLE["gold"], "#ff8c69", CHART_STYLE["bear"]]
    widths = [0.9, 0.78, 0.65, 0.52, 0.38, 0.25]

    ax.set_xlim(0, 1)
    ax.set_ylim(0, len(tfs) + 0.5)
    ax.axis("off")

    for i, (tf, purpose, color, w) in enumerate(zip(reversed(tfs), reversed(purposes),
                                                      reversed(colors), reversed(widths))):
        y = i + 0.3
        x = (1 - w) / 2
        rect = Rectangle((x, y), w, 0.65, linewidth=0, facecolor=color, alpha=0.85)
        ax.add_patch(rect)
        ax.text(0.5, y + 0.33, tf, ha="center", va="center",
                color="white", fontsize=9, fontweight="bold")
        ax.text(0.5, y + 0.08, purpose, ha="center", va="center",
                color=CHART_STYLE["bg"], fontsize=7.5, alpha=0.9)

    ax.annotate("", xy=(0.5, 0.0), xytext=(0.5, len(tfs) + 0.2),
                arrowprops=dict(arrowstyle="-|>", color=CHART_STYLE["muted"], lw=1.5))
    ax.text(0.5, -0.3, "Сверху вниз: от Макро к Микро", ha="center",
            color=CHART_STYLE["muted"], fontsize=9, style="italic")

    return fig_to_bytes(fig)


def chart_market_structure() -> io.BytesIO:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    set_dark_style(fig, [ax1, ax2])
    fig.suptitle("Market Structure: BOS & CHoCH", color=CHART_STYLE["text"], fontsize=13, fontweight="bold")

    # Бычья структура с BOS
    t = np.linspace(0, 10, 200)
    bull = 1.5 * np.sin(0.7 * t) + 0.25 * t + 10 + 0.15 * np.random.randn(200)
    ax1.plot(t, bull, color=CHART_STYLE["bull"], lw=1.5)

    pts = [(0.5, 9.8), (2.0, 11.2), (3.2, 10.3), (4.8, 12.1), (6.1, 11.2), (7.7, 13.4), (9.2, 12.5)]
    for i, (x, y) in enumerate(pts):
        color = CHART_STYLE["bull"] if i % 2 == 1 else CHART_STYLE["bear"]
        lbl = "HH" if i % 2 == 1 and i > 0 else ("HL" if i % 2 == 0 and i > 0 else "SL")
        ax1.annotate(lbl, (x, y), textcoords="offset points", xytext=(0, 8 if i % 2 == 1 else -14),
                     color=color, fontsize=8, fontweight="bold", ha="center")
        ax1.plot(x, y, "o", color=color, ms=5, zorder=5)

    ax1.axhline(12.1, color=CHART_STYLE["gold"], lw=1, ls="--", alpha=0.7)
    ax1.text(9.5, 12.2, "BOS →", color=CHART_STYLE["gold"], fontsize=8)
    ax1.set_title("Бычий тренд: HH / HL", color=CHART_STYLE["text"])
    ax1.set_xlabel("Время")
    ax1.set_ylabel("Цена")

    # Разворот с CHoCH
    t2 = np.linspace(0, 10, 200)
    bear_wave = -1.2 * np.sin(0.65 * t2 - 0.5) + 12 - 0.2 * t2 + 0.1 * np.random.randn(200)
    ax2.plot(t2, bear_wave, color=CHART_STYLE["bear"], lw=1.5)

    choch_pts = [(0.5, 12.2), (2.0, 13.1), (3.5, 11.5), (5.0, 12.2), (6.5, 10.8), (8.0, 11.2), (9.5, 9.5)]
    for i, (x, y) in enumerate(choch_pts):
        lbl = ["HL", "HH", "LL", "LH", "LL", "CHoCH", "LL"][i]
        c = CHART_STYLE["bear"] if "L" in lbl else CHART_STYLE["bull"]
        if lbl == "CHoCH":
            c = CHART_STYLE["accent"]
        ax2.annotate(lbl, (x, y), textcoords="offset points", xytext=(0, 10 if y > 11.3 else -14),
                     color=c, fontsize=8, fontweight="bold", ha="center")
        ax2.plot(x, y, "o", color=c, ms=5, zorder=5)

    ax2.axhline(11.5, color=CHART_STYLE["accent"], lw=1.2, ls="--", alpha=0.8)
    ax2.text(0.2, 11.3, "CHoCH — разворот!", color=CHART_STYLE["accent"], fontsize=8)
    ax2.set_title("CHoCH — Смена характера структуры", color=CHART_STYLE["text"])
    ax2.set_xlabel("Время")

    plt.tight_layout()
    return fig_to_bytes(fig)


def chart_inducement() -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(10, 6))
    set_dark_style(fig, [ax])
    fig.suptitle("Inducement (Ловушка для толпы)", color=CHART_STYLE["text"], fontsize=13, fontweight="bold")

    t = np.linspace(0, 12, 300)
    price = (
        10 + 0.5 * np.sin(t) + 0.1 * t
        + np.where(t < 5, 0, np.where(t < 6, 1.2 * (t - 5), 1.2))
        + np.where(t > 8, -2 * (t - 8), 0)
        + 0.05 * np.random.randn(300)
    )
    price = np.clip(price, 8, 14)
    ax.plot(t, price, color=CHART_STYLE["accent"], lw=1.8)

    # Inducement zone
    ax.axhline(11.8, color=CHART_STYLE["gold"], lw=1.2, ls="--", alpha=0.85)
    ax.text(0.2, 11.9, "Inducement Level (видимый уровень)", color=CHART_STYLE["gold"], fontsize=8.5)

    ax.annotate("🪤 Толпа\nпродаёт/покупает", xy=(5.5, 11.95), xytext=(3.5, 13.0),
                arrowprops=dict(arrowstyle="->", color=CHART_STYLE["bear"], lw=1.5),
                color=CHART_STYLE["bear"], fontsize=8.5, fontweight="bold", ha="center")

    ax.annotate("Sweep!\nТолпа выбита", xy=(6.5, 12.55), xytext=(8.0, 13.3),
                arrowprops=dict(arrowstyle="->", color=CHART_STYLE["bear"], lw=1.5),
                color=CHART_STYLE["bear"], fontsize=8.5, fontweight="bold", ha="center")

    ax.annotate("SM разворачивает\nнастоящее движение", xy=(9.0, 11.0), xytext=(10.0, 12.8),
                arrowprops=dict(arrowstyle="->", color=CHART_STYLE["bull"], lw=1.5),
                color=CHART_STYLE["bull"], fontsize=8.5, fontweight="bold", ha="center")

    ax.fill_between(t, 11.6, 12.0, where=(t >= 4.5) & (t <= 7.0),
                    alpha=0.15, color=CHART_STYLE["gold"], label="Зона Inducement")
    ax.set_xlabel("Время")
    ax.set_ylabel("Цена")
    ax.legend(facecolor=CHART_STYLE["panel"], edgecolor=CHART_STYLE["grid"],
              labelcolor=CHART_STYLE["text"], fontsize=8)
    return fig_to_bytes(fig)


def chart_liquidity() -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(10, 6))
    set_dark_style(fig, [ax])
    fig.suptitle("Ликвидность: BSL & SSL", color=CHART_STYLE["text"], fontsize=13, fontweight="bold")

    np.random.seed(42)
    t = np.arange(0, 100)
    price = 100 + np.cumsum(np.random.randn(100) * 0.6)
    ax.plot(t, price, color=CHART_STYLE["accent"], lw=1.5, zorder=3)

    # BSL — over highs
    bsl_levels = [105.5, 108.2, 112.0]
    for lvl in bsl_levels:
        ax.axhline(lvl, color=CHART_STYLE["bull"], lw=1.2, ls="--", alpha=0.7)
        ax.text(1, lvl + 0.3, f"BSL {lvl:.1f}", color=CHART_STYLE["bull"], fontsize=7.5, fontweight="bold")

    # SSL — under lows
    ssl_levels = [94.8, 97.3, 99.0]
    for lvl in ssl_levels:
        ax.axhline(lvl, color=CHART_STYLE["bear"], lw=1.2, ls="--", alpha=0.7)
        ax.text(1, lvl - 1.0, f"SSL {lvl:.1f}", color=CHART_STYLE["bear"], fontsize=7.5, fontweight="bold")

    # Equal Highs annotation
    ax.annotate("Equal Highs\n(видимая ликвидность)", xy=(70, 108.2), xytext=(50, 111.0),
                arrowprops=dict(arrowstyle="->", color=CHART_STYLE["gold"]),
                color=CHART_STYLE["gold"], fontsize=8, ha="center")

    # Sweeps
    ax.scatter([72, 85], [108.5, 94.5], s=120, color=CHART_STYLE["gold"],
               zorder=6, marker="*", label="Sweep (сбор ликвидности)")

    bsl_patch = mpatches.Patch(color=CHART_STYLE["bull"], label="BSL — над максимумами (стопы продавцов)")
    ssl_patch = mpatches.Patch(color=CHART_STYLE["bear"], label="SSL — под минимумами (стопы покупателей)")
    ax.legend(handles=[bsl_patch, ssl_patch], facecolor=CHART_STYLE["panel"],
              edgecolor=CHART_STYLE["grid"], labelcolor=CHART_STYLE["text"], fontsize=8,
              loc="upper left")
    ax.set_xlabel("Время (бары)")
    ax.set_ylabel("Цена")
    return fig_to_bytes(fig)


def chart_liquidity_pools() -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(10, 6))
    set_dark_style(fig, [ax])
    fig.suptitle("Пулы Ликвидности — Маршрут цены", color=CHART_STYLE["text"], fontsize=13, fontweight="bold")

    np.random.seed(7)
    t = np.linspace(0, 20, 400)
    price = (
        100
        + 3 * np.sin(0.5 * t)
        + 2 * np.sin(1.2 * t + 1)
        + 0.5 * np.cumsum(np.random.randn(400) * 0.05)
    )

    ax.plot(t, price, color=CHART_STYLE["accent"], lw=1.5, zorder=3)

    pools = [
        (102.8, "Asia High Pool", CHART_STYLE["gold"]),
        (108.5, "Weekly High Pool", CHART_STYLE["bull"]),
        (97.2, "Asia Low Pool", CHART_STYLE["bear"]),
        (93.5, "Weekly Low Pool", CHART_STYLE["purple"]),
    ]

    for lvl, name, c in pools:
        ax.axhline(lvl, color=c, lw=1.5, ls=(0, (5, 3)), alpha=0.85)
        ax.text(20.1, lvl, name, color=c, fontsize=7.5, va="center", fontweight="bold")
        ax.fill_between(t, lvl - 0.4, lvl + 0.4, alpha=0.12, color=c)

    arrows = [(3, 102.2, 6, 108.0), (6, 107.8, 10, 97.5), (10, 97.3, 15, 102.5)]
    for x1, y1, x2, y2 in arrows:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="-|>", color=CHART_STYLE["muted"], lw=1.2, alpha=0.6))

    ax.text(0.5, 110, "💡 Цена движется от пула к пулу", color=CHART_STYLE["muted"], fontsize=9, style="italic")
    ax.set_xlabel("Время")
    ax.set_ylabel("Цена")
    ax.set_xlim(0, 22)
    return fig_to_bytes(fig)


def _draw_candles(ax, data, bull_c, bear_c):
    """data = [(open, high, low, close), ...]"""
    for i, (o, h, l, c) in enumerate(data):
        color = bull_c if c >= o else bear_c
        ax.plot([i, i], [l, h], color=color, lw=1.2, zorder=3)
        rect = Rectangle((i - 0.3, min(o, c)), 0.6, abs(c - o),
                          facecolor=color, edgecolor=color, lw=0.5, zorder=4)
        ax.add_patch(rect)
    ax.set_xlim(-0.8, len(data) - 0.2)


def chart_order_blocks() -> io.BytesIO:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    set_dark_style(fig, [ax1, ax2])
    fig.suptitle("Order Blocks: бычий и медвежий", color=CHART_STYLE["text"], fontsize=13, fontweight="bold")

    # Бычий OB — последняя медвежья свеча перед импульсом вверх
    bull_candles = [
        (10.0, 10.5, 9.8, 10.2), (10.2, 10.4, 9.9, 10.1), (10.1, 10.3, 9.7, 9.9),
        (9.9, 10.0, 9.6, 9.7),   # <-- Бычий OB (медвежья свеча)
        (9.7, 11.0, 9.6, 10.8), (10.8, 11.5, 10.7, 11.4), (11.4, 12.0, 11.2, 11.9),
        (11.9, 12.3, 11.7, 12.1),
    ]
    _draw_candles(ax1, bull_candles, CHART_STYLE["bull"], CHART_STYLE["bear"])
    ob_rect = Rectangle((2.7, 9.6), 0.6, 0.4,
                         facecolor=CHART_STYLE["bull"], edgecolor=CHART_STYLE["bull"],
                         alpha=0.25, lw=1.5, linestyle="--", zorder=2)
    ax1.add_patch(ob_rect)
    ax1.axhspan(9.6, 10.0, alpha=0.08, color=CHART_STYLE["bull"])
    ax1.text(3, 9.3, "📦 Бычий OB\n(последняя медвежья свеча)", color=CHART_STYLE["bull"],
             fontsize=8, ha="center", fontweight="bold")
    ax1.annotate("Импульс вверх (BOS)", xy=(4, 10.9), xytext=(1.5, 12.0),
                 arrowprops=dict(arrowstyle="->", color=CHART_STYLE["bull"]),
                 color=CHART_STYLE["bull"], fontsize=8, ha="center")
    ax1.set_title("Бычий Order Block", color=CHART_STYLE["text"])
    ax1.set_ylabel("Цена")

    # Медвежий OB — последняя бычья свеча перед импульсом вниз
    bear_candles = [
        (12.0, 12.4, 11.9, 12.3), (12.3, 12.5, 12.1, 12.4), (12.4, 12.7, 12.2, 12.6),
        (12.6, 13.0, 12.4, 12.9),  # <-- Медвежий OB (бычья свеча)
        (12.9, 13.1, 11.5, 11.7), (11.7, 11.9, 11.0, 11.1), (11.1, 11.3, 10.5, 10.6),
        (10.6, 10.8, 10.2, 10.4),
    ]
    _draw_candles(ax2, bear_candles, CHART_STYLE["bull"], CHART_STYLE["bear"])
    ob_rect2 = Rectangle((2.7, 12.4), 0.6, 0.7,
                          facecolor=CHART_STYLE["bear"], edgecolor=CHART_STYLE["bear"],
                          alpha=0.25, lw=1.5, linestyle="--", zorder=2)
    ax2.add_patch(ob_rect2)
    ax2.axhspan(12.4, 13.1, alpha=0.08, color=CHART_STYLE["bear"])
    ax2.text(3, 13.3, "📦 Медвежий OB\n(последняя бычья свеча)", color=CHART_STYLE["bear"],
             fontsize=8, ha="center", fontweight="bold")
    ax2.annotate("Импульс вниз (BOS)", xy=(4, 11.6), xytext=(1.5, 10.3),
                 arrowprops=dict(arrowstyle="->", color=CHART_STYLE["bear"]),
                 color=CHART_STYLE["bear"], fontsize=8, ha="center")
    ax2.set_title("Медвежий Order Block", color=CHART_STYLE["text"])

    for ax in [ax1, ax2]:
        ax.set_xticks([])

    plt.tight_layout()
    return fig_to_bytes(fig)


def chart_fvg() -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(10, 6))
    set_dark_style(fig, [ax])
    fig.suptitle("Fair Value Gap (FVG) — Имбаланс", color=CHART_STYLE["text"], fontsize=13, fontweight="bold")

    candles = [
        (10.0, 10.3, 9.9, 10.2), (10.2, 10.4, 10.1, 10.3), (10.3, 10.5, 10.2, 10.4),
        (10.4, 11.8, 10.3, 11.6),  # свеча 1 (импульс) — верх = 11.8
        (11.6, 12.5, 11.3, 12.4),  # свеча 2 (большая бычья) — низ = 11.3
        (12.4, 12.7, 12.2, 12.6),  # свеча 3 — низ = 12.2
        # FVG между 11.8 (верх свечи 1) и 12.2 (низ свечи 3)?
        # Нет — FVG: low свечи 3 > high свечи 1 → 12.2 > 11.8 → зазор [11.8, 12.2]
        (12.6, 12.8, 12.3, 12.5), (12.5, 12.7, 11.9, 12.0), (12.0, 12.1, 11.7, 11.85),
        (11.85, 12.4, 11.8, 12.3),  # цена возвращается в FVG
        (12.3, 12.6, 12.2, 12.5), (12.5, 12.9, 12.4, 12.8),
    ]
    _draw_candles(ax, candles, CHART_STYLE["bull"], CHART_STYLE["bear"])

    # FVG зона — between high of candle[3] (11.8) and low of candle[5] (12.2)
    ax.fill_between([-0.8, 11.8], 11.8, 12.2, alpha=0.22, color=CHART_STYLE["gold"])
    ax.axhline(11.8, color=CHART_STYLE["gold"], lw=1, ls="--", alpha=0.8)
    ax.axhline(12.2, color=CHART_STYLE["gold"], lw=1, ls="--", alpha=0.8)
    ax.text(1.5, 12.0, "⚡ FVG зона (Имбаланс)", color=CHART_STYLE["gold"], fontsize=9, va="center", fontweight="bold")

    ax.annotate("Цена заполняет FVG\nперед продолжением", xy=(9.5, 11.9), xytext=(6.5, 11.3),
                arrowprops=dict(arrowstyle="->", color=CHART_STYLE["accent"]),
                color=CHART_STYLE["accent"], fontsize=8.5, ha="center")
    ax.annotate("Импульс создаёт FVG", xy=(4.5, 12.0), xytext=(3.0, 13.0),
                arrowprops=dict(arrowstyle="->", color=CHART_STYLE["bull"]),
                color=CHART_STYLE["bull"], fontsize=8.5, ha="center")

    ax.set_xticks([])
    ax.set_ylabel("Цена")
    ax.set_ylim(9.5, 13.5)
    return fig_to_bytes(fig)


def chart_breaker_blocks() -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(10, 6))
    set_dark_style(fig, [ax])
    fig.suptitle("Breaker Block — Эволюция Order Block", color=CHART_STYLE["text"], fontsize=13, fontweight="bold")

    candles = [
        (12.0, 12.5, 11.9, 12.4), (12.4, 12.6, 12.2, 12.5),
        (12.5, 12.9, 12.3, 12.8), (12.8, 13.2, 12.6, 12.7),  # Потенциальный OB (бычья свеча) → станет Breaker
        (12.7, 12.8, 11.4, 11.5), (11.5, 11.7, 11.0, 11.1),  # Пробой вниз
        (11.1, 11.3, 10.8, 11.0), (11.0, 11.2, 10.9, 11.1),
        (11.1, 12.6, 11.0, 12.5), (12.5, 12.7, 12.0, 12.3),  # Ретест Breaker
        (12.3, 12.1, 11.5, 11.6), (11.6, 11.8, 11.2, 11.3),  # Отбой вниз
    ]
    _draw_candles(ax, candles, CHART_STYLE["bull"], CHART_STYLE["bear"])

    # Original OB zone
    ax.fill_between([-0.5, 3.7], 12.6, 13.2, alpha=0.15, color=CHART_STYLE["gold"])
    ax.text(1.5, 13.25, "Исходный бычий OB", color=CHART_STYLE["gold"], fontsize=8, ha="center")

    # Breaker zone (same range, now bearish)
    ax.fill_between([7.5, 11.8], 12.3, 12.8, alpha=0.25, color=CHART_STYLE["bear"])
    ax.text(9.5, 12.88, "🔴 Breaker Block (медвежий)", color=CHART_STYLE["bear"], fontsize=8.5, ha="center", fontweight="bold")

    # BOS arrow
    ax.annotate("BOS — пробой OB вниз", xy=(4.5, 12.0), xytext=(2.5, 11.0),
                arrowprops=dict(arrowstyle="->", color=CHART_STYLE["bear"]),
                color=CHART_STYLE["bear"], fontsize=8, ha="center")
    ax.annotate("Ретест Breaker → продажи", xy=(8.5, 12.4), xytext=(6.5, 13.5),
                arrowprops=dict(arrowstyle="->", color=CHART_STYLE["bear"]),
                color=CHART_STYLE["bear"], fontsize=8.5, ha="center")

    ax.set_xticks([])
    ax.set_ylabel("Цена")
    return fig_to_bytes(fig)


def chart_mitigation_blocks() -> io.BytesIO:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    set_dark_style(fig, [ax1, ax2])
    fig.suptitle("Mitigation Block vs Breaker Block", color=CHART_STYLE["text"], fontsize=13, fontweight="bold")

    # Mitigation — возврат к OB, не пробивает
    mit_c = [
        (10.0, 10.4, 9.9, 10.3), (10.3, 10.6, 10.2, 10.5),
        (10.5, 10.8, 10.3, 10.4),  # OB (медвежья)
        (10.4, 11.2, 10.3, 11.1), (11.1, 11.5, 11.0, 11.4),
        (11.4, 11.6, 11.1, 11.2), (11.2, 11.3, 10.7, 10.8),  # Mitigation — возврат к OB
        (10.8, 10.95, 10.6, 10.7),
        (10.7, 11.8, 10.6, 11.7), (11.7, 12.0, 11.5, 11.9),  # продолжение
    ]
    _draw_candles(ax1, mit_c, CHART_STYLE["bull"], CHART_STYLE["bear"])
    ax1.fill_between([-0.5, 9.5], 10.3, 10.8, alpha=0.2, color=CHART_STYLE["accent"])
    ax1.text(4.5, 10.15, "🔄 Mitigation Block (OB удержан)", color=CHART_STYLE["accent"], fontsize=8, ha="center", fontweight="bold")
    ax1.annotate("Цена митигирует OB\n(не пробивает)", xy=(6.5, 10.75), xytext=(4.5, 12.0),
                 arrowprops=dict(arrowstyle="->", color=CHART_STYLE["accent"]),
                 color=CHART_STYLE["accent"], fontsize=8, ha="center")
    ax1.set_title("Mitigation Block", color=CHART_STYLE["text"])
    ax1.set_ylabel("Цена")

    # Breaker — пробивает
    br_c = [
        (12.0, 12.5, 11.9, 12.4), (12.4, 12.7, 12.3, 12.6),
        (12.6, 13.0, 12.4, 12.7),  # OB (бычья) → станет Breaker
        (12.7, 12.8, 11.0, 11.1),  # Пробой вниз
        (11.1, 11.3, 10.8, 11.0), (11.0, 12.8, 10.9, 12.7),  # Ретест
        (12.7, 12.9, 12.3, 12.4), (12.4, 12.2, 11.5, 11.6),  # Отбой
    ]
    _draw_candles(ax2, br_c, CHART_STYLE["bull"], CHART_STYLE["bear"])
    ax2.fill_between([-0.5, 7.5], 12.4, 13.0, alpha=0.22, color=CHART_STYLE["bear"])
    ax2.text(3.5, 13.15, "💥 Breaker Block (пробит, сменил роль)", color=CHART_STYLE["bear"], fontsize=8, ha="center", fontweight="bold")
    ax2.annotate("Пробой OB = он\nстановится Breaker", xy=(3, 12.2), xytext=(1.5, 11.2),
                 arrowprops=dict(arrowstyle="->", color=CHART_STYLE["bear"]),
                 color=CHART_STYLE["bear"], fontsize=8, ha="center")
    ax2.set_title("Breaker Block", color=CHART_STYLE["text"])

    for ax in [ax1, ax2]:
        ax.set_xticks([])

    plt.tight_layout()
    return fig_to_bytes(fig)


def chart_premium_discount() -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(10, 7))
    set_dark_style(fig, [ax])
    fig.suptitle("Premium & Discount Zones", color=CHART_STYLE["text"], fontsize=13, fontweight="bold")

    np.random.seed(3)
    t = np.arange(0, 80)
    price = 100 + np.cumsum(np.random.randn(80) * 0.7)

    swing_low = 93.0
    swing_high = 113.0
    mid = (swing_low + swing_high) / 2
    ote_low = swing_low + 0.62 * (swing_high - swing_low)
    ote_high = swing_low + 0.79 * (swing_high - swing_low)

    ax.plot(t, price, color=CHART_STYLE["accent"], lw=1.5, zorder=4)

    # Zones
    ax.fill_between(t, swing_high, 120, alpha=0.12, color=CHART_STYLE["bear"], label="Premium — зона продаж")
    ax.fill_between(t, swing_low, mid, alpha=0.12, color=CHART_STYLE["bull"], label="Discount — зона покупок")
    ax.fill_between(t, ote_low, ote_high, alpha=0.18, color=CHART_STYLE["gold"], label="OTE (62–79%)")

    ax.axhline(swing_high, color=CHART_STYLE["bear"], lw=1.5, ls="--")
    ax.axhline(swing_low, color=CHART_STYLE["bull"], lw=1.5, ls="--")
    ax.axhline(mid, color=CHART_STYLE["muted"], lw=1.5, ls="-")
    ax.axhline(ote_low, color=CHART_STYLE["gold"], lw=1, ls=":")
    ax.axhline(ote_high, color=CHART_STYLE["gold"], lw=1, ls=":")

    ax.text(81, swing_high, "Swing High", color=CHART_STYLE["bear"], fontsize=8, va="center", fontweight="bold")
    ax.text(81, swing_low, "Swing Low", color=CHART_STYLE["bull"], fontsize=8, va="center", fontweight="bold")
    ax.text(81, mid, "50% EQ", color=CHART_STYLE["muted"], fontsize=8, va="center")
    ax.text(81, (ote_low + ote_high) / 2, "OTE\n62-79%", color=CHART_STYLE["gold"], fontsize=7.5, va="center")

    ax.text(35, 117, "📉 PREMIUM — Smart Money продают", color=CHART_STYLE["bear"],
            fontsize=9, ha="center", fontweight="bold")
    ax.text(35, 96, "📈 DISCOUNT — Smart Money покупают", color=CHART_STYLE["bull"],
            fontsize=9, ha="center", fontweight="bold")

    ax.legend(facecolor=CHART_STYLE["panel"], edgecolor=CHART_STYLE["grid"],
              labelcolor=CHART_STYLE["text"], fontsize=8, loc="lower right")
    ax.set_ylabel("Цена")
    ax.set_xlabel("Время (бары)")
    ax.set_xlim(0, 95)
    return fig_to_bytes(fig)


def chart_killzones() -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(12, 5))
    set_dark_style(fig, [ax])
    fig.suptitle("Kill Zones — Торговые Сессии (UTC+3)", color=CHART_STYLE["text"], fontsize=13, fontweight="bold")

    sessions = [
        ("Азия", 2, 6, CHART_STYLE["purple"], "Формирование диапазона\n(Asia Range)"),
        ("Лондон", 10, 14, CHART_STYLE["accent"], "Sweep Asia High/Low\n→ Kill Zone"),
        ("Нью-Йорк", 15, 19, CHART_STYLE["gold"], "Основное движение\n→ Kill Zone"),
        ("Ночь", 0, 2, CHART_STYLE["muted"], "Низкий объём"),
        ("Пост-NY", 19, 24, CHART_STYLE["muted"], "Низкий объём"),
    ]

    ax.set_xlim(0, 24)
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.set_xticks(range(0, 25, 2))
    ax.set_xticklabels([f"{h}:00" for h in range(0, 25, 2)], fontsize=8)
    ax.set_xlabel("Время (UTC+3)", color=CHART_STYLE["text"])

    for name, start, end, color, desc in sessions:
        alpha = 0.75 if color != CHART_STYLE["muted"] else 0.3
        rect = Rectangle((start, 0.2), end - start, 0.6, facecolor=color, alpha=alpha, edgecolor="none")
        ax.add_patch(rect)
        mid = (start + end) / 2
        ax.text(mid, 0.62, name, ha="center", va="center", color="white", fontsize=9, fontweight="bold")
        ax.text(mid, 0.35, desc, ha="center", va="center", color=CHART_STYLE["bg"], fontsize=7)

    # Стрелки время
    ax.annotate("", xy=(10, 0.9), xytext=(4, 0.9),
                arrowprops=dict(arrowstyle="-|>", color=CHART_STYLE["accent"], lw=1.5))
    ax.text(7, 0.93, "Sweep", ha="center", color=CHART_STYLE["accent"], fontsize=8)
    ax.annotate("", xy=(15.5, 0.9), xytext=(12.5, 0.9),
                arrowprops=dict(arrowstyle="-|>", color=CHART_STYLE["gold"], lw=1.5))
    ax.text(14.0, 0.93, "NY движение", ha="center", color=CHART_STYLE["gold"], fontsize=8)

    return fig_to_bytes(fig)


def chart_ote() -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(10, 7))
    set_dark_style(fig, [ax])
    fig.suptitle("OTE — Optimal Trade Entry (62–79% по Фибо)", color=CHART_STYLE["text"], fontsize=13, fontweight="bold")

    low = 100.0
    high = 115.0
    levels = {
        "100%": low, "78.6%": low + 0.214 * (high - low), "70.5%": low + 0.295 * (high - low),
        "61.8%": low + 0.382 * (high - low), "50%": low + 0.5 * (high - low),
        "38.2%": low + 0.618 * (high - low), "23.6%": low + 0.764 * (high - low), "0%": high,
    }

    t = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    price = [100, 101, 103, 106, 110, 115, 113, 111, 109, 107.5, 108, 110, 113]
    ax.plot(t, price, color=CHART_STYLE["accent"], lw=2, zorder=5, label="Цена")

    colors_fib = {
        "0%": CHART_STYLE["bull"], "23.6%": CHART_STYLE["bull"],
        "38.2%": CHART_STYLE["muted"], "50%": CHART_STYLE["muted"],
        "61.8%": CHART_STYLE["gold"], "70.5%": CHART_STYLE["gold"],
        "78.6%": CHART_STYLE["gold"], "100%": CHART_STYLE["bear"],
    }
    for label, val in levels.items():
        c = colors_fib.get(label, CHART_STYLE["muted"])
        ax.axhline(val, color=c, lw=0.8, ls="--", alpha=0.7)
        ax.text(12.2, val, f"{label} — {val:.1f}", color=c, fontsize=7.5, va="center")

    ote_low = low + 0.214 * (high - low)
    ote_high = low + 0.382 * (high - low)
    ax.fill_between([0, 12], ote_low, ote_high, alpha=0.18, color=CHART_STYLE["gold"])
    ax.text(6, (ote_low + ote_high) / 2, "⭐ OTE ZONE (62–79%)", ha="center", va="center",
            color=CHART_STYLE["gold"], fontsize=10, fontweight="bold")

    ax.scatter([9], [107.5], color=CHART_STYLE["gold"], s=150, zorder=8, marker="*",
               label="Вход в OTE")
    ax.annotate("Вход в OTE\n(OB + FVG + Kill Zone)", xy=(9, 107.5), xytext=(7, 103.5),
                arrowprops=dict(arrowstyle="->", color=CHART_STYLE["gold"]),
                color=CHART_STYLE["gold"], fontsize=8.5, ha="center", fontweight="bold")

    ax.set_ylabel("Цена")
    ax.set_xlabel("Время")
    ax.set_xlim(0, 14.5)
    ax.legend(facecolor=CHART_STYLE["panel"], edgecolor=CHART_STYLE["grid"],
              labelcolor=CHART_STYLE["text"], fontsize=8)
    return fig_to_bytes(fig)


def chart_amd_model() -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(12, 6))
    set_dark_style(fig, [ax])
    fig.suptitle("AMD Model: Accumulation → Manipulation → Distribution", color=CHART_STYLE["text"], fontsize=13, fontweight="bold")

    t = np.linspace(0, 15, 400)
    acc = np.where(t <= 5, 100 + 0.3 * np.sin(3 * t) + 0.05 * np.random.randn(400), 0)
    man = np.where((t > 5) & (t <= 8), 100 + 0.3 * np.sin(3 * t) - 1.5 * (t - 5) + 0.05 * np.random.randn(400), 0)
    dist_base = np.where(t > 8, 95.5 + 3.0 * (t - 8) + 0.1 * np.sin(1.5 * t) + 0.05 * np.random.randn(400), 0)

    price = acc + man + dist_base
    price = np.where(price == 0, np.nan, price)
    ax.plot(t, price, color=CHART_STYLE["accent"], lw=2, zorder=4)

    ax.axvline(5, color=CHART_STYLE["muted"], lw=1, ls="--", alpha=0.6)
    ax.axvline(8, color=CHART_STYLE["muted"], lw=1, ls="--", alpha=0.6)

    ax.fill_between(t, 97, 103, where=(t <= 5), alpha=0.12, color=CHART_STYLE["purple"])
    ax.fill_between(t, 92, 103, where=(t > 5) & (t <= 8), alpha=0.12, color=CHART_STYLE["bear"])
    ax.fill_between(t, 92, 120, where=(t > 8), alpha=0.10, color=CHART_STYLE["bull"])

    ax.text(2.5, 96.5, "📦 ACCUMULATION\nАзия — накопление", ha="center",
            color=CHART_STYLE["purple"], fontsize=9, fontweight="bold")
    ax.text(6.5, 93.5, "🪤 MANIPULATION\nЛондон — Judas Swing", ha="center",
            color=CHART_STYLE["bear"], fontsize=9, fontweight="bold")
    ax.text(11.5, 96.5, "🚀 DISTRIBUTION\nNY — настоящее движение", ha="center",
            color=CHART_STYLE["bull"], fontsize=9, fontweight="bold")

    ax.annotate("Sweep SSL\n(ложный пробой)", xy=(7.5, 93.8), xytext=(6.8, 101.5),
                arrowprops=dict(arrowstyle="->", color=CHART_STYLE["bear"]),
                color=CHART_STYLE["bear"], fontsize=8, ha="center")

    ax.set_xlabel("Время")
    ax.set_ylabel("Цена")
    ax.set_ylim(90, 125)
    return fig_to_bytes(fig)


def chart_power_of_three() -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(10, 6))
    set_dark_style(fig, [ax])
    fig.suptitle("Power of Three (Po3) — Дневной цикл", color=CHART_STYLE["text"], fontsize=13, fontweight="bold")

    t = np.linspace(0, 24, 500)

    asia = np.where(t <= 6, 100 + 0.4 * np.sin(2 * t) + 0.03 * np.random.randn(500), np.nan)
    london_sw = np.where((t > 6) & (t <= 9), 100 + 0.4 * np.sin(2 * 6) - 1.5 * (t - 6) + 0.03 * np.random.randn(500), np.nan)
    ny = np.where(t > 9, 97.5 + 2.0 * (t - 9) + 0.1 * np.sin(t) + 0.05 * np.random.randn(500), np.nan)

    ax.plot(t, asia, color=CHART_STYLE["purple"], lw=2.5, label="Азия — диапазон")
    ax.plot(t, london_sw, color=CHART_STYLE["bear"], lw=2.5, label="Лондон — Judas Swing")
    ax.plot(t, ny, color=CHART_STYLE["bull"], lw=2.5, label="NY — настоящее движение")

    ax.axvline(6, color=CHART_STYLE["muted"], lw=1, ls="--")
    ax.axvline(9, color=CHART_STYLE["muted"], lw=1, ls="--")

    # Asia range
    ax.fill_between(t, 99, 101, where=(t <= 6), alpha=0.1, color=CHART_STYLE["purple"])
    ax.text(3, 98.5, "Asia Range", ha="center", color=CHART_STYLE["purple"], fontsize=8.5)

    ax.annotate("Judas Swing\n(ложный пробой SSL)", xy=(7.5, 97.4), xytext=(5.5, 95.5),
                arrowprops=dict(arrowstyle="->", color=CHART_STYLE["bear"]),
                color=CHART_STYLE["bear"], fontsize=8, ha="center")
    ax.annotate("Po3 — настоящий\nдневной тренд вверх", xy=(16, 112.5), xytext=(12, 117),
                arrowprops=dict(arrowstyle="->", color=CHART_STYLE["bull"]),
                color=CHART_STYLE["bull"], fontsize=8, ha="center")

    ax.set_xlim(0, 24)
    ax.set_xticks([0, 3, 6, 9, 12, 15, 18, 21, 24])
    ax.set_xticklabels(["00:00", "03:00", "06:00", "09:00", "12:00", "15:00", "18:00", "21:00", "24:00"], fontsize=7)
    ax.set_xlabel("Время суток (UTC+3)")
    ax.set_ylabel("Цена")
    ax.legend(facecolor=CHART_STYLE["panel"], edgecolor=CHART_STYLE["grid"],
              labelcolor=CHART_STYLE["text"], fontsize=8)
    return fig_to_bytes(fig)


def chart_market_maker_model() -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(12, 7))
    set_dark_style(fig, [ax])
    fig.suptitle("Market Maker Model — Полный Цикл", color=CHART_STYLE["text"], fontsize=13, fontweight="bold")

    stages = {
        "1. Accumulation\n(Набор позиции)": (0, 3, 99, 101, CHART_STYLE["purple"]),
        "2. Manipulation\n(Sweep BSL)": (3, 5, 99, 103.5, CHART_STYLE["gold"]),
        "3. Smart Money Reversal\n(CHoCH)": (5, 7, 97, 103.5, CHART_STYLE["accent"]),
        "4. Distribution\n(Движение к цели)": (7, 12, 95, 115, CHART_STYLE["bull"]),
    }

    np.random.seed(99)
    t = np.linspace(0, 12, 300)
    p = (
        100
        + np.where(t < 3, 0.3 * np.sin(5 * t), 0)
        + np.where((t >= 3) & (t < 5), 0.3 * np.sin(5 * t) + 1.5 * (t - 3), 0)
        + np.where((t >= 5) & (t < 7), 3.0 - 2.5 * (t - 5), 0)
        + np.where(t >= 7, -2.0 + 3.5 * (t - 7), 0)
        + 0.08 * np.random.randn(300)
    )
    ax.plot(t, p, color=CHART_STYLE["accent"], lw=1.8, zorder=5)

    for label, (x1, x2, y1, y2, c) in stages.items():
        ax.fill_between([x1, x2], y1, y2, alpha=0.1, color=c)
        ax.axvline(x1, color=c, lw=0.8, ls=":", alpha=0.5)
        ax.text((x1 + x2) / 2, y1 - 1.5, label, ha="center",
                color=c, fontsize=8, fontweight="bold")

    ax.annotate("Sweep BSL\n(ловушка покупателей)", xy=(4.5, 103.2), xytext=(3.5, 107),
                arrowprops=dict(arrowstyle="->", color=CHART_STYLE["gold"]),
                color=CHART_STYLE["gold"], fontsize=8, ha="center")
    ax.annotate("CHoCH — разворот", xy=(6, 99.5), xytext=(5.5, 95),
                arrowprops=dict(arrowstyle="->", color=CHART_STYLE["accent"]),
                color=CHART_STYLE["accent"], fontsize=8, ha="center")
    ax.annotate("Цель — следующий пул\nликвидности", xy=(11, 114.5), xytext=(9, 110),
                arrowprops=dict(arrowstyle="->", color=CHART_STYLE["bull"]),
                color=CHART_STYLE["bull"], fontsize=8, ha="center")

    ax.set_xlabel("Время")
    ax.set_ylabel("Цена")
    ax.set_ylim(91, 120)
    return fig_to_bytes(fig)


def chart_ict_2022_model() -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(12, 7))
    set_dark_style(fig, [ax])
    fig.suptitle("ICT 2022 Mentorship Model — Алгоритм Long", color=CHART_STYLE["text"], fontsize=13, fontweight="bold")
    ax.axis("off")

    steps = [
        ("1. HTF тренд\n(D1/H4)", CHART_STYLE["purple"], "Бычий тренд — ищем покупки"),
        ("2. Kill Zone\n(Лондон / NY)", CHART_STYLE["accent"], "Вход только в активные сессии"),
        ("3. Sweep SSL\n(Ложный пробой)", CHART_STYLE["gold"], "Цена выбивает минимумы (стопы)"),
        ("4. CHoCH / MSS\n(Слом структуры)", CHART_STYLE["bull"], "Смена структуры вверх на M5–M15"),
        ("5. FVG или OB\n(Зона для входа)", CHART_STYLE["bull"], "Находим POI на откате"),
        ("6. Вход + SL + TP\n(Исполнение)", CHART_STYLE["gold"], "SL под SSL, TP к BSL (1:3+)"),
    ]

    n = len(steps)
    for i, (title, color, desc) in enumerate(steps):
        x = 0.12 + (i % 3) * 0.28
        y = 0.72 if i < 3 else 0.28
        box = FancyArrowPatch((x, y), (x, y), arrowstyle="simple")
        rect = Rectangle((x - 0.11, y - 0.16), 0.22, 0.32, facecolor=color,
                          edgecolor="white", linewidth=1.2, alpha=0.85, transform=ax.transAxes)
        ax.add_patch(rect)
        ax.text(x, y + 0.08, title, ha="center", va="center", transform=ax.transAxes,
                color="white", fontsize=9, fontweight="bold")
        ax.text(x, y - 0.06, desc, ha="center", va="center", transform=ax.transAxes,
                color=CHART_STYLE["bg"], fontsize=7.5, alpha=0.9)
        ax.text(x - 0.10, y + 0.14, f"Step {i+1}", transform=ax.transAxes,
                color=CHART_STYLE["bg"], fontsize=7, fontweight="bold")

    # Стрелки
    for i in range(n - 1):
        x1 = 0.12 + (i % 3) * 0.28 + 0.11
        x2 = 0.12 + ((i + 1) % 3) * 0.28 - 0.11
        if i == 2:
            ax.annotate("", xy=(0.12 - 0.11, 0.28 + 0.16), xytext=(0.12 + 2 * 0.28 + 0.11, 0.72 - 0.16),
                        arrowprops=dict(arrowstyle="-|>", color=CHART_STYLE["muted"], lw=1.5),
                        xycoords="axes fraction", textcoords="axes fraction")
        else:
            y = 0.72 + 0.0 if i < 2 else 0.28
            ax.annotate("", xy=(x2, y), xytext=(x1, y),
                        arrowprops=dict(arrowstyle="-|>", color=CHART_STYLE["muted"], lw=1.5),
                        xycoords="axes fraction", textcoords="axes fraction")

    ax.text(0.5, 0.04, "🎯 Результат: высоковероятная сделка с R:R ≥ 1:3",
            ha="center", transform=ax.transAxes, color=CHART_STYLE["gold"], fontsize=10, fontweight="bold")
    return fig_to_bytes(fig)


def chart_session_sweep_model() -> io.BytesIO:
    fig, ax = plt.subplots(figsize=(12, 6))
    set_dark_style(fig, [ax])
    fig.suptitle("Session Sweep Model: Asia → London → NY", color=CHART_STYLE["text"], fontsize=13, fontweight="bold")

    t = np.linspace(0, 24, 500)
    np.random.seed(55)

    asia_range_h = 101.5
    asia_range_l = 98.5

    p = np.where(t <= 8, 100 + 0.6 * np.sin(1.5 * t) + 0.05 * np.random.randn(500), 0)
    sweep_up = np.where((t > 8) & (t <= 10), 100 + 0.6 * np.sin(1.5 * 8) + 1.8 * (t - 8) + 0.05 * np.random.randn(500), 0)
    reversal = np.where((t > 10) & (t <= 12), asia_range_h + 2.16 - 2.0 * (t - 10) + 0.05 * np.random.randn(500), 0)
    ny_move = np.where(t > 12, 99.5 - 2.5 * (t - 12) + 0.05 * np.cumsum(np.random.randn(500)) * (t > 12), 0)

    price = p + sweep_up + reversal + ny_move
    price = np.where(price == 0, np.nan, price)
    ax.plot(t, price, color=CHART_STYLE["accent"], lw=2, zorder=5)

    ax.axhline(asia_range_h, color=CHART_STYLE["bull"], lw=1.2, ls="--", alpha=0.8, label="Asia High")
    ax.axhline(asia_range_l, color=CHART_STYLE["bear"], lw=1.2, ls="--", alpha=0.8, label="Asia Low")
    ax.fill_between(t, asia_range_l, asia_range_h, where=(t <= 8), alpha=0.08, color=CHART_STYLE["purple"])

    ax.fill_between(t, 96, 106, where=(t <= 8), alpha=0.08, color=CHART_STYLE["purple"])
    ax.fill_between(t, 96, 106, where=(t > 8) & (t <= 12), alpha=0.08, color=CHART_STYLE["accent"])
    ax.fill_between(t, 60, 106, where=(t > 12), alpha=0.08, color=CHART_STYLE["bull"])

    ax.text(4, 97.0, "Азия\nДиапазон формируется", ha="center", color=CHART_STYLE["purple"], fontsize=8.5, fontweight="bold")
    ax.annotate("Sweep Asia High\n(ловушка для быков)", xy=(9.2, 103.5), xytext=(7, 106),
                arrowprops=dict(arrowstyle="->", color=CHART_STYLE["gold"]),
                color=CHART_STYLE["gold"], fontsize=8.5, ha="center")
    ax.text(11, 101.5, "Разворот", ha="center", color=CHART_STYLE["accent"], fontsize=8, fontweight="bold")
    ax.text(18, 97.5, "NY — движение\nв противоположную сторону", ha="center", color=CHART_STYLE["bull"], fontsize=8.5, fontweight="bold")

    ax.set_xlim(0, 24)
    ax.set_xticks([0, 3, 6, 8, 10, 12, 15, 18, 21, 24])
    ax.set_xticklabels(["00", "03", "06", "08\nАзия", "10\nЛондон", "12", "15\nNY", "18", "21", "24"], fontsize=7)
    ax.set_xlabel("Время (UTC+3)")
    ax.set_ylabel("Цена")
    ax.legend(facecolor=CHART_STYLE["panel"], edgecolor=CHART_STYLE["grid"],
              labelcolor=CHART_STYLE["text"], fontsize=8)
    return fig_to_bytes(fig)


def chart_risk_management() -> io.BytesIO:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    set_dark_style(fig, [ax1, ax2])
    fig.suptitle("Риск-менеджмент в SMC", color=CHART_STYLE["text"], fontsize=13, fontweight="bold")

    # График R:R соотношение
    rr_ratios = ["1:1", "1:2", "1:3 (цель)", "1:5"]
    win_rates_needed = [50, 34, 25, 17]
    colors = [CHART_STYLE["bear"], CHART_STYLE["gold"], CHART_STYLE["bull"], CHART_STYLE["accent"]]
    bars = ax1.bar(rr_ratios, win_rates_needed, color=colors, width=0.5, edgecolor="none")
    for bar, val in zip(bars, win_rates_needed):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f"{val}%", ha="center", color=CHART_STYLE["text"], fontsize=9, fontweight="bold")
    ax1.axhline(33, color=CHART_STYLE["muted"], lw=1, ls="--", alpha=0.7)
    ax1.text(3.4, 34, "Рекомендуемый WR", color=CHART_STYLE["muted"], fontsize=8)
    ax1.set_ylabel("Минимальный Win Rate (%)")
    ax1.set_title("R:R vs минимальный Win Rate", color=CHART_STYLE["text"])
    ax1.set_ylim(0, 60)

    # Симуляция эквити при разном риске
    n = 50
    np.random.seed(22)
    trades = np.random.choice([-1, 2.5], size=n, p=[0.4, 0.6])  # 60% WR, R:R 1:2.5

    for risk_pct, c, lbl in [(0.005, CHART_STYLE["bull"], "0.5% риск"),
                               (0.01, CHART_STYLE["gold"], "1% риск"),
                               (0.03, CHART_STYLE["bear"], "3% риск (опасно)")]:
        equity = [1000]
        for t in trades:
            equity.append(equity[-1] * (1 + risk_pct * t))
        ax2.plot(equity, color=c, lw=1.8, label=lbl)

    ax2.axhline(1000, color=CHART_STYLE["muted"], lw=0.8, ls=":", alpha=0.5)
    ax2.set_title("Рост депозита при разном риске", color=CHART_STYLE["text"])
    ax2.set_xlabel("Сделки")
    ax2.set_ylabel("Депозит ($)")
    ax2.legend(facecolor=CHART_STYLE["panel"], edgecolor=CHART_STYLE["grid"],
               labelcolor=CHART_STYLE["text"], fontsize=8)

    plt.tight_layout()
    return fig_to_bytes(fig)


def chart_psychology() -> io.BytesIO:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    set_dark_style(fig, [ax1, ax2])
    fig.suptitle("Психология трейдера — Цикл эмоций", color=CHART_STYLE["text"], fontsize=13, fontweight="bold")

    # Цикл эмоций рынка
    ax1.axis("off")
    emotions = ["Оптимизм", "Эйфория\n(MAX риск)", "Тревога", "Отрицание",
                "Паника", "Капитуляция\n(MAX боль)", "Депрессия", "Надежда"]
    colors_em = [CHART_STYLE["bull"], CHART_STYLE["gold"], CHART_STYLE["gold"],
                 CHART_STYLE["bear"], CHART_STYLE["bear"], CHART_STYLE["bear"],
                 CHART_STYLE["muted"], CHART_STYLE["accent"]]
    angles = np.linspace(0, 2 * np.pi, len(emotions), endpoint=False)
    r = 0.35
    cx, cy = 0.5, 0.5

    for i, (em, angle, c) in enumerate(zip(emotions, angles, colors_em)):
        x = cx + r * np.cos(angle)
        y = cy + r * np.sin(angle)
        ax1.text(x, y, em, ha="center", va="center", color=c, fontsize=8, fontweight="bold",
                 transform=ax1.transAxes)
        if i < len(emotions) - 1:
            next_angle = angles[i + 1]
            nx = cx + r * np.cos(next_angle)
            ny = cy + r * np.sin(next_angle)
            ax1.annotate("", xy=(nx, ny), xytext=(x, y),
                         arrowprops=dict(arrowstyle="-|>", color=CHART_STYLE["muted"], lw=1),
                         xycoords="axes fraction", textcoords="axes fraction")

    ax1.text(0.5, 0.5, "💹\nЦикл\nрынка", ha="center", va="center", transform=ax1.transAxes,
             color=CHART_STYLE["text"], fontsize=10, fontweight="bold")
    ax1.set_title("Эмоциональный цикл", color=CHART_STYLE["text"])

    # Ошибки трейдера
    mistakes = ["FOMO\n(вход за рынком)", "Месть\n(без плана)", "Овертрейдинг", "Без SL", "Завышенный риск"]
    impact = [35, 25, 20, 10, 10]
    c2 = [CHART_STYLE["bear"], CHART_STYLE["gold"], CHART_STYLE["bear"],
           CHART_STYLE["bear"], CHART_STYLE["gold"]]
    wedges, texts, autos = ax2.pie(impact, labels=mistakes, colors=c2, autopct="%1.0f%%",
                                    startangle=90, textprops={"color": CHART_STYLE["text"], "fontsize": 8})
    for at in autos:
        at.set_color(CHART_STYLE["bg"])
        at.set_fontweight("bold")
    ax2.set_title("Главные причины слива", color=CHART_STYLE["text"])

    plt.tight_layout()
    return fig_to_bytes(fig)


# Маппинг ключей урока → функции графика
CHART_GENERATORS = {
    "what_is_smc": chart_what_is_smc,
    "timeframes": chart_timeframes,
    "market_structure": chart_market_structure,
    "inducement": chart_inducement,
    "liquidity": chart_liquidity,
    "liquidity_pools": chart_liquidity_pools,
    "order_blocks": chart_order_blocks,
    "fvg": chart_fvg,
    "breaker_blocks": chart_breaker_blocks,
    "mitigation_blocks": chart_mitigation_blocks,
    "premium_discount": chart_premium_discount,
    "killzones": chart_killzones,
    "ote": chart_ote,
    "amd_model": chart_amd_model,
    "power_of_three": chart_power_of_three,
    "market_maker_model": chart_market_maker_model,
    "ict_2022_model": chart_ict_2022_model,
    "session_sweep_model": chart_session_sweep_model,
    "risk_management": chart_risk_management,
    "psychology": chart_psychology,
}


def generate_chart(lesson_key: str) -> Optional[io.BytesIO]:
    fn = CHART_GENERATORS.get(lesson_key)
    if fn is None:
        return None
    try:
        return fn()
    except Exception as e:
        logger.error(f"Chart error [{lesson_key}]: {e}")
        return None


# ─────────────────────────────────────────────────────
# БАЗА КУРСА — расширенные статьи для каждого урока
# ─────────────────────────────────────────────────────

LESSONS: Dict[str, Dict[str, Any]] = {
    "what_is_smc": {
        "title": "🏦 Что такое Smart Money?",
        "text": "Smart Money — крупные институциональные игроки. Цель SMC — торговать вместе с ними.",
        "article": (
            "*🏦 Что такое Smart Money?*\n\n"
            "Smart Money (SM) — это крупные институциональные участники рынка: центральные и коммерческие *банки*, "
            "*хедж-фонды*, *маркет-мейкеры* и корпорации. Они контролируют около 85% всего объёма финансовых рынков.\n\n"
            "*Почему розничные трейдеры проигрывают?*\n"
            "Большинство ритейл-трейдеров используют индикаторы RSI, MACD, уровни поддержки/сопротивления — "
            "именно те инструменты, которые SM используют как ориентиры для сбора ликвидности. "
            "Когда толпа ставит стоп-лоссы под очевидный уровень, SM точно знает, куда прийти за ликвидностью.\n\n"
            "*Что делает Smart Money?*\n"
            "1️⃣ Создают *ловушки* — ложные пробои уровней, за которыми стоят стопы розничных трейдеров\n"
            "2️⃣ *Собирают ликвидность* — входят в позицию, поглощая рыночные ордера на остановках\n"
            "3️⃣ *Двигают цену* к следующему пулу ликвидности\n"
            "4️⃣ *Фиксируют прибыль* — распределяют позицию на ритейл-покупателей\n\n"
            "*Цель методологии SMC* — читать следы Smart Money на графике (структура, Order Blocks, FVG, "
            "ликвидность) и торговать *в их сторону*, а не против них.\n\n"
            "📌 *Ключевая мысль:* рынок не хаотичен — он манипулятивен, и эта манипуляция имеет чёткую логику."
        ),
        "video": "https://www.youtube.com/watch?v=6IBhAcS5dVw",
    },
    "timeframes": {
        "title": "🕐 Таймфреймы и Top-Down анализ",
        "text": "Top-Down — анализ от старших ТФ к младшим. W1/D1→H4→H1→M15→M5.",
        "article": (
            "*🕐 Таймфреймы и Top-Down Анализ*\n\n"
            "Top-Down — фундаментальный принцип SMC: всегда начинать анализ со *старшего таймфрейма* "
            "(макро) и двигаться к *младшему* (микро) для поиска точки входа.\n\n"
            "*Пирамида таймфреймов:*\n\n"
            "🔹 *W1 / Monthly* — глобальный тренд. Определяем: бычий или медвежий рынок? "
            "Это направление священно — против него лучше не торговать.\n\n"
            "🔹 *D1* — основной тренд и крупные пулы ликвидности. Видим недельные экстремумы, "
            "дневные OB, FVG, которые отрабатываются неделями.\n\n"
            "🔹 *H4* — структура свинг-трейда. Здесь определяем Swing High/Low, "
            "BOS и CHoCH высшего порядка, HTF Order Blocks.\n\n"
            "🔹 *H1* — рабочая структура. Detailing: видим более мелкие BOS, "
            "внутренние CHoCH, inducement, зоны OB/FVG для H1.\n\n"
            "🔹 *M15* — зоны для сетапов. Здесь выбираем конкретную POI (Point of Interest) "
            "для входа, смотрим на реакцию цены.\n\n"
            "🔹 *M5 / M1* — точка входа. После CHoCH/MSS на M5 ищем FVG или последнюю свечу OB "
            "для установки лимитного ордера.\n\n"
            "*Правило:* никогда не входи в сделку, пока не знаешь направление на H4 и D1. "
            "Торговля против HTF тренда — 95% причина убытков у новичков.\n\n"
            "📌 *Чек-лист Top-Down:*\n"
            "✅ D1 — тренд определён\n"
            "✅ H4 — структура подтверждена\n"
            "✅ H1 — CHoCH/BOS по направлению\n"
            "✅ M15 — зона POI выбрана\n"
            "✅ M5/M1 — триггер для входа"
        ),
        "video": "https://www.youtube.com/watch?v=mqBR-DRQT_o&t=89s",
    },
    "market_structure": {
        "title": "📐 Структура рынка (Market Structure)",
        "text": "Бычий тренд: HH/HL. Медвежий: LL/LH. BOS — по тренду, CHoCH — разворот.",
        "article": (
            "*📐 Market Structure — Структура рынка*\n\n"
            "Структура рынка — *основа всего SMC*. Без понимания структуры нельзя определить, "
            "куда движется цена и где искать вход.\n\n"
            "*Типы трендов:*\n"
            "📈 *Бычий тренд* — цена создаёт Higher Highs (HH) и Higher Lows (HL). "
            "Каждый откат выше предыдущего минимума — структура сильна.\n"
            "📉 *Медвежий тренд* — Lower Lows (LL) и Lower Highs (LH). "
            "Продавцы контролируют рынок.\n\n"
            "*Ключевые концепции:*\n\n"
            "🔸 *BOS (Break of Structure)* — пробой экстремума *по тренду*. "
            "В бычьем тренде: пробой предыдущего HH = BOS = структура продолжается. "
            "Это не сигнал для входа, это подтверждение тренда.\n\n"
            "🔸 *CHoCH (Change of Character)* — пробой экстремума *против тренда*. "
            "В бычьем тренде: если цена пробивает последний HL — это CHoCH, "
            "возможная смена тренда. Именно здесь SM начинает набор позиции в другую сторону.\n\n"
            "🔸 *MSS (Market Structure Shift)* — то же что CHoCH, но термин ICT. "
            "Используется взаимозаменяемо.\n\n"
            "*Внутренняя vs. Внешняя структура:*\n"
            "HTF (H4) структура — внешняя (defines bias). "
            "LTF (M15/M5) структура — внутренняя (defines entry).\n\n"
            "📌 *Правило SMC:* торгуй только по direction HTF структуры. "
            "CHoCH на M5 в сторону HTF тренда = твой триггер для входа."
        ),
        "video": "https://www.youtube.com/watch?v=mqBR-DRQT_o&t=592s",
    },
    "inducement": {
        "title": "🪤 Inducement (Ловушка для толпы)",
        "text": "Inducement — видимый уровень, который создаётся специально для сбора стопов толпы.",
        "article": (
            "*🪤 Inducement — Ловушка для Розничных Трейдеров*\n\n"
            "Inducement (IDM) — один из самых мощных концептов SMC. "
            "Это *намеренно созданный уровень* (обычно в форме очевидного хая или лоя), "
            "который привлекает розничных трейдеров входить или ставить стопы, "
            "после чего SM выбивает эти стопы (sweep) и идёт в противоположном направлении.\n\n"
            "*Как выглядит Inducement?*\n"
            "В ходе коррекционного движения цена формирует очевидный максимум или минимум. "
            "Розничные трейдеры видят этот уровень как 'поддержку/сопротивление' и:\n"
            "• Ставят стоп-лоссы за этим уровнем\n"
            "• Открывают позиции в направлении 'очевидного' пробоя\n\n"
            "*Механизм работы:*\n"
            "1️⃣ SM формирует IDM (подсадку) — небольшой локальный экстремум\n"
            "2️⃣ Толпа реагирует — стопы и ордера накапливаются за уровнем\n"
            "3️⃣ Sweep — SM проводит цену через IDM, собирая ликвидность\n"
            "4️⃣ Разворот — SM разворачивает цену и идёт в противоположную сторону\n\n"
            "*Как использовать IDM в трейдинге?*\n"
            "• Видишь очевидный уровень после коррекции в тренде — это IDM\n"
            "• Жди sweep (ложный пробой) этого уровня\n"
            "• После sweep + CHoCH на LTF — ищи вход в сторону основного HTF тренда\n\n"
            "📌 *Золотое правило:* не входи В сторону sweep. Входи ПОСЛЕ sweep "
            "— в противоположную сторону, когда SM уже забрал ликвидность.\n\n"
            "🎯 IDM + Sweep + CHoCH + OB/FVG = один из лучших сетапов в SMC"
        ),
        "video": "https://www.youtube.com/watch?v=mqBR-DRQT_o&t=1323s",
    },
    "liquidity": {
        "title": "💧 Ликвидность (Liquidity)",
        "text": "BSL — над максимумами. SSL — под минимумами. Equal H/L — видимые уровни ликвидности.",
        "article": (
            "*💧 Ликвидность — Топливо Smart Money*\n\n"
            "Ликвидность — это накопленные ордера (стоп-лоссы и отложенные ордера) на определённых "
            "ценовых уровнях. Smart Money *нуждается* в ликвидности для входа в позицию: "
            "чтобы купить 1 000 лотов, нужно столько же продавцов.\n\n"
            "*Типы ликвидности:*\n\n"
            "🟢 *BSL (Buy-Side Liquidity)* — ликвидность над максимумами. "
            "Здесь стоят стоп-лоссы продавцов и отложенные Buy Stop ордера трейдеров, "
            "ожидающих пробоя вверх. SM придёт сюда, чтобы *продать*.\n\n"
            "🔴 *SSL (Sell-Side Liquidity)* — ликвидность под минимумами. "
            "Стоп-лоссы покупателей и Sell Stop ордера. SM придёт сюда, чтобы *купить*.\n\n"
            "⚡ *Equal Highs / Equal Lows* — два или более максимума/минимума на одном уровне. "
            "Это *очень видимая* ликвидность — трейдеры массово ставят ордера за эти уровни. "
            "SM гарантированно придёт за ней.\n\n"
            "*Как Smart Money забирает ликвидность:*\n"
            "Sweep — ложный пробой: цена кратковременно выходит за уровень ликвидности, "
            "срабатывают стопы (сделки исполняются), после чего цена разворачивается.\n\n"
            "*Источники ликвидности (по приоритету):*\n"
            "1. Дневные/недельные High & Low\n"
            "2. Предыдущие сессионные экстремумы (Asia High/Low)\n"
            "3. Equal Highs/Lows\n"
            "4. Old Highs/Lows (экстремумы прошлого)\n\n"
            "📌 *Правило:* следи за пулами ликвидности как за целями движения цены. "
            "Если выше есть BSL — цена, скорее всего, придёт за ней прежде чем развернуться вниз."
        ),
        "video": "https://www.youtube.com/watch?v=mqBR-DRQT_o&t=278s",
    },
    "liquidity_pools": {
        "title": "🌊 Пулы ликвидности",
        "text": "Пулы: дневные/недельные экстремумы, Asia H/L, Equal H/L. Цена ходит от пула к пулу.",
        "article": (
            "*🌊 Пулы Ликвидности — Дорожная карта цены*\n\n"
            "Пулы ликвидности (Liquidity Pools) — это конкретные ценовые зоны, где накоплено "
            "максимальное количество ордеров. Понимание их расположения позволяет *предсказывать* "
            "движение цены, потому что SM всегда ведёт рынок от одного пула к другому.\n\n"
            "*Основные пулы ликвидности:*\n\n"
            "📅 *Недельные пулы* — предыдущий недельный максимум (PWH) и минимум (PWL). "
            "Самые мощные уровни. Разворот или пробой здесь = крупное движение.\n\n"
            "📅 *Дневные пулы* — предыдущий дневной максимум (PDH) и минимум (PDL). "
            "Часто служат первой целью внутридневного движения.\n\n"
            "🌙 *Азиатский пул* — Asia High (AH) и Asia Low (AL). "
            "Формируются во время азиатской сессии (02:00–06:00 UTC+3). "
            "Лондон почти всегда делает sweep одной из сторон.\n\n"
            "⚡ *Equal Highs/Lows* — визуально привлекательные уровни. "
            "Розничные трейдеры видят 'двойную вершину/дно' — это просто скопление ликвидности.\n\n"
            "*Как строить карту ликвидности:*\n"
            "1. Открой D1 — отметь PDH, PDL, PWH, PWL\n"
            "2. Добавь H1/M15 — найди Equal Highs/Lows\n"
            "3. Отметь Asia High/Low\n"
            "4. Расставь приоритеты по значимости\n\n"
            "*Алгоритм торговли:*\n"
            "SM забрал SSL (под минимумами) → разворот → цель BSL (над максимумами). "
            "Вход: на CHoCH после sweep SSL + OB/FVG на LTF.\n\n"
            "📌 *Цена — это река.* Она течёт от пула к пулу, как вода между водоёмами. "
            "Твоя задача — знать, к какому водоёму она течёт сейчас."
        ),
        "video": "https://www.youtube.com/watch?v=mqBR-DRQT_o&t=1323s",
    },
    "order_blocks": {
        "title": "📦 Order Blocks (OB)",
        "text": "Бычий OB — последняя медвежья свеча перед BOS вверх. Медвежий OB — наоборот.",
        "article": (
            "*📦 Order Blocks — Следы Институциональных Ордеров*\n\n"
            "Order Block (OB) — это *зона*, где Smart Money набирал крупную позицию. "
            "Это последняя противоположная свеча *перед сильным импульсом* с BOS. "
            "Цена часто возвращается в OB, чтобы SM мог добрать позицию или частично зафиксировать прибыль.\n\n"
            "*Бычий Order Block:*\n"
            "Последняя *медвежья* свеча (или группа свечей) *перед* восходящим импульсом с BOS. "
            "Зона OB = от Low до High этой медвежьей свечи (или тела). "
            "Когда цена откатится в эту зону — ищем покупки.\n\n"
            "*Медвежий Order Block:*\n"
            "Последняя *бычья* свеча перед нисходящим импульсом с BOS. "
            "Зона = от High до Low. Ищем продажи при ретесте.\n\n"
            "*Признаки сильного OB:*\n"
            "✅ Перед OB есть *sweep* уровня ликвидности\n"
            "✅ Импульс из OB создаёт *BOS* или *CHoCH*\n"
            "✅ OB находится в *Discount* (для бычьего) или *Premium* (для медвежьего)\n"
            "✅ OB совпадает с *FVG* — зона становится OB+FVG\n"
            "✅ OB формируется в *Kill Zone* (Лондон/NY)\n\n"
            "*Как торговать OB:*\n"
            "1. Определи HTF тренд и bias\n"
            "2. Найди OB после sweep ликвидности на HTF\n"
            "3. Жди ретеста OB\n"
            "4. На LTF (M5) дождись CHoCH/MSS\n"
            "5. Вход с SL за OB, TP — следующий пул ликвидности\n\n"
            "*Типы OB:*\n"
            "• Классический OB (одна свеча)\n"
            "• Breaker Block (OB, пробитый ценой — меняет роль)\n"
            "• Mitigation Block (OB, не пробитый — отработал)\n\n"
            "📌 OB без sweep ликвидности перед ним = слабый OB. "
            "Сначала sweep → потом OB → потом вход."
        ),
        "video": "https://www.youtube.com/watch?v=mqBR-DRQT_o&t=1741s",
    },
    "fvg": {
        "title": "⚡ Fair Value Gap (FVG)",
        "text": "FVG — имбаланс между тенями свечей 1 и 3 при импульсе. Цена часто возвращается заполнить FVG.",
        "article": (
            "*⚡ Fair Value Gap (FVG) — Имбаланс цены*\n\n"
            "FVG (Fair Value Gap) или IFVG (Imbalance) — это *зазор между тенями* трёх последовательных свечей, "
            "возникающий при сильном импульсном движении, когда рынок двигается так быстро, "
            "что не заполняет все ценовые уровни.\n\n"
            "*Как определить FVG:*\n"
            "Три свечи: 1️⃣ 2️⃣ 3️⃣\n"
            "• *Бычий FVG*: Low свечи 3 > High свечи 1 → имбаланс между ними\n"
            "• *Медвежий FVG*: High свечи 3 < Low свечи 1 → имбаланс сверху\n\n"
            "*Почему цена возвращается в FVG?*\n"
            "Рынок стремится к эффективности. FVG — это область, где не было двусторонней торговли. "
            "SM использует возврат в FVG для добора позиции или фиксации прибыли, "
            "а розничные трейдеры создают ликвидность для их ордеров.\n\n"
            "*Типы FVG:*\n"
            "• *FVG на откате* — цена возвращается для доработки, затем продолжает движение (торговый FVG)\n"
            "• *FVG на сломе структуры* — образуется при CHoCH/BOS — очень сильная зона\n"
            "• *OB + FVG* — когда FVG совпадает с OB — максимальная зона интереса\n\n"
            "*Признаки сильного FVG:*\n"
            "✅ Создан импульсом с BOS/CHoCH\n"
            "✅ Находится в Discount/Premium зоне\n"
            "✅ Предшествует sweep ликвидности\n"
            "✅ Совпадает с OB (OBFVG)\n\n"
            "*Алгоритм входа через FVG:*\n"
            "1. Sweep SSL на H1 → CHoCH вверх\n"
            "2. Откат цены в FVG на M15/M5\n"
            "3. Реакция (бычья свеча, смена структуры M1)\n"
            "4. Вход по рынку / лимитом в FVG, SL под FVG\n\n"
            "📌 *50% FVG* — часто используемая точка входа внутри зоны FVG. "
            "Цена приходит к середине FVG и разворачивается."
        ),
        "video": "https://www.youtube.com/watch?v=mqBR-DRQT_o&t=1621s",
    },
    "breaker_blocks": {
        "title": "💥 Breaker Block",
        "text": "Breaker — бывший OB, пробитый ценой. Становится зоной противоположного направления.",
        "article": (
            "*💥 Breaker Block — Сломанный Order Block*\n\n"
            "Breaker Block — это *бывший OB*, который был пробит ценой и *изменил свою роль*. "
            "Если бычий OB был пробит вниз (цена закрылась ниже его) — он становится *медвежьим Breaker Block*. "
            "При ретесте этой зоны сверху ищем продажи.\n\n"
            "*Алгоритм формирования Breaker:*\n\n"
            "1️⃣ Формируется *бычий OB* (последняя медвежья свеча перед импульсом вверх)\n"
            "2️⃣ Цена создаёт HH (Higher High) — структура бычья\n"
            "3️⃣ Цена разворачивается и *пробивает этот OB вниз* (BOS вниз = CHoCH)\n"
            "4️⃣ OB теперь стал *Breaker Block* — медвежьим\n"
            "5️⃣ При ретесте зоны сверху → продажи с SL выше Breaker\n\n"
            "*Медвежий → Бычий Breaker:*\n"
            "Медвежий OB пробивается вверх → становится *бычьим Breaker*. "
            "При ретесте снизу → покупки.\n\n"
            "*Почему Breaker мощная зона?*\n"
            "• Здесь стоят стопы тех, кто торговал с оригинального OB (они открыли сделку и теперь в убытке)\n"
            "• SM использует эти стопы как ликвидность для своих ордеров\n"
            "• Breaker — подтверждённый shift структуры\n\n"
            "*Отличие от Mitigation Block:*\n"
            "— Breaker: OB *пробит* → новая зона противоположного направления\n"
            "— Mitigation: OB *не пробит* → та же зона, то же направление (SM просто доработал)\n\n"
            "📌 *Лучший сетап Breaker:*\n"
            "HTF BOS → Breaker Block на LTF → ретест + CHoCH → вход. "
            "Цель — следующий пул ликвидности."
        ),
        "video": "https://www.youtube.com/watch?v=mqBR-DRQT_o&t=2101s",
    },
    "mitigation_blocks": {
        "title": "🔄 Mitigation Block",
        "text": "Mitigation — возврат к OB для добора позиции SM. OB не пробивается — направление то же.",
        "article": (
            "*🔄 Mitigation Block — Дополнение позиции*\n\n"
            "Mitigation Block — это OB, к которому цена возвращается, *не пробивая его*, "
            "позволяя Smart Money *доработать* (митигировать) свою позицию по лучшей цене.\n\n"
            "*Что значит митигировать?*\n"
            "SM набрал крупную позицию в OB. Позиция открыта, но цена не пошла сразу — "
            "сначала небольшой ретест. SM добирает позицию в том же направлении по чуть лучшей цене. "
            "После этого рынок резко движется к цели.\n\n"
            "*Характеристики Mitigation Block:*\n"
            "✅ Цена возвращается в зону OB\n"
            "✅ Не закрывается *за* OB (в отличие от Breaker)\n"
            "✅ Формируется реакция (bullish/bearish candle) точно в зоне\n"
            "✅ После реакции — продолжение тренда\n\n"
            "*Как определить Mitigation vs простой OB:*\n"
            "После первого импульса из OB цена частично откатывает *в зону* OB:\n"
            "— Если откат не пробивает хай/лоу первоначального OB → *Mitigation*\n"
            "— Если откат пробивает → *Breaker* (смена роли)\n\n"
            "*Торговля Mitigation Block:*\n"
            "1. Определи HTF тренд (бычий)\n"
            "2. После BOS на H1 жди откат к OB\n"
            "3. Цена заходит в OB, но не пробивает его снизу\n"
            "4. На M5 дождись бычьей реакции + CHoCH\n"
            "5. Вход с SL ниже OB, TP — следующий BSL\n\n"
            "*Цепочка:* OB → импульс → ретест (Mitigation) → продолжение → цель.\n\n"
            "📌 Mitigation + Kill Zone + Premium/Discount = точный вход с минимальным риском."
        ),
        "video": "https://www.youtube.com/watch?v=mqBR-DRQT_o&t=2270s",
    },
    "premium_discount": {
        "title": "📊 Premium & Discount",
        "text": "Ниже 50% диапазона — Discount (покупки). Выше 50% — Premium (продажи).",
        "article": (
            "*📊 Premium & Discount — Где покупать и продавать*\n\n"
            "Концепция Premium & Discount — это *фильтр*, который помогает определить, "
            "находится ли цена в *зоне покупки* (Discount) или *продажи* (Premium).\n\n"
            "*Как определить Premium & Discount:*\n"
            "1. Найди значимый Swing Low и Swing High на HTF\n"
            "2. Проведи уровень 50% (середина диапазона — Equilibrium)\n"
            "3. Ниже 50% = *Discount* (выгодная зона для покупок)\n"
            "4. Выше 50% = *Premium* (дорогая зона — зона продаж SM)\n\n"
            "*Уровни Фибоначчи в Premium/Discount:*\n"
            "• 0% — Swing Low (Discount старт)\n"
            "• 23.6% / 38.2% — мелкие коррекции (слабый Discount)\n"
            "• 50% — Equilibrium\n"
            "• 61.8% / 70.5% / 78.6% — *OTE зона* (самый сильный Discount)\n"
            "• 100% — Swing High (Premium максимум)\n\n"
            "*Smart Money логика:*\n"
            "SM покупает в *Discount* (накапливает дёшево) и продаёт в *Premium* (распределяет дорого). "
            "Розничные трейдеры делают наоборот — покупают на хаях в Premium (FOMO).\n\n"
            "*OTE (Optimal Trade Entry):*\n"
            "Диапазон 62–79% коррекции импульса — лучшее место для входа. "
            "OTE + OB + Kill Zone = идеальный сетап.\n\n"
            "*Как использовать на практике:*\n"
            "• Бычий тренд на H4 → ждём откат в Discount (ниже 50%)\n"
            "• В Discount находим OB/FVG → вход на покупку\n"
            "• Продавать в Premium против бычьего HTF тренда — опасно\n\n"
            "📌 *Никогда не покупай в Premium и не продавай в Discount* — "
            "ты буквально торгуешь против SM."
        ),
        "video": "https://www.youtube.com/watch?v=mqBR-DRQT_o&t=3439s",
    },
    "killzones": {
        "title": "⏰ Kill Zones",
        "text": "Азия (02–06) — диапазон. Лондон (10–13) — sweep Asia. NY (15:30–18) — основное движение.",
        "article": (
            "*⏰ Kill Zones — Лучшее время для торговли*\n\n"
            "Kill Zones — это временные *окна*, во время которых Smart Money наиболее активен. "
            "Торговля вне Kill Zones значительно снижает вероятность успеха.\n\n"
            "*Азиатская сессия (02:00–06:00 UTC+3):*\n"
            "Рынок Forex находится в низкой волатильности. Формируется *Asia Range* — "
            "узкий ценовой диапазон. Этот диапазон критически важен: его High и Low — "
            "это уровни ликвидности, за которыми придёт Лондон или NY.\n\n"
            "*Лондонская Kill Zone (10:00–13:00 UTC+3):*\n"
            "🔥 Самая активная Kill Zone. Лондонский открытие почти всегда делает *sweep* "
            "одной из сторон Asia Range, собирая ликвидность. "
            "После sweep + CHoCH — начинается настоящее движение дня. "
            "Это лучшее время для поиска сетапов.\n\n"
            "*Нью-Йоркская Kill Zone (15:30–18:00 UTC+3):*\n"
            "🔥 Второй по силе период. NY часто продолжает или реверсирует Лондонский тренд. "
            "Самые сильные движения дня случаются здесь — особенно при выходе новостей.\n\n"
            "*Торговые правила Kill Zones:*\n"
            "✅ Ищи сетапы только в Kill Zones\n"
            "✅ Если Kill Zone прошла и сетапа нет — *не входи*\n"
            "✅ Лучший сетап Лондона: sweep Asia High/Low → CHoCH → OB/FVG → вход\n"
            "✅ Лучший NY: продолжение Лондонского движения к ближайшему пулу\n\n"
            "*Почему важно время?*\n"
            "Вне Kill Zones рынок часто хаотичен, спреды выше, объёмы низкие. "
            "SM не активен = нет смысла торговать.\n\n"
            "📌 *Дисциплина времени* — одно из главных преимуществ SMC трейдера. "
            "2 часа активной торговли в Kill Zone > 8 часов случайной торговли."
        ),
        "video": "https://www.youtube.com/watch?v=mqBR-DRQT_o&t=4356s",
    },
    "ote": {
        "title": "🎯 OTE — Optimal Trade Entry",
        "text": "OTE — откат 62–79% импульса по Фибо. OTE + OB + Kill Zone = сильный сетап.",
        "article": (
            "*🎯 OTE — Optimal Trade Entry*\n\n"
            "OTE (Optimal Trade Entry) — концепция ICT, определяющая *лучшую зону* для входа "
            "в позицию после импульсного движения. Это диапазон *62–79% коррекции* от импульса, "
            "соответствующий уровням Фибоначчи 61.8%, 70.5%, 78.6%.\n\n"
            "*Логика OTE:*\n"
            "SM набирает позицию по возможно лучшей цене. После создания импульса (с BOS/CHoCH) "
            "они позволяют цене откатиться глубже, чем ожидает розничный трейдер, "
            "чтобы набрать максимальный объём по минимальным ценам (в бычьем сценарии).\n\n"
            "*Как строить OTE:*\n"
            "1. Найди значимый импульс с BOS (начало — swing low, конец — swing high)\n"
            "2. Примени Фибоначчи от Low до High (для бычьего)\n"
            "3. OTE зона: 61.8% – 78.6% коррекции\n"
            "4. Ищи внутри OTE: OB, FVG, реакцию цены\n\n"
            "*OTE в Kill Zone:*\n"
            "Лучший вариант — OTE формируется именно во время Лондонской или NY Kill Zone. "
            "Это значит: откат пришёл в OTE зону в 10:00–13:00 → идеальный вход.\n\n"
            "*Признаки подтверждения входа в OTE:*\n"
            "✅ OTE + OB (или FVG) в одной зоне\n"
            "✅ Kill Zone активна\n"
            "✅ CHoCH/MSS на LTF (M5)\n"
            "✅ Sweep ликвидности перед входом\n"
            "✅ HTF тренд в сторону входа\n\n"
            "*R:R при OTE входе:*\n"
            "SL: ниже последнего лоя (за зоной OTE)\n"
            "TP1: 50% (Equilibrium), TP2: Swing High (BSL), TP3: следующий пул\n"
            "R:R обычно получается 1:3 – 1:7\n\n"
            "📌 OTE — не просто уровень, а *состояние рынка*: "
            "цена вернулась за SM-позицией, и теперь они готовы двигаться."
        ),
        "video": "https://www.youtube.com/watch?v=6gYm0GH8LeQ&t=520s",
    },
    "amd_model": {
        "title": "🔄 AMD Model",
        "text": "Accumulation → Manipulation → Distribution. Азия — накопление, Лондон — манипуляция, NY — движение.",
        "article": (
            "*🔄 AMD Model — Алгоритм SM на каждый день*\n\n"
            "AMD Model (Accumulation → Manipulation → Distribution) — фундаментальная модель поведения "
            "Smart Money, которая повторяется ежедневно и на всех таймфреймах.\n\n"
            "*Фаза 1: Accumulation (Накопление)*\n"
            "🕰 Азиатская сессия (02:00–06:00)\n"
            "SM тихо набирает позицию в узком ценовом диапазоне. "
            "Рынок кажется скучным и без направления. Это не хаос — это *замысел*. "
            "Asia Range формирует ключевые уровни ликвидности для следующих фаз.\n\n"
            "*Фаза 2: Manipulation (Манипуляция)*\n"
            "🕰 Лондонская сессия (10:00–13:00)\n"
            "SM делает *Judas Swing* — ложное движение в *противоположную* от дневного тренда сторону. "
            "Если дневной тренд бычий → Лондон сначала делает снижение, sweep SSL, "
            "выбивает стопы и набирает полную позицию на покупку. Толпа входит в продажи — "
            "именно тогда SM разворачивается.\n\n"
            "*Фаза 3: Distribution (Распределение/движение)*\n"
            "🕰 Нью-Йоркская сессия (15:30–18:00)\n"
            "SM начинает *настоящее* движение дня. Цена резко движется к цели — пулу ликвидности. "
            "Розничные трейдеры, видя движение, входят поздно (FOMO). SM начинает фиксировать прибыль, "
            "распределяя позицию на этих покупателей/продавцов.\n\n"
            "*AMD в числах и сигналах:*\n"
            "• Accumulation: Asia Range < 50 пипс → сжатие = энергия\n"
            "• Manipulation: Judas Swing = sweep + CHoCH (разворот)\n"
            "• Distribution: движение > 50% от Manipulation\n\n"
            "📌 *AMD — это не теория.* Открой любой дневной график и найди: "
            "узкий Азиатский диапазон → ложное Лондонское движение → мощный NY тренд. "
            "Это происходит 70-80% торговых дней."
        ),
        "video": "https://www.youtube.com/watch?v=mqBR-DRQT_o&t=3961s",
    },
    "power_of_three": {
        "title": "3️⃣ Power of Three (Po3)",
        "text": "Po3: Asia Range → Judas Swing (ложный пробой) → настоящее движение дня.",
        "article": (
            "*3️⃣ Power of Three (Po3) — Трёхфазный Дневной Цикл*\n\n"
            "Power of Three — концепция ICT (Inner Circle Trader), описывающая три обязательные "
            "фазы дневного ценового цикла: *Opening Range → Judas Swing → True Expansion*.\n\n"
            "*Фаза 1: Opening Range (Азия)*\n"
            "Формируется Asia Range — ценовой диапазон ночного спокойствия. "
            "Его High и Low — ключевые уровни ликвидности. SM аккумулирует позицию.\n\n"
            "*Фаза 2: Judas Swing (Лондон)*\n"
            "Judas = предатель. Цена делает *ложное движение* против направления дня:\n"
            "• Если день бычий → Judas Swing идёт ВНИЗ, sweep Asia Low (SSL)\n"
            "• Если день медвежий → Judas Swing идёт ВВЕРХ, sweep Asia High (BSL)\n"
            "Это манипуляция: толпа входит в ложном направлении, SM набирает позицию.\n\n"
            "*Фаза 3: True Daily Expansion (NY)*\n"
            "Настоящее движение дня — мощный тренд к основному пулу ликвидности. "
            "Именно здесь SM реализует прибыль.\n\n"
            "*Как определить направление Po3 (daily bias):*\n"
            "1. D1 тренд (HH/HL = бычий → bias покупки)\n"
            "2. PDH/PDL — что ближе и более значимо?\n"
            "3. Какой пул ликвидности SM соберёт сегодня?\n\n"
            "*Практический алгоритм Po3:*\n"
            "• 08:00 — определяю Asia Range и bias\n"
            "• 10:00–11:00 — жду Judas Swing (sweep протвоположного направления)\n"
            "• После CHoCH → вход в направлении daily bias\n"
            "• TP = Daily Liquidity Pool (PDH/PDL или выше)\n\n"
            "📌 Po3 + AMD — это одно и то же. ICT использует оба термина взаимозаменяемо. "
            "Понимание этого цикла меняет то, как ты смотришь на каждый торговый день."
        ),
        "video": "https://www.youtube.com/watch?v=6gYm0GH8LeQ&t=300s",
    },
    "market_maker_model": {
        "title": "🏛 Market Maker Model",
        "text": "Набор → Sweep BSL/SSL → Разворот (CHoCH) → Движение к цели.",
        "article": (
            "*🏛 Market Maker Model (MMM) — Полный цикл SM*\n\n"
            "Market Maker Model — наиболее полная модель поведения маркет-мейкера "
            "(крупного институционального участника), объединяющая все концепции SMC в единый алгоритм.\n\n"
            "*4 стадии MMM:*\n\n"
            "🔵 *Стадия 1 — Accumulation (Набор позиции)*\n"
            "MM тихо накапливает позицию в широком диапазоне. Цена колеблется вверх-вниз без тренда. "
            "Розничные трейдеры торгуют 'уровни поддержки/сопротивления' и теряют деньги.\n\n"
            "🟡 *Стадия 2 — Manipulation (Sweep BSL или SSL)*\n"
            "MM делает ложный выброс за ближайший пул ликвидности. "
            "Sweeps срабатывают стопы, а ордера розничных трейдеров заполняют MM позицию. "
            "После sweep цена резко разворачивается.\n\n"
            "🟢 *Стадия 3 — Smart Money Reversal (CHoCH)*\n"
            "Слом структуры подтверждает разворот. На LTF (M5/M15) видим CHoCH/MSS. "
            "Это триггер для входа. MM двигает цену в направлении Distribution.\n\n"
            "🟣 *Стадия 4 — Distribution (Движение к цели)*\n"
            "MM реализует прибыль, двигая цену к противоположному пулу ликвидности. "
            "По пути создаются новые BOS, FVG, OB для более мелких сделок.\n\n"
            "*Полная цепочка сигналов для Long:*\n"
            "Бычий D1 → Ждём Sweep SSL → CHoCH вверх на H1 → OB/FVG на M15 в Kill Zone → Вход\n\n"
            "*Почему MMM работает:*\n"
            "Потому что это не технический анализ — это *понимание потока ордеров*. "
            "MM нужна ликвидность для входа/выхода. Его действия всегда оставляют следы на графике.\n\n"
            "📌 Масштаб MMM: на D1 цикл = недели. На H1 = дни. На M15 = часы. Везде одна логика."
        ),
        "video": "https://www.youtube.com/watch?v=6gYm0GH8LeQ",
    },
    "ict_2022_model": {
        "title": "📈 ICT 2022 Mentorship Model",
        "text": "HTF тренд → Kill Zone → Sweep SSL/BSL → CHoCH → FVG/OB на M5 → Вход.",
        "article": (
            "*📈 ICT 2022 Mentorship Model — Пошаговый Алгоритм*\n\n"
            "ICT 2022 Mentorship Model — наиболее проработанный алгоритм Inner Circle Trader, "
            "объединяющий всю методологию в чёткий пошаговый план для торговли.\n\n"
            "*Алгоритм для Long (покупки):*\n\n"
            "1️⃣ *HTF Bias* (D1/H4): определяем бычий тренд (HH/HL). Только покупки.\n\n"
            "2️⃣ *Kill Zone*: входим в режим наблюдения в 10:00–13:00 (Лондон) или 15:30–18:00 (NY).\n\n"
            "3️⃣ *Sweep SSL*: ждём, пока цена выбьет ближайшие минимумы (SSL). "
            "Это манипуляция — Judas Swing вниз. Stoploss толпы срабатывает.\n\n"
            "4️⃣ *CHoCH/MSS на H1*: после sweep SSL цена разворачивается и делает CHoCH вверх — "
            "слом медвежьей структуры. Подтверждение разворота.\n\n"
            "5️⃣ *Ищем POI на M5/M15*: находим бычий FVG или OB в зоне CHoCH. "
            "Это наша точка входа.\n\n"
            "6️⃣ *Вход*: ждём возврата цены к POI (OB/FVG). "
            "Лимитный ордер или рыночный при повторном CHoCH на M1.\n\n"
            "7️⃣ *SL*: ниже sweep SSL (под пробитыми минимумами). "
            "Если SM ушёл ещё ниже — сигнал был ложный.\n\n"
            "8️⃣ *TP*: BSL (над ближайшими максимумами). TP2 — HTF OB выше. "
            "R:R минимум 1:3.\n\n"
            "*Алгоритм для Short — зеркально:*\n"
            "Медвежий HTF → Kill Zone → Sweep BSL → CHoCH вниз → Медвежий OB/FVG → Продажа\n\n"
            "📌 Этот алгоритм — полная система. Если все 6 шагов совпадают — "
            "это высоковероятная сделка. Если нет хотя бы одного — лучше пропустить."
        ),
        "video": "https://rutube.ru/video/e3cd0f739cb02101c4b694f7fbf42942/",
    },
    "session_sweep_model": {
        "title": "🌊 Session Sweep Model",
        "text": "Азия задаёт диапазон. Лондон делает sweep одной стороны. Движение идёт в противоположную.",
        "article": (
            "*🌊 Session Sweep Model — Торговля на сессиях*\n\n"
            "Session Sweep Model — простая и эффективная модель, основанная на поведении цены "
            "между торговыми сессиями. Центральная идея: Лондон *почти всегда* делает sweep "
            "одной из сторон Asia Range, после чего движется в противоположном направлении.\n\n"
            "*Как работает модель:*\n\n"
            "🌙 *Азия (02:00–06:00 UTC+3)* — формируется Asia Range.\n"
            "Отметь Asia High (AH) и Asia Low (AL). Это ключевые уровни ликвидности дня.\n\n"
            "☀️ *Лондон (10:00–13:00 UTC+3)* — sweep одной стороны.\n"
            "Вариант А: *Sweep Asia High* → разворот вниз → торгуем Short\n"
            "Вариант Б: *Sweep Asia Low* → разворот вверх → торгуем Long\n\n"
            "🌆 *NY (15:30–18:00 UTC+3)* — продолжение или разворот Лондона.\n\n"
            "*Правила входа:*\n"
            "1. Определи Asia High и Asia Low\n"
            "2. В Лондонскую Kill Zone жди sweep одной стороны\n"
            "3. После sweep + CHoCH на M15/M5 → вход в противоположном направлении\n"
            "4. SL — за swept уровнем (выше AH или ниже AL)\n"
            "5. TP — противоположная сторона Asia Range → PDH/PDL\n\n"
            "*Статистика модели:*\n"
            "По данным ICT и независимых трейдеров, sweep Asia Range в Лондон "
            "происходит в ~70-75% торговых дней на Forex.\n\n"
            "*Дополнительные условия для сильного сигнала:*\n"
            "✅ Asia Range узкий (менее 30-50 пипс)\n"
            "✅ Sweep совпадает с HTF уровнем (OB, FVG, EQH/EQL)\n"
            "✅ Направление совпадает с Daily Bias\n\n"
            "📌 Session Sweep Model — отличная *первая стратегия* для новичков в SMC. "
            "Чёткие правила, понятные уровни, высокая повторяемость."
        ),
        "video": "https://www.youtube.com/watch?v=mqBR-DRQT_o&t=3961s",
    },
    "risk_management": {
        "title": "💰 Риск-менеджмент",
        "text": "Риск 0.5–1% на сделку. R:R минимум 1:2, цель 1:3+. Без SL = слив.",
        "article": (
            "*💰 Риск-менеджмент — Защита Капитала*\n\n"
            "Риск-менеджмент — единственное, что отделяет успешного трейдера от слитого депозита. "
            "Даже идеальная стратегия SMC не спасёт, если ты не управляешь рисками.\n\n"
            "*Базовые правила риска:*\n\n"
            "📉 *Риск на сделку:*\n"
            "• Новичок (< 6 мес): 0.25–0.5% депозита\n"
            "• Продвинутый (6–18 мес): 0.5–1%\n"
            "• Профессионал: 1–2% (только с proven edge)\n"
            "❌ Никогда > 2% на одну сделку\n\n"
            "📊 *R:R (Risk:Reward Ratio):*\n"
            "• Минимально приемлемый: 1:2 (за каждый $1 риска — $2 потенциала)\n"
            "• Цель SMC трейдера: 1:3 – 1:5\n"
            "• При хорошем сетапе (OB + FVG + Kill Zone): 1:5 – 1:10\n\n"
            "*Математика выживания:*\n"
            "При R:R 1:3 и WR 40% → ты В ПЛЮСЕ:\n"
            "40 побед × 3 = 120 единиц прибыли\n"
            "60 поражений × 1 = 60 единиц убытка\n"
            "Чистая прибыль: +60 единиц\n\n"
            "*Правила работы со сделкой:*\n"
            "✅ Всегда устанавливай SL *до* входа\n"
            "✅ Не двигай SL в убыток\n"
            "✅ Частичная фиксация: 50% позиции на TP1 (1:1), остаток до TP2\n"
            "✅ Break-even: переноси SL в безубыток после достижения 1:1\n"
            "✅ Лимит сделок в день: максимум 2-3 сигнала\n\n"
            "*Максимальная просадка:*\n"
            "Дневная: -2% депозита → стоп торговля на сегодня\n"
            "Недельная: -5% → пауза, разбор ошибок\n\n"
            "📌 *Трейдинг — это марафон, не спринт.* При риске 1% и серии из 10 убытков подряд "
            "ты теряешь ~10% депозита. Это пережить можно. Потеря 50% — психологически разрушительна."
        ),
        "video": "https://www.youtube.com/watch?v=mqBR-DRQT_o&t=6495s",
    },
    "psychology": {
        "title": "🧠 Психология трейдера",
        "text": "FOMO, месть рынку, овертрейдинг — главные причины слива. Решения: правила, лимиты, дневник.",
        "article": (
            "*🧠 Психология трейдера — Главный враг внутри*\n\n"
            "Исследования показывают: 80% убытков розничных трейдеров связаны не с плохой стратегией, "
            "а с *психологическими ошибками*. Технические навыки — это 20% успеха. Психология — 80%.\n\n"
            "*Главные психологические ловушки:*\n\n"
            "😰 *FOMO (Fear of Missing Out)*\n"
            "Видишь сильное движение и входишь «на бегу» без сетапа. "
            "Результат: вход в Premium против тренда → убыток.\n"
            "Решение: если сигнал пропустил — ищи следующий. Рынок всегда даёт новые возможности.\n\n"
            "😡 *Revenge Trading (Месть рынку)*\n"
            "После убытка немедленно открываешь следующую сделку, чтобы «отыграться». "
            "Без анализа, без сетапа, с завышенным лотом.\n"
            "Решение: после убыточной сделки — 15 минут перерыв. Обязательно.\n\n"
            "🤦 *Overtrading (Овертрейдинг)*\n"
            "Торгуешь вне Kill Zones, на любое движение, без подтверждений.\n"
            "Решение: лимит — не более 2 сделок в день. Kill Zones только.\n\n"
            "😨 *Страх убытка — ранний выход*\n"
            "Фиксируешь прибыль слишком рано, не давая сделке достичь TP.\n"
            "Решение: установи TP заранее и не смотри на график после входа.\n\n"
            "*Инструменты психологической устойчивости:*\n\n"
            "📓 *Торговый дневник* — записывай каждую сделку: причина входа, скрин, результат, эмоции.\n"
            "📋 *Торговый план* — чёткие правила когда входить/не входить.\n"
            "🛑 *Стоп-правила* — максимальный убыток в день/неделю, после которого СТОП.\n"
            "🧘 *Медитация и режим* — сон, спорт, питание влияют на решения.\n\n"
            "📌 *Лучшие сделки приходят без эмоций.* Если ты взволнован, напуган или злой — "
            "закрой терминал. Рынок никуда не денется."
        ),
        "video": "https://www.youtube.com/watch?v=mqBR-DRQT_o&t=6878s",
    },
}


# ─────────────────────────────────────────────────────
# МОДУЛИ
# ─────────────────────────────────────────────────────
MODULES: List[Dict[str, Any]] = [
    {
        "key": "basics",
        "lesson_key": "what_is_smc",
        "title": "Модуль 1: Основы SMC и таймфреймы",
        "lessons": ["what_is_smc", "timeframes"],
        "homework": (
            "📌 *Домашка — Модуль 1:*\n\n"
            "Сделай Top-Down анализ (D1, H4, H1, M15) по одной паре.\n"
            "Опиши тренд на каждом ТФ и общий вывод."
        ),
    },
    {
        "key": "structure",
        "lesson_key": "market_structure",
        "title": "Модуль 2: Структура рынка и Inducement",
        "lessons": ["market_structure", "inducement"],
        "homework": (
            "📌 *Домашка — Модуль 2:*\n\n"
            "Найди примеры BOS, CHoCH и Inducement. Скрины + подписи."
        ),
    },
    {
        "key": "liquidity",
        "lesson_key": "liquidity",
        "title": "Модуль 3: Ликвидность и пулы",
        "lessons": ["liquidity", "liquidity_pools"],
        "homework": (
            "📌 *Домашка — Модуль 3:*\n\n"
            "Сделай карту ликвидности: BSL/SSL, Equal Highs/Lows, один sweep."
        ),
    },
    {
        "key": "poi",
        "lesson_key": "order_blocks",
        "title": "Модуль 4: Order Blocks и FVG",
        "lessons": ["order_blocks", "fvg"],
        "homework": (
            "📌 *Домашка — Модуль 4:*\n\n"
            "2 бычьих и 2 медвежьих OB + 3 FVG и их отработка."
        ),
    },
    {
        "key": "advanced_blocks",
        "lesson_key": "breaker_blocks",
        "title": "Модуль 5: Breaker и Mitigation Blocks",
        "lessons": ["breaker_blocks", "mitigation_blocks"],
        "homework": (
            "📌 *Домашка — Модуль 5:*\n\n"
            "Найди по одному примеру Breaker и Mitigation Block и опиши разницу."
        ),
    },
    {
        "key": "zones_sessions",
        "lesson_key": "premium_discount",
        "title": "Модуль 6: Зоны, OTE и Kill Zones",
        "lessons": ["premium_discount", "killzones", "ote"],
        "homework": (
            "📌 *Домашка — Модуль 6:*\n\n"
            "Разметь Premium/Discount, OTE и Kill Zones на одном активе."
        ),
    },
    {
        "key": "advanced_models",
        "lesson_key": "amd_model",
        "title": "Модуль 7: AMD, Po3, MMM",
        "lessons": ["amd_model", "power_of_three", "market_maker_model"],
        "homework": (
            "📌 *Домашка — Модуль 7:*\n\n"
            "Разбери 3 дня по AMD/Po3 (накопление, манипуляция, движение)."
        ),
    },
    {
        "key": "strategies",
        "lesson_key": "ict_2022_model",
        "title": "Модуль 8: Стратегии, риск, психология",
        "lessons": ["ict_2022_model", "session_sweep_model", "risk_management", "psychology"],
        "homework": (
            "📌 *Финал — Модуль 8:*\n\n"
            "Неделя демо-торговли по SMC с дневником сделок."
        ),
    },
]

# ─────────────────────────────────────────────────────
# КВИЗЫ
# ─────────────────────────────────────────────────────
QUIZZES: Dict[str, List[Dict[str, Any]]] = {
    "basics_quiz": [
        {
            "question": "Кто такие Smart Money?",
            "options": [
                ("Крупные институциональные игроки", True),
                ("Розничные трейдеры", False),
                ("Маркетинговые агентства", False),
                ("Криптоинфлюенсеры", False),
            ],
        },
        {
            "question": "С какого ТФ начинать Top-Down анализ?",
            "options": [
                ("С W1/D1", True),
                ("С M1", False),
                ("С H1", False),
                ("С любого — неважно", False),
            ],
        },
        {
            "question": "Какова главная цель методологии SMC?",
            "options": [
                ("Торговать вместе с институциональными игроками", True),
                ("Угадывать новости", False),
                ("Использовать RSI и MACD", False),
                ("Торговать против тренда", False),
            ],
        },
    ],
    "structure_quiz": [
        {
            "question": "Что такое BOS?",
            "options": [
                ("Пробой экстремума по направлению тренда", True),
                ("Любой gap на графике", False),
                ("Любой пробой уровня поддержки", False),
                ("Смена тренда", False),
            ],
        },
        {
            "question": "CHoCH — это...",
            "options": [
                ("Смена характера структуры, возможный разворот", True),
                ("Продолжение тренда", False),
                ("Открытие новой сессии", False),
                ("Fair Value Gap", False),
            ],
        },
        {
            "question": "Что означает Inducement?",
            "options": [
                ("Видимый уровень-ловушка для сбора стопов толпы", True),
                ("Сильный тренд", False),
                ("Уровень поддержки D1", False),
                ("Техника управления рисками", False),
            ],
        },
    ],
    "liquidity_quiz": [
        {
            "question": "BSL — это ликвидность...",
            "options": [
                ("Над максимумами (стопы продавцов)", True),
                ("Под минимумами", False),
                ("В середине дневного диапазона", False),
                ("На открытии рынка", False),
            ],
        },
        {
            "question": "Sweep — это...",
            "options": [
                ("Ложный пробой уровня ликвидности", True),
                ("Пробой с закреплением", False),
                ("Fair Value Gap", False),
                ("Двойная вершина", False),
            ],
        },
        {
            "question": "Что такое Equal Highs?",
            "options": [
                ("Два или более максимума на одном уровне — видимая ликвидность", True),
                ("Равные объёмы двух сессий", False),
                ("Уровень 50% по Фибо", False),
                ("Дневная средняя", False),
            ],
        },
    ],
    "poi_quiz": [
        {
            "question": "Бычий OB — это...",
            "options": [
                ("Последняя медвежья свеча перед импульсом вверх", True),
                ("Любая зелёная свеча", False),
                ("Любой минимум на графике", False),
                ("Уровень 50% по Фибо", False),
            ],
        },
        {
            "question": "FVG — это...",
            "options": [
                ("Имбаланс между тенями свечей 1 и 3 при импульсе", True),
                ("Уровень поддержки", False),
                ("Gap на открытии рынка", False),
                ("Любое большое тело свечи", False),
            ],
        },
        {
            "question": "OB + FVG в одной зоне — это...",
            "options": [
                ("Максимальная зона интереса (POI)", True),
                ("Слабый сигнал", False),
                ("Зона разворота без потенциала", False),
                ("Не имеет значения", False),
            ],
        },
    ],
    "advanced_blocks_quiz": [
        {
            "question": "Breaker Block появляется, когда...",
            "options": [
                ("Цена пробивает OB и он меняет роль на противоположную", True),
                ("Цена касается OB и отскакивает", False),
                ("Формируется новый FVG", False),
                ("Меняется тренд на D1", False),
            ],
        },
        {
            "question": "Mitigation Block — это OB, который...",
            "options": [
                ("Не пробит — цена митигировала его и продолжила тренд", True),
                ("Пробит ценой", False),
                ("Стал Breaker", False),
                ("Находится в Premium зоне", False),
            ],
        },
    ],
    "zones_quiz": [
        {
            "question": "Где Smart Money покупают?",
            "options": [
                ("В Discount зоне (ниже 50% диапазона)", True),
                ("В Premium зоне (выше 50%)", False),
                ("По новостям", False),
                ("Где угодно, если RSI перекуплен", False),
            ],
        },
        {
            "question": "OTE — это зона откатa...",
            "options": [
                ("62–79% от импульса (Фибо 61.8–78.6%)", True),
                ("0–23.6%", False),
                ("100–161.8%", False),
                ("Ровно 50%", False),
            ],
        },
        {
            "question": "Лучшая Kill Zone для сделки с Forex по SMC — это...",
            "options": [
                ("Лондонская (10:00–13:00 UTC+3)", True),
                ("Азиатская (02:00–06:00)", False),
                ("Ночь воскресенья", False),
                ("Пятница после 18:00", False),
            ],
        },
    ],
    "advanced_models_quiz": [
        {
            "question": "AMD расшифровывается как...",
            "options": [
                ("Accumulation, Manipulation, Distribution", True),
                ("Analysis, Market, Delivery", False),
                ("Ask, Mid, Demand", False),
                ("Average Market Deviation", False),
            ],
        },
        {
            "question": "Judas Swing в Po3 — это...",
            "options": [
                ("Ложное движение против дневного тренда для сбора ликвидности", True),
                ("Реальное движение дня", False),
                ("Азиатский диапазон", False),
                ("BOS на H4", False),
            ],
        },
    ],
    "strategies_quiz": [
        {
            "question": "В ICT 2022 модели для Long нужен...",
            "options": [
                ("Sweep SSL + CHoCH вверх + вход из FVG/OB", True),
                ("Любой пробой максимума", False),
                ("RSI < 30", False),
                ("Случайный вход по настроению", False),
            ],
        },
        {
            "question": "Оптимальный риск на сделку для новичка...",
            "options": [
                ("0.25–0.5% депозита", True),
                ("5–10% депозита", False),
                ("Сколько не жалко", False),
                ("Фиксированные $100", False),
            ],
        },
        {
            "question": "Минимальный R:R для SMC сделки...",
            "options": [
                ("1:2 (цель 1:3+)", True),
                ("1:0.5", False),
                ("Любой", False),
                ("1:1", False),
            ],
        },
    ],
}

# ─────────────────────────────────────────────────────
# КВЕСТЫ
# ─────────────────────────────────────────────────────
QUESTS: List[Dict[str, Any]] = [
    # Модуль 1
    {"id": "m1_task", "module_index": 0, "title": "Миссия 1-1: Первый взгляд",
     "type": "task", "xp_reward": 25, "auto": False,
     "description": "Сделай скрин D1 любой пары и опиши тренд (HH/HL или LL/LH)."},
    {"id": "m1_quiz", "module_index": 0, "title": "Миссия 1-2: Квиз по основам",
     "type": "quiz", "xp_reward": 35, "quiz_ref": "basics_quiz", "auto": True},
    {"id": "m1_boss", "module_index": 0, "title": "БОСС 1: Top-Down",
     "type": "task", "xp_reward": 50, "auto": False,
     "description": "Полный Top-Down: D1, H4, H1, M15 + вывод и обоснование направления."},
    # Модуль 2
    {"id": "m2_task", "module_index": 1, "title": "Миссия 2-1: Структура",
     "type": "task", "xp_reward": 30, "auto": False,
     "description": "Найди тренд и один BOS на H1/H4. Скрин + подпись."},
    {"id": "m2_quiz", "module_index": 1, "title": "Миссия 2-2: Квиз по структуре",
     "type": "quiz", "xp_reward": 40, "quiz_ref": "structure_quiz", "auto": True},
    {"id": "m2_boss", "module_index": 1, "title": "БОСС 2: Inducement",
     "type": "task", "xp_reward": 60, "auto": False,
     "description": "Найди пример Inducement + sweep + разворот. Скрин с разметкой."},
    # Модуль 3
    {"id": "m3_task", "module_index": 2, "title": "Миссия 3-1: Карта ликвидности",
     "type": "task", "xp_reward": 30, "auto": False,
     "description": "Разметь BSL/SSL и один sweep на H1."},
    {"id": "m3_quiz", "module_index": 2, "title": "Миссия 3-2: Квиз по ликвидности",
     "type": "quiz", "xp_reward": 40, "quiz_ref": "liquidity_quiz", "auto": True},
    {"id": "m3_boss", "module_index": 2, "title": "БОСС 3: Sweep и движение",
     "type": "task", "xp_reward": 65, "auto": False,
     "description": "Найди sweep уровня и последующее движение. Опиши логику."},
    # Модуль 4
    {"id": "m4_task", "module_index": 3, "title": "Миссия 4-1: Охота на OB",
     "type": "task", "xp_reward": 35, "auto": False,
     "description": "Найди 2 бычьих и 2 медвежьих OB. Скрины + описание."},
    {"id": "m4_quiz", "module_index": 3, "title": "Миссия 4-2: Квиз по POI",
     "type": "quiz", "xp_reward": 40, "quiz_ref": "poi_quiz", "auto": True},
    {"id": "m4_boss", "module_index": 3, "title": "БОСС 4: OB + FVG",
     "type": "task", "xp_reward": 70, "auto": False,
     "description": "Найди зону, где совпадают OB и FVG, и её отработку."},
    # Модуль 5
    {"id": "m5_task", "module_index": 4, "title": "Миссия 5-1: Breaker vs Mitigation",
     "type": "task", "xp_reward": 35, "auto": False,
     "description": "Найди по одному примеру Breaker и Mitigation Block."},
    {"id": "m5_quiz", "module_index": 4, "title": "Миссия 5-2: Квиз по блокам",
     "type": "quiz", "xp_reward": 40, "quiz_ref": "advanced_blocks_quiz", "auto": True},
    {"id": "m5_boss", "module_index": 4, "title": "БОСС 5: Эволюция блока",
     "type": "task", "xp_reward": 70, "auto": False,
     "description": "Покажи путь OB → Breaker → ретест."},
    # Модуль 6
    {"id": "m6_task", "module_index": 5, "title": "Миссия 6-1: Зоны и OTE",
     "type": "task", "xp_reward": 35, "auto": False,
     "description": "Построй Premium/Discount + OTE на H4."},
    {"id": "m6_quiz", "module_index": 5, "title": "Миссия 6-2: Квиз по зонам",
     "type": "quiz", "xp_reward": 45, "quiz_ref": "zones_quiz", "auto": True},
    {"id": "m6_boss", "module_index": 5, "title": "БОСС 6: Снайперский вход",
     "type": "task", "xp_reward": 75, "auto": False,
     "description": "Собери идеальный сетап: OTE + OB/FVG + Kill Zone."},
    # Модуль 7
    {"id": "m7_task", "module_index": 6, "title": "Миссия 7-1: AMD на деле",
     "type": "task", "xp_reward": 40, "auto": False,
     "description": "Разметь Accumulation, Manipulation, Distribution за один торговый день."},
    {"id": "m7_quiz", "module_index": 6, "title": "Миссия 7-2: Квиз по моделям",
     "type": "quiz", "xp_reward": 45, "quiz_ref": "advanced_models_quiz", "auto": True},
    {"id": "m7_boss", "module_index": 6, "title": "БОСС 7: Прогноз дня",
     "type": "task", "xp_reward": 80, "auto": False,
     "description": "Сделай прогноз по Po3/AMD на следующий день."},
    # Модуль 8
    {"id": "m8_task", "module_index": 7, "title": "Миссия 8-1: Сделка по ICT 2022",
     "type": "task", "xp_reward": 50, "auto": False,
     "description": "Сделай одну сделку по ICT 2022 на демо и разбор."},
    {"id": "m8_quiz", "module_index": 7, "title": "Миссия 8-2: Финальный квиз",
     "type": "quiz", "xp_reward": 50, "quiz_ref": "strategies_quiz", "auto": True},
    {"id": "m8_boss", "module_index": 7, "title": "ФИНАЛЬНЫЙ БОСС: Торговая неделя",
     "type": "task", "xp_reward": 150, "auto": False,
     "description": "Неделя торговли на демо по SMC с дневником сделок."},
]

# ─────────────────────────────────────────────────────
# ПРОГРЕСС, ДЕДЛАЙНЫ, XP
# ─────────────────────────────────────────────────────
user_progress: Dict[int, Dict[str, Any]] = {}


def load_progress():
    global user_progress
    if PROGRESS_FILE.exists():
        try:
            data = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
            user_progress = {int(k): v for k, v in data.items()}
        except Exception as e:
            logger.error(f"Ошибка загрузки прогресса: {e}")
            user_progress = {}
    else:
        user_progress = {}


def save_progress():
    data = {str(k): v for k, v in user_progress.items()}
    PROGRESS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_user_state(user_id: int) -> Dict[str, Any]:
    if user_id not in user_progress:
        user_progress[user_id] = {
            "module_index": 0,
            "homework_status": "none",
            "xp": 0,
            "level": 1,
            "rank": "Novice Liquidity Hunter",
            "streak": 0,
            "completed_quests": [],
            "active_quest": None,
            "quiz_state": None,
            "module_deadline": None,
            "deadline_extensions": 0,
            "name": None,
        }
    return user_progress[user_id]


def add_xp(user_id: int, amount: int):
    state = get_user_state(user_id)
    state["xp"] += amount
    leveled_up = False
    while state["xp"] >= state["level"] * 100:
        state["xp"] -= state["level"] * 100
        state["level"] += 1
        leveled_up = True
    lvl = state["level"]
    if lvl < 3:
        state["rank"] = "Novice Liquidity Hunter"
    elif lvl < 6:
        state["rank"] = "Order Block Apprentice"
    elif lvl < 10:
        state["rank"] = "FVG Sniper"
    elif lvl < 15:
        state["rank"] = "Smart Money Operative"
    else:
        state["rank"] = "Institutional Level Trader"
    save_progress()
    return state["level"], leveled_up


def is_deadline_expired(state: Dict[str, Any]) -> bool:
    dl = state.get("module_deadline")
    if not dl:
        return False
    try:
        dt = datetime.fromisoformat(dl)
    except Exception:
        return False
    return datetime.utcnow() > dt


def reset_user_progress(user_id: int):
    state = get_user_state(user_id)
    name = state.get("name")
    user_progress[user_id] = {
        "module_index": 0, "homework_status": "none", "xp": 0, "level": 1,
        "rank": "Novice Liquidity Hunter", "streak": 0, "completed_quests": [],
        "active_quest": None, "quiz_state": None, "module_deadline": None,
        "deadline_extensions": 0, "name": name,
    }
    save_progress()


def set_module_deadline(state: Dict[str, Any]):
    deadline = datetime.utcnow() + timedelta(days=DEFAULT_DEADLINE_DAYS)
    state["module_deadline"] = deadline.isoformat()
    state["deadline_extensions"] = 0


def try_advance_module(user_id: int) -> bool:
    state = get_user_state(user_id)
    idx = state["module_index"]
    module_quests = [q for q in QUESTS if q["module_index"] == idx]
    done = all(q["id"] in state["completed_quests"] for q in module_quests)
    if not done:
        return False
    if idx + 1 < len(MODULES):
        state["module_index"] = idx + 1
        state["homework_status"] = "none"
        set_module_deadline(state)
    else:
        state["homework_status"] = "approved"
        state["module_deadline"] = None
    save_progress()
    return True


def get_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    players = []
    for uid, st in user_progress.items():
        players.append({
            "user_id": uid, "level": st.get("level", 1), "xp": st.get("xp", 0),
            "module": st.get("module_index", 0), "name": st.get("name") or str(uid),
        })
    players.sort(key=lambda x: (x["level"], x["xp"]), reverse=True)
    return players[:limit]


# ─────────────────────────────────────────────────────
# ХЕЛПЕР — отправка урока с графиком
# ─────────────────────────────────────────────────────
def send_lesson_with_chart(chat_id: int, lesson_key: str, back_callback: str, original_msg_id: int = None):
    """Удаляет предыдущее сообщение, отправляет график + статью + видео."""
    lesson = LESSONS.get(lesson_key)
    if not lesson:
        return

    # Удаляем старое inline-сообщение
    if original_msg_id:
        try:
            bot.delete_message(chat_id, original_msg_id)
        except Exception:
            pass

    # Отправляем график
    chart = generate_chart(lesson_key)
    if chart:
        try:
            bot.send_photo(chat_id, chart, caption=f"📊 {lesson['title']}")
        except Exception as e:
            logger.error(f"Photo send error: {e}")

    # Клавиатура навигации
    kb = types.InlineKeyboardMarkup()
    video = lesson.get("video", "")
    if video:
        kb.row(types.InlineKeyboardButton("🎥 Видео по теме", url=video))
    kb.row(types.InlineKeyboardButton("🔙 Назад", callback_data=back_callback))
    kb.row(types.InlineKeyboardButton("🏠 Главное меню", callback_data="back_main_new"))

    # Отправляем статью
    article = lesson.get("article", lesson["text"])
    bot.send_message(chat_id, article, reply_markup=kb, parse_mode="Markdown")


# ─────────────────────────────────────────────────────
# КЛАВИАТУРЫ
# ─────────────────────────────────────────────────────
def main_menu_keyboard():
    kb = types.InlineKeyboardMarkup()
    kb.row(types.InlineKeyboardButton("🎓 Учебный путь", callback_data="path"))
    kb.row(types.InlineKeyboardButton("🗺 Квесты модуля", callback_data="module_quests"))
    kb.row(types.InlineKeyboardButton("📚 Уроки", callback_data="menu_lessons"))
    kb.row(types.InlineKeyboardButton("📊 Профиль", callback_data="profile"))
    kb.row(types.InlineKeyboardButton("🏆 Лидерборд", callback_data="leaderboard"))
    return kb


def lessons_keyboard():
    kb = types.InlineKeyboardMarkup()
    for key, data in LESSONS.items():
        kb.row(types.InlineKeyboardButton(data["title"], callback_data=f"lesson_{key}"))
    kb.row(types.InlineKeyboardButton("🔙 Назад", callback_data="back_main"))
    return kb


def path_keyboard(user_id: int):
    state = get_user_state(user_id)
    idx = state["module_index"]
    status = state["homework_status"]
    kb = types.InlineKeyboardMarkup()
    for i, module in enumerate(MODULES):
        if i < idx:
            label = f"✅ {module['title']}"
        elif i == idx:
            label = f"🟡 {module['title']} (текущий)"
        else:
            label = f"🔒 {module['title']}"
        kb.row(types.InlineKeyboardButton(label, callback_data=f"module_{i}"))
    kb.row(types.InlineKeyboardButton("🔙 В меню", callback_data="back_main"))
    hw_text = ""
    if status == "pending":
        hw_text = "\n\n📨 Домашка отправлена. Ждёт проверки."
    elif status == "rejected":
        hw_text = "\n\n❌ Домашка не принята. Доработай и отправь снова."
    return kb, hw_text


def available_quests(user_id: int):
    state = get_user_state(user_id)
    idx = state["module_index"]
    completed = set(state["completed_quests"])
    return [q for q in QUESTS if q["module_index"] == idx and q["id"] not in completed]


# ─────────────────────────────────────────────────────
# ХЕНДЛЕРЫ КОМАНД
# ─────────────────────────────────────────────────────
@bot.message_handler(commands=["start"])
def cmd_start(message: types.Message):
    user = message.from_user
    st = get_user_state(user.id)
    st["name"] = user.username or (f"{user.first_name or ''} {user.last_name or ''}".strip() or str(user.id))
    if st["module_index"] == 0 and not st.get("module_deadline"):
        set_module_deadline(st)
    save_progress()
    bot.reply_to(
        message,
        "👋 Добро пожаловать в *SMC Trading Quest*.\n\n"
        "Это VIP-курс с дедлайнами, квестами и рейтингом.\n"
        "Каждый урок содержит *полную статью*, *интерактивный график* и *видео*.\n"
        "Начни с учебного пути! 🚀",
        reply_markup=main_menu_keyboard(),
    )


@bot.message_handler(commands=["top"])
def cmd_top(message: types.Message):
    board = get_leaderboard(10)
    if not board:
        bot.reply_to(message, "Пока нет данных по ученикам.")
        return
    lines = ["🏆 *Лидерборд курса:*"]
    for i, p in enumerate(board, start=1):
        lines.append(f"{i}) {p['name']} — lvl {p['level']} | XP {p['xp']} | модуль {p['module'] + 1}")
    bot.reply_to(message, "\n".join(lines))


@bot.message_handler(commands=["stats"])
def cmd_stats(message: types.Message):
    args = message.text.split()[1:]
    if not args:
        uid = message.from_user.id
    else:
        arg = args[0]
        if arg.startswith("@"):
            uid = None
            for k, st in user_progress.items():
                if st.get("name") == arg[1:]:
                    uid = k
                    break
            if uid is None:
                bot.reply_to(message, "Пользователь не найден.")
                return
        else:
            uid = int(arg)
    state = get_user_state(uid)
    module_title = MODULES[state["module_index"]]["title"]
    dl = state.get("module_deadline")
    dl_text = dl.split("T")[0] if dl else "не установлен"
    bot.reply_to(
        message,
        f"📊 *Статистика:*\n\n"
        f"Имя: {state.get('name', uid)}\n"
        f"Уровень: {state['level']}\n"
        f"XP: {state['xp']}\n"
        f"Звание: {state['rank']}\n"
        f"Текущий модуль: {state['module_index'] + 1} — {module_title}\n"
        f"Пройдено квестов: {len(state['completed_quests'])}\n"
        f"Дедлайн модуля: {dl_text}\n"
        f"Продлений: {state.get('deadline_extensions', 0)}",
    )


@bot.message_handler(commands=["extend_me"])
def cmd_extend_me(message: types.Message):
    user = message.from_user
    uid = user.id
    state = get_user_state(uid)
    if not is_deadline_expired(state) and state.get("module_deadline"):
        bot.reply_to(message, "Твой дедлайн ещё не истёк.")
        return
    if state.get("deadline_extensions", 0) >= MAX_EXTENSIONS:
        bot.reply_to(message, "Лимит продлений исчерпан.")
        return
    if ADMIN_ID:
        bot.send_message(
            ADMIN_ID,
            f"🧾 Запрос продления от @{user.username or user.id}\n"
            f"user_id: {uid}\n"
            f"/extend {uid} 3"
        )
    bot.reply_to(message, "Запрос на продление отправлен админу.")


@bot.message_handler(commands=["extend"])
def cmd_extend(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()[1:]
    if len(args) < 2:
        bot.reply_to(message, "Использование: /extend user_id дни")
        return
    uid = int(args[0])
    days = int(args[1])
    state = get_user_state(uid)
    if state.get("deadline_extensions", 0) >= MAX_EXTENSIONS:
        bot.reply_to(message, "Лимит продлений исчерпан.")
        return
    now = datetime.utcnow()
    if state.get("module_deadline"):
        try:
            dl = datetime.fromisoformat(state["module_deadline"])
        except Exception:
            dl = now
        new_dl = dl + timedelta(days=days)
    else:
        new_dl = now + timedelta(days=days)
    state["module_deadline"] = new_dl.isoformat()
    state["deadline_extensions"] = state.get("deadline_extensions", 0) + 1
    save_progress()
    bot.send_message(uid, f"📅 Дедлайн продлён на {days} дн. Новый: {new_dl.date()}")
    bot.reply_to(message, "Дедлайн продлён.")


@bot.message_handler(commands=["approve"])
def cmd_approve(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()[1:]
    if not args:
        bot.reply_to(message, "Использование: /approve user_id")
        return
    uid = int(args[0])
    if try_advance_module(uid):
        bot.send_message(uid, "✅ Домашка принята! Открылся следующий модуль!")
        bot.reply_to(message, "Пользователь переведён на следующий модуль.")
    else:
        bot.reply_to(message, "Не все квесты завершены. Нельзя перевести.")


@bot.message_handler(commands=["reject"])
def cmd_reject(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split(None, 2)[1:]
    if not args:
        bot.reply_to(message, "Использование: /reject user_id [комментарий]")
        return
    uid = int(args[0])
    comment = args[1] if len(args) > 1 else "Нужно доработать."
    state = get_user_state(uid)
    state["homework_status"] = "rejected"
    save_progress()
    bot.send_message(uid, f"❌ Домашка не принята.\nКомментарий: {comment}")
    bot.reply_to(message, "Домашка отклонена.")


@bot.message_handler(commands=["qapprove"])
def cmd_qapprove(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()[1:]
    if len(args) < 2:
        bot.reply_to(message, "Использование: /qapprove user_id quest_id")
        return
    uid, quest_id = int(args[0]), args[1]
    state = get_user_state(uid)
    quest = next((x for x in QUESTS if x["id"] == quest_id), None)
    if not quest:
        bot.reply_to(message, "Квест не найден.")
        return
    state["completed_quests"].append(quest_id)
    state["active_quest"] = None
    level, leveled = add_xp(uid, quest["xp_reward"])
    save_progress()
    bot.send_message(uid, f"✅ Квест «{quest['title']}» принят! +{quest['xp_reward']} XP")
    if leveled:
        bot.send_message(uid, f"🎉 Новый уровень: {level}!")
    if quest_id.endswith("_boss"):
        if try_advance_module(uid):
            bot.send_message(uid, "🎓 Модуль завершён! Открылся следующий модуль!")
    bot.reply_to(message, "Квест засчитан.")


@bot.message_handler(commands=["qreject"])
def cmd_qreject(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split(None, 3)[1:]
    if len(args) < 2:
        bot.reply_to(message, "Использование: /qreject user_id quest_id [комментарий]")
        return
    uid, quest_id = int(args[0]), args[1]
    comment = args[2] if len(args) > 2 else "Доработай и попробуй снова."
    state = get_user_state(uid)
    state["active_quest"] = None
    save_progress()
    quest = next((x for x in QUESTS if x["id"] == quest_id), None)
    title = quest["title"] if quest else quest_id
    bot.send_message(uid, f"❌ Квест «{title}» не принят.\nКомментарий: {comment}")
    bot.reply_to(message, "Квест отклонён.")


# ─────────────────────────────────────────────────────
# CALLBACK ХЕНДЛЕР
# ─────────────────────────────────────────────────────
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call: types.CallbackQuery):
    uid = call.from_user.id
    state = get_user_state(uid)
    data = call.data

    # Главное меню (редактирование существующего сообщения)
    if data == "back_main":
        try:
            bot.edit_message_text(
                "Главное меню:",
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=main_menu_keyboard(),
            )
        except Exception:
            pass
        return

    # Главное меню (новое сообщение, после отправки фото)
    if data == "back_main_new":
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(
            call.message.chat.id,
            "Главное меню:",
            reply_markup=main_menu_keyboard(),
        )
        return

    if data == "profile":
        text = (
            f"*Профиль:*\n\n"
            f"Имя: {state.get('name', uid)}\n"
            f"Уровень: {state['level']}\n"
            f"XP: {state['xp']}\n"
            f"Звание: {state['rank']}\n"
            f"Модуль: {state['module_index'] + 1}/{len(MODULES)}"
        )
        kb = types.InlineKeyboardMarkup()
        kb.row(types.InlineKeyboardButton("🔙 Назад", callback_data="back_main"))
        bot.edit_message_text(text, chat_id=call.message.chat.id,
                              message_id=call.message.message_id, reply_markup=kb)
        return

    if data == "leaderboard":
        board = get_leaderboard(10)
        if not board:
            bot.edit_message_text("Пока нет данных.", chat_id=call.message.chat.id,
                                  message_id=call.message.message_id, reply_markup=main_menu_keyboard())
            return
        lines = ["🏆 *Лидерборд курса:*"]
        for i, p in enumerate(board, start=1):
            lines.append(f"{i}) {p['name']} — lvl {p['level']} | XP {p['xp']} | модуль {p['module'] + 1}")
        bot.edit_message_text("\n".join(lines), chat_id=call.message.chat.id,
                              message_id=call.message.message_id, reply_markup=main_menu_keyboard())
        return

    if data == "path":
        kb, hw_text = path_keyboard(uid)
        m = MODULES[state["module_index"]]
        dl = state.get("module_deadline")
        dl_text = dl.split("T")[0] if dl else "не установлен"
        text = (
            f"*Учебный путь:*\n\n"
            f"Текущий модуль: {m['title']}\n"
            f"Дедлайн: {dl_text}\n"
            f"Статус домашки: {state['homework_status']}{hw_text}"
        )
        bot.edit_message_text(text, chat_id=call.message.chat.id,
                              message_id=call.message.message_id, reply_markup=kb)
        return

    if data.startswith("module_") and not data.startswith("module_lesson_") and not data.startswith("module_hw_"):
        idx = int(data.split("_")[1])
        current_idx = state["module_index"]
        if idx > current_idx:
            bot.answer_callback_query(call.id, "Сначала пройди текущий модуль и квесты.", show_alert=True)
            return
        module = MODULES[idx]
        kb = types.InlineKeyboardMarkup()
        kb.row(types.InlineKeyboardButton("📚 Уроки модуля", callback_data=f"module_lesson_{idx}"))
        kb.row(types.InlineKeyboardButton("📝 Домашка", callback_data=f"module_hw_{idx}"))
        kb.row(types.InlineKeyboardButton("🔙 К пути", callback_data="path"))
        bot.edit_message_text(module["title"], chat_id=call.message.chat.id,
                              message_id=call.message.message_id, reply_markup=kb)
        return

    if data.startswith("module_lesson_"):
        idx = int(data.split("_")[2])
        module = MODULES[idx]
        kb = types.InlineKeyboardMarkup()
        for lesson_key in module["lessons"]:
            lesson = LESSONS[lesson_key]
            kb.row(types.InlineKeyboardButton(
                lesson["title"],
                callback_data=f"lesson_mod_{idx}_{lesson_key}"
            ))
        kb.row(types.InlineKeyboardButton("🔙 Назад", callback_data=f"module_{idx}"))
        bot.edit_message_text(
            f"*{module['title']}*\n\nВыбери урок для изучения:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=kb,
        )
        return

    # Урок из модуля — с графиком
    if data.startswith("lesson_mod_"):
        parts = data.split("_", 4)
        # lesson_mod_{idx}_{lesson_key}
        idx = int(parts[2])
        lesson_key = parts[3]
        send_lesson_with_chart(
            call.message.chat.id,
            lesson_key,
            back_callback=f"module_lesson_{idx}",
            original_msg_id=call.message.message_id,
        )
        return

    if data.startswith("module_hw_"):
        idx = int(data.split("_")[2])
        if idx != state["module_index"]:
            bot.answer_callback_query(call.id, "Домашку можно сдавать только по текущему модулю.", show_alert=True)
            return
        module = MODULES[idx]
        kb = types.InlineKeyboardMarkup()
        kb.row(types.InlineKeyboardButton("📤 Отправить домашку", callback_data=f"hw_submit_{idx}"))
        kb.row(types.InlineKeyboardButton("🔙 Назад", callback_data=f"module_{idx}"))
        bot.edit_message_text(module["homework"], chat_id=call.message.chat.id,
                              message_id=call.message.message_id, reply_markup=kb)
        return

    if data.startswith("hw_submit_"):
        idx = int(data.split("_")[2])
        if idx != state["module_index"]:
            bot.answer_callback_query(call.id, "Это не твой текущий модуль.", show_alert=True)
            return
        state["homework_status"] = "pending"
        save_progress()
        kb = types.InlineKeyboardMarkup()
        kb.row(types.InlineKeyboardButton("🔙 К пути", callback_data="path"))
        bot.edit_message_text(
            "📬 Домашка помечена как отправленная.\nПришли скрины и разбор сообщением.",
            chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=kb)
        return

    if data == "menu_lessons":
        bot.edit_message_text("📚 Выбери тему:", chat_id=call.message.chat.id,
                              message_id=call.message.message_id, reply_markup=lessons_keyboard())
        return

    # Урок из меню уроков — с графиком
    if data.startswith("lesson_") and not data.startswith("lesson_mod_"):
        lesson_key = data.replace("lesson_", "")
        send_lesson_with_chart(
            call.message.chat.id,
            lesson_key,
            back_callback="menu_lessons",
            original_msg_id=call.message.message_id,
        )
        return

    if data == "module_quests":
        quests = available_quests(uid)
        idx = state["module_index"]
        if not quests:
            kb = types.InlineKeyboardMarkup()
            kb.row(types.InlineKeyboardButton("📝 Домашка модуля", callback_data=f"module_hw_{idx}"))
            kb.row(types.InlineKeyboardButton("🔙 В меню", callback_data="back_main"))
            bot.edit_message_text(
                "✅ Все квесты модуля выполнены!\nСдай домашку или жди открытия следующего модуля.",
                chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=kb)
        else:
            kb = types.InlineKeyboardMarkup()
            for q in quests:
                icon = "🔥" if "БОСС" in q["title"] else "🟡"
                kb.row(types.InlineKeyboardButton(f"{icon} {q['title']}", callback_data=f"quest_{q['id']}"))
            kb.row(types.InlineKeyboardButton("🔙 В меню", callback_data="back_main"))
            bot.edit_message_text("🗺 Квесты модуля:", chat_id=call.message.chat.id,
                                  message_id=call.message.message_id, reply_markup=kb)
        return

    if data.startswith("quest_") and not data.startswith("quest_start_"):
        qid = data.split("quest_")[1]
        quest = next((x for x in QUESTS if x["id"] == qid), None)
        if not quest:
            bot.answer_callback_query(call.id, "Квест не найден", show_alert=True)
            return
        if quest["module_index"] != state["module_index"]:
            bot.answer_callback_query(call.id, "Этот квест не для твоего уровня.", show_alert=True)
            return
        text = f"*{quest['title']}*\n\n{quest.get('description', '')}\n\nНаграда: *{quest['xp_reward']} XP*"
        kb = types.InlineKeyboardMarkup()
        kb.row(types.InlineKeyboardButton("🚀 Начать квест", callback_data=f"quest_start_{qid}"))
        kb.row(types.InlineKeyboardButton("🔙 К квестам", callback_data="module_quests"))
        bot.edit_message_text(text, chat_id=call.message.chat.id,
                              message_id=call.message.message_id, reply_markup=kb)
        return

    if data.startswith("quest_start_"):
        qid = data.split("quest_start_")[1]
        quest = next((x for x in QUESTS if x["id"] == qid), None)
        if not quest:
            bot.answer_callback_query(call.id, "Квест не найден", show_alert=True)
            return
        if quest["module_index"] != state["module_index"]:
            bot.answer_callback_query(call.id, "Этот квест не для твоего уровня.", show_alert=True)
            return
        state["active_quest"] = qid
        save_progress()
        if quest["type"] == "quiz":
            state["quiz_state"] = {"quiz_id": quest["quiz_ref"], "index": 0, "correct": 0}
            save_progress()
            send_quiz_question(call.message, uid)
        else:
            bot.edit_message_text(
                f"⚔️ Квест начат!\n\n{quest['description']}\n\nВыполни задание и отправь ответ (текст/скрины).",
                chat_id=call.message.chat.id, message_id=call.message.message_id)
        return

    if data.startswith("quiz_answer_"):
        handle_quiz_answer(call)
        return

    if data == "quiz_next":
        send_quiz_question(call.message, uid)
        return


# ─────────────────────────────────────────────────────
# КВИЗЫ
# ─────────────────────────────────────────────────────
def send_quiz_question(message: types.Message, user_id: int):
    state = get_user_state(user_id)
    qstate = state.get("quiz_state")
    if not qstate:
        bot.edit_message_text("Квиз не активен.", chat_id=message.chat.id, message_id=message.message_id)
        return
    quiz_id = qstate["quiz_id"]
    idx = qstate["index"]
    quiz_list = QUIZZES.get(quiz_id, [])
    if idx >= len(quiz_list):
        correct = qstate["correct"]
        total = len(quiz_list)
        score = correct / total if total else 0
        MIN_SCORE = 0.7
        quest_id = state.get("active_quest")
        if score >= MIN_SCORE and quest_id:
            quest = next((x for x in QUESTS if x["id"] == quest_id), None)
            if quest:
                state["completed_quests"].append(quest_id)
                state["active_quest"] = None
                state["quiz_state"] = None
                level, leveled = add_xp(user_id, quest["xp_reward"])
                text = (
                    f"🎉 *Квиз завершён!*\n\n"
                    f"Правильных: {correct}/{total} ({round(score * 100)}%)\n"
                    f"Награда: *{quest['xp_reward']} XP*\n"
                    f"Твой уровень: *{level}*"
                )
                bot.edit_message_text(text, chat_id=message.chat.id, message_id=message.message_id)
                if leveled:
                    bot.send_message(user_id, "🎉 Новый уровень!")
                if quest_id.endswith("_quiz"):
                    if try_advance_module(user_id):
                        bot.send_message(user_id, "🎓 Модуль завершён! Открылся следующий!")
                return
        else:
            state["quiz_state"] = None
            state["active_quest"] = None
            save_progress()
            bot.edit_message_text(
                f"❌ Недостаточно правильных ответов ({round(score * 100)}%).\n"
                f"Нужно минимум 70%. Повтори урок и попробуй снова.",
                chat_id=message.chat.id, message_id=message.message_id)
            return

    quiz = quiz_list[idx]
    options = quiz["options"].copy()
    random.shuffle(options)
    kb = types.InlineKeyboardMarkup()
    for text, is_correct in options:
        cb = f"quiz_answer_{'correct' if is_correct else 'wrong'}"
        kb.row(types.InlineKeyboardButton(text, callback_data=cb))
    bot.edit_message_text(
        f"❓ Вопрос {idx + 1}/{len(quiz_list)}\n\n{quiz['question']}",
        chat_id=message.chat.id, message_id=message.message_id, reply_markup=kb)


def handle_quiz_answer(call: types.CallbackQuery):
    uid = call.from_user.id
    state = get_user_state(uid)
    qstate = state.get("quiz_state")
    if not qstate:
        bot.answer_callback_query(call.id, "Квиз не активен.", show_alert=True)
        return
    quiz_id = qstate["quiz_id"]
    idx = qstate["index"]
    quiz_list = QUIZZES.get(quiz_id, [])
    is_correct = call.data.endswith("_correct")
    if is_correct:
        qstate["correct"] += 1
    qstate["index"] += 1
    state["quiz_state"] = qstate
    save_progress()
    if idx < len(quiz_list):
        result = "✅ Верно!" if is_correct else "❌ Неверно!"
        kb = types.InlineKeyboardMarkup()
        kb.row(types.InlineKeyboardButton("➡️ Далее", callback_data="quiz_next"))
        bot.edit_message_text(f"{result}\n\nЖми далее.",
                              chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=kb)
    else:
        send_quiz_question(call.message, uid)


# ─────────────────────────────────────────────────────
# ОБРАБОТКА ДЗ И КВЕСТОВ
# ─────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: True, content_types=["text", "photo", "document"])
def hw_handler(message: types.Message):
    if message.text and message.text.startswith("/"):
        return
    user = message.from_user
    uid = user.id
    state = get_user_state(uid)

    if is_deadline_expired(state):
        reset_user_progress(uid)
        bot.reply_to(message,
                     "⏰ Дедлайн по модулю просрочен.\nТвой прогресс и XP обнулены.\n\nНачни сначала с /start.")
        return

    qid = state.get("active_quest")
    if qid:
        quest = next((x for x in QUESTS if x["id"] == qid), None)
        if quest and quest["type"] == "task":
            if ADMIN_ID:
                bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
                bot.send_message(ADMIN_ID,
                                 f"Ответ на квест от @{user.username or user.id}\n"
                                 f"Квест: {quest['title']} ({quest['id']})\n\n"
                                 f"/qapprove {uid} {quest['id']}\n"
                                 f"/qreject {uid} {quest['id']} комментарий")
            bot.reply_to(message, "📬 Ответ на квест получен. Ждёт проверки.")
            return

    if state["homework_status"] in ("pending", "rejected"):
        if ADMIN_ID:
            idx = state["module_index"]
            module = MODULES[idx]
            bot.forward_message(ADMIN_ID, message.chat.id, message.message_id)
            bot.send_message(ADMIN_ID,
                             f"Домашка по модулю от @{user.username or user.id}\n"
                             f"Модуль: {module['title']}\n\n"
                             f"/approve {uid}\n"
                             f"/reject {uid} комментарий")
        bot.reply_to(message, "📬 Домашка получена. Ждёт проверки.")
        return

    bot.reply_to(message, "Чтобы двигаться по курсу — открой /start и выбери модуль или квест.")


# ─────────────────────────────────────────────────────
# ЗАПУСК
# ─────────────────────────────────────────────────────
def main():
    load_progress()
    logger.info("SMC Quest Bot запущен")
    bot.infinity_polling()


if __name__ == "__main__":
    main()
