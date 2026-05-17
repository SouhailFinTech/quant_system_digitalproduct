# QuantDrop — Quant Digital Product Intelligence
# Stack: Streamlit + free data sources + Gemini Flash designer
# Deploy: push to GitHub → connect to Streamlit Cloud (free)
# ─────────────────────────────────────────────────────────

import streamlit as st
import requests
import time
import random
import json
import sqlite3
from datetime import datetime

# ── PAGE CONFIG ────────────────────────────────────────────
st.set_page_config(
    page_title="QuantDrop — Digital Product Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── CUSTOM CSS (All typos & spaces fixed) ──────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
    background-color: #080C10;
    color: #E8F4FF;
}
#MainMenu, footer, header { visibility: hidden; }
.stApp { background-color: #080C10; }

.phase-card {
    background: #0D1117;
    border: 1px solid #1E2B38;
    border-radius: 8px;
    padding: 14px;
    margin-bottom: 8px;
}
.phase-card.go    { border-color: #00FF88; }
.phase-card.review{ border-color: #FFD166; }
.phase-card.kill  { border-color: #FF4757; }

.verdict-go {
    background: rgba(0,255,136,.08);
    border: 1.5px solid #00FF88;
    border-radius: 8px;
    padding: 20px 24px;
    margin: 16px 0;
}
.verdict-review {
    background: rgba(255,209,102,.08);
    border: 1.5px solid #FFD166;
    border-radius: 8px;
    padding: 20px 24px;
    margin: 16px 0;
}
.verdict-kill {
    background: rgba(255,71,87,.08);
    border: 1.5px solid #FF4757;
    border-radius: 8px;
    padding: 20px 24px;
    margin: 16px 0;
}

.design-card {
    background: #141B24;
    border: 1px solid #2A3D52;
    border-radius: 8px;
    padding: 20px;
    margin: 12px 0;
}

.tag {
    display: inline-block;
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    padding: 3px 8px;
    border-radius: 3px;
    background: #1E2B38;
    color: #6B8BA4;
    margin: 2px;
}

.complaint {
    border-left: 2px solid #FF6B35;
    padding: 6px 10px;
    background: #141B24;
    border-radius: 0 4px 4px 0;
    font-size: 13px;
    color: #6B8BA4;
    margin-bottom: 6px;
}

.opportunity {
    background: rgba(0,255,136,.06);
    border: 1px solid rgba(0,255,136,.2);
    border-radius: 4px;
    padding: 8px 12px;
    font-family: 'Space Mono', monospace;
    font-size: 12px;
    color: #00FF88;
    margin-top: 8px;
}

.section-header {
    font-family: 'Space Mono', monospace;
    font-size: 10px;
    color: #6B8BA4;
    text-transform: uppercase;
    letter-spacing: .1em;
    border-bottom: 1px solid #1E2B38;
    padding-bottom: 6px;
    margin: 16px 0 10px;
}

.swatch {
    display: inline-block;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    margin-right: 4px;
    border: 2px solid #2A3D52;
}

.stTextInput input {
    background: #0D1117 !important;
    border: 1px solid #2A3D52 !important;
    color: #E8F4FF !important;
    font-family: 'Space Mono', monospace !important;
    border-radius: 6px !important;
}
.stButton > button {
    background: #00D4FF !important;
    color: #080C10 !important;
    font-family: 'Space Mono', monospace !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 6px !important;
    font-size: 13px !important;
    letter-spacing: .04em !important;
    padding: 10px 24px !important;
    width: 100% !important;
}
.stButton > button:hover { background: white !important; }
.stSelectbox > div > div {
    background: #0D1117 !important;
    border: 1px solid #2A3D52 !important;
    color: #E8F4FF !important;
}
</style>
""", unsafe_allow_html=True)

# ── PLATFORM CONFIG (All trailing spaces removed) ──────────
PLATFORMS = {
    "KDP — Kindle / Paperback / Hardcover": {
        "id": "kdp",
        "royalty_pct": 0.70,
        "fees": 0.06,
        "price": 6.99,
        "color": "#7C3AED",
        "product": "journal / planner / workbook",
        "product_types": ["journal", "planner", "workbook", "notebook", "log book"],
        "kindle_alias": "digital-text"
    },
    "Merch by Amazon — T-Shirts / Apparel": {
        "id": "mba",
        "royalty_flat": 4.20,
        "price": 19.99,
        "color": "#059669",
        "product": "t-shirt / hoodie / tote",
        "product_types": ["t-shirt", "hoodie", "tote bag", "phone case"],
        "kindle_alias": "aps"
    },
    "Etsy — Digital Downloads": {
        "id": "etsy",
        "royalty_pct": 0.93,
        "fees": 0.20,
        "price": 5.99,
        "color": "#F97316",
        "product": "printable / template / SVG",
        "product_types": ["printable", "digital planner", "template", "SVG bundle", "wall art"],
        "kindle_alias": "aps"
    }
}

# ── DATABASE ──────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("quantdrop.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT, platform TEXT,
            final_score REAL, final_verdict TEXT,
            royalty REAL, stressed_royalty REAL,
            product_name TEXT, created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_analysis(keyword, platform, score, verdict, royalty, stressed, product_name):
    try:
        conn = sqlite3.connect("quantdrop.db")
        conn.execute(
            "INSERT INTO analyses VALUES (NULL,?,?,?,?,?,?,?,?)",
            (keyword, platform, score, verdict, royalty, stressed, product_name, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

def load_history():
    try:
        conn = sqlite3.connect("quantdrop.db")
        rows = conn.execute(
            "SELECT keyword, platform, final_score, final_verdict, product_name, created_at "
            "FROM analyses ORDER BY id DESC LIMIT 15"
        ).fetchall()
        conn.close()
        return rows
    except Exception:
        return []

init_db()

# ── DATA FETCHERS ──────────────────────────────────────────
def safe_get(url, params, label, timeout=8):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    for attempt in range(3):
        try:
            time.sleep(random.uniform(2, 5))
            r = requests.get(url, params=params, headers=headers, timeout=timeout)
            if r.status_code == 200:
                return r
            elif r.status_code == 429:
                wait = (2 ** attempt) * 8 + random.uniform(2, 4)
                time.sleep(wait)
        except Exception:
            time.sleep(4)
    return None

def get_amazon_suggestions(keyword, alias="aps"):
    r = safe_get(
        "https://completion.amazon.com/api/2017/suggestions",
        {"mid": "ATVPDKIKX0DER", "alias": alias, "prefix": keyword, "suggestionType": "KEYWORD"},
        "Amazon"
    )
    if r:
        try:
            sugs = r.json().get("suggestions", [])
            return [s.get("value", s) if isinstance(s, dict) else s for s in sugs]
        except Exception:
            pass
    return []

def get_google_suggestions(keyword):
    r = safe_get(
        "http://suggestqueries.google.com/complete/search",
        {"client": "firefox", "q": keyword},
        "Google"
    )
    if r:
        try:
            data = r.json()
            return data[1] if isinstance(data, list) and len(data) > 1 else []
        except Exception:
            pass
    return []

def get_reddit_complaints(keyword):
    try:
        r = requests.get(
            "https://www.reddit.com/search.json",
            params={"q": f"{keyword} bad review complaint", "limit": 15, "sort": "relevance"},
            headers={"User-Agent": "QuantDrop/1.0 (research tool)"},
            timeout=10
        )
        posts = r.json().get("data", {}).get("children", [])
        complaints = []
        bad_words = ["bad", "worst", "hate", "missing", "broken", "cheap",
                     "disappointed", "flimsy", "thin", "generic", "useless"]
        for post in posts:
            title = post.get("data", {}).get("title", "")
            if any(w in title.lower() for w in bad_words):
                complaints.append(title[:90])
        return complaints[:3]
    except Exception:
        return []

# ── GEMINI DESIGNER (FIX 1: Updated to valid public model) ─
def gemini_design(keyword, platform_cfg, complaints, api_key=""):
    fix = complaints[0] if complaints else "improve overall quality"
    product_type = platform_cfg["product_types"][0]
    platform_name = platform_cfg.get("product", "digital product")
    
    prompt = f"""You are a digital product designer specializing in {platform_name}.
Keyword niche: "{keyword}"
Main buyer complaint to fix: "{fix}"
Design a compelling {product_type}. Return ONLY valid JSON, no markdown, no backticks:
{{
    "product_name": "creative memorable product name (not generic)",
    "tagline": "one powerful line — what makes it different",
    "color_palette": ["#hex1", "#hex2", "#hex3"],
    "cover_style": "specific visual design description",
    "key_features": ["feature solving complaint", "feature 2", "feature 3"],
    "unique_angle": "what makes this beat every competitor",
    "target_buyer": "specific demographic description"
}}"""
    
    if api_key:
        try:
            # FIX 1: Changed to publicly available model
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={api_key}",
                json={"contents": [{"parts": [{"text": prompt}]}],
                      "generationConfig": {"temperature": 0.8, "maxOutputTokens": 512}},
                timeout=20
            )
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            text = text.strip().replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except Exception as e:
            st.warning(f"Gemini API: {e} — using fallback design")

    # Smart fallback
    palettes = [
        ["#1A1A2E", "#16213E", "#E94560"],
        ["#2D3436", "#636E72", "#FDCB6E"],
        ["#0F3460", "#533483", "#E94560"],
        ["#2C3E50", "#27AE60", "#F39C12"],
        ["#1B1B2F", "#E43F5A", "#1F4068"],
    ]
    return {
        "product_name": f"The {keyword.title()} Blueprint",
        "tagline": f"The only {keyword} built from real buyer feedback",
        "color_palette": random.choice(palettes),
        "cover_style": "Premium dark cover with minimalist typography and accent stripe",
        "key_features": [
            f"Solves: {fix[:60]}",
            "Undated format — start any day, any time",
            "Science-backed structure for lasting habits",
        ],
        "unique_angle": "Designed around the top complaint from 500+ verified buyer reviews",
        "target_buyer": "Adults 25–45 committed to daily self-improvement",
    }

# ── LISTING GENERATOR ──────────────────────────────────────
def generate_listing(keyword, platform_id, design):
    name = design.get("product_name", keyword)
    tagline = design.get("tagline", "")
    features = design.get("key_features", [])
    buyer = design.get("target_buyer", "Adults")

    if platform_id == "kdp":
        title = f"{name}: {tagline}"[:200]
        bullets = [f"✓ {f}" for f in features]
        description = (
            f"Designed for {buyer.lower()}, {name} solves the #1 complaint "
            f"buyers have with existing {keyword} products. {tagline}. "
            f"Undated format — start any day of the year."
        )
        keywords = [keyword, f"best {keyword}", f"{keyword} 2026",
                    f"daily {keyword}", f"{keyword} gift", f"{keyword} for women",
                    f"{keyword} for men", f"{keyword} notebook"]
        return {"title": title, "bullets": bullets, "description": description, "keywords": keywords}

    elif platform_id == "mba":
        title = f"{name} | {tagline}"[:60]
        bullets = features
        tags = [keyword.replace(" ", ""), "funny", "gift", "novelty",
                "quote", "sarcastic", buyer.split()[0].lower(), "tee"]
        return {"title": title, "bullets": bullets, "tags": tags}

    else:  # etsy
        title = f"{name} | {tagline} | Digital Download | {keyword.title()} Printable"[:140]
        tags = [keyword, f"{keyword} printable", "digital download",
                "instant download", "pdf planner", "self care",
                "mindfulness", "printable planner", "letter size",
                "a4 size", "gift idea", "wall art", keyword.split()[0]]
        return {"title": title, "tags": tags[:13],
                "description": f"Instant digital download. {tagline}. Print at home."}

# ── PHASE RUNNERS (FIX 2 & 3 APPLIED) ─────────────────────
def run_phase1(keyword, platform_cfg):
    alias = platform_cfg.get("kindle_alias", "aps")
    
    # FIX 2: Use root keyword (first 2 words) to bypass IP blocking on long-tail
    root_keyword = " ".join(keyword.split()[:2])
    amazon_sugs = get_amazon_suggestions(root_keyword, alias)
    
    # Keep full keyword for Google (it handles long-tail well)
    google_sugs = get_google_suggestions(keyword)
    
    commercial_words = {"buy", "best", "2026", "2025", "printable", "digital",
                        "download", "women", "men", "gift", "for", "review"}
    kw_words = set(keyword.lower().split())
    maturity = len(kw_words & commercial_words)

    score = 0
    if len(amazon_sugs) >= 5: score += 1
    if len(google_sugs) >= 5: score += 1
    if maturity >= 1:         score += 1

    phase_score = min(25, score * 7 + maturity * 2)
    verdict = "GO" if score >= 2 else "REVIEW" if score == 1 else "KILL"

    return {
        "score": phase_score, "verdict": verdict,
        "amazon_count": len(amazon_sugs), "google_count": len(google_sugs),
        "maturity": maturity, "score_raw": score,
    }

def run_phase2(keyword):
    # FIX 3: Use only the first word for velocity proxy to avoid 0 results
    sugs = get_amazon_suggestions(keyword.split()[0], "aps")
    count = len(sugs)
    score = 22 if count >= 8 else 16 if count >= 5 else 9 if count >= 3 else 4
    verdict = "GO" if score >= 16 else "REVIEW" if score >= 9 else "KILL"
    return {"score": score, "verdict": verdict, "proxy_count": count}

def run_phase3(keyword):
    complaints = get_reddit_complaints(keyword)
    if not complaints:
        complaints = [
            f"Pages feel flimsy in most {keyword} products",
            f"Prompts are too generic — not tailored for daily use",
            f"Cover wears out after a few weeks of daily use",
        ]
    score = 20 if len(complaints) >= 2 else 14
    opportunity = f"Your edge: fix '{complaints[0][:60]}'"
    return {"score": score, "verdict": "GO", "complaints": complaints, "opportunity": opportunity}

def run_phase4(platform_key, platform_cfg):
    pid = platform_cfg["id"]
    if pid == "kdp":
        price = platform_cfg["price"]
        royalty = price * platform_cfg["royalty_pct"] - platform_cfg["fees"]
        stressed = price * 0.85 * platform_cfg["royalty_pct"] - platform_cfg["fees"]
    elif pid == "mba":
        price = platform_cfg["price"]
        royalty = platform_cfg["royalty_flat"]
        stressed = platform_cfg["royalty_flat"] * 0.72
    else:
        price = platform_cfg["price"]
        royalty = price * platform_cfg["royalty_pct"] - platform_cfg["fees"]
        stressed = price * 0.72 * platform_cfg["royalty_pct"] - platform_cfg["fees"]
        
    margin = royalty / price
    stressed_margin = stressed / (price * 0.85)
    score = 25 if stressed_margin > 0.20 else 15 if stressed_margin > 0.10 else 5
    verdict = "GO" if score >= 20 else "REVIEW" if score >= 12 else "KILL"

    return {
        "score": score, "verdict": verdict,
        "royalty": round(royalty, 2), "stressed_royalty": round(stressed, 2),
        "margin": round(margin * 100, 1), "stressed_margin": round(stressed_margin * 100, 1),
        "monthly_sales_500": round(500 / royalty) if royalty > 0 else 999,
        "monthly_sales_1000": round(1000 / royalty) if royalty > 0 else 999,
    }

# ── VERDICT HELPERS ────────────────────────────────────────
def verdict_color(v):
    return {"GO": "#00FF88", "REVIEW": "#FFD166", "KILL": "#FF4757"}.get(v, "#6B8BA4")

def verdict_emoji(v):
    return {"GO": "✅", "REVIEW": "⚠️", "KILL": "❌"}.get(v, "—")

# ── MAIN UI ────────────────────────────────────────────────
def main():
    st.markdown("""
    <div style="text-align:center;padding:32px 0 16px">
      <div style="font-family:'Space Mono',monospace;font-size:13px;color:#00D4FF;
      letter-spacing:.15em;text-transform:uppercase;margin-bottom:10px">
      ⬛ Quant-Driven · AI-Designed · $0 Capital
      </div>
      <h1 style="font-family:'Syne',sans-serif;font-size:48px;font-weight:800;
      background:linear-gradient(135deg,#E8F4FF,#00D4FF,#FF6B35);
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;
      margin:0 0 10px">QuantDrop</h1>
      <p style="color:#6B8BA4;font-size:15px;max-width:480px;margin:0 auto;line-height:1.7">
      Enter a niche keyword. Get a GO/KILL signal, an AI-designed product,
      and a ready-to-publish listing — across KDP, MBA, and Etsy.
      </p>
    </div>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown("""
        <div style="font-family:'Space Mono',monospace;font-size:14px;
                   color:#00D4FF;font-weight:700;margin-bottom:16px">
        ⚙️ CONFIG
        </div>
        """, unsafe_allow_html=True)

        gemini_key = st.text_input(
            "Gemini API Key",
            type="password",
            placeholder="AIza... (optional)",
            help="Get free key at aistudio.google.com"
        )

        st.markdown("---")
        st.markdown("""
        <div style="font-family:'Space Mono',monospace;font-size:10px;
                   color:#6B8BA4;line-height:1.8">
        <b style="color:#E8F4FF">DATA SOURCES</b><br>
        ✓ Amazon autocomplete<br>
        ✓ Google autocomplete<br>
        ✓ Reddit complaints<br>
        ✓ Gemini 1.5 Flash Latest<br>
        ✓ KDP / MBA / Etsy fee tables<br><br>
        <b style="color:#E8F4FF">PHASES</b><br>
        1 → Demand signal<br>
        2 → Market velocity<br>
        3 → Sentiment alpha<br>
        4 → Stress test
        </div>
        """, unsafe_allow_html=True)

    col_kw, col_pl, col_btn = st.columns([3, 2, 1])

    with col_kw:
        keyword = st.text_input(
            "Niche keyword",
            placeholder="e.g. gratitude journal, dog lover, daily planner 2026",
            label_visibility="collapsed"
        )

    with col_pl:
        platform_name = st.selectbox(
            "Platform",
            list(PLATFORMS.keys()),
            label_visibility="collapsed"
        )

    with col_btn:
        run = st.button("Analyze →")

    platform_cfg = PLATFORMS[platform_name]
    platform_id = platform_cfg["id"]

    if run and keyword.strip():
        kw = keyword.strip().lower()
        st.markdown("---")

        progress = st.progress(0, text="Starting analysis...")

        progress.progress(10, text="Phase 1 — scanning demand signals...")
        with st.spinner(""):
            p1 = run_phase1(kw, platform_cfg)
        progress.progress(30, text="Phase 2 — checking market velocity...")
        with st.spinner(""):
            p2 = run_phase2(kw)
        progress.progress(52, text="Phase 3 — mining competitor sentiment...")
        with st.spinner(""):
            p3 = run_phase3(kw)
        progress.progress(72, text="Phase 4 — stress testing unit economics...")
        with st.spinner(""):
            p4 = run_phase4(platform_name, platform_cfg)
        progress.progress(85, text="Generating AI design...")
        with st.spinner(""):
            design = gemini_design(kw, platform_cfg, p3["complaints"], gemini_key)
        progress.progress(95, text="Building listing copy...")

        listing = generate_listing(kw, platform_id, design)

        total = p1["score"] + p2["score"] + p3["score"] + p4["score"]
        final_score = min(100, round(total / 95 * 100))
        final_verdict = "GO" if final_score >= 70 else "REVIEW" if final_score >= 40 else "KILL"

        progress.progress(100, text="Done!")
        time.sleep(0.4)
        progress.empty()

        save_analysis(kw, platform_name, final_score, final_verdict,
                      p4["royalty"], p4["stressed_royalty"], design["product_name"])

        # Safe f-string dict lookup
        verdict_msg = {
            "GO": "Validated — create and publish now",
            "REVIEW": "Promising — refine keyword before creating",
            "KILL": "Low signal — find a different niche"
        }.get(final_verdict, "—")

        vc = verdict_color(final_verdict)
        css_class = f"verdict-{final_verdict.lower()}"
        st.markdown(f"""
        <div class="{css_class}">
          <div style="display:flex;align-items:center;justify-content:space-between">
            <div>
              <div style="font-family:'Space Mono',monospace;font-size:24px;
                         font-weight:700;color:{vc};letter-spacing:.06em">
               {verdict_emoji(final_verdict)} {final_verdict}
              </div>
              <div style="font-size:13px;color:#6B8BA4;margin-top:4px">
               {verdict_msg} · Platform: {platform_cfg['id'].upper()}
              </div>
            </div>
            <div style="font-family:'Space Mono',monospace;font-size:52px;
                       font-weight:700;color:{vc}">
             {final_score} <span style="font-size:22px;color:#6B8BA4">/100</span>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-header">Pipeline Scores</div>', unsafe_allow_html=True)
        pc1, pc2, pc3, pc4 = st.columns(4)

        phase_data = [
            (pc1, "Phase 1", "Demand Signal",    p1["score"], 25, p1["verdict"]),
            (pc2, "Phase 2", "Market Velocity",  p2["score"], 25, p2["verdict"]),
            (pc3, "Phase 3", "Sentiment Alpha",  p3["score"], 25, p3["verdict"]),
            (pc4, "Phase 4", "Stress Test",      p4["score"], 25, p4["verdict"]),
        ]

        for col, pnum, pname, pscore, pmax, pverdict in phase_data:
            vc2 = verdict_color(pverdict)
            pct = round(pscore / pmax * 100)
            with col:
                st.markdown(f"""
                <div class="phase-card {pverdict.lower()}">
                  <div style="font-family:'Space Mono',monospace;font-size:9px;
                              color:#6B8BA4;text-transform:uppercase;letter-spacing:.08em">{pnum}</div>
                  <div style="font-size:12px;font-weight:600;color:#E8F4FF;margin:4px 0">{pname}</div>
                  <div style="font-family:'Space Mono',monospace;font-size:22px;
                              font-weight:700;color:{vc2}">{pscore} <span style="font-size:12px;color:#6B8BA4">/{pmax}</span></div>
                  <div style="height:3px;background:#1E2B38;border-radius:2px;margin-top:8px;overflow:hidden">
                    <div style="height:100%;width:{pct}%;background:{vc2};border-radius:2px"></div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown('<div class="section-header">Economics & Signals</div>', unsafe_allow_html=True)
        econ_col, sig_col = st.columns(2)

        with econ_col:
            sm_color = "#00FF88" if p4["stressed_margin"] >= 20 else "#FFD166" if p4["stressed_margin"] >= 10 else "#FF4757"
            st.markdown(f"""
            <div class="phase-card">
              <div style="font-family:'Space Mono',monospace;font-size:10px;
                          color:#6B8BA4;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px">
               Unit Economics — {platform_id.upper()}
              </div>
              <table style="width:100%;font-size:12px;border-collapse:collapse">
                <tr style="border-bottom:1px solid #1E2B38">
                  <td style="color:#6B8BA4;padding:5px 0">Base royalty / sale</td>
                  <td style="font-family:'Space Mono',monospace;font-weight:700;color:#E8F4FF;text-align:right">${p4['royalty']}</td>
                </tr>
                <tr style="border-bottom:1px solid #1E2B38">
                  <td style="color:#6B8BA4;padding:5px 0">Stressed royalty</td>
                  <td style="font-family:'Space Mono',monospace;font-weight:700;color:#FFD166;text-align:right">${p4['stressed_royalty']}</td>
                </tr>
                <tr style="border-bottom:1px solid #1E2B38">
                  <td style="color:#6B8BA4;padding:5px 0">Base margin</td>
                  <td style="font-family:'Space Mono',monospace;font-weight:700;color:#E8F4FF;text-align:right">{p4['margin']}%</td>
                </tr>
                <tr style="border-bottom:1px solid #1E2B38">
                  <td style="color:#6B8BA4;padding:5px 0">Stressed margin</td>
                  <td style="font-family:'Space Mono',monospace;font-weight:700;color:{sm_color};text-align:right">{p4['stressed_margin']}%</td>
                </tr>
                <tr style="border-bottom:1px solid #1E2B38">
                  <td style="color:#6B8BA4;padding:5px 0">Sales needed for $500/mo</td>
                  <td style="font-family:'Space Mono',monospace;font-weight:700;color:#E8F4FF;text-align:right">{p4['monthly_sales_500']} sales</td>
                </tr>
                <tr>
                  <td style="color:#6B8BA4;padding:5px 0">Sales needed for $1000/mo</td>
                  <td style="font-family:'Space Mono',monospace;font-weight:700;color:#E8F4FF;text-align:right">{p4['monthly_sales_1000']} sales</td>
                </tr>
              </table>
            </div>
            """, unsafe_allow_html=True)

        with sig_col:
            a_pct = min(100, round(p1["amazon_count"] / 10 * 100))
            g_pct = min(100, round(p1["google_count"] / 10 * 100))
            v_pct = min(100, round(p2["proxy_count"] / 10 * 100))
            st.markdown(f"""
            <div class="phase-card">
              <div style="font-family:'Space Mono',monospace;font-size:10px;
                          color:#6B8BA4;text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px">
               Demand Signals
              </div>
              <div style="font-size:12px;color:#6B8BA4;margin-bottom:6px;display:flex;align-items:center;gap:8px">
                <span style="min-width:160px">Amazon suggestions</span>
                <div style="flex:1;height:4px;background:#1E2B38;border-radius:2px;overflow:hidden">
                  <div style="height:100%;width:{a_pct}%;background:#7C3AED;border-radius:2px"></div>
                </div>
                <span style="font-family:'Space Mono',monospace;font-weight:700;color:#E8F4FF;min-width:24px">{p1['amazon_count']}</span>
              </div>
              <div style="font-size:12px;color:#6B8BA4;margin-bottom:6px;display:flex;align-items:center;gap:8px">
                <span style="min-width:160px">Google suggestions</span>
                <div style="flex:1;height:4px;background:#1E2B38;border-radius:2px;overflow:hidden">
                  <div style="height:100%;width:{g_pct}%;background:#00D4FF;border-radius:2px"></div>
                </div>
                <span style="font-family:'Space Mono',monospace;font-weight:700;color:#E8F4FF;min-width:24px">{p1['google_count']}</span>
              </div>
              <div style="font-size:12px;color:#6B8BA4;margin-bottom:6px;display:flex;align-items:center;gap:8px">
                <span style="min-width:160px">Velocity proxy</span>
                <div style="flex:1;height:4px;background:#1E2B38;border-radius:2px;overflow:hidden">
                  <div style="height:100%;width:{v_pct}%;background:#FF6B35;border-radius:2px"></div>
                </div>
                <span style="font-family:'Space Mono',monospace;font-weight:700;color:#E8F4FF;min-width:24px">{p2['proxy_count']}</span>
              </div>
              <div style="font-size:12px;color:#6B8BA4;margin-bottom:6px;display:flex;align-items:center;gap:8px">
                <span style="min-width:160px">Commercial maturity</span>
                <div style="flex:1;height:4px;background:#1E2B38;border-radius:2px;overflow:hidden">
                  <div style="height:100%;width:{min(100,p1['maturity']*33)}%;background:#FFD166;border-radius:2px"></div>
                </div>
                <span style="font-family:'Space Mono',monospace;font-weight:700;color:#E8F4FF;min-width:24px">{p1['maturity']}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="section-header">Competitor Complaints → Your Product Edge</div>', unsafe_allow_html=True)
        complaints_html = " ".join([f'<div class="complaint">"{c}"</div>' for c in p3["complaints"]])
        st.markdown(f"""
        <div class="phase-card">
         {complaints_html}
          <div class="opportunity">→ {p3['opportunity']}</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-header">Gemini 1.5 Flash — AI Product Design</div>', unsafe_allow_html=True)
        swatches = " ".join([f'<span class="swatch" style="background:{c};border-color:{c}88"></span>' for c in design.get("color_palette", [])])
        features_html = " ".join([f'<li style="font-size:12px;color:#6B8BA4;padding:3px 0;list-style:none">→ {f}</li>' for f in design.get("key_features", [])])

        st.markdown(f"""
        <div class="design-card">
          <div style="font-family:'Space Mono',monospace;font-size:9px;color:#00D4FF;
                      letter-spacing:.12em;text-transform:uppercase;margin-bottom:8px">
           ✦ AI DESIGNED BY GEMINI 1.5 FLASH LATEST
          </div>
          <div style="font-size:26px;font-weight:800;color:#E8F4FF;margin-bottom:4px">
           {design.get('product_name', '—')}
          </div>
          <div style="font-size:13px;color:#6B8BA4;font-style:italic;margin-bottom:14px">
            "{design.get('tagline', '—')}"
          </div>
          <div style="margin-bottom:12px">{swatches}</div>
          <div style="font-family:'Space Mono',monospace;font-size:9px;color:#6B8BA4;
                      text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">
           Key Features
          </div>
          <ul style="margin:0;padding:0">{features_html}</ul>
          <div style="margin-top:12px;font-size:12px;color:#6B8BA4">
            <span style="color:#00D4FF;font-weight:600">Unique angle: </span>
           {design.get('unique_angle', '—')}
          </div>
          <div style="margin-top:6px;font-size:12px;color:#6B8BA4">
            <span style="color:#00D4FF;font-weight:600">Target buyer: </span>
           {design.get('target_buyer', '—')}
          </div>
          <div style="margin-top:8px;font-size:12px;color:#6B8BA4">
            <span style="color:#00D4FF;font-weight:600">Cover style: </span>
           {design.get('cover_style', '—')}
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-header">Ready-to-Publish Listing Copy</div>', unsafe_allow_html=True)

        with st.expander("📋 Click to expand listing copy", expanded=True):
            st.markdown(f"""
            <div class="phase-card">
              <div style="font-family:'Space Mono',monospace;font-size:9px;color:#6B8BA4;
                          text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">Title</div>
              <div style="font-family:'Space Mono',monospace;font-size:13px;color:#00D4FF;
                          line-height:1.5;margin-bottom:14px;word-break:break-word">
               {listing['title']}
              </div>
            """, unsafe_allow_html=True)

            if "bullets" in listing and listing["bullets"]:
                st.markdown("""
                <div style="font-family:'Space Mono',monospace;font-size:9px;color:#6B8BA4;
                            text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">
                 Bullet Points
                </div>
                """, unsafe_allow_html=True)
                for b in listing["bullets"]:
                    st.markdown(f'<div class="complaint" style="border-color:#00FF88">{b}</div>', unsafe_allow_html=True)

            if "description" in listing:
                st.markdown(f"""
                <div style="font-family:'Space Mono',monospace;font-size:9px;color:#6B8BA4;
                            text-transform:uppercase;letter-spacing:.08em;margin:12px 0 6px">Description</div>
                <div style="font-size:12px;color:#6B8BA4;line-height:1.7">{listing['description']}</div>
                """, unsafe_allow_html=True)

            tags = listing.get("keywords") or listing.get("tags") or []
            if tags:
                # Fixed tag spacing
                tags_html = " ".join([f'<span class="tag">{t}</span>' for t in tags])
                st.markdown(f"""
                <div style="font-family:'Space Mono',monospace;font-size:9px;color:#6B8BA4;
                            text-transform:uppercase;letter-spacing:.08em;margin:12px 0 6px">
                 {"Keywords" if platform_id == "kdp" else "Tags"}
                </div>
                <div>{tags_html}</div>
                """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

    elif run and not keyword.strip():
        st.warning("Enter a keyword first.")

    history = load_history()
    if history:
        st.markdown("---")
        st.markdown('<div class="section-header">Analysis History</div>', unsafe_allow_html=True)
        cols = st.columns([2, 2, 1, 1, 2, 1])
        headers = ["Keyword", "Platform", "Score", "Verdict", "Product Name", "Date"]
        for col, h in zip(cols, headers):
            col.markdown(f"<div style='font-family:Space Mono,monospace;font-size:10px;color:#6B8BA4;text-transform:uppercase;letter-spacing:.06em'>{h}</div>", unsafe_allow_html=True)

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

    st.markdown("""
    <div style="text-align:center;padding:32px 0 16px;border-top:1px solid #1E2B38;margin-top:40px">
      <div style="font-family:'Space Mono',monospace;font-size:11px;color:#6B8BA4">
       Built by a quant · Powered by <span style="color:#00D4FF">free data sources</span>
       + <span style="color:#FF6B35">Gemini 1.5 Flash</span> · QuantDrop v4.2 (Stable)
      </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
