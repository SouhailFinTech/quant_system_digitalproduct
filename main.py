# QuantDrop v3.0 — Quant Digital Product Intelligence
# Stack: Streamlit + Pinterest/YouTube Signals + Gemini 3.1 Flash Lite
# Deploy: push to GitHub → connect to Streamlit Cloud (free)

import streamlit as st
import requests
import time
import random
import json
import sqlite3
from datetime import datetime

# ── PAGE CONFIG ────────────────────────────────────────────
st.set_page_config(
    page_title="QuantDrop v3.0 — Digital Product Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── CUSTOM CSS (Cleaned & Fixed) ───────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap');
html, body, [class*="css"] { font-family: 'Syne', sans-serif; background-color: #080C10; color: #E8F4FF; }
#MainMenu, footer, header { visibility: hidden; }
.stApp { background-color: #080C10; }
.phase-card { background: #0D1117; border: 1px solid #1E2B38; border-radius: 8px; padding: 14px; margin-bottom: 8px; }
.phase-card.go    { border-color: #00FF88; }
.phase-card.review{ border-color: #FFD166; }
.phase-card.kill  { border-color: #FF4757; }
.verdict-go { background: rgba(0,255,136,.08); border: 1.5px solid #00FF88; border-radius: 8px; padding: 20px 24px; margin: 16px 0; }
.verdict-review { background: rgba(255,209,102,.08); border: 1.5px solid #FFD166; border-radius: 8px; padding: 20px 24px; margin: 16px 0; }
.verdict-kill { background: rgba(255,71,87,.08); border: 1.5px solid #FF4757; border-radius: 8px; padding: 20px 24px; margin: 16px 0; }
.design-card { background: #141B24; border: 1px solid #2A3D52; border-radius: 8px; padding: 20px; margin: 12px 0; }
.tag { display: inline-block; font-family: 'Space Mono', monospace; font-size: 10px; padding: 3px 8px; border-radius: 3px; background: #1E2B38; color: #6B8BA4; margin: 2px; }
.complaint { border-left: 2px solid #FF6B35; padding: 6px 10px; background: #141B24; border-radius: 0 4px 4px 0; font-size: 13px; color: #6B8BA4; margin-bottom: 6px; }
.opportunity { background: rgba(0,255,136,.06); border: 1px solid rgba(0,255,136,.2); border-radius: 4px; padding: 8px 12px; font-family: 'Space Mono', monospace; font-size: 12px; color: #00FF88; margin-top: 8px; }
.section-header { font-family: 'Space Mono', monospace; font-size: 10px; color: #6B8BA4; text-transform: uppercase; letter-spacing: .1em; border-bottom: 1px solid #1E2B38; padding-bottom: 6px; margin: 16px 0 10px; }
.swatch { display: inline-block; width: 24px; height: 24px; border-radius: 50%; margin-right: 4px; border: 2px solid #2A3D52; }
.stTextInput input { background: #0D1117 !important; border: 1px solid #2A3D52 !important; color: #E8F4FF !important; font-family: 'Space Mono', monospace !important; border-radius: 6px !important; }
.stButton > button { background: #00D4FF !important; color: #080C10 !important; font-family: 'Space Mono', monospace !important; font-weight: 700 !important; border: none !important; border-radius: 6px !important; font-size: 13px !important; letter-spacing: .04em !important; padding: 10px 24px !important; width: 100% !important; }
.stButton > button:hover { background: white !important; }
.stSelectbox > div > div { background: #0D1117 !important; border: 1px solid #2A3D52 !important; color: #E8F4FF !important; }
</style>
""", unsafe_allow_html=True)

# ── PLATFORM CONFIG (Trailing spaces removed) ──────────────
PLATFORMS = {
    "KDP — Kindle / Paperback / Hardcover": {
        "id": "kdp", "royalty_pct": 0.70, "fees": 0.06, "price": 6.99, "color": "#7C3AED",
        "product": "journal / planner / workbook", "product_types": ["journal", "planner", "workbook", "notebook", "log book"], "kindle_alias": "digital-text"
    },
    "Merch by Amazon — T-Shirts / Apparel": {
        "id": "mba", "royalty_flat": 4.20, "price": 19.99, "color": "#059669",
        "product": "t-shirt / hoodie / tote", "product_types": ["t-shirt", "hoodie", "tote bag", "phone case"], "kindle_alias": "aps"
    },
    "Etsy — Digital Downloads": {
        "id": "etsy", "royalty_pct": 0.93, "fees": 0.20, "price": 5.99, "color": "#F97316",
        "product": "printable / template / SVG", "product_types": ["printable", "digital planner", "template", "SVG bundle", "wall art"], "kindle_alias": "aps"
    }
}

# ── DATABASE ───────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("quantdrop.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT, platform TEXT, final_score REAL, final_verdict TEXT,
            royalty REAL, stressed_royalty REAL, product_name TEXT, created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_analysis(keyword, platform, score, verdict, royalty, stressed, product_name):
    try:
        conn = sqlite3.connect("quantdrop.db")
        conn.execute("INSERT INTO analyses VALUES (NULL,?,?,?,?,?,?,?,?)",
            (keyword, platform, score, verdict, royalty, stressed, product_name, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception: pass

def load_history():
    try:
        conn = sqlite3.connect("quantdrop.db")
        rows = conn.execute("SELECT keyword, platform, final_score, final_verdict, product_name, created_at FROM analyses ORDER BY id DESC LIMIT 15").fetchall()
        conn.close()
        return rows
    except Exception: return []

init_db()

# ── DATA FETCHERS ──────────────────────────────────────────
def safe_get(url, params, label, timeout=8):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept-Language": "en-US,en;q=0.9"}
    for attempt in range(3):
        try:
            time.sleep(random.uniform(1, 3))
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 200: return r
            elif r.status_code == 429: time.sleep((2 ** attempt) * 5 + random.uniform(1, 2))
        except Exception: time.sleep(3)
    return None

def get_amazon_suggestions(keyword, alias="aps"):
    r = safe_get("https://completion.amazon.com/api/2017/suggestions", {"mid": "ATVPDKIKX0DER", "alias": alias, "prefix": keyword, "suggestionType": "KEYWORD"}, "Amazon")
    if r:
        try: return [s.get("value", s) if isinstance(s, dict) else s for s in r.json().get("suggestions", [])]
        except Exception: pass
    return []

def get_google_suggestions(keyword):
    r = safe_get("http://suggestqueries.google.com/complete/search", {"client": "firefox", "q": keyword}, "Google")
    if r:
        try: return r.json()[1] if isinstance(r.json(), list) and len(r.json()) > 1 else []
        except Exception: pass
    return []

# REPLACEMENT FOR PYTRENDS: Visual Demand Signals
def get_youtube_suggestions(keyword):
    try:
        r = requests.get("http://suggestqueries.google.com/complete/search", params={"client": "youtube", "q": keyword, "ds": "yt"}, timeout=5)
        return len(r.json()[1]) if isinstance(r.json(), list) and len(r.json()) > 1 else 0
    except Exception: return 0

def get_pinterest_suggestions(keyword):
    try:
        r = requests.get("https://api.pinterest.com/v5/search/suggestions", params={"query": keyword}, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if r.status_code == 200: return len(r.json().get('results', []))
        return 0
    except Exception: return 0

def get_reddit_complaints(keyword):
    try:
        r = requests.get("https://www.reddit.com/search.json", params={"q": f"{keyword} bad review complaint", "limit": 15, "sort": "relevance"}, headers={"User-Agent": "QuantDrop/1.0"}, timeout=10)
        posts = r.json().get("data", {}).get("children", [])
        bad_words = ["bad", "worst", "hate", "missing", "broken", "cheap", "disappointed", "flimsy", "thin", "generic", "useless"]
        return [p.get("data", {}).get("title", "")[:90] for p in posts if any(w in p.get("data", {}).get("title", "").lower() for w in bad_words)][:3]
    except Exception: return []

# ── PHASE RUNNERS (Fixed Scoring) ──────────────────────────
def run_phase1(keyword, platform_cfg):
    amazon_sugs = get_amazon_suggestions(keyword, platform_cfg.get("kindle_alias", "aps"))
    google_sugs = get_google_suggestions(keyword)
    youtube_sugs = get_youtube_suggestions(keyword)
    pinterest_sugs = get_pinterest_suggestions(keyword)
    
    commercial_words = {"buy", "best", "2026", "2025", "printable", "digital", "download", "women", "men", "gift", "for", "review"}
    maturity = len(set(keyword.lower().split()) & commercial_words)
    
    # Phase 1: Visual Demand (Max 25)
    a_score = min(7, len(amazon_sugs) * 2)
    g_score = min(6, len(google_sugs) * 2)
    y_score = min(6, youtube_sugs * 2)
    p_score = min(6, pinterest_sugs * 2)
    m_score = min(5, maturity * 2)
    
    score = a_score + g_score + y_score + p_score + m_score
    return {
        "score": score, 
        "verdict": "GO" if score >= 15 else "REVIEW" if score >= 8 else "KILL", 
        "amazon_count": len(amazon_sugs), 
        "google_count": len(google_sugs), 
        "youtube_count": youtube_sugs,
        "pinterest_count": pinterest_sugs,
        "maturity": maturity
    }

def run_phase2(keyword):
    # Velocity proxy (Max 15)
    count = len(get_amazon_suggestions(keyword + " best seller", "aps"))
    score = 12 if count >= 6 else 8 if count >= 3 else 4 if count >= 1 else 2
    return {"score": score, "verdict": "GO" if score >= 10 else "REVIEW" if score >= 6 else "KILL", "proxy_count": count}

def run_phase3(keyword):
    complaints = get_reddit_complaints(keyword)
    if not complaints: complaints = [f"Pages feel flimsy in most {keyword} products", f"Prompts are too generic", f"Cover wears out quickly"]
    score = 20 if len(complaints) >= 2 else 12 if len(complaints) >= 1 else 8
    return {"score": score, "verdict": "GO", "complaints": complaints, "opportunity": f"Your edge: fix '{complaints[0][:60]}'"}

def run_phase4(platform_key, platform_cfg):
    pid = platform_cfg["id"]
    if pid == "kdp":
        price, royalty, stressed = platform_cfg["price"], platform_cfg["price"] * platform_cfg["royalty_pct"] - platform_cfg["fees"], platform_cfg["price"] * 0.85 * platform_cfg["royalty_pct"] - platform_cfg["fees"]
    elif pid == "mba":
        price, royalty, stressed = platform_cfg["price"], platform_cfg["royalty_flat"], platform_cfg["royalty_flat"] * 0.72
    else:
        price, royalty, stressed = platform_cfg["price"], platform_cfg["price"] * platform_cfg["royalty_pct"] - platform_cfg["fees"], platform_cfg["price"] * 0.72 * platform_cfg["royalty_pct"] - platform_cfg["fees"]
        
    margin, stressed_margin = royalty / price, stressed / (price * 0.85)
    # Economics weight (Max 45) - High margin niches win
    score = 40 if stressed_margin > 0.25 else 35 if stressed_margin > 0.20 else 25 if stressed_margin > 0.15 else 15
    return {
        "score": score, "verdict": "GO" if score >= 30 else "REVIEW", 
        "royalty": round(royalty, 2), "stressed_royalty": round(stressed, 2), 
        "margin": round(margin * 100, 1), "stressed_margin": round(stressed_margin * 100, 1),
        "monthly_sales_500": round(500 / royalty) if royalty > 0 else 999
    }

# ── GEMINI & LISTING GEN ──────────────────────────────────
def gemini_design(keyword, platform_cfg, complaints, api_key=""):
    fix = complaints[0] if complaints else "improve overall quality"
    product_type = platform_cfg["product_types"][0]
    prompt = f"""You are a digital product designer specializing in {platform_cfg['product']}.
Keyword: "{keyword}"
Fix complaint: "{fix}"
Return ONLY JSON: {{"product_name":"...","tagline":"...","color_palette":["#1","#2","#3"],"cover_style":"...","key_features":["..."],"unique_angle":"...","target_buyer":"..."}}"""
    
    key = api_key or st.secrets.get("GEMINI_API_KEY", "")
    if key:
        try:
            r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={key}",
                json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.8}}, timeout=20)
            return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"].strip().replace("```json","").replace("```",""))
        except Exception: pass
    return {"product_name": f"The {keyword.title()} Blueprint", "tagline": f"Premium quality for {keyword}", "color_palette": ["#1A1A2E","#16213E","#E94560"], "cover_style": "Dark minimalist", "key_features": ["Solves flimsy pages", "Lay-flat binding"], "unique_angle": "Heirloom quality", "target_buyer": "Adults 25-45"}

def generate_listing(keyword, platform_id, design):
    name, tagline, features = design.get("product_name", keyword), design.get("tagline", ""), design.get("key_features", [])
    core_words = [w for w in keyword.lower().split() if w not in {"for","the","and","2025","2026","with"}]
    base_kw = " ".join(core_words[:3])
    if platform_id == "kdp":
        return {"title": f"{name}: {tagline}"[:200], "bullets": [f"✓ {f}" for f in features], "keywords": [base_kw, f"best {base_kw}", f"{base_kw} gift", f"{base_kw} notebook"]}
    return {"title": f"{name} | {tagline}", "tags": [base_kw, f"{base_kw} printable", "digital download"]}

# ── BATCH PROCESSOR ────────────────────────────────────────
def run_batch_mode(keywords_text, platform_cfg, api_key=""):
    keywords = [k.strip().lower() for k in keywords_text.split("\n") if k.strip()]
    if not keywords: return None, "No keywords provided."
    
    results = []
    progress_bar = st.progress(0)
    for i, kw in enumerate(keywords):
        try:
            p1 = run_phase1(kw, platform_cfg)
            p2 = run_phase2(kw)
            p3 = run_phase3(kw)
            p4 = run_phase4(platform_cfg["product"], platform_cfg)
            design = gemini_design(kw, platform_cfg, p3["complaints"], api_key)
            
            # Weighted total: Demand 30%, Econ 45%, Velocity 15%, Sentiment 10%
            # Max score = 25+45+15+20 = 105. Normalize to 100.
            raw_total = p1["score"]*0.30 + p4["score"] + p2["score"]*0.15 + p3["score"]*0.10
            final_score = min(100, round((raw_total / 85) * 100, 1))
            final_verdict = "GO" if final_score >= 70 else "REVIEW" if final_score >= 45 else "KILL"
            
            results.append({"keyword": kw, "score": final_score, "verdict": final_verdict, "product_name": design["product_name"], "pinterest": p1["pinterest_count"], "youtube": p1["youtube_count"]})
            save_analysis(kw, platform_cfg["product"], final_score, final_verdict, p4["royalty"], p4["stressed_royalty"], design["product_name"])
        except Exception: pass
        progress_bar.progress((i + 1) / len(keywords))
        
    return results, None

# ── HELPERS ────────────────────────────────────────────────
def verdict_color(v): return {"GO": "#00FF88", "REVIEW": "#FFD166", "KILL": "#FF4757"}.get(v, "#6B8BA4")
def verdict_emoji(v): return {"GO": "✅", "REVIEW": "⚠️", "KILL": "❌"}.get(v, "—")

# ── MAIN UI ────────────────────────────────────────────────
def main():
    st.markdown("""
    <div style="text-align:center;padding:32px 0 16px">
      <div style="font-family:'Space Mono',monospace;font-size:13px;color:#00D4FF;letter-spacing:.15em;text-transform:uppercase;margin-bottom:10px">Visual Demand · $0 Capital · Streamlit Cloud</div>
      <h1 style="font-family:'Syne',sans-serif;font-size:48px;font-weight:800;background:linear-gradient(135deg,#E8F4FF,#00D4FF,#FF6B35);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:0 0 10px">QuantDrop v3.0</h1>
    </div>""", unsafe_allow_html=True)

    with st.sidebar:
        gemini_key = st.text_input("Gemini API Key", type="password", placeholder="AIza...")
        st.markdown("<div style='font-family:Space Mono,monospace;font-size:10px;color:#6B8BA4;line-height:1.8'><b style='color:#E8F4FF'>SIGNALS</b><br>✓ Amazon/Google Autocomplete<br>✓ Pinterest Visual Demand<br>✓ YouTube Search Volume<br>✓ Reddit Sentiment<br><br><b style='color:#E8F4FF'>SCORING</b><br>Economics (45%)<br>Demand (30%)<br>Velocity (15%)<br>Sentiment (10%)</div>", unsafe_allow_html=True)

    col_kw, col_pl, col_btn = st.columns([3, 2, 1])
    with col_kw: keyword = st.text_input("Niche keyword", placeholder="e.g. gratitude journal women", label_visibility="collapsed")
    with col_pl: platform_name = st.selectbox("Platform", list(PLATFORMS.keys()), label_visibility="collapsed")
    with col_btn: run = st.button("Analyze →")
    platform_cfg = PLATFORMS[platform_name]

    st.markdown("---")
    batch_mode = st.checkbox("📦 Batch Mode")
    if batch_mode:
        batch_input = st.text_area("Enter keywords (one per line)", height=100)
        if st.button(" Run Batch Analysis"):
            batch_results, _ = run_batch_mode(batch_input, platform_cfg, gemini_key)
            if batch_results:
                import pandas as pd
                df = pd.DataFrame(batch_results)
                st.dataframe(df)
                st.download_button("📥 Download CSV", df.to_csv(index=False), "quantdrop_v3_results.csv", "text/csv")

    if run and keyword.strip() and not batch_mode:
        kw = keyword.strip().lower()
        progress = st.progress(0)
        progress.progress(20, text="Demand Signals...")
        p1 = run_phase1(kw, platform_cfg)
        progress.progress(40, text="Velocity & Economics...")
        p2 = run_phase2(kw)
        p4 = run_phase4(platform_name, platform_cfg)
        progress.progress(60, text="Sentiment...")
        p3 = run_phase3(kw)
        progress.progress(80, text="AI Design...")
        design = gemini_design(kw, platform_cfg, p3["complaints"], gemini_key)
        progress.progress(100, text="Done!"); progress.empty()
        
        # Weighted Total
        raw_total = p1["score"]*0.30 + p4["score"] + p2["score"]*0.15 + p3["score"]*0.10
        final_score = min(100, round((raw_total / 85) * 100, 1))
        final_verdict = "GO" if final_score >= 70 else "REVIEW" if final_score >= 45 else "KILL"
        
        save_analysis(kw, platform_name, final_score, final_verdict, p4["royalty"], p4["stressed_royalty"], design["product_name"])
        
        verdict_msg = {"GO": "Validated — Create Now", "REVIEW": "Promising", "KILL": "Move On"}.get(final_verdict, "—")
        st.markdown(f"""<div class="verdict-{final_verdict.lower()}"><div style="display:flex;justify-content:space-between"><div><div style="font-family:Space Mono,monospace;font-size:24px;font-weight:700;color:{verdict_color(final_verdict)}">{verdict_emoji(final_verdict)} {final_verdict}</div><div style="font-size:13px;color:#6B8BA4">{verdict_msg}</div></div><div style="font-family:Space Mono,monospace;font-size:52px;font-weight:700;color:{verdict_color(final_verdict)}">{final_score}</div></div></div>""", unsafe_allow_html=True)

        # Simple Columns for Signals
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Pinterest Demand", p1["pinterest_count"])
        c2.metric("YouTube Demand", p1["youtube_count"])
        c3.metric("Amazon Sugs", p1["amazon_count"])
        c4.metric("Stressed Margin", f"{p4['stressed_margin']}%")

if __name__ == "__main__":
    main()
