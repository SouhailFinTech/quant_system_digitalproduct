# QuantDrop v4.1 — Profitable Digital Product Intelligence
# Stack: Streamlit + SerpAPI + ScraperAPI + pytrends + Gemini 3.1 Flash Lite
# Deploy: GitHub → Streamlit Cloud (free)
# ──────────────────────────────────────────────────────────────────────────────
# SETUP: Streamlit Cloud → Settings → Secrets → paste:
#   GEMINI_API_KEY = "AIza..."
#   SERPAPI_KEY = "your_serpapi_key"
#   SCRAPERAPI_KEY = "your_scraperapi_key"
#   REDDIT_CLIENT_ID = "optional"
#   REDDIT_CLIENT_SECRET = "optional"
# ──────────────────────────────────────────────────────────────────────────────

import streamlit as st
import requests
import json
import time
import random
import sqlite3
import hashlib
import numpy as np
from datetime import datetime, timedelta

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="QuantDrop v4.1 — Profitable Digital Products",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── CUSTOM CSS (All typos fixed) ───────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap');
html,body,[class*="css"]{font-family:'Syne',sans-serif;background:#080C10;color:#E8F4FF}
#MainMenu,footer,header{visibility:hidden}
.stApp{background:#080C10}
.phase-card{background:#0D1117;border:1px solid #1E2B38;border-radius:8px;padding:14px;margin-bottom:8px}
.phase-card.go{border-color:#00FF88}.phase-card.review{border-color:#FFD166}.phase-card.kill{border-color:#FF4757}
.verdict-go{background:rgba(0,255,136,.08);border:1.5px solid #00FF88;border-radius:8px;padding:20px 24px;margin:16px 0}
.verdict-review{background:rgba(255,209,102,.08);border:1.5px solid #FFD166;border-radius:8px;padding:20px 24px;margin:16px 0}
.verdict-kill{background:rgba(255,71,87,.08);border:1.5px solid #FF4757;border-radius:8px;padding:20px 24px;margin:16px 0}
.design-card{background:#141B24;border:1px solid #2A3D52;border-radius:8px;padding:20px;margin:12px 0}
.tag{display:inline-block;font-family:'Space Mono',monospace;font-size:10px;padding:3px 8px;border-radius:3px;background:#1E2B38;color:#6B8BA4;margin:2px}
.complaint{border-left:2px solid #FF6B35;padding:6px 10px;background:#141B24;border-radius:0 4px 4px 0;font-size:13px;color:#6B8BA4;margin-bottom:6px}
.opportunity{background:rgba(0,255,136,.06);border:1px solid rgba(0,255,136,.2);border-radius:4px;padding:8px 12px;font-family:'Space Mono',monospace;font-size:12px;color:#00FF88;margin-top:8px}
.section-header{font-family:'Space Mono',monospace;font-size:10px;color:#6B8BA4;text-transform:uppercase;letter-spacing:.1em;border-bottom:1px solid #1E2B38;padding-bottom:6px;margin:16px 0 10px}
.cache-badge{font-family:'Space Mono',monospace;font-size:9px;color:#6B8BA4;background:#1E2B38;padding:2px 7px;border-radius:3px;margin-left:6px}
.stTextInput input{background:#0D1117!important;border:1px solid #2A3D52!important;color:#E8F4FF!important;font-family:'Space Mono',monospace!important;border-radius:6px!important}
.stButton>button{background:#00D4FF!important;color:#080C10!important;font-family:'Space Mono',monospace!important;font-weight:700!important;border:none!important;border-radius:6px!important;font-size:13px!important;letter-spacing:.04em!important;padding:10px 24px!important;width:100%!important}
.stButton>button:hover{background:white!important}
.stSelectbox>div>div{background:#0D1117!important;border:1px solid #2A3D52!important;color:#E8F4FF!important}
.stTextArea textarea{background:#0D1117!important;border:1px solid #2A3D52!important;color:#E8F4FF!important;font-family:'Space Mono',monospace!important}
</style>
""", unsafe_allow_html=True)

# ── PLATFORM CONFIG (Trailing spaces removed) ──────────────────────────────────
PLATFORMS = {
    "KDP — Kindle / Paperback / Hardcover": {
        "id": "kdp", "royalty_pct": 0.70, "fees": 0.06, "price": 6.99, "color": "#7C3AED",
        "product": "journal / planner / workbook",
        "product_types": ["journal", "planner", "workbook", "notebook", "log book"],
        "kindle_alias": "digital-text"
    },
    "Merch by Amazon — T-Shirts / Apparel": {
        "id": "mba", "royalty_flat": 4.20, "price": 19.99, "color": "#059669",
        "product": "t-shirt / hoodie / tote",
        "product_types": ["t-shirt", "hoodie", "tote bag", "phone case"],
        "kindle_alias": "aps"
    },
    "Etsy — Digital Downloads": {
        "id": "etsy", "royalty_pct": 0.93, "fees": 0.20, "price": 5.99, "color": "#F97316",
        "product": "printable / template / SVG",
        "product_types": ["printable", "digital planner", "template", "SVG bundle", "wall art"],
        "kindle_alias": "aps"
    }
}

# ── CACHE & USAGE DATABASE ─────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("quantdrop.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_cache (
            cache_key TEXT PRIMARY KEY, data TEXT NOT NULL, fetched_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS api_usage (
            source TEXT, calls INTEGER, month TEXT, PRIMARY KEY(source, month)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT, keyword TEXT, platform TEXT,
            final_score REAL, final_verdict TEXT, royalty REAL, stressed_royalty REAL,
            product_name TEXT, created_at TEXT
        )
    """)
    conn.commit()
    conn.close()
init_db()

def cache_key(source, keyword):
    return hashlib.md5(f"{source}:{keyword.lower().strip()}".encode()).hexdigest()

def cache_get(source, keyword, ttl_days=7):
    key = cache_key(source, keyword)
    try:
        conn = sqlite3.connect("quantdrop.db")
        row = conn.execute("SELECT data, fetched_at FROM api_cache WHERE cache_key=?", (key,)).fetchone()
        conn.close()
        if row:
            age = datetime.now() - datetime.fromisoformat(row[1])
            if age < timedelta(days=ttl_days):
                return json.loads(row[0])
    except: pass
    return None

def cache_set(source, keyword, data):
    key = cache_key(source, keyword)
    try:
        conn = sqlite3.connect("quantdrop.db")
        conn.execute("INSERT OR REPLACE INTO api_cache VALUES (?,?,?)", (key, json.dumps(data), datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except: pass

def increment_usage(source):
    try:
        conn = sqlite3.connect("quantdrop.db")
        month = datetime.now().strftime("%Y-%m")
        conn.execute("""
            INSERT INTO api_usage (source, calls, month) VALUES (?, 1, ?)
            ON CONFLICT(source, month) DO UPDATE SET calls = calls + 1
        """, (source, month))
        conn.commit()
        conn.close()
    except: pass

def get_usage(source):
    try:
        conn = sqlite3.connect("quantdrop.db")
        month = datetime.now().strftime("%Y-%m")
        row = conn.execute("SELECT calls FROM api_usage WHERE source=? AND month=?", (source, month)).fetchone()
        conn.close()
        return row[0] if row else 0
    except: return 0

def save_analysis(keyword, platform, score, verdict, royalty, stressed, name):
    try:
        conn = sqlite3.connect("quantdrop.db")
        conn.execute("INSERT INTO analyses VALUES (NULL,?,?,?,?,?,?,?,?)",
            (keyword, platform, score, verdict, royalty, stressed, name, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except: pass

def load_history():
    try:
        conn = sqlite3.connect("quantdrop.db")
        rows = conn.execute("SELECT keyword,platform,final_score,final_verdict,product_name,created_at FROM analyses ORDER BY id DESC LIMIT 20").fetchall()
        conn.close()
        return rows
    except: return []

# ── API KEY HELPERS ────────────────────────────────────────────────────────────
def get_secret(key, fallback=""):
    try: return st.secrets[key]
    except: return fallback

# ── DATA FETCHERS (All cached + usage tracked) ─────────────────────────────────
def fetch_google_autocomplete(keyword):
    cached = cache_get("google_auto", keyword)
    if cached: return cached, True
    key = get_secret("SERPAPI_KEY")
    if not key: return [], False
    try:
        r = requests.get("https://serpapi.com/search", params={"engine": "google_autocomplete", "q": keyword, "api_key": key}, timeout=10)
        sugs = [s.get("value", "") for s in r.json().get("suggestions", [])]
        cache_set("google_auto", keyword, sugs)
        increment_usage("serpapi")
        return sugs, False
    except: return [], False

def fetch_amazon_search(keyword):
    cached = cache_get("amazon_search", keyword)
    if cached: return cached, True
    key = get_secret("SERPAPI_KEY")
    if not key: return {"count": 0, "top_results": []}, False
    try:
        r = requests.get("https://serpapi.com/search", params={"engine": "amazon", "q": keyword, "api_key": key}, timeout=12)
        data = r.json()
        results = data.get("organic_results", [])
        out = {
            "count": len(results),
            "top_results": [{"title": x.get("title",""), "rating": x.get("rating",0), "reviews": x.get("reviews",0), "price": x.get("price","")} for x in results[:5]]
        }
        cache_set("amazon_search", keyword, out)
        increment_usage("serpapi")
        return out, False
    except: return {"count": 0, "top_results": []}, False

def fetch_google_trends(keyword):
    cached = cache_get("trends", keyword)
    if cached: return cached, True
    scraper_key = get_secret("SCRAPERAPI_KEY")
    try:
        from pytrends.request import TrendReq
        proxies = {}
        if scraper_key:
            proxy_url = f"http://scraperapi:{scraper_key}@proxy-server.scraperapi.com:8001"
            proxies = {"https": proxy_url, "http": proxy_url}
        pt = TrendReq(hl="en-US", tz=360, proxies=proxies, retries=2, backoff_factor=0.5, timeout=(10,25))
        time.sleep(random.uniform(3,6))
        pt.build_payload([keyword], timeframe="today 12-m", geo="US")
        df = pt.interest_over_time()
        if df.empty or keyword not in df.columns:
            out = {"slope": 0, "current": 0, "avg": 0, "status": "no_data"}
        else:
            vals = df[keyword].dropna().values
            slope = float(np.polyfit(range(len(vals)), vals, 1)[0])
            out = {"slope": round(slope,4), "current": int(vals[-1]), "avg": round(float(vals.mean()),1), "peak": int(vals.max()), "status": "ok"}
        cache_set("trends", keyword, out)
        increment_usage("scraperapi")
        return out, False
    except Exception as e:
        out = {"slope": 0, "current": 0, "avg": 0, "status": f"error:{str(e)[:40]}"}
        return out, False

def fetch_reddit_complaints(keyword):
    cached = cache_get("reddit", keyword)
    if cached: return cached, True
    client_id = get_secret("REDDIT_CLIENT_ID")
    client_secret = get_secret("REDDIT_CLIENT_SECRET")
    try:
        if client_id and client_secret:
            import praw
            reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=get_secret("REDDIT_USER_AGENT", "QuantDrop/4.1"))
            bad = ["bad","worst","hate","missing","broken","cheap","disappointed","flimsy","thin","generic","useless","poor"]
            complaints = [p.title[:90] for p in reddit.subreddit("all").search(f"{keyword} complaint review", limit=20, sort="relevance") if any(w in p.title.lower() for w in bad)][:3]
        else:
            r = requests.get("https://www.reddit.com/search.json", params={"q": f"{keyword} bad complaint review", "limit": 15}, headers={"User-Agent": "QuantDrop/4.1"}, timeout=10)
            posts = r.json().get("data", {}).get("children", [])
            bad = ["bad","worst","hate","missing","broken","cheap","disappointed","flimsy","thin","generic","useless"]
            complaints = [p["data"]["title"][:90] for p in posts if any(w in p["data"].get("title","").lower() for w in bad)][:3]
        cache_set("reddit", keyword, complaints)
        return complaints, False
    except: return [], False

def call_gemini(keyword, platform_cfg, complaints):
    cached = cache_get("gemini", f"{keyword}:{platform_cfg['id']}")
    if cached: return cached, True
    key = get_secret("GEMINI_API_KEY")
    fix = complaints[0] if complaints else "improve overall quality"
    prompt = f'You are a digital product designer for {platform_cfg["product"]}.\nKeyword: "{keyword}"\nFix complaint: "{fix}"\nReturn ONLY valid JSON, no markdown:\n{{"product_name":"...","tagline":"...","color_palette":["#hex","#hex","#hex"],"cover_style":"...","key_features":["...","...","..."],"unique_angle":"...","target_buyer":"..."}}'
    if key:
        try:
            # Ordered model: gemini-3.1-flash-lite
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={key}",
                json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.85, "maxOutputTokens": 512}},
                timeout=20
            )
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip().replace("```json","").replace("```","").strip()
            design = json.loads(text)
            cache_set("gemini", f"{keyword}:{platform_cfg['id']}", design)
            return design, False
        except: pass
    # Smart fallback
    fallback = {
        "product_name": f"The {keyword.title()} Blueprint", "tagline": f"The only {keyword} built from real buyer feedback",
        "color_palette": ["#1A1A2E","#6C5CE7","#FDCB6E"], "cover_style": "Dark premium cover with geometric accent",
        "key_features": [f"Solves: {fix[:55]}", "Undated format", "Science-backed prompts"],
        "unique_angle": "Designed around top buyer complaints", "target_buyer": "Adults 25–45"
    }
    cache_set("gemini", f"{keyword}:{platform_cfg['id']}", fallback)
    return fallback, False

# ── SCORING ENGINE (Weighted: Econ 40%, Demand 30%, Trend 20%, Sentiment 10%) ─
def score_economics(platform_cfg):
    pid = platform_cfg["id"]
    if pid == "kdp":
        price = platform_cfg["price"]
        royalty = price * platform_cfg["royalty_pct"] - platform_cfg["fees"]
        stressed = price * 0.80 * platform_cfg["royalty_pct"] - platform_cfg["fees"]
    elif pid == "mba":
        price = platform_cfg["price"]
        royalty = platform_cfg["royalty_flat"]
        stressed = platform_cfg["royalty_flat"] * 0.72
    else:
        price = platform_cfg["price"]
        royalty = price * platform_cfg["royalty_pct"] - platform_cfg["fees"]
        stressed = price * 0.72 * platform_cfg["royalty_pct"] - platform_cfg["fees"]
    margin = royalty / price
    s_margin = stressed / (price * 0.80)
    score = 40 if s_margin >= 0.35 else 35 if s_margin >= 0.25 else 28 if s_margin >= 0.20 else 18 if s_margin >= 0.12 else 6
    return {"score": score, "max": 40, "verdict": "GO" if score >= 28 else "REVIEW" if score >= 18 else "KILL",
            "royalty": round(royalty,2), "stressed_royalty": round(stressed,2), "margin": round(margin*100,1),
            "stressed_margin": round(s_margin*100,1), "monthly_for_500": round(500/royalty) if royalty>0 else 999}

def score_demand(google_sugs, amazon_data, trends):
    g_count = len(google_sugs)
    a_count = amazon_data.get("count", 0)
    g_score = min(12, g_count * 1.5)
    a_score = min(12, a_count * 2.4)
    top = amazon_data.get("top_results", [])
    avg_rev = sum(r.get("reviews",0) for r in top) / len(top) if top else 0
    rev_score = 6 if avg_rev > 500 else 4 if avg_rev > 100 else 2 if avg_rev > 10 else 0
    score = min(30, round(g_score + a_score + rev_score))
    return {"score": score, "max": 30, "verdict": "GO" if score >= 20 else "REVIEW" if score >= 12 else "KILL",
            "google_count": g_count, "amazon_count": a_count, "avg_reviews": round(avg_rev)}

def score_trend(trends):
    if trends.get("status") != "ok": return {"score": 10, "max": 20, "verdict": "REVIEW", "note": "Trend data unavailable"}
    slope, current, avg = trends["slope"], trends["current"], trends["avg"]
    slope_s = 10 if slope >= 1.0 else 8 if slope >= 0.3 else 6 if slope >= 0.0 else 3 if slope >= -0.5 else 0
    now_s = 10 if avg > 0 and current/avg >= 1.3 else 7 if avg > 0 and current/avg >= 1.0 else 4 if avg > 0 and current/avg >= 0.7 else 1 if avg > 0 else 5
    score = min(20, slope_s + now_s)
    return {"score": score, "max": 20, "verdict": "GO" if score >= 14 else "REVIEW" if score >= 8 else "KILL",
            "slope": slope, "current": current, "avg": avg, "note": "ok"}

def score_sentiment(complaints):
    score = 10 if len(complaints) >= 3 else 8 if len(complaints) == 2 else 5 if len(complaints) == 1 else 3
    return {"score": score, "max": 10, "verdict": "GO" if score >= 7 else "REVIEW",
            "complaints": complaints, "opportunity": f"Fix: {complaints[0][:65]}" if complaints else "No clear gap found"}

def compute_final(econ, demand, trend, sentiment):
    total = econ["score"] + demand["score"] + trend["score"] + sentiment["score"]
    score = min(100, round(total))
    if econ["verdict"] == "KILL": return score, "KILL", "Economics fail — margin too thin"
    verdict = "GO" if score >= 70 else "REVIEW" if score >= 45 else "KILL"
    msgs = {"GO": "Validated — create and publish now", "REVIEW": "Promising — refine keyword", "KILL": "Low signal — find better niche"}
    return score, verdict, msgs[verdict]

# ── LISTING GENERATOR ──────────────────────────────────────────────────────────
def generate_listing(keyword, platform_id, design):
    name, tagline, features, buyer = design.get("product_name", keyword), design.get("tagline", ""), design.get("key_features", []), design.get("target_buyer", "Adults")
    core = " ".join(w for w in keyword.lower().split() if w not in {"for","the","and","2025","2026","with","a","an"})[:40]
    if platform_id == "kdp":
        return {"title": f"{name}: {tagline}"[:200], "bullets": [f"✓ {f}" for f in features],
                "description": f"Designed for {buyer.lower()}, {name} solves the #1 complaint buyers have with existing {keyword} products. {tagline}. Undated — start any day.",
                "keywords": [core, f"best {core}", f"{core} 2026", f"daily {core}", f"{core} gift", f"{core} women", f"{core} men"]}
    elif platform_id == "mba":
        return {"title": f"{name} | {tagline}"[:60], "bullets": features,
                "tags": [core, "funny", "gift", "novelty", "quote", buyer.split()[0].lower() if buyer else "adult"]}
    else:
        return {"title": f"{name} | {tagline} | Digital Download | {keyword.title()} Printable"[:140],
                "tags": [core, f"{core} printable", "digital download", "instant download", "pdf planner", "self care", "mindfulness", "printable pdf", "letter size", "a4 size", "gift idea", keyword.split()[0] if keyword.split() else core][:13],
                "description": f"Instant digital download. {tagline}. Print at home. {features[0] if features else ''}"}

# ── UI HELPERS ─────────────────────────────────────────────────────────────────
def vc(v): return {"GO":"#00FF88","REVIEW":"#FFD166","KILL":"#FF4757"}.get(v,"#6B8BA4")
def ve(v): return {"GO":"✅","REVIEW":"⚠️","KILL":"❌"}.get(v,"—")

def render_phase(col, num, name, score, max_score, verdict):
    color, pct = vc(verdict), round(score / max_score * 100)
    col.markdown(f"""<div class="phase-card {verdict.lower()}">
      <div style="font-family:'Space Mono',monospace;font-size:9px;color:#6B8BA4;text-transform:uppercase;letter-spacing:.08em">Phase {num}</div>
      <div style="font-size:12px;font-weight:600;color:#E8F4FF;margin:4px 0">{name}</div>
      <div style="font-family:'Space Mono',monospace;font-size:20px;font-weight:700;color:{color}">{score}<span style="font-size:11px;color:#6B8BA4">/{max_score}</span></div>
      <div style="height:3px;background:#1E2B38;border-radius:2px;margin-top:7px;overflow:hidden"><div style="height:100%;width:{pct}%;background:{color};border-radius:2px"></div></div>
    </div>""", unsafe_allow_html=True)

def render_signal_bar(label, value, max_val, color):
    pct = min(100, round(value / max_val * 100)) if max_val > 0 else 0
    return f'<div style="display:flex;align-items:center;gap:8px;font-size:12px;color:#6B8BA4;padding:5px 0;border-bottom:1px solid #1E2B38"><span style="min-width:150px">{label}</span><div style="flex:1;height:4px;background:#1E2B38;border-radius:2px;overflow:hidden"><div style="height:100%;width:{pct}%;background:{color};border-radius:2px"></div></div><span style="font-family:Space Mono,monospace;font-weight:700;color:#E8F4FF;min-width:28px;text-align:right">{value}</span></div>'

# ── MAIN APP ───────────────────────────────────────────────────────────────────
def main():
    st.markdown("""<div style="text-align:center;padding:28px 0 12px">
      <div style="font-family:'Space Mono',monospace;font-size:12px;color:#00D4FF;letter-spacing:.15em;text-transform:uppercase;margin-bottom:10px">Profit-First · $0 Capital · All Free APIs</div>
      <h1 style="font-family:'Syne',sans-serif;font-size:46px;font-weight:800;background:linear-gradient(135deg,#E8F4FF,#00D4FF,#FF6B35);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:0 0 8px">QuantDrop v4.1</h1>
      <p style="color:#6B8BA4;font-size:14px;max-width:500px;margin:0 auto;line-height:1.6">5-phase quant validation — scores profit potential. All data cached 7 days to protect free API credits.</p>
    </div>""", unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("<div style='font-family:Space Mono,monospace;font-size:13px;color:#00D4FF;font-weight:700;margin-bottom:14px'>⚙ CONFIG</div>", unsafe_allow_html=True)
        keys_status = {"SerpAPI": bool(get_secret("SERPAPI_KEY")), "Reddit": bool(get_secret("REDDIT_CLIENT_ID")), "ScraperAPI": bool(get_secret("SCRAPERAPI_KEY")), "Gemini": bool(get_secret("GEMINI_API_KEY"))}
        for name, ok in keys_status.items():
            st.markdown(f"<div style='font-family:Space Mono,monospace;font-size:11px;color:{'#00FF88' if ok else '#FF4757'}'>{'🟢' if ok else '🔴'} {name} — {'connected' if ok else 'missing'}</div>", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("""<div style='font-family:Space Mono,monospace;font-size:10px;color:#6B8BA4;line-height:1.9'><b style='color:#E8F4FF'>SCORING WEIGHTS</b><br>Economics 40% — margin first<br>Demand 30% — buyers exist<br>Trend 20% — niche growing<br>Sentiment 10% — gap to fill<br><br><b style='color:#E8F4FF'>CACHE TTL</b><br>All API calls: 7 days<br>Gemini design: 30 days<br><br><b style='color:#E8F4FF'>FREE LIMITS/MO</b><br>SerpAPI: 100 calls<br>ScraperAPI: 5000 calls<br>Gemini: 1500/day</div>""", unsafe_allow_html=True)
        # Usage tracking
        serp_used = get_usage("serpapi"); scraper_used = get_usage("scraperapi")
        st.markdown(f"""<div style='font-family:Space Mono,monospace;font-size:10px;color:#6B8BA4'><b style='color:#E8F4FF'>API USAGE THIS MONTH</b><br>SerpAPI: {serp_used}/100 calls<br>ScraperAPI: {scraper_used}/5000 calls<br><span style='color:#00FF88'>→ Est. keywords validated: {(serp_used*7) + (scraper_used//10)}</span></div>""", unsafe_allow_html=True)
        if st.button("Clear Cache"):
            try:
                conn = sqlite3.connect("quantdrop.db"); conn.execute("DELETE FROM api_cache"); conn.commit(); conn.close()
                st.success("Cache cleared")
            except: pass

    c1, c2, c3 = st.columns([3, 2, 1])
    with c1: keyword = st.text_input("keyword", placeholder="e.g. gratitude journal women", label_visibility="collapsed")
    with c2: platform_name = st.selectbox("platform", list(PLATFORMS.keys()), label_visibility="collapsed")
    with c3: run = st.button("Analyze →")
    cfg = PLATFORMS[platform_name]; pid = cfg["id"]

    # Batch mode
    with st.expander("📦 Batch Mode — analyze multiple keywords"):
        batch_text = st.text_area("One keyword per line", placeholder="gratitude journal\ndaily planner 2026", height=100, label_visibility="collapsed")
        run_batch = st.button("Run Batch →")

    st.markdown("---")

    # Single analysis
    if run and keyword.strip():
        kw = keyword.strip().lower()
        _run_single(kw, platform_name, cfg, pid)

    # Batch analysis
    if run_batch and batch_text.strip():
        keywords = [k.strip().lower() for k in batch_text.strip().split("\n") if k.strip()]
        st.markdown(f"### Batch Results — {len(keywords)} keywords")
        progress = st.progress(0); batch_out = []
        for i, kw in enumerate(keywords):
            progress.progress((i+1)/len(keywords), text=f"Analyzing: {kw}")
            try:
                econ = score_economics(cfg)
                g_sugs, _ = fetch_google_autocomplete(kw)
                az_data, _ = fetch_amazon_search(kw)
                trends, _ = fetch_google_trends(kw)
                complaints, _ = fetch_reddit_complaints(kw)
                demand = score_demand(g_sugs, az_data, trends)
                trend_s = score_trend(trends)
                sentiment = score_sentiment(complaints)
                final, verdict, _ = compute_final(econ, demand, trend_s, sentiment)
                design, _ = call_gemini(kw, cfg, complaints)
                batch_out.append({"keyword": kw, "score": final, "verdict": verdict, "royalty": econ["royalty"], "s_margin": econ["stressed_margin"], "demand": demand["score"], "trend_slope": trends.get("slope",0), "product_name": design.get("product_name",""), "complaints": len(complaints)})
                save_analysis(kw, platform_name, final, verdict, econ["royalty"], econ["stressed_royalty"], design.get("product_name",""))
            except Exception as e:
                batch_out.append({"keyword": kw, "score": 0, "verdict": "ERROR", "royalty": 0, "s_margin": 0, "demand": 0, "trend_slope": 0, "product_name": str(e), "complaints": 0})
        progress.empty()
        import pandas as pd
        df = pd.DataFrame(batch_out).sort_values("score", ascending=False)
        def color_verdict(v): return f"color: {({'GO':'#00FF88','REVIEW':'#FFD166','KILL':'#FF4757'}).get(v,'#6B8BA4')}"
        st.dataframe(df.style.applymap(lambda v: color_verdict(v), subset=["verdict"]), use_container_width=True)
        st.download_button("📥 Download CSV", df.to_csv(index=False), f"quantdrop_batch_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", "text/csv")

    # History
    history = load_history()
    if history:
        st.markdown('<div class="section-header">Analysis History</div>', unsafe_allow_html=True)
        cols = st.columns([2,2,1,1,2,1])
        for col, h in zip(cols, ["Keyword","Platform","Score","Verdict","Product","Date"]):
            col.markdown(f"<div style='font-family:Space Mono,monospace;font-size:10px;color:#6B8BA4;text-transform:uppercase;letter-spacing:.06em'>{h}</div>", unsafe_allow_html=True)
        for row in history:
            kw, pl, sc, vd, pn, dt = row; color = vc(vd)
            c1,c2,c3,c4,c5,c6 = st.columns([2,2,1,1,2,1])
            c1.markdown(f"<div style='font-size:12px;color:#E8F4FF;font-weight:600'>{kw}</div>", unsafe_allow_html=True)
            c2.markdown(f"<div style='font-family:Space Mono,monospace;font-size:10px;color:#6B8BA4'>{pl.split('—')[0].strip()}</div>", unsafe_allow_html=True)
            c3.markdown(f"<div style='font-family:Space Mono,monospace;font-size:13px;font-weight:700;color:{color}'>{sc}</div>", unsafe_allow_html=True)
            c4.markdown(f"<div style='font-family:Space Mono,monospace;font-size:11px;font-weight:700;color:{color}'>{vd}</div>", unsafe_allow_html=True)
            c5.markdown(f"<div style='font-size:11px;color:#6B8BA4'>{pn or '—'}</div>", unsafe_allow_html=True)
            c6.markdown(f"<div style='font-family:Space Mono,monospace;font-size:10px;color:#6B8BA4'>{dt[:10] if dt else '—'}</div>", unsafe_allow_html=True)

    st.markdown("""<div style="text-align:center;padding:28px 0 12px;border-top:1px solid #1E2B38;margin-top:40px"><div style="font-family:'Space Mono',monospace;font-size:11px;color:#6B8BA4">QuantDrop v4.1 · <span style="color:#00D4FF">All free APIs</span> · <span style="color:#FF6B35">7-day local cache</span> · Built by a quant</div></div>""", unsafe_allow_html=True)

# ── SINGLE RUN HELPER ──────────────────────────────────────────────────────────
def _run_single(kw, platform_name, cfg, pid):
    progress = st.progress(0)
    progress.progress(10, text="Phase 1 — stress testing economics...")
    econ = score_economics(cfg)
    if econ["verdict"] == "KILL":
        progress.empty()
        st.markdown(f"""<div class="verdict-kill"><div style="font-family:'Space Mono',monospace;font-size:22px;font-weight:700;color:#FF4757">❌ KILL — Economics Fail</div><div style="font-size:13px;color:#6B8BA4;margin-top:4px">Stressed margin {econ['stressed_margin']}% is too thin. Platform {pid.upper()} not viable for this niche.</div></div>""", unsafe_allow_html=True)
        return
    progress.progress(28, text="Phase 2 — fetching demand signals (SerpAPI)...")
    g_sugs, g_cached = fetch_google_autocomplete(kw)
    az_data, a_cached = fetch_amazon_search(kw)
    demand = score_demand(g_sugs, az_data, {})
    progress.progress(50, text="Phase 3 — reading trend curve (Google Trends)...")
    trends, t_cached = fetch_google_trends(kw)
    trend_s = score_trend(trends)
    progress.progress(68, text="Phase 4 — mining Reddit complaints...")
    complaints, r_cached = fetch_reddit_complaints(kw)
    sentiment = score_sentiment(complaints)
    progress.progress(82, text="Phase 5 — generating AI design (Gemini 3.1 Flash Lite)...")
    design, d_cached = call_gemini(kw, cfg, complaints)
    listing = generate_listing(kw, pid, design)
    final, verdict, msg = compute_final(econ, demand, trend_s, sentiment)
    save_analysis(kw, platform_name, final, verdict, econ["royalty"], econ["stressed_royalty"], design.get("product_name",""))
    progress.progress(100, text="Done!"); time.sleep(0.3); progress.empty()

    # Cache indicators
    cache_info = []; 
    if g_cached or a_cached: cache_info.append("demand")
    if t_cached: cache_info.append("trends")
    if r_cached: cache_info.append("reddit")
    if d_cached: cache_info.append("design")
    if cache_info:
        st.markdown(f"<div style='font-family:Space Mono,monospace;font-size:10px;color:#6B8BA4;margin-bottom:8px'>🗄 Loaded from cache (0 API credits used): {', '.join(cache_info)}</div>", unsafe_allow_html=True)

    # Verdict banner
    color = vc(verdict)
    st.markdown(f"""<div class="verdict-{verdict.lower()}"><div style="display:flex;align-items:center;justify-content:space-between"><div><div style="font-family:'Space Mono',monospace;font-size:22px;font-weight:700;color:{color};letter-spacing:.06em">{ve(verdict)} {verdict}</div><div style="font-size:13px;color:#6B8BA4;margin-top:4px">{msg} · Platform: {pid.upper()}</div></div><div style="font-family:'Space Mono',monospace;font-size:50px;font-weight:700;color:{color}">{final}<span style="font-size:20px;color:#6B8BA4">/100</span></div></div></div>""", unsafe_allow_html=True)

    # Phase scores
    st.markdown('<div class="section-header">Pipeline Scores</div>', unsafe_allow_html=True)
    p1c,p2c,p3c,p4c = st.columns(4)
    render_phase(p1c, 1, "Economics", econ["score"], 40, econ["verdict"])
    render_phase(p2c, 2, "Demand", demand["score"], 30, demand["verdict"])
    render_phase(p3c, 3, "Trend", trend_s["score"], 20, trend_s["verdict"])
    render_phase(p4c, 4, "Sentiment", sentiment["score"], 10, sentiment["verdict"])

    # Economics + Signals
    st.markdown('<div class="section-header">Economics & Market Signals</div>', unsafe_allow_html=True)
    ec_col, sig_col = st.columns(2)
    with ec_col:
        sm_c = "#00FF88" if econ["stressed_margin"] >= 25 else "#FFD166" if econ["stressed_margin"] >= 15 else "#FF4757"
        st.markdown(f"""<div class="phase-card"><div style="font-family:'Space Mono',monospace;font-size:9px;color:#6B8BA4;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px">Unit Economics — {pid.upper()}</div><table style="width:100%;border-collapse:collapse"><tr style="border-bottom:1px solid #1E2B38"><td style="color:#6B8BA4;font-size:12px;padding:5px 0">Base royalty/sale</td><td style="font-family:Space Mono,monospace;font-weight:700;color:#E8F4FF;text-align:right;font-size:13px">${econ['royalty']}</td></tr><tr style="border-bottom:1px solid #1E2B38"><td style="color:#6B8BA4;font-size:12px;padding:5px 0">Stressed royalty</td><td style="font-family:Space Mono,monospace;font-weight:700;color:#FFD166;text-align:right;font-size:13px">${econ['stressed_royalty']}</td></tr><tr style="border-bottom:1px solid #1E2B38"><td style="color:#6B8BA4;font-size:12px;padding:5px 0">Base margin</td><td style="font-family:Space Mono,monospace;font-weight:700;color:#E8F4FF;text-align:right">{econ['margin']}%</td></tr><tr style="border-bottom:1px solid #1E2B38"><td style="color:#6B8BA4;font-size:12px;padding:5px 0">Stressed margin</td><td style="font-family:Space Mono,monospace;font-weight:700;color:{sm_c};text-align:right">{econ['stressed_margin']}%</td></tr><tr style="border-bottom:1px solid #1E2B38"><td style="color:#6B8BA4;font-size:12px;padding:5px 0">Sales for $500/mo</td><td style="font-family:Space Mono,monospace;font-weight:700;color:#E8F4FF;text-align:right">{econ['monthly_for_500']}</td></tr><tr><td style="color:#6B8BA4;font-size:12px;padding:5px 0">Sales for $1000/mo</td><td style="font-family:Space Mono,monospace;font-weight:700;color:#E8F4FF;text-align:right">{econ['monthly_for_1000']}</td></tr></table></div>""", unsafe_allow_html=True)
    with sig_col:
        trend_color = "#00FF88" if trend_s["slope"] > 0 else "#FF4757"
        trend_label = f"↑ {trend_s['slope']:+.2f}/wk" if trends.get("status")=="ok" else "no data"
        signals_html = (render_signal_bar("Google suggestions", demand["google_count"], 10, "#00D4FF") + render_signal_bar("Amazon results", demand["amazon_count"], 10, "#7C3AED") + render_signal_bar("Avg page-1 reviews", min(demand["avg_reviews"],1000), 1000, "#F97316") + render_signal_bar("Trend current", trends.get("current",0), 100, trend_color) + render_signal_bar("Sentiment gaps", sentiment["score"], 10, "#FF6B35"))
        st.markdown(f"""<div class="phase-card"><div style="font-family:'Space Mono',monospace;font-size:9px;color:#6B8BA4;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px">Market Signals &nbsp;<span style="color:{trend_color}">{trend_label}</span></div>{signals_html}</div>""", unsafe_allow_html=True)

    # Trend detail
    if trends.get("status") == "ok":
        st.markdown('<div class="section-header">Google Trends — 12 Month View</div>', unsafe_allow_html=True)
        tc1,tc2,tc3,tc4 = st.columns(4)
        for col, label, val, color in [(tc1,"Current Interest",trends["current"],trend_color),(tc2,"12M Average",trends["avg"],"#6B8BA4"),(tc3,"Peak Interest",trends["peak"],"#00D4FF"),(tc4,"Weekly Slope",f"{trends['slope']:+.3f}",trend_color)]:
            col.markdown(f"""<div class="phase-card" style="text-align:center"><div style="font-family:Space Mono,monospace;font-size:9px;color:#6B8BA4;text-transform:uppercase;margin-bottom:6px">{label}</div><div style="font-family:Space Mono,monospace;font-size:22px;font-weight:700;color:{color}">{val}</div></div>""", unsafe_allow_html=True)

    # Sentiment
    st.markdown('<div class="section-header">Competitor Gaps → Your Product Edge</div>', unsafe_allow_html=True)
    complaints_html = "".join([f'<div class="complaint">"{c}"</div>' for c in sentiment["complaints"]]) or '<div class="complaint">No specific complaints found — niche may be too broad</div>'
    st.markdown(f"""<div class="phase-card">{complaints_html}<div class="opportunity">→ {sentiment['opportunity']}</div></div>""", unsafe_allow_html=True)

    # AI Design
    cache_tag = '<span class="cache-badge">from cache</span>' if d_cached else ""
    swatches = "".join(f'<span style="display:inline-block;width:24px;height:24px;border-radius:50%;background:{c};border:2px solid #2A3D52;margin-right:4px"></span>' for c in design.get("color_palette",[]))
    features_html = "".join(f'<li style="font-size:12px;color:#6B8BA4;padding:3px 0;list-style:none">→ {f}</li>' for f in design.get("key_features",[]))
    st.markdown(f"""<div class="design-card"><div style="font-family:'Space Mono',monospace;font-size:9px;color:#00D4FF;letter-spacing:.12em;text-transform:uppercase;margin-bottom:8px">✦ GEMINI 3.1 FLASH LITE — AI PRODUCT DESIGN {cache_tag}</div><div style="font-size:26px;font-weight:800;color:#E8F4FF;margin-bottom:4px">{design.get('product_name','—')}</div><div style="font-size:13px;color:#6B8BA4;font-style:italic;margin-bottom:14px">"{design.get('tagline','—')}"</div><div style="margin-bottom:12px">{swatches}</div><div style="font-family:Space Mono,monospace;font-size:9px;color:#6B8BA4;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">Key Features</div><ul style="margin:0;padding:0">{features_html}</ul><div style="margin-top:10px;font-size:12px;color:#6B8BA4"><span style="color:#00D4FF;font-weight:600">Unique angle:</span> {design.get('unique_angle','—')}</div><div style="margin-top:6px;font-size:12px;color:#6B8BA4"><span style="color:#00D4FF;font-weight:600">Target buyer:</span> {design.get('target_buyer','—')}</div><div style="margin-top:6px;font-size:12px;color:#6B8BA4"><span style="color:#00D4FF;font-weight:600">Cover style:</span> {design.get('cover_style','—')}</div></div>""", unsafe_allow_html=True)

    # Listing copy
    st.markdown('<div class="section-header">Ready-to-Publish Listing Copy</div>', unsafe_allow_html=True)
    with st.expander("📋 Expand listing copy", expanded=True):
        st.markdown(f"""<div class="phase-card"><div style="font-family:Space Mono,monospace;font-size:9px;color:#6B8BA4;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">Title</div><div style="font-family:Space Mono,monospace;font-size:13px;color:#00D4FF;line-height:1.5;margin-bottom:14px;word-break:break-word">{listing['title']}</div>""", unsafe_allow_html=True)
        if listing.get("bullets"):
            st.markdown("""<div style="font-family:Space Mono,monospace;font-size:9px;color:#6B8BA4;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">Bullet Points</div>""", unsafe_allow_html=True)
            for b in listing["bullets"]: st.markdown(f'<div class="complaint" style="border-color:#00FF88">{b}</div>', unsafe_allow_html=True)
        if listing.get("description"):
            st.markdown(f"""<div style="font-family:Space Mono,monospace;font-size:9px;color:#6B8BA4;text-transform:uppercase;letter-spacing:.08em;margin:12px 0 6px">Description</div><div style="font-size:12px;color:#6B8BA4;line-height:1.7">{listing['description']}</div>""", unsafe_allow_html=True)
        tags = listing.get("keywords") or listing.get("tags") or []
        if tags:
            label = "Keywords" if pid == "kdp" else "Tags"
            tags_html = "".join(f'<span class="tag">{t}</span>' for t in tags)
            st.markdown(f"""<div style="font-family:Space Mono,monospace;font-size:9px;color:#6B8BA4;text-transform:uppercase;letter-spacing:.08em;margin:12px 0 6px">{label}</div><div>{tags_html}</div>""", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Amazon page 1 intel
    top_results = az_data.get("top_results", []) if "az_data" in dir() else []
    if top_results:
        st.markdown('<div class="section-header">Page 1 Competition Intel</div>', unsafe_allow_html=True)
        for i, r in enumerate(top_results[:3]):
            rev_color = "#00FF88" if r.get("reviews",0) < 100 else "#FFD166" if r.get("reviews",0) < 500 else "#FF4757"
            st.markdown(f"""<div class="phase-card" style="margin-bottom:6px"><div style="font-size:12px;color:#E8F4FF;font-weight:600;margin-bottom:4px">#{i+1} {r.get('title','')[:70]}</div><div style="display:flex;gap:16px;font-family:Space Mono,monospace;font-size:11px"><span style="color:#6B8BA4">Price: <b style="color:#E8F4FF">{r.get('price','—')}</b></span><span style="color:#6B8BA4">Rating: <b style="color:#FFD166">{r.get('rating','—')}★</b></span><span style="color:#6B8BA4">Reviews: <b style="color:{rev_color}">{r.get('reviews',0):,}</b></span>{'<span style="color:#00FF88;font-size:10px">← LOW COMPETITION</span>' if r.get("reviews",0) < 100 else ''}</div></div>""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
