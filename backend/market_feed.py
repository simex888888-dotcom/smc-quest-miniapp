"""
market_feed.py — Live BTC/ETH market data from Binance public API.

Fetches every 60 s, caches in memory. No auth, no Redis needed.
Computes: price_change_1h, volatility_index, market_state → pet_mood.
"""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

BINANCE_BASE = "https://api.binance.com"
_CACHE_TTL = 60       # seconds before re-fetch
_FETCH_TIMEOUT = 8.0  # httpx timeout

_cache: Dict[str, Any] = {}
_fetch_lock: Optional[asyncio.Lock] = None   # created lazily (event loop may not exist at import)


def _get_lock() -> asyncio.Lock:
    global _fetch_lock
    if _fetch_lock is None:
        _fetch_lock = asyncio.Lock()
    return _fetch_lock


# ── Market state classification ───────────────────────────────────────────────

_STATE_RULES = [
    # (state,      condition fn(change_1h, volatility))
    ("crash",    lambda ch, v: ch <= -4.0),
    ("dump",     lambda ch, v: ch <= -1.5),
    ("pump",     lambda ch, v: ch >= 3.0),
    ("rally",    lambda ch, v: ch >= 1.0),
    ("volatile", lambda ch, v: v >= 65),
    ("flat",     lambda ch, v: abs(ch) < 0.3 and v < 25),
]

# Per-state pet presentation data
_MOOD_MAP: Dict[str, Dict[str, Any]] = {
    "crash":    {"visual": "sick",    "aura": "#ef4444", "pulse_speed": 0.35, "label": "Крэш рынка 📉"},
    "dump":     {"visual": "hungry",  "aura": "#f97316", "pulse_speed": 0.65, "label": "Нисходящий тренд"},
    "pump":     {"visual": "excited", "aura": "#fbbf24", "pulse_speed": 1.7,  "label": "Бычий импульс 🚀"},
    "rally":    {"visual": "happy",   "aura": "#10b981", "pulse_speed": 1.3,  "label": "Восходящий тренд"},
    "volatile": {"visual": "excited", "aura": "#a855f7", "pulse_speed": 2.2,  "label": "Высокая волатильность ⚡"},
    "flat":     {"visual": "idle",    "aura": "#64748b", "pulse_speed": 0.45, "label": "Флет. Лисичка дремлет..."},
    "neutral":  {"visual": "idle",    "aura": "#ff8c42", "pulse_speed": 1.0,  "label": "Нейтральный рынок"},
}


def _classify(price_change_1h: float, volatility: float) -> str:
    for state, fn in _STATE_RULES:
        if fn(price_change_1h, volatility):
            return state
    return "neutral"


def _build_pet_mood(state: str, change: float, vol: float) -> Dict[str, Any]:
    m = dict(_MOOD_MAP.get(state, _MOOD_MAP["neutral"]))
    m["market_state"]     = state
    m["price_change_1h"]  = round(change, 2)
    m["volatility_index"] = round(vol, 1)
    return m


# ── Binance API helpers ───────────────────────────────────────────────────────

async def _fetch_klines(symbol: str, interval: str, limit: int) -> List[list]:
    url = f"{BINANCE_BASE}/api/v3/klines"
    async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT) as client:
        r = await client.get(url, params={"symbol": symbol, "interval": interval, "limit": limit})
        r.raise_for_status()
        return r.json()


def _calc_volatility(klines: List[list]) -> float:
    """Normalized ATR volatility 0-100 from high-low range / close."""
    if not klines:
        return 50.0
    ranges = []
    for k in klines:
        high, low, close = float(k[2]), float(k[3]), float(k[4])
        if close > 0:
            ranges.append((high - low) / close * 100)
    if not ranges:
        return 50.0
    avg = sum(ranges) / len(ranges)
    # 0.3% range → 0, 3%+ range → 100
    return min(100.0, max(0.0, (avg - 0.3) / 2.7 * 100))


# ── Main refresh ─────────────────────────────────────────────────────────────

async def refresh_market_data() -> Dict[str, Any]:
    """Fetch & compute market pulse. Returns full pulse dict."""
    lock = _get_lock()
    async with lock:
        now = time.time()
        cached = _cache.get("pulse")
        if cached and now - cached.get("_fetched_at", 0) < _CACHE_TTL:
            return cached

        try:
            klines = await _fetch_klines("BTCUSDT", "1h", 25)
            if len(klines) < 3:
                raise ValueError("insufficient kline data")

            close_now  = float(klines[-1][4])
            close_prev = float(klines[-2][4])
            open_24h   = float(klines[0][1])

            change_1h  = (close_now - close_prev) / close_prev * 100
            change_24h = (close_now - open_24h)   / open_24h   * 100
            vol        = _calc_volatility(klines[-6:])  # last 6 candles
            state      = _classify(change_1h, vol)

            result = {
                "ok":              True,
                "btc_price":       round(close_now, 2),
                "price_change_1h": round(change_1h, 2),
                "price_change_24h":round(change_24h, 2),
                "volatility_index":round(vol, 1),
                "market_state":    state,
                "pet_mood":        _build_pet_mood(state, change_1h, vol),
                "_fetched_at":     now,
            }
            _cache["pulse"] = result
            logger.info(
                f"Market pulse: BTC=${close_now:.0f} "
                f"1h={change_1h:+.2f}% vol={vol:.0f} → {state}"
            )
            return result

        except Exception as e:
            logger.error(f"market_feed refresh error: {e}")
            fallback = dict(_cache.get("pulse") or {})
            fallback["ok"] = False
            fallback["error"] = str(e)
            if "pet_mood" not in fallback:
                fallback["pet_mood"] = _build_pet_mood("neutral", 0.0, 50.0)
            return fallback


def get_cached_pulse() -> Optional[Dict[str, Any]]:
    return _cache.get("pulse")


async def start_market_feed_loop():
    """Infinite background loop — refresh market data every 60 s."""
    logger.info("Market feed loop started")
    while True:
        try:
            await refresh_market_data()
        except Exception as e:
            logger.error(f"Market feed loop error: {e}")
        await asyncio.sleep(60)
