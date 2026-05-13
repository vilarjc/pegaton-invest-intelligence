#!/usr/bin/python3
"""
Olympiad API Server — serves static frontend + RISE ratings + Widget Factory.
Widget Factory: agents develop independent widgets, you evaluate & integrate.
"""
import json, os, re, sqlite3, sys
sys.path.insert(0, "/root/pegaton_invest_intelligence")
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime

FRONTEND_DIR = "/root/pegaton_invest_intelligence/frontend"
WIDGETS_DIR  = os.path.join(FRONTEND_DIR, "widgets")
DB_PATH      = "/root/pegaton_invest_intelligence/harness.db"
PORT         = 8765

os.makedirs(WIDGETS_DIR, exist_ok=True)

# ── Database ─────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS olympiad_ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_id TEXT NOT NULL UNIQUE, user_stars INTEGER NOT NULL DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS widgets (
        id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT,
        section TEXT DEFAULT '', team_label TEXT DEFAULT '',
        expert TEXT, pm TEXT, programmer TEXT,
        endpoint TEXT, html_file TEXT,
        rating INTEGER DEFAULT 0, integrated INTEGER DEFAULT 0,
        status TEXT DEFAULT 'draft',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    # Migrate: add columns if missing
    cols = [r[1] for r in conn.execute("PRAGMA table_info(widgets)").fetchall()]
    if 'section' not in cols:
        conn.execute("ALTER TABLE widgets ADD COLUMN section TEXT DEFAULT ''")
    if 'team_label' not in cols:
        conn.execute("ALTER TABLE widgets ADD COLUMN team_label TEXT DEFAULT ''")
    # News Sentiment snapshots
    conn.execute("""CREATE TABLE IF NOT EXISTS news_sentiment_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        score INTEGER,
        total_articles INTEGER DEFAULT 0,
        sources TEXT DEFAULT '{}',
        batch_id TEXT,
        captured_at TEXT DEFAULT (datetime('now')))
    """)
    conn.execute("""CREATE TABLE IF NOT EXISTS news_sentiment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_hash TEXT UNIQUE, title TEXT, summary TEXT, source TEXT,
        link TEXT, published TEXT, sentiment_score INTEGER,
        compound_score REAL, batch_id TEXT,
        captured_at TEXT DEFAULT (datetime('now')))
    """)
    conn.execute("""CREATE TABLE IF NOT EXISTS widget_adjustments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        widget_id TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (widget_id) REFERENCES widgets(id)
    )""")
    conn.commit()
    conn.close()

# ── Widget CRUD ──────────────────────────────────────────────────

def widget_all():
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM widgets ORDER BY created_at DESC").fetchall()
    conn.close(); return [dict(r) for r in rows]

def widget_get(wid):
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    r = conn.execute("SELECT * FROM widgets WHERE id=?", (wid,)).fetchone()
    conn.close(); return dict(r) if r else None

def widget_upsert(data):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""INSERT INTO widgets (id, name, description, section, team_label, expert, pm, programmer, endpoint, html_file, status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET
        name=excluded.name, description=excluded.description,
        section=excluded.section, team_label=excluded.team_label,
        expert=excluded.expert, pm=excluded.pm, programmer=excluded.programmer,
        endpoint=excluded.endpoint, html_file=excluded.html_file,
        status=excluded.status, updated_at=CURRENT_TIMESTAMP""",
        (data["id"], data["name"], data.get("description",""),
         data.get("section",""), data.get("team_label",""),
         data.get("expert",""), data.get("pm",""), data.get("programmer",""),
         data.get("endpoint",""), data.get("html_file",""), data.get("status","draft")))
    conn.commit(); conn.close()
    return widget_get(data["id"])

def widget_rate(wid, stars):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE widgets SET rating=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (stars, wid))
    conn.commit(); conn.close()
    return widget_get(wid)

def widget_toggle_integrate(wid):
    conn = sqlite3.connect(DB_PATH)
    r = conn.execute("SELECT integrated FROM widgets WHERE id=?", (wid,)).fetchone()
    if not r: conn.close(); return None
    new_val = 0 if r[0] else 1
    conn.execute("UPDATE widgets SET integrated=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (new_val, wid))
    conn.commit(); conn.close()
    return widget_get(wid)

def widget_integrated():
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM widgets WHERE integrated=1 ORDER BY rating DESC").fetchall()
    conn.close(); return [dict(r) for r in rows]

# ── Adjustment CRUD ────────────────────────────────────────────

def adjustment_create(widget_id, description):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO widget_adjustments (widget_id, description) VALUES (?,?)", (widget_id, description))
    conn.commit()
    aid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return adjustment_get(aid)

def adjustment_get(aid):
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    r = conn.execute("SELECT * FROM widget_adjustments WHERE id=?", (aid,)).fetchone()
    conn.close(); return dict(r) if r else None

def adjustment_list(widget_id=None):
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    if widget_id:
        rows = conn.execute("SELECT * FROM widget_adjustments WHERE widget_id=? ORDER BY created_at DESC", (widget_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM widget_adjustments ORDER BY created_at DESC").fetchall()
    conn.close(); return [dict(r) for r in rows]

def widget_sections():
    """Returns widgets grouped by section. Each section has: {section, label, teams: [...]}"""
    all_w = widget_all()
    sections = {}
    for w in all_w:
        sec = w.get("section") or w["id"]
        if sec not in sections:
            sections[sec] = {"section": sec, "name": w["name"], "teams": []}
        sections[sec]["teams"].append(w)
    # Sort: sections with integrated teams first, then by team count desc
    result = sorted(sections.values(), key=lambda s: ( -(sum(1 for t in s["teams"] if t["integrated"])), -len(s["teams"]) ))
    return result

# ── Seed initial widgets ─────────────────────────────────────────

SEED_WIDGETS = [
    # ── Sección: Fear & Greed (del concurso original) ──
    {"id":"fear-greed-a", "name":"Fear & Greed", "section":"fear-greed", "team_label":"Equipo A",
     "description":"Widget con velocímetro semicircular y aguja", "expert":"Organizador",
     "pm":"Gemini 2.5 Flash", "programmer":"Tencent HY3",
     "endpoint":"/api/v1/fear-greed", "html_file":"fear-greed-equipo-a.html", "status":"ready"},
    {"id":"fear-greed-b", "name":"Fear & Greed", "section":"fear-greed", "team_label":"Equipo B",
     "description":"Widget con anillo tipo speedometer con glow", "expert":"Organizador",
     "pm":"Nemotron 3 Super", "programmer":"Owl Alpha",
     "endpoint":"/api/v1/fear-greed", "html_file":"fear-greed-equipo-b.html", "status":"ready"},
    {"id":"fear-greed-c", "name":"Fear & Greed", "section":"fear-greed", "team_label":"Equipo C",
     "description":"Widget con barra termómetro horizontal", "expert":"Organizador",
     "pm":"DeepSeek V4 Flash", "programmer":"DeepSeek V4 Flash",
     "endpoint":"/api/v1/fear-greed", "html_file":"fear-greed-equipo-c.html", "status":"ready"},

    # ── Sección: Sentimiento ──
    {"id":"sentimiento", "name":"Sentimiento de Mercado", "section":"sentimiento", "team_label":"Equipo Principal",
     "description":"Análisis de sentimiento agregado de redes sociales y noticias",
     "expert":"Experto en Sentimiento", "pm":"PM Sentimiento", "programmer":"Equipo Demo",
     "endpoint":"/api/widgets/sentimiento/data", "html_file":"sentimiento.html", "status":"ready"},

    # ── Sección: Macro ──
    {"id":"macro", "name":"Indicadores Macroeconómicos", "section":"macro", "team_label":"Equipo Principal",
     "description":"VIX, DXY, PMIs, Inflación, S&P 500, Oro, Petróleo",
     "expert":"Experto en Macroeconomía", "pm":"PM Macro", "programmer":"Equipo Programación",
     "endpoint":"/api/widgets/macro/data", "html_file":"macro.html", "status":"ready"},
    {"id":"macro-b", "name":"Indicadores Macroeconómicos", "section":"macro", "team_label":"Equipo B",
     "description":"Panorama macro con dashboard de indicadores y semáforos",
     "expert":"Experto en Macroeconomía", "pm":"DeepSeek V4 Flash", "programmer":"Qwen3 Coder",
     "endpoint":"/api/widgets/macro/data", "html_file":"macro-equipo-b.html", "status":"ready"},
    {"id":"macro-c", "name":"Indicadores Macroeconómicos", "section":"macro", "team_label":"Equipo C",
     "description":"Dashboard macro con score circular y diagnóstico de mercado",
     "expert":"Experto en Macroeconomía", "pm":"Groq Qwen3", "programmer":"DeepSeek V4 Flash",
     "endpoint":"/api/widgets/macro/data", "html_file":"macro-equipo-c.html", "status":"ready"},

    # ── Sección: Noticias/Sentimiento (nuevo equipo) ──
    {"id":"news-sentimiento-a", "name":"Sentimiento de Noticias", "section":"noticias", "team_label":"Equipo Noticias",
     "description":"Widget que extrae noticias de RSS (Reuters, CNBC, MarketWatch, Google News) y calcula índice de sentimiento 0-100 usando VADER",
     "expert":"Experto en Noticias", "pm":"PM Noticias", "programmer":"Programador",
     "endpoint":"/api/v1/news-sentiment", "html_file":"news-sentimiento.html", "status":"ready"},

    # ── Secciones pendientes ──
    {"id":"tecnico", "name":"Análisis Técnico", "section":"tecnico", "team_label":"",
     "description":"Gráficos de velas, RSI, MACD, medias móviles",
     "expert":"Experto en Análisis Técnico", "pm":"", "programmer":"",
     "endpoint":"", "html_file":"", "status":"spec"},
    {"id":"cartera", "name":"Cartera y Asignación", "section":"cartera", "team_label":"",
     "description":"Distribución de activos, riesgo, rebalanceo",
     "expert":"Experto en Cartera", "pm":"", "programmer":"",
     "endpoint":"", "html_file":"", "status":"spec"},
    {"id":"flujos", "name":"Flujos de Capital", "section":"flujos", "team_label":"",
     "description":"Flujos institucionales, ETFs, money market",
     "expert":"Experto en Flujos", "pm":"", "programmer":"",
     "endpoint":"", "html_file":"", "status":"spec"},
    {"id":"regimen", "name":"Régimen de Mercado", "section":"regimen", "team_label":"",
     "description":"Volatilidad, correlaciones, regime change detection",
     "expert":"Experto en Régimen", "pm":"", "programmer":"",
     "endpoint":"", "html_file":"", "status":"spec"},
    {"id":"mesaredonda", "name":"Mesa Redonda Multi-Modelo", "section":"mesaredonda", "team_label":"",
     "description":"Consenso entre modelos AI sobre dirección del mercado",
     "expert":"Experto en AI Trading", "pm":"", "programmer":"",
     "endpoint":"", "html_file":"", "status":"spec"},
]

def seed_widgets():
    """Seed only if widget doesn't exist (preserves ratings & integration)."""
    for w in SEED_WIDGETS:
        existing = widget_get(w["id"])
        if not existing:
            widget_upsert(w)

# ── HTTP Handler ─────────────────────────────────────────────────

class OlympiadHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path); path = parsed.path

        # ── Widget APIs ──
        if path == "/api/widgets":
            return self._send_json(widget_all())
        if path == "/api/widgets/sections":
            return self._send_json(widget_sections())
        if path == "/api/widgets/integrated":
            return self._send_json(widget_integrated())
        if path == "/api/widgets/adjustments":
            return self._send_json(adjustment_list())
        if path.startswith("/api/widgets/adjustments/"):
            wid = path.split("/api/widgets/adjustments/")[1].split("?")[0]
            return self._send_json(adjustment_list(widget_id=wid))

        # ── MACRO Widget Data (reads from harness.db macro_snapshots) ──
        if path == "/api/widgets/macro/data":
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM macro_snapshots ORDER BY captured_at DESC LIMIT 10"
                ).fetchall()
                conn.close()

                if not rows:
                    return self._send_json({"widget":{"id":"macro","name":"Indicadores Macroeconómicos","status":"pending"},"html":"","data":{"indicators":[],"diagnosis":"Esperando primera ingesta de datos","timestamp":datetime.now().isoformat()}})

                latest = dict(rows[0])
                prev = dict(rows[1]) if len(rows) > 1 else None

                def pf(val, default=None):
                    if val is None: return default
                    try: return float(val)
                    except: return default

                def calc_change(curr, prev_val):
                    if curr is None or prev_val is None or prev_val == 0: return None
                    return round((curr - prev_val) / prev_val * 100, 2)

                def lv(v):
                    if v is None: return "gray"
                    if v < 15: return "green"
                    if v < 20: return "yellow"
                    return "red"
                def ld(v):
                    if v is None: return "gray"
                    if v < 96: return "green"
                    if v < 100: return "yellow"
                    return "red"
                def lp(v):
                    if v is None: return "gray"
                    if v > 50: return "green"
                    if v > 48: return "yellow"
                    return "red"
                def li(v):
                    if v is None: return "gray"
                    if v < 2.5: return "green"
                    if v < 3.5: return "yellow"
                    return "red"
                def lfed(v):
                    if v is None: return "gray"
                    if v < 3: return "green"
                    if v < 5: return "yellow"
                    return "red"
                def lsp(v):
                    if v is None: return "gray"
                    if v > 7000: return "green"
                    if v > 6500: return "yellow"
                    return "red"
                def lg(v):
                    if v is None: return "gray"
                    return "yellow"
                def lo(v):
                    if v is None: return "gray"
                    if v < 70: return "green"
                    if v < 90: return "yellow"
                    return "red"

                def cs(curr, prev):
                    c = calc_change(curr, prev)
                    if c is None: return "—"
                    return f"{'+' if c>=0 else ''}{c}%"

                vix_v = pf(latest.get("vix"))
                vix_p = pf(prev.get("vix")) if prev else None
                dxy_v = pf(latest.get("dxy"))
                dxy_p = pf(prev.get("dxy")) if prev else None
                sp_v = pf(latest.get("sp500"))
                sp_p = pf(prev.get("sp500")) if prev else None
                g_v = pf(latest.get("gold_price"))
                g_p = pf(prev.get("gold_price")) if prev else None
                o_v = pf(latest.get("oil_price"))
                o_p = pf(prev.get("oil_price")) if prev else None
                pm_v = pf(latest.get("pmi_manufacturing"))
                pm_p = pf(prev.get("pmi_manufacturing")) if prev else None
                ps_v = pf(latest.get("pmi_services"))
                ps_p = pf(prev.get("pmi_services")) if prev else None
                inf_v = pf(latest.get("inflation"))
                inf_p = pf(prev.get("inflation")) if prev else None
                fed_v = pf(latest.get("fed_rate"))
                fed_p = pf(prev.get("fed_rate")) if prev else None

                indicators = [
                    {"id":"vix","name":"VIX","band":"riesgo","value":f"{vix_v:.1f}" if vix_v else "—","level":lv(vix_v),"change":cs(vix_v,vix_p),"label":"Volatilidad"},
                    {"id":"dxy","name":"DXY","band":"riesgo","value":f"{dxy_v:.2f}" if dxy_v else "—","level":ld(dxy_v),"change":cs(dxy_v,dxy_p),"label":"Dólar"},
                    {"id":"gold","name":"Oro","band":"riesgo","value":f"${g_v:,.0f}" if g_v else "—","level":lg(g_v),"change":cs(g_v,g_p),"label":"Safe Haven"},
                    {"id":"pmi_m","name":"PMI Manufacturero","band":"ciclo","value":f"{pm_v:.1f}" if pm_v else "—","level":lp(pm_v),"change":cs(pm_v,pm_p),"label":"Manufactura"},
                    {"id":"pmi_s","name":"PMI Servicios","band":"ciclo","value":f"{ps_v:.1f}" if ps_v else "—","level":lp(ps_v),"change":cs(ps_v,ps_p),"label":"Servicios"},
                    {"id":"inflation","name":"Inflación","band":"ciclo","value":f"{inf_v:.1f}%" if inf_v else "—","level":li(inf_v),"change":cs(inf_v,inf_p),"label":"IPC"},
                    {"id":"fed_rate","name":"Tasa Fed","band":"ciclo","value":f"{fed_v:.2f}%" if fed_v else "—","level":lfed(fed_v),"change":cs(fed_v,fed_p),"label":"Política Monetaria"},
                    {"id":"sp500","name":"S&P 500","band":"global","value":f"{sp_v:,.0f}" if sp_v else "—","level":lsp(sp_v),"change":cs(sp_v,sp_p),"label":"Mercado"},
                    {"id":"oil","name":"Petróleo","band":"global","value":f"${o_v:.2f}" if o_v else "—","level":lo(o_v),"change":cs(o_v,o_p),"label":"Energía"},
                ]

                reds = [i for i in indicators if i["level"]=="red"]
                yellows = [i for i in indicators if i["level"]=="yellow"]
                greens = [i for i in indicators if i["level"]=="green"]
                parts = []
                if reds: parts.append(f"🔴 {len(reds)} en alerta")
                if yellows: parts.append(f"🟡 {len(yellows)} en precaución")
                if greens: parts.append(f"🟢 {len(greens)} estables")
                diagnosis = " · ".join(parts) if parts else "⚪ Sin datos"

                # Build history from all rows
                history = [{"captured_at": dict(r)["captured_at"], "sp500": dict(r)["sp500"], "vix": dict(r)["vix"], "dxy": dict(r)["dxy"]} for r in rows]

                return self._send_json({
                    "widget":{"id":"macro","name":"Indicadores Macroeconómicos","status":"ready"},
                    "html":"",
                    "data":{
                        "indicators":indicators,
                        "diagnosis":diagnosis,
                        "summary":latest.get("summary",""),
                        "history":history,
                        "total_records": len(rows),
                        "timestamp":latest.get("captured_at",datetime.now().isoformat()),
                    }
                })
            except Exception as e:
                return self._send_json({
                    "widget":{"id":"macro","name":"Indicadores Macroeconómicos","status":"error"},
                    "html":"",
                    "data":{"indicators":[],"diagnosis":f"Error: {e}","timestamp":datetime.now().isoformat()}
                })

        # ── Generic widget data handler ──
        if path.startswith("/api/widgets/") and path.endswith("/data"):
            wid = path.split("/api/widgets/")[1].split("/data")[0]
            w = widget_get(wid)
            if not w: return self._send_json({"error":"not_found"}, 404)
            html_path = os.path.join(WIDGETS_DIR, w.get("html_file",""))
            html = ""
            if os.path.exists(html_path):
                with open(html_path) as f: html = f.read()
            return self._send_json({"widget":w, "html":html})
        if path.startswith("/api/widgets/"):
            wid = path.split("/api/widgets/")[1].split("?")[0]
            if wid == "integrated": pass  # already handled above
            else:
                w = widget_get(wid)
                if w: return self._send_json(w)
                return self._send_json({"error":"not_found"}, 404)

        # ── OLYMPIAD APIs (existing) ──
        if path == "/api/ratings":
            return self._send_json(self._get_ratings())
        if path.startswith("/api/fullcode/"):
            model_id = path.split("/api/fullcode/")[1].split("?")[0]
            html_path = os.path.join(FRONTEND_DIR, "coding-olympiad", "html", f"{model_id}.html")
            if os.path.exists(html_path):
                with open(html_path) as f: code = f.read()
                return self._send_json({"model_id":model_id,"code":code,"lines":len(code.splitlines()),"chars":len(code)})
            return self._send_json({"error":"not_found"}, 404)
        if path == "/api/pm":
            pm_path = os.path.join(FRONTEND_DIR,"coding-olympiad","pm-data.json")
            if os.path.exists(pm_path):
                with open(pm_path) as f: return self._send_json(json.load(f))
            return self._send_json({"error":"not_found"}, 404)
        if path == "/api/v1/fear-greed":
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM fear_greed_snapshots ORDER BY captured_at DESC LIMIT 1"
                ).fetchone()
                conn.close()
                if row:
                    r = dict(row)
                    # Try to return full JSON from stored full_response
                    if r.get("full_response"):
                        try:
                            full = json.loads(r["full_response"])
                            # Add action_emoji mapping
                            emoji_map = {"Miedo extremo": "🔴", "Miedo": "🟠", "Neutral": "⚪", "Codicia": "🟢", "Codicia extrema": "🔵"}
                            full["action_emoji"] = emoji_map.get(full.get("action",""), "⚪")
                            full["cacheado"] = True
                            return self._send_json(full)
                        except: pass  # fall through to manual reconstruction
                    # Manual reconstruction
                    score = r.get("score", 50)
                    if score <= 25: action = "Miedo extremo"
                    elif score <= 45: action = "Miedo"
                    elif score <= 55: action = "Neutral"
                    elif score <= 75: action = "Codicia"
                    else: action = "Codicia extrema"
                    emoji_map = {"Miedo extremo": "🔴", "Miedo": "🟠", "Neutral": "⚪", "Codicia": "🟢", "Codicia extrema": "🔵"}
                    return self._send_json({
                        "score": score,
                        "action": action,
                        "action_emoji": emoji_map.get(action, "⚪"),
                        "timestamp": str(r.get("captured_at", datetime.now().isoformat())),
                        "cacheado": True,
                        "factores": {
                            "vix": {"value": r.get("vix_value"), "score": r.get("vix_score"), "peso": "40%"},
                            "macro": {"score": r.get("macro_score"), "peso": "35%"},
                            "sentimiento": {"score": r.get("sent_score"), "peso": "25%"}
                        }
                    })
                return self._send_json({"score":50,"action":"Neutral","action_emoji":"⚪","timestamp":datetime.now().isoformat(),"cacheado":False,"factores":{"vix":None,"macro":None,"sentimiento":None}})
            except Exception as e:
                return self._send_json({"error":str(e),"score":50,"action":"Neutral","action_emoji":"⚪","timestamp":datetime.now().isoformat(),"cacheado":False})

        # ── News Sentiment API ──
        if path == "/api/v1/news-sentiment":
            try:
                conn = sqlite3.connect(DB_PATH)
                conn.row_factory = sqlite3.Row
                # Get latest snapshot
                snap = conn.execute(
                    "SELECT * FROM news_sentiment_snapshots ORDER BY captured_at DESC LIMIT 1"
                ).fetchone()
                if snap: snap = dict(snap)
                # Get previous snapshot for delta calculation
                prev_snap = conn.execute(
                    "SELECT * FROM news_sentiment_snapshots ORDER BY captured_at DESC LIMIT 1 OFFSET 1"
                ).fetchone()
                if prev_snap: prev_snap = dict(prev_snap)
                # Get articles in the last 72h
                articles = conn.execute(
                    "SELECT source, sentiment_score, title FROM news_sentiment "
                    "WHERE captured_at > datetime('now', '-72 hours') "
                    "ORDER BY captured_at DESC"
                ).fetchall()
                conn.close()

                sources = {}
                total_arts = 0
                article_scores = []
                all_titles = []
                for a in articles:
                    d = dict(a)
                    source_key = d['source'].lower().replace(' ','_').split('/')[0].split('.')[0]
                    if not source_key: source_key = 'unknown'
                    sources[source_key] = sources.get(source_key, 0) + 1
                    total_arts += 1
                    if d.get('sentiment_score') is not None:
                        article_scores.append(d['sentiment_score'])
                    if d.get('title'):
                        all_titles.append(d['title'])

                # Compute distribution
                fear = sum(1 for s in article_scores if s < 25)
                neutral = sum(1 for s in article_scores if 25 <= s < 75)
                greed = sum(1 for s in article_scores if s >= 75)
                distribution = {"fear": fear, "neutral": neutral, "greed": greed}

                # Compute top keywords (pure counting, 0 LLM tokens)
                top_keywords = []
                if all_titles:
                    from collections import Counter
                    stopwords = set(["the","a","an","and","or","but","in","on","at","to","for","of","with","is","are","was","were","be","been","being","have","has","had","do","does","did","will","would","could","should","may","might","shall","can","this","that","these","those","it","its","not","no","nor","so","too","very","just","about","above","after","again","all","also","am","any","as","at","because","before","between","both","by","came","come","each","few","from","get","got","had","has","have","he","her","here","him","himself","his","how","if","into","it","its","like","make","made","many","me","might","more","most","much","my","never","now","of","on","only","other","our","out","over","own","said","same","see","she","should","some","still","such","take","than","that","the","their","them","then","there","these","they","this","those","through","to","too","under","up","very","was","way","we","well","were","what","when","where","which","while","who","why","will","with","would","you","your","from","sent","reuters","cnbc","marketwatch","says","report","according","new","news","time","year","day","week","month","stock","market","investor","investment","price","prices","shares","company","companies","economy","economic","federal","reserve","rate","rates","bank","trade","trading","financial","finance","data","analysis","analyst","action","actions","policy","policies","growth","growing","fell","fall","rise","rising","down","up","high","low","record","level","levels","billion","million","percent","today","world","global","us","china","europe","business","corporate","earnings","revenue","profit","loss","results","guidance","outlook","forecast","expected"])

                    words = []
                    for title in all_titles:
                        # Simple word extraction
                        for w in re.split(r'[^a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+', title.lower()):
                            w = w.strip()
                            if len(w) > 2 and w not in stopwords:
                                words.append(w)

                    word_counts = Counter(words)
                    top_keywords = [
                        {"word": w, "count": c}
                        for w, c in word_counts.most_common(10)
                        if c >= 3
                    ]

                # Compute delta vs previous snapshot
                delta = 0
                delta_pct = "0%"
                if snap and prev_snap:
                    current_score = snap.get("score", 50)
                    prev_score = prev_snap.get("score", 50)
                    delta = round(current_score - prev_score)
                    if prev_score != 0:
                        pct = round(abs(delta) / prev_score * 100)
                        delta_pct = ("+" if delta >= 0 else "-") + str(pct) + "%"
                    else:
                        delta_pct = ("+" if delta >= 0 else "-") + str(abs(delta)) + "%"

                # Determine alert
                alert = None
                score_val = snap.get("score", 50) if snap else 50
                if score_val < 20:
                    alert = "EXTREME_FEAR"
                elif score_val > 80:
                    alert = "EXTREME_GREED"

                if snap:
                    s = dict(snap)
                    return self._send_json({
                        "score": s.get("score", 50),
                        "delta": delta,
                        "delta_pct": delta_pct,
                        "alert": alert,
                        "total_articles": s.get("total_articles", total_arts),
                        "sources": sources,
                        "top_keywords": top_keywords,
                        "distribution": distribution,
                        "timestamp": s.get("captured_at", datetime.now().isoformat()),
                        "status": "ready"
                    })
                return self._send_json({
                    "score": 50, "delta": 0, "delta_pct": "0%", "alert": None,
                    "total_articles": 0, "sources": {}, "top_keywords": [],
                    "distribution": {"fear":0,"neutral":0,"greed":0},
                    "timestamp": datetime.now().isoformat(),
                    "status": "pending"
                })
            except Exception as e:
                return self._send_json({
                    "error": str(e), "score": 50, "delta": 0, "delta_pct": "0%",
                    "alert": None, "total_articles": 0, "sources": {},
                    "top_keywords": [], "distribution": {"fear":0,"neutral":0,"greed":0},
                    "timestamp": datetime.now().isoformat(),
                    "status": "error"
                })
        if parsed.path.startswith("/api/specs/"):
            spec_id = parsed.path.replace("/api/specs/","")
            conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM specs WHERE id=?",(spec_id,)).fetchone(); conn.close()
            if row: return self._send_json(dict(row))
            return self._send_json({"error":"not_found"}, 404)


        if path == "/api/health":
            return self._send_json({"status":"ok","db":os.path.exists(DB_PATH)})

        # ── Serve static files ──
        if not os.path.splitext(path)[1] and not path.startswith("/api/"):
            html_candidate = path.lstrip("/") or "index.html"
            if html_candidate != "index.html": html_candidate += ".html"
            if os.path.isfile(os.path.join(FRONTEND_DIR, html_candidate)):
                self.path = "/" + html_candidate
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
        try: data = json.loads(body) if body else {}
        except: return self._send_json({"error":"invalid_json"}, 400)

        # ── Widget APIs ──
        if parsed.path == "/api/widgets":
            return self._send_json(widget_upsert(data))
        if parsed.path == "/api/widgets/rate":
            wid, stars = data.get("widget_id",""), int(data.get("stars",0))
            if not wid or stars<0 or stars>10:
                return self._send_json({"error":"invalid_data"}, 400)
            return self._send_json(widget_rate(wid, stars))
        if parsed.path == "/api/widgets/integrate":
            wid = data.get("widget_id","")
            if not wid: return self._send_json({"error":"missing_widget_id"}, 400)
            result = widget_toggle_integrate(wid)
            if result: return self._send_json(result)
            return self._send_json({"error":"not_found"}, 404)

        # ── Adjustments ──
        if parsed.path == "/api/widgets/adjust":
            wid = data.get("widget_id","")
            desc = data.get("description","")
            if not wid or not desc:
                return self._send_json({"error":"widget_id and description required"}, 400)
            return self._send_json(adjustment_create(wid, desc))

        # ── OLYMPIAD rating (existing) ──
        if parsed.path == "/api/ratings":
            model_id = data.get("model_id",""); stars = int(data.get("stars",0))
            if not model_id or stars<0 or stars>10:
                return self._send_json({"error":"invalid_data"}, 400)
            return self._send_json(self._save_rating(model_id, stars))

        return self._send_json({"error":"not_found"}, 404)

    def _get_ratings(self):
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute("SELECT model_id,user_stars FROM olympiad_ratings").fetchall()
        conn.close(); return {r[0]:r[1] for r in rows}

    def _save_rating(self, model_id, stars):
        conn = sqlite3.connect(DB_PATH)
        conn.execute("""INSERT INTO olympiad_ratings (model_id,user_stars,updated_at)
            VALUES (?,?,CURRENT_TIMESTAMP) ON CONFLICT(model_id) DO UPDATE SET
            user_stars=excluded.user_stars, updated_at=CURRENT_TIMESTAMP""", (model_id, stars))
        conn.commit(); conn.close()
        return {"status":"ok","model_id":model_id,"stars":stars}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
        self.end_headers()

    def _send_json(self, data, status=200):
        body = json.dumps(data, default=str, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type","application/json")
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Content-Length",len(body))
        self.end_headers(); self.wfile.write(body)

    def log_message(self, format, *args):
        if args[1] != '200':
            sys.stderr.write(f"[API] {args[0]} → {args[1]}\n")

# ── Main ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    seed_widgets()
    print(f"🏆 Olympiad API Server + Widget Factory")
    print(f"   Frontend: {FRONTEND_DIR}")
    print(f"   Widgets:  {WIDGETS_DIR}")
    print(f"   Database: {DB_PATH}")
    print(f"   Port:     {PORT}")
    print(f"   Evaluador: http://localhost:{PORT}/widget-evaluator")
    print(f"   Dashboard: http://localhost:{PORT}/inversor")
    server = HTTPServer(("0.0.0.0", PORT), OlympiadHandler)
    try: server.serve_forever()
    except KeyboardInterrupt: print("\n👋 Shutting down..."); server.shutdown()
