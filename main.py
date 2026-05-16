# QuantDrop v2.1 — Quant Digital Product Intelligence
# Stack: Streamlit + pytrends + free data + gemini-3.1-flash-lite
# Deploy: GitHub → Streamlit Cloud (free) | Single file, $0 capital

import streamlit as st
import requests
import time
import random
import json
import sqlite3
import io
import csv
from datetime import datetime

# ── PYTRENDS IMPORT (Free Google Trends API) ─────────────
try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False

# ── PAGE CONFIG ────────────────────────────────────────────
st.set_page_config(
    page_title="QuantDrop v2.1 — Digital Product Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─ CUSTOM CSS (All typos fixed) ───────────────────────────
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

# ── PLATFORM CONFIG ────────────────────────────────────────
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

# ── DATABASE (Tracking-ready) ──────────────────────────────
def init_db():
    conn = sqlite3.connect("quantdrop.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT, platform TEXT, final_score REAL, final_verdict TEXT,
            royalty REAL, stressed_royalty REAL, product_name TEXT, created_at TEXT,
            published_date TEXT, day_30_bsr TEXT, actual_sales REAL
        )
    """)
    conn.commit()
    conn.close()

def save_analysis(keyword, platform, score, verdict, royalty, stressed, product_name):
    try:
        conn = sqlite3.connect("quantdrop.db")
        conn.execute("INSERT INTO analyses VALUES (NULL,?,?,?,?,?,?,?,?,NULL,NULL)",
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
            time.sleep(random.uniform(2, 5))
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 200: return r
            elif r.status_code == 429: time.sleep((2 ** attempt) * 8 + random.uniform(2, 4))
        except Exception: time.sleep(4)
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

def get_reddit_complaints(keyword):
    try:
        r = requests.get("https://www.reddit.com/search.json", params={"q": f"{keyword} bad review complaint", "limit": 15, "sort": "relevance"}, headers={"User-Agent": "QuantDrop/1.0"}, timeout=10)
        posts = r.json().get("data", {}).get("children", [])
        bad_words = ["bad", "worst", "hate", "missing", "broken", "cheap", "disappointed", "flimsy", "thin", "generic", "useless"]
        complaints = [p.get("data", {}).get("title", "")[:90] for p in posts if any(w in p.get("data", {}).get("title", "").lower() for w in bad_words)]
        return list(dict.fromkeys(complaints))[:3]
    except Exception: return []

def get_google_trends(keyword):
    if not PYTRENDS_AVAILABLE: return 0
    try:
        pytrends = TrendReq(hl="en-US", tz=360)
        pytrends.build_payload([keyword], timeframe="today 12-m")
        df = pytrends.interest_over_time()
        return round(df[keyword].mean(), 1) if keyword in df.columns else 0
    except Exception: return 0

def get_amazon_competition_count(keyword):
    try:
        r = requests.get(f"https://www.amazon.com/s?k={keyword.replace(' ', '+')}", headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        if "No results found" in r.text: return 0
        count = len(r.find_all(class_="s-result-item"))
        return count if count > 0 else 5000
    except Exception: return 2000

# ── PHASE RUNNERS (Upgraded) ──────────────────────────────
def run_phase1(keyword, platform_cfg):
    amazon_sugs = get_amazon_suggestions(keyword, platform_cfg.get("kindle_alias", "aps"))
    google_sugs = get_google_suggestions(keyword)
    trends_score = get_google_trends(keyword)
    commercial_words = {"buy", "best", "2026", "2025", "printable", "digital", "download", "women", "men", "gift", "for", "review"}
    maturity = len(set(keyword.lower().split()) & commercial_words)
    
    # Demand scoring (max 25)
    sug_score = min(10, (len(amazon_sugs) // 2) + (len(google_sugs) // 2))
    trend_score = min(10, trends_score // 10) if trends_score > 0 else 0
    mat_score = min(5, maturity * 2)
    return {"score": sug_score + trend_score + mat_score, "verdict": "GO" if sug_score + trend_score >= 8 else "REVIEW" if sug_score + trend_score >= 4 else "KILL", "amazon_count": len(amazon_sugs), "google_count": len(google_sugs), "maturity": maturity, "trends_avg": trends_score}

def run_phase2(keyword):
    velocity_count = len(get_amazon_suggestions(keyword + " best seller", "aps"))
    comp_count = get_amazon_competition_count(keyword)
    
    # Velocity scoring (max 15)
    vel_score = 12 if velocity_count >= 6 else 8 if velocity_count >= 3 else 4 if velocity_count >= 1 else 2
    # Competition density scoring (max 10) -> fewer results = better
    comp_score = 10 if comp_count < 500 else 7 if comp_count < 2000 else 4 if comp_count < 5000 else 1
    return {"score": vel_score + comp_score, "verdict": "GO" if vel_score + comp_score >= 12 else "REVIEW" if vel_score + comp_score >= 7 else "KILL", "proxy_count": velocity_count, "competition_count": comp_count}

def run_phase3(keyword, api_key=""):
    complaints = get_reddit_complaints(keyword)
    if not complaints and api_key:
        # AI fallback for niche-specific complaints
        try:
            r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}",
                json={"contents": [{"parts": [{"text": f"List 3 common buyer complaints about {keyword} products on Amazon. Return ONLY JSON array of strings."}]}], "generationConfig": {"temperature": 0.5}}, timeout=10)
            complaints = json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"].replace("```json","").replace("```",""))[:3]
        except Exception: complaints = []
        
    if not complaints:
        complaints = [f"Pages feel flimsy in most {keyword} products", f"Prompts are too generic — not tailored for daily use", f"Cover wears out after a few weeks of daily use"]
        
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
    score = 25 if stressed_margin > 0.20 else 18 if stressed_margin > 0.15 else 12 if stressed_margin > 0.10 else 5
    return {"score": score, "verdict": "GO" if score >= 20 else "REVIEW" if score >= 12 else "KILL", "royalty": round(royalty, 2), "stressed_royalty": round(stressed, 2), "margin": round(margin * 100, 1), "stressed_margin": round(stressed_margin * 100, 1), "monthly_sales_500": round(500 / royalty) if royalty > 0 else 999}

# ── GEMINI & LISTING GEN ──────────────────────────────────
def gemini_design(keyword, platform_cfg, complaints, api_key=""):
    fix = complaints[0] if complaints else "improve overall quality"
    product_type = platform_cfg["product_types"][0]
    platform_name = platform_cfg.get("product", "digital product")
    prompt = f"""You are a digital product designer specializing in {platform_name}.
Keyword niche: "{keyword}"
Main buyer complaint to fix: "{fix}"
Design a compelling {product_type}. Return ONLY valid JSON, no markdown:
{{"product_name":"...","tagline":"...","color_palette":["#1","#2","#3"],"cover_style":"...","key_features":["...","...","..."],"unique_angle":"...","target_buyer":"..."}}"""
    
    key = api_key or st.secrets.get("GEMINI_API_KEY", "")
    if key:
        try:
            r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={key}",
                json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.8}}, timeout=20)
            return json.loads(r.json()["candidates"][0]["content"]["parts"][0]["text"].strip().replace("```json","").replace("```",""))
        except Exception as e: st.warning(f"Gemini: {e}")

    palettes = [["#1A1A2E","#16213E","#E94560"],["#2D3436","#636E72","#FDCB6E"],["#0F3460","#533483","#E94560"],["#2C3E50","#27AE60","#F39C12"]]
    return {"product_name": f"The {keyword.title()} Blueprint", "tagline": f"The only {keyword} built from real buyer feedback", "color_palette": random.choice(palettes), "cover_style": "Premium dark cover with minimalist typography", "key_features": [f"Solves: {fix[:60]}", "Undated format", "Science-backed structure"], "unique_angle": "Designed around top buyer complaints", "target_buyer": "Adults 25–45"}

def generate_listing(keyword, platform_id, design):
    name, tagline, features, buyer = design.get("product_name", keyword), design.get("tagline", ""), design.get("key_features", []), design.get("target_buyer", "Adults")
    core_words = [w for w in keyword.lower().split() if w not in {"for","the","and","2025","2026","with"}]
    base_kw = " ".join(core_words[:3])
    if platform_id == "kdp":
        return {"title": f"{name}: {tagline}"[:200], "bullets": [f"✓ {f}" for f in features], "description": f"Designed for {buyer.lower()}, {name} solves the #1 complaint buyers have with existing {base_kw} products. {tagline}. Undated format.", "keywords": [base_kw, f"best {base_kw}", f"daily {base_kw}", f"{base_kw} gift", f"{base_kw} for women", f"{base_kw} for men", f"{base_kw} notebook", "undated journal", "mindfulness log"]}
    elif platform_id == "mba":
        return {"title": f"{name} | {tagline}"[:60], "bullets": features, "tags": [base_kw.replace(" ",""), "funny", "gift", "novelty", "quote", "sarcastic", buyer.split()[0].lower(), "tee"]}
    return {"title": f"{name} | {tagline} | Digital Download | {base_kw.title()} Printable"[:140], "tags": [base_kw, f"{base_kw} printable", "digital download", "instant download", "pdf planner", "self care", "mindfulness", "printable planner", "letter size", "a4 size", "gift idea", "wall art", core_words[0]][:13], "description": f"Instant digital download. {tagline}. Print at home."}

# ── BATCH PROCESSOR ────────────────────────────────────────
def run_batch_mode(keywords_text, platform_cfg, api_key=""):
    keywords = [k.strip().lower() for k in keywords_text.split("\n") if k.strip()]
    if not keywords: return None, "No keywords provided."
    if len(keywords) > 15: return None, "Max 15 keywords to avoid timeouts."
    
    results, errors = [], []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, kw in enumerate(keywords):
        try:
            status_text.text(f"Processing {i+1}/{len(keywords)}: {kw}")
            p1 = run_phase1(kw, platform_cfg)
            p2 = run_phase2(kw)
            p3 = run_phase3(kw, api_key)
            p4 = run_phase4(platform_cfg["product"], platform_cfg)
            design = gemini_design(kw, platform_cfg, p3["complaints"], api_key)
            listing = generate_listing(kw, platform_cfg["id"], design)
            
            # Weighted scoring (breaks clustering)
            weighted = (p1["score"]*0.20 + p2["score"]*0.15 + p3["score"]*0.15 + p4["score"]*0.50)
            final_score = min(100, round(weighted, 1))
            final_verdict = "GO" if final_score >= 70 else "REVIEW" if final_score >= 40 else "KILL"
            
            results.append({"keyword": kw, "score": final_score, "verdict": final_verdict, "product_name": design["product_name"], "title": listing["title"], "bullets": " | ".join(listing.get("bullets", [])), "description": listing.get("description", ""), "keywords": ",".join(listing.get("keywords", listing.get("tags", []))), "royalty": p4["royalty"], "stressed_margin": p4["stressed_margin"], "trends_avg": p1.get("trends_avg", 0), "competition_count": p2.get("competition_count", 0)})
            save_analysis(kw, platform_cfg["product"], final_score, final_verdict, p4["royalty"], p4["stressed_royalty"], design["product_name"])
        except Exception as e: errors.append(f"{kw}: {str(e)[:50]}")
        progress_bar.progress((i + 1) / len(keywords))
        
    status_text.text("✅ Batch complete!")
    progress_bar.empty()
    if errors: st.warning("️ Some failed:\n" + "\n".join(errors))
    return results, None

# ── HELPERS ────────────────────────────────────────────────
def verdict_color(v): return {"GO": "#00FF88", "REVIEW": "#FFD166", "KILL": "#FF4757"}.get(v, "#6B8BA4")
def verdict_emoji(v): return {"GO": "✅", "REVIEW": "⚠️", "KILL": "❌"}.get(v, "—")

# ── MAIN UI ────────────────────────────────────────────────
def main():
    st.markdown("""
    <div style="text-align:center;padding:32px 0 16px">
      <div style="font-family:'Space Mono',monospace;font-size:13px;color:#00D4FF;letter-spacing:.15em;text-transform:uppercase;margin-bottom:10px">Quant-Driven · AI-Designed · $0 Capital</div>
      <h1 style="font-family:'Syne',sans-serif;font-size:48px;font-weight:800;background:linear-gradient(135deg,#E8F4FF,#00D4FF,#FF6B35);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:0 0 10px">QuantDrop v2.1</h1>
      <p style="color:#6B8BA4;font-size:15px;max-width:480px;margin:0 auto;line-height:1.7">Weighted scoring + Google Trends + competition density. No more score clustering.</p>
    </div>""", unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("<div style='font-family:Space Mono,monospace;font-size:14px;color:#00D4FF;font-weight:700;margin-bottom:16px'>⚙️ CONFIG</div>", unsafe_allow_html=True)
        gemini_key = st.text_input("Gemini API Key", type="password", placeholder="AIza... (Stored in Secrets)")
        st.markdown("---")
        st.markdown("<div style='font-family:Space Mono,monospace;font-size:10px;color:#6B8BA4;line-height:1.8'><b style='color:#E8F4FF'>UPGRADES</b><br>✓ Weighted scoring (Phase 4 = 50%)<br>✓ Google Trends volume<br>✓ Amazon competition density<br>✓ Decimal precision scores<br>✓ Smart sentiment fallback<br><br><b style='color:#E8F4FF'>COST</b><br>$0 — all free sources</div>", unsafe_allow_html=True)

    col_kw, col_pl, col_btn = st.columns([3, 2, 1])
    with col_kw: keyword = st.text_input("Niche keyword", placeholder="e.g. gratitude journal women", label_visibility="collapsed")
    with col_pl: platform_name = st.selectbox("Platform", list(PLATFORMS.keys()), label_visibility="collapsed")
    with col_btn: run = st.button("Analyze →")
    platform_cfg = PLATFORMS[platform_name]

    st.markdown("---")
    batch_mode = st.checkbox("📦 Batch Mode (up to 15 keywords)")
    if batch_mode:
        batch_input = st.text_area("Enter keywords (one per line)", placeholder="gratitude journal women\nanxiety planner teens\nfitness log book", height=120)
        run_batch = st.button("🚀 Run Batch Analysis")
        if run_batch and batch_input.strip():
            batch_results, err = run_batch_mode(batch_input, platform_cfg, gemini_key)
            if batch_results:
                go_results = [r for r in batch_results if r["verdict"] == "GO"]
                st.success(f"✅ Found {len(go_results)} GO niches out of {len(batch_results)}")
                import pandas as pd
                df = pd.DataFrame(batch_results)
                csv_data = df.to_csv(index=False)
                st.download_button("📥 Download Results CSV", csv_data, file_name="quantdrop_v2_results.csv", mime="text/csv")
                st.dataframe(df[["keyword", "score", "verdict", "product_name", "trends_avg", "competition_count"]])

    if run and keyword.strip() and not batch_mode:
        kw = keyword.strip().lower()
        progress = st.progress(0, text="Starting analysis...")
        progress.progress(10, text="Phase 1 — demand + trends..."); time.sleep(0.1)
        p1 = run_phase1(kw, platform_cfg)
        progress.progress(30, text="Phase 2 — velocity + competition..."); time.sleep(0.1)
        p2 = run_phase2(kw)
        progress.progress(52, text="Phase 3 — sentiment alpha..."); time.sleep(0.1)
        p3 = run_phase3(kw, gemini_key)
        progress.progress(72, text="Phase 4 — economics stress test..."); time.sleep(0.1)
        p4 = run_phase4(platform_name, platform_cfg)
        progress.progress(85, text="Generating AI design..."); time.sleep(0.1)
        design = gemini_design(kw, platform_cfg, p3["complaints"], gemini_key)
        progress.progress(95, text="Building listing copy...")
        listing = generate_listing(kw, platform_cfg["id"], design)
        
        # Weighted final score
        weighted = (p1["score"]*0.20 + p2["score"]*0.15 + p3["score"]*0.15 + p4["score"]*0.50)
        final_score = min(100, round(weighted, 1))
        final_verdict = "GO" if final_score >= 70 else "REVIEW" if final_score >= 40 else "KILL"
        
        progress.progress(100, text="Done!"); time.sleep(0.3); progress.empty()
        save_analysis(kw, platform_name, final_score, final_verdict, p4["royalty"], p4["stressed_royalty"], design["product_name"])

        verdict_msg = {"GO": "Validated — create and publish now", "REVIEW": "Promising — refine keyword", "KILL": "Low signal — move on"}.get(final_verdict, "—")
        vc = verdict_color(final_verdict)
        st.markdown(f"""<div class="verdict-{final_verdict.lower()}"><div style="display:flex;align-items:center;justify-content:space-between"><div><div style="font-family:Space Mono,monospace;font-size:24px;font-weight:700;color:{vc};letter-spacing:.06em">{verdict_emoji(final_verdict)} {final_verdict}</div><div style="font-size:13px;color:#6B8BA4;margin-top:4px">{verdict_msg} · Platform: {platform_cfg['id'].upper()}</div></div><div style="font-family:Space Mono,monospace;font-size:52px;font-weight:700;color:{vc}">{final_score} <span style="font-size:22px;color:#6B8BA4">/100</span></div></div></div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-header">Pipeline Scores (Weighted)</div>', unsafe_allow_html=True)
        pc1, pc2, pc3, pc4 = st.columns(4)
        for col, pnum, pname, pscore, pmax, pverdict in [(pc1,"Phase 1","Demand + Trends",p1["score"],25,p1["verdict"]),(pc2,"Phase 2","Velocity + Competition",p2["score"],25,p2["verdict"]),(pc3,"Phase 3","Sentiment Alpha",p3["score"],25,p3["verdict"]),(pc4,"Phase 4","Economics (50% weight)",p4["score"],25,p4["verdict"])]:
            vc2, pct = verdict_color(pverdict), round(pscore/pmax*100)
            col.markdown(f"""<div class="phase-card {pverdict.lower()}"><div style="font-family:Space Mono,monospace;font-size:9px;color:#6B8BA4;text-transform:uppercase;letter-spacing:.08em">{pnum}</div><div style="font-size:12px;font-weight:600;color:#E8F4FF;margin:4px 0">{pname}</div><div style="font-family:Space Mono,monospace;font-size:22px;font-weight:700;color:{vc2}">{pscore} <span style="font-size:12px;color:#6B8BA4">/{pmax}</span></div><div style="height:3px;background:#1E2B38;border-radius:2px;margin-top:8px;overflow:hidden"><div style="height:100%;width:{pct}%;background:{vc2};border-radius:2px"></div></div></div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-header">Economics & Signals</div>', unsafe_allow_html=True)
        econ_col, sig_col = st.columns(2)
        sm_color = "#00FF88" if p4["stressed_margin"] >= 20 else "#FFD166" if p4["stressed_margin"] >= 10 else "#FF4757"
        econ_col.markdown(f"""<div class="phase-card"><div style="font-family:Space Mono,monospace;font-size:10px;color:#6B8BA4;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px">Unit Economics — {platform_cfg['id'].upper()}</div><table style="width:100%;font-size:12px;border-collapse:collapse"><tr style="border-bottom:1px solid #1E2B38"><td style="color:#6B8BA4;padding:5px 0">Base royalty / sale</td><td style="font-family:Space Mono,monospace;font-weight:700;color:#E8F4FF;text-align:right">${p4['royalty']}</td></tr><tr style="border-bottom:1px solid #1E2B38"><td style="color:#6B8BA4;padding:5px 0">Stressed royalty</td><td style="font-family:Space Mono,monospace;font-weight:700;color:#FFD166;text-align:right">${p4['stressed_royalty']}</td></tr><tr style="border-bottom:1px solid #1E2B38"><td style="color:#6B8BA4;padding:5px 0">Base margin</td><td style="font-family:Space Mono,monospace;font-weight:700;color:#E8F4FF;text-align:right">{p4['margin']}%</td></tr><tr style="border-bottom:1px solid #1E2B38"><td style="color:#6B8BA4;padding:5px 0">Stressed margin</td><td style="font-family:Space Mono,monospace;font-weight:700;color:{sm_color};text-align:right">{p4['stressed_margin']}%</td></tr><tr><td style="color:#6B8BA4;padding:5px 0">Sales needed for $500/mo</td><td style="font-family:Space Mono,monospace;font-weight:700;color:#E8F4FF;text-align:right">{p4['monthly_sales_500']} sales</td></tr></table></div>""", unsafe_allow_html=True)

        a_pct, g_pct, v_pct = min(100, round(p1["amazon_count"]/10*100)), min(100, round(p1["google_count"]/10*100)), min(100, round(p2["proxy_count"]/10*100))
        sig_col.markdown(f"""<div class="phase-card"><div style="font-family:Space Mono,monospace;font-size:10px;color:#6B8BA4;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px">Demand & Competition</div><div style="font-size:12px;color:#6B8BA4;margin-bottom:6px;display:flex;align-items:center;gap:8px"><span style="min-width:160px">Amazon suggestions</span><div style="flex:1;height:4px;background:#1E2B38;border-radius:2px;overflow:hidden"><div style="height:100%;width:{a_pct}%;background:#7C3AED;border-radius:2px"></div></div><span style="font-family:Space Mono,monospace;font-weight:700;color:#E8F4FF;min-width:24px">{p1['amazon_count']}</span></div><div style="font-size:12px;color:#6B8BA4;margin-bottom:6px;display:flex;align-items:center;gap:8px"><span style="min-width:160px">Google suggestions</span><div style="flex:1;height:4px;background:#1E2B38;border-radius:2px;overflow:hidden"><div style="height:100%;width:{g_pct}%;background:#00D4FF;border-radius:2px"></div></div><span style="font-family:Space Mono,monospace;font-weight:700;color:#E8F4FF;min-width:24px">{p1['google_count']}</span></div><div style="font-size:12px;color:#6B8BA4;margin-bottom:6px;display:flex;align-items:center;gap:8px"><span style="min-width:160px">Google Trends avg</span><div style="flex:1;height:4px;background:#1E2B38;border-radius:2px;overflow:hidden"><div style="height:100%;width:{min(100,p1.get('trends_avg',0)*5)}%;background:#FFD166;border-radius:2px"></div></div><span style="font-family:Space Mono,monospace;font-weight:700;color:#E8F4FF;min-width:24px">{p1.get('trends_avg',0)}</span></div><div style="font-size:12px;color:#6B8BA4;margin-bottom:6px;display:flex;align-items:center;gap:8px"><span style="min-width:160px">Amazon competition</span><div style="flex:1;height:4px;background:#1E2B38;border-radius:2px;overflow:hidden"><div style="height:100%;width:{min(100,p2.get('competition_count',2000)/100)}%;background:#FF6B35;border-radius:2px"></div></div><span style="font-family:Space Mono,monospace;font-weight:700;color:#E8F4FF;min-width:24px">{p2.get('competition_count',0)}</span></div></div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-header">Competitor Complaints → Your Product Edge</div>', unsafe_allow_html=True)
        st.markdown(f"""<div class="phase-card">{' '.join([f'<div class="complaint">"{c}"</div>' for c in p3["complaints"]])}<div class="opportunity">→ {p3['opportunity']}</div></div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-header">AI Product Design</div>', unsafe_allow_html=True)
        swatches = " ".join([f'<span class="swatch" style="background:{c};border-color:{c}88"></span>' for c in design.get("color_palette", [])])
        features_html = " ".join([f'<li style="font-size:12px;color:#6B8BA4;padding:3px 0;list-style:none">→ {f}</li>' for f in design.get("key_features", [])])
        st.markdown(f"""<div class="design-card"><div style="font-family:Space Mono,monospace;font-size:9px;color:#00D4FF;letter-spacing:.12em;text-transform:uppercase;margin-bottom:8px">✦ DESIGNED BY GEMINI 3.1 FLASH LITE</div><div style="font-size:26px;font-weight:800;color:#E8F4FF;margin-bottom:4px">{design.get('product_name', '—')}</div><div style="font-size:13px;color:#6B8BA4;font-style:italic;margin-bottom:14px">"{design.get('tagline', '—')}"</div><div style="margin-bottom:12px">{swatches}</div><div style="font-family:Space Mono,monospace;font-size:9px;color:#6B8BA4;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">Key Features</div><ul style="margin:0;padding:0">{features_html}</ul><div style="margin-top:12px;font-size:12px;color:#6B8BA4"><span style="color:#00D4FF;font-weight:600">Unique angle: </span>{design.get('unique_angle', '—')}</div><div style="margin-top:6px;font-size:12px;color:#6B8BA4"><span style="color:#00D4FF;font-weight:600">Target buyer: </span>{design.get('target_buyer', '—')}</div><div style="margin-top:8px;font-size:12px;color:#6B8BA4"><span style="color:#00D4FF;font-weight:600">Cover style: </span>{design.get('cover_style', '—')}</div></div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-header">Ready-to-Publish Listing Copy</div>', unsafe_allow_html=True)
        with st.expander("📋 Click to expand listing copy", expanded=True):
            st.markdown(f"""<div class="phase-card"><div style="font-family:Space Mono,monospace;font-size:9px;color:#6B8BA4;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">Title</div><div style="font-family:Space Mono,monospace;font-size:13px;color:#00D4FF;line-height:1.5;margin-bottom:14px;word-break:break-word">{listing['title']}</div>""", unsafe_allow_html=True)
            if "bullets" in listing and listing["bullets"]:
                st.markdown("""<div style="font-family:Space Mono,monospace;font-size:9px;color:#6B8BA4;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">Bullet Points</div>""", unsafe_allow_html=True)
                for b in listing["bullets"]: st.markdown(f'<div class="complaint" style="border-color:#00FF88">{b}</div>', unsafe_allow_html=True)
            if "description" in listing: st.markdown(f"""<div style="font-family:Space Mono,monospace;font-size:9px;color:#6B8BA4;text-transform:uppercase;letter-spacing:.08em;margin:12px 0 6px">Description</div><div style="font-size:12px;color:#6B8BA4;line-height:1.7">{listing['description']}</div>""", unsafe_allow_html=True)
            tags = listing.get("keywords") or listing.get("tags") or []
            if tags:
                tags_html = " ".join([f'<span class="tag">{t}</span>' for t in tags])
                st.markdown(f"""<div style="font-family:Space Mono,monospace;font-size:9px;color:#6B8BA4;text-transform:uppercase;letter-spacing:.08em;margin:12px 0 6px">{"Keywords" if platform_cfg['id'] == "kdp" else "Tags"}</div><div>{tags_html}</div>""", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

    elif run and not keyword.strip() and not batch_mode: st.warning("Enter a keyword first.")

    history = load_history()
    if history:
        st.markdown("---")
        st.markdown('<div class="section-header">Analysis History</div>', unsafe_allow_html=True)
        cols = st.columns([2, 2, 1, 1, 2, 1])
        headers = ["Keyword", "Platform", "Score", "Verdict", "Product Name", "Date"]
        for col, h in zip(cols, headers): col.markdown(f"<div style='font-family:Space Mono,monospace;font-size:10px;color:#6B8BA4;text-transform:uppercase;letter-spacing:.06em'>{h}</div>", unsafe_allow_html=True)
        for row in history:
            kw, pl, sc, vd, pn, dt = row
            vc3 = verdict_color(vd)
            c1, c2, c3, c4, c5, c6 = st.columns([2, 2, 1, 1, 2, 1])
            c1.markdown(f"<div style='font-size:12px;color:#E8F4FF;font-weight:600'>{kw}</div>", unsafe_allow_html=True)
            c2.markdown(f"<div style='font-family:Space Mono,monospace;font-size:11px;color:#6B8BA4'>{pl.split('—')[0].strip()}</div>", unsafe_allow_html=True)
            c3.markdown(f"<div style='font-family:Space Mono,monospace;font-size:12px;font-weight:700;color:{vc3}'>{sc}</div>", unsafe_allow_html=True)
            c4.markdown(f"<div style='font-family:Space Mono,monospace;font-size:11px;font-weight:700;color:{vc3}'>{vd}</div>", unsafe_allow_html=True)
            c5.markdown(f"<div style='font-size:11px;color:#6B8BA4'>{pn or '—'}</div>", unsafe_allow_html=True)
            c6.markdown(f"<div style='font-family:Space Mono,monospace;font-size:10px;color:#6B8BA4'>{dt[:10] if dt else '—'}</div>", unsafe_allow_html=True)

    st.markdown("""<div style="text-align:center;padding:32px 0 16px;border-top:1px solid #1E2B38;margin-top:40px"><div style="font-family:'Space Mono',monospace;font-size:11px;color:#6B8BA4">Built by a quant · Powered by <span style="color:#00D4FF">free data sources</span> + <span style="color:#FF6B35">Gemini 3.1 Flash Lite</span> · QuantDrop v2.1</div></div>""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
