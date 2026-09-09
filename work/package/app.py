import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

load_dotenv()
BASE = Path(__file__).parent
DATA = BASE / "data"
DATA.mkdir(exist_ok=True)
DB_PATH = BASE / os.getenv("SQLITE_PATH", "data/businesspulse.db")

app = FastAPI(title="BusinessPulse AI", version="0.2.0")

EXPOSURES = [
    ("Taiwan Chip Partner", "supplier", "supply_chain", "Taiwan", 90, 14, 30, "Demo semiconductor dependency for Model 3 and Model Y"),
    ("China Battery Cell Partner", "supplier", "supply_chain", "China", 95, 21, 40, "Demo battery-cell dependency for Model Y"),
    ("Model Y", "product", "market", "United States", 85, 0, 40, "High-volume Tesla product in demo model"),
    ("BYD", "competitor", "competitor", "China", 70, 0, 30, "Competitor monitored for prices, launches and market share"),
    ("US EV Incentives", "regulation", "regulation", "United States", 80, 0, 35, "Demo policy exposure for customer demand and pricing"),
]

DEMO_ITEMS = [
    {
        "title": "Severe weather alert: Typhoon warning issued for northern Taiwan semiconductor corridor",
        "source_name": "Meteorological & Maritime Intelligence",
        "source_url": "https://example.com/taiwan-typhoon-warning",
        "content": "A category 4 typhoon warning has been issued across northern Taiwan. High winds and localized power grid fluctuations are threatening semiconductor fabrication facilities and industrial parks near Hsinchu and Taichung.",
    },
    {
        "title": "Taiwanese ports report container vessel delays and logistics bottlenecks",
        "source_name": "Pacific Freight Journal",
        "source_url": "https://example.com/taiwan-port-congestion",
        "content": "Port operations in Kaohsiung and Keelung have slowed due to severe weather conditions and backlogged container traffic. Outbound automotive component and microchip shipments are facing estimated delays of 5 to 10 days.",
    },
    {
        "title": "Automotive microcontroller delivery lead times surge following facility downtime",
        "source_name": "Global Semiconductor Tracker",
        "source_url": "https://example.com/automotive-mcu-lead-times",
        "content": "Tier-1 semiconductor fabricators in Taiwan have signaled scheduled downtime and wafer packaging delays. Delivery times for automotive-grade power management ICs and microcontrollers have spiked by 18% week-over-week.",
    },
    {
        "title": "U.S. federal proposal introduces stricter battery component origin rules for EV tax credits",
        "source_name": "Federal Policy Monitor",
        "source_url": "https://example.com/us-ev-tax-credit-proposal",
        "content": "A new regulatory revision in the United States proposes tighter critical mineral and battery component domestic sourcing thresholds, potentially adjusting buyer tax credit eligibility for electric vehicles produced in Q4.",
    },
    {
        "title": "BYD initiates aggressive price reductions across premium electric sedan and SUV models in China",
        "source_name": "Asian EV Market Review",
        "source_url": "https://example.com/byd-ev-pricing-initiative",
        "content": "BYD announced a targeted 7% to 11% price cut on mid-to-high trim electric models in China, intensifying pricing pressure against foreign electric vehicle manufacturers and challenging current margin targets.",
    },
]

class Article(BaseModel):
    title: str = Field(min_length=5, max_length=1000)
    content: str = Field(min_length=20, max_length=15000)
    source_name: str = "Live News Feed"
    source_url: str = ""

class TaskStatusUpdate(BaseModel):
    status: str

@contextmanager
def db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()

def initialize_database():
    with db() as con:
        try:
            con.execute("SELECT target_entity FROM early_warnings LIMIT 1")
        except Exception:
            con.execute("DROP TABLE IF EXISTS early_warnings")
            con.execute("DROP TABLE IF EXISTS mitigation_tasks")
            con.execute("DROP TABLE IF EXISTS contingency_options")

        con.executescript("""
        CREATE TABLE IF NOT EXISTS tesla_exposure (
          exposure_id INTEGER PRIMARY KEY AUTOINCREMENT, entity_name TEXT, entity_type TEXT,
          category TEXT, region TEXT, dependency_score REAL, inventory_days REAL,
          revenue_weight REAL, notes TEXT
        );
        CREATE TABLE IF NOT EXISTS news_events (
          event_id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, source_url TEXT, source_name TEXT,
          published_at TEXT, event_type TEXT, entities TEXT, summary TEXT, severity REAL,
          urgency REAL, likelihood REAL, confidence REAL, status TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS event_exposure_map (
          map_id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER, exposure_id INTEGER,
          match_confidence REAL, impact_path TEXT
        );
        CREATE TABLE IF NOT EXISTS risk_scores (
          risk_id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER, priority_score REAL,
          priority_label TEXT, revenue_at_risk_usd REAL, recommended_action TEXT, calculated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS early_warnings (
          warning_id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, region TEXT, target_entity TEXT,
          probability_7d REAL, signal_count INTEGER, predicted_timeframe TEXT, leading_indicators TEXT,
          readiness_action TEXT, status TEXT DEFAULT 'Active', created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS mitigation_tasks (
          task_id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER, warning_id INTEGER,
          department TEXT, assigned_role TEXT, priority TEXT, due_date TEXT,
          action_summary TEXT, escalation_path TEXT, status TEXT DEFAULT 'Assigned', created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS contingency_options (
          option_id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER, warning_id INTEGER,
          option_title TEXT, department TEXT, speed TEXT, cost TEXT, business_benefit TEXT,
          feasibility_rank INTEGER, approval_status TEXT DEFAULT 'Proposed', notes TEXT, created_at TEXT
        );
        """)
        count = con.execute("SELECT COUNT(*) FROM tesla_exposure").fetchone()[0]
        if count == 0:
            con.executemany("""INSERT INTO tesla_exposure
                (entity_name, entity_type, category, region, dependency_score, inventory_days, revenue_weight, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", EXPOSURES)

def fallback_analysis(article: Article) -> dict[str, Any]:
    text = f"{article.title} {article.content}".lower()
    if any(w in text for w in ["chip", "semiconductor", "taiwan", "mcu", "wafer", "foundry"]):
        return {
            "event_type": "supply_chain",
            "entities": ["Taiwan Chip Partner", "Taiwan", "semiconductors", "Model 3", "Model Y"],
            "summary": "Leading indicators suggest potential semiconductor fabrication and shipping disruptions affecting Tesla production schedules.",
            "severity": 82, "urgency": 78, "likelihood": 75, "confidence": 80,
            "recommended_action": "Audit current automotive chip inventory levels (14-day coverage), engage secondary suppliers, and allocate chips to high-margin Model Y lines."
        }
    if any(w in text for w in ["incentive", "tariff", "regulation", "policy", "tax credit", "origin"]):
        return {
            "event_type": "regulation",
            "entities": ["Tesla", "US EV Incentives", "United States", "Battery Components"],
            "summary": "Proposed policy shifts in EV tax credit requirements could impact customer incentive qualification and pricing flexibility.",
            "severity": 74, "urgency": 65, "likelihood": 70, "confidence": 78,
            "recommended_action": "Audit component origin compliance across vehicle trims, evaluate demand elasticity, and model contingency customer financing options."
        }
    if any(w in text for w in ["byd", "competitor", "price cut", "pricing", "discount"]):
        return {
            "event_type": "competitor",
            "entities": ["Tesla", "BYD", "China", "Model 3"],
            "summary": "Aggressive competitor pricing moves in China increase margin pressure and necessitate market-specific promotional responses.",
            "severity": 68, "urgency": 60, "likelihood": 80, "confidence": 76,
            "recommended_action": "Evaluate regional financing promotions and feature bundling to protect market share without diluting base vehicle MSRP."
        }
    return {
        "event_type": "market",
        "entities": ["Tesla", "Global Supply Chain"],
        "summary": "External operational signal detected that may affect regional business velocity and component delivery schedules.",
        "severity": 60, "urgency": 50, "likelihood": 65, "confidence": 70,
        "recommended_action": "Monitor signal evolution, track tier-1 delivery milestones, and assess regional supply chain buffers."
    }

def gemini_analysis(article: Article) -> dict[str, Any]:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return fallback_analysis(article)
    prompt = f'''You are BusinessPulse AI, an executive risk and resilience analyst monitoring Tesla. Analyze the news article below. Return JSON only with this exact shape:
{{"event_type":"supply_chain|market|competitor|regulation","entities":["..."],"summary":"max 35 words","severity":0-100,"urgency":0-100,"likelihood":0-100,"confidence":0-100,"recommended_action":"one practical action"}}
Focus only on material Tesla exposure. Do not invent facts.\n\nTITLE: {article.title}\nSOURCE: {article.source_name}\nARTICLE: {article.content}'''
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}},
            timeout=15,
        )
        if not response.ok:
            print(f"[Gemini Notice] API returned status {response.status_code}. Using local deterministic analysis.")
            return fallback_analysis(article)
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(text)
        required = {"event_type", "entities", "summary", "severity", "urgency", "likelihood", "confidence", "recommended_action"}
        if not required.issubset(result):
            return fallback_analysis(article)
        return result
    except Exception as error:
        print(f"[Gemini Notice] Analysis exception ({error}). Using local deterministic analysis.")
        return fallback_analysis(article)

def match_exposure(entities: list[str], event_type: str):
    with db() as con:
        candidates = con.execute("SELECT * FROM tesla_exposure WHERE category = ? OR entity_type = ?", (event_type, event_type)).fetchall()
        if not candidates:
            candidates = con.execute("SELECT * FROM tesla_exposure").fetchall()
    entity_text = " ".join(entities).lower()
    scored = []
    for row in candidates:
        overlap = 100 if row["entity_name"].lower() in entity_text or row["region"].lower() in entity_text else 65
        scored.append((dict(row), overlap))
    return max(scored, key=lambda x: x[0]["dependency_score"] * x[1])[0], max(scored, key=lambda x: x[0]["dependency_score"] * x[1])[1]

def priority_label(score: float) -> str:
    if score >= 80: return "Critical"
    if score >= 60: return "High"
    if score >= 35: return "Medium"
    return "Low"

def evaluate_early_warnings(con, new_event_id: int, event_type: str, entities: list[str], severity: float, exposure: dict) -> Optional[int]:
    """Predictive Early-Warning Engine: clusters leading signals and calculates 7-day disruption probability."""
    region = exposure.get("region", "Global")
    entity_name = exposure.get("entity_name", "General Operations")
    dep_score = exposure.get("dependency_score", 50.0)

    # Query recent events sharing the same category or region
    recent = con.execute("""
        SELECT e.event_id, e.title, e.severity, e.created_at FROM news_events e
        WHERE e.event_type = ? OR e.entities LIKE ?
        ORDER BY e.event_id DESC LIMIT 10
    """, (event_type, f"%{region}%")).fetchall()

    signal_count = len(recent)
    if signal_count >= 2 and dep_score >= 70:
        # Calculate Predictive Threat Probability (0-100%)
        prob = min(96.0, round(40.0 + (signal_count * 11.5) + (dep_score * 0.22) + (severity * 0.12), 1))
        
        indicators = [r["title"] for r in recent[:3]]
        indicators_text = " • " + " • ".join(indicators)

        readiness_action = f"Early preparedness: Confirm {exposure.get('inventory_days', 14):.0f}-day inventory buffer with {entity_name}, reserve secondary supplier allocation, and prioritize high-margin vehicle lines."

        existing = con.execute("SELECT warning_id FROM early_warnings WHERE target_entity = ? AND status = 'Active'", (entity_name,)).fetchone()
        now = datetime.now(timezone.utc).isoformat()
        
        if existing:
            warning_id = existing[0]
            con.execute("""UPDATE early_warnings
                SET probability_7d = ?, signal_count = ?, leading_indicators = ?, readiness_action = ?, created_at = ?
                WHERE warning_id = ?""",
                (prob, signal_count, indicators_text, readiness_action, now, warning_id))
            return warning_id
        else:
            warning_id = con.execute("""INSERT INTO early_warnings
                (category, region, target_entity, probability_7d, signal_count, predicted_timeframe, leading_indicators, readiness_action, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (event_type, region, entity_name, prob, signal_count, "Within 7 days", indicators_text, readiness_action, "Active", now)).lastrowid
            return warning_id
    return None

def route_department_actions(con, event_id: int, warning_id: Optional[int], event_type: str, title: str, priority_lbl: str, exposure: dict):
    """Department Responsibility & Action Routing Engine."""
    entity_name = exposure.get("entity_name", "Supplier")
    now = datetime.now(timezone.utc).isoformat()
    tasks_to_add = []

    if event_type == "supply_chain":
        tasks_to_add.append({
            "department": "Procurement & Global Supply Chain",
            "assigned_role": "VP of Global Procurement",
            "priority": priority_lbl,
            "due_date": "Immediate (Within 12h)" if priority_lbl in ["Critical", "High"] else "Within 24h",
            "action_summary": f"Contact {entity_name} to audit 14-day component buffer coverage, verify shipment schedules, and lock volume allocations.",
            "escalation_path": "Escalate to Chief Operations Officer (COO) if shipment confirmation is unverified within 24h."
        })
        if any(w in title.lower() for w in ["port", "shipping", "weather", "vessel", "freight", "logistics"]):
            tasks_to_add.append({
                "department": "Logistics & Transportation Operations",
                "assigned_role": "Director of Global Freight Logistics",
                "priority": "High",
                "due_date": "Within 24h",
                "action_summary": "Evaluate secondary shipping lanes and prepare expedited air-freight routing for pending transit lots.",
                "escalation_path": "Escalate to VP of Supply Chain if port transit exceeds 5-day delay threshold."
            })
    elif event_type == "regulation":
        tasks_to_add.append({
            "department": "Legal, Regulatory & Government Affairs",
            "assigned_role": "Director of Regulatory Compliance & Policy Strategy",
            "priority": priority_lbl,
            "due_date": "Within 48h",
            "action_summary": "Model compliance guidelines and tax credit qualification criteria across North American vehicle trims.",
            "escalation_path": "Escalate to General Counsel and Chief Financial Officer (CFO)."
        })
        tasks_to_add.append({
            "department": "Sales, Pricing & Commercial Operations",
            "assigned_role": "Head of Consumer Financing & Pricing",
            "priority": "Medium",
            "due_date": "Within 3 business days",
            "action_summary": "Model demand sensitivity and prepare contingency promotional lease/financing packages.",
            "escalation_path": "Escalate to Chief Commercial Officer (CCO)."
        })
    elif event_type == "competitor":
        tasks_to_add.append({
            "department": "Commercial Sales, Pricing & Strategy",
            "assigned_role": "Head of Regional Pricing & Product Strategy",
            "priority": priority_lbl,
            "due_date": "Within 24h",
            "action_summary": "Assess margin elasticity and evaluate regional discount / feature bundling to protect vehicle order conversion.",
            "escalation_path": "Escalate to Chief Commercial Officer (CCO)."
        })
    else:
        tasks_to_add.append({
            "department": "Finance & Corporate FP&A",
            "assigned_role": "VP of Financial Planning & Analysis",
            "priority": priority_lbl,
            "due_date": "Within 3 business days",
            "action_summary": "Update quarterly revenue risk forecasts and margin sensitivity models based on external event impact.",
            "escalation_path": "Escalate to Chief Financial Officer (CFO)."
        })

    for task in tasks_to_add:
        con.execute("""INSERT INTO mitigation_tasks
            (event_id, warning_id, department, assigned_role, priority, due_date, action_summary, escalation_path, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (event_id, warning_id, task["department"], task["assigned_role"], task["priority"],
             task["due_date"], task["action_summary"], task["escalation_path"], "Assigned", now))

def generate_contingencies(con, event_id: int, warning_id: Optional[int], event_type: str, exposure: dict):
    """Contingency Recommendation Engine: generates ranked immediate and alternate solutions."""
    now = datetime.now(timezone.utc).isoformat()
    options = []

    if event_type == "supply_chain":
        options = [
            {
                "title": f"Audit {exposure.get('entity_name', 'supplier')} buffer stock and lock immediate shipment allocations",
                "department": "Procurement",
                "speed": "Immediate",
                "cost": "Low",
                "benefit": "Secures existing inventory and prevents immediate assembly line stoppages.",
                "rank": 1
            },
            {
                "title": "Prioritize high-margin Model Y vehicle production over standard trims",
                "department": "Operations & Finance",
                "speed": "Immediate",
                "cost": "Low",
                "benefit": "Protects higher-margin vehicle revenue and maximizes cash flow during component constraints.",
                "rank": 2
            },
            {
                "title": "Activate pre-qualified secondary European/US semiconductor supplier",
                "department": "Procurement & Engineering",
                "speed": "Medium",
                "cost": "Medium",
                "benefit": "Diversifies supply source and secures bridge volume within 10-14 days.",
                "rank": 3
            },
            {
                "title": "Authorize express air-freight routing for pending transit batches",
                "department": "Logistics",
                "speed": "Fast",
                "cost": "Medium",
                "benefit": "Bypasses congested seaport delays by 5-7 calendar days.",
                "rank": 4
            },
        ]
    elif event_type == "regulation":
        options = [
            {
                "title": "Audit vehicle bill-of-materials for domestic content qualification",
                "department": "Compliance & Supply Chain",
                "speed": "Fast",
                "cost": "Low",
                "benefit": "Identifies exact vehicle trims qualifying under revised rules.",
                "rank": 1
            },
            {
                "title": "Adjust promotional lease and consumer financing incentives",
                "department": "Sales & Marketing",
                "speed": "Fast",
                "cost": "Medium",
                "benefit": "Maintains customer order conversion rates and order backlog stability.",
                "rank": 2
            },
        ]
    elif event_type == "competitor":
        options = [
            {
                "title": "Introduce targeted promotional financing or enhanced feature bundles",
                "department": "Sales & Product",
                "speed": "Fast",
                "cost": "Low",
                "benefit": "Neutralizes competitor price advantages without permanently cutting base vehicle MSRP.",
                "rank": 1
            },
            {
                "title": "Accelerate regional marketing on Total Cost of Ownership (TCO) & safety ratings",
                "department": "Marketing",
                "speed": "Medium",
                "cost": "Medium",
                "benefit": "Reinforces brand equity and premium residual value perception.",
                "rank": 2
            },
        ]
    else:
        options = [
            {
                "title": "Monitor weekly delivery milestones and re-evaluate buffer coverage",
                "department": "Operations",
                "speed": "Immediate",
                "cost": "Low",
                "benefit": "Provides early visibility before operational bottleneck materializes.",
                "rank": 1
            }
        ]

    for opt in options:
        con.execute("""INSERT INTO contingency_options
            (event_id, warning_id, option_title, department, speed, cost, business_benefit, feasibility_rank, approval_status, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (event_id, warning_id, opt["title"], opt["department"], opt["speed"], opt["cost"],
             opt["benefit"], opt["rank"], "Proposed", "Requires management approval before execution", now))

def analyze_and_store(article: Article) -> int:
    analysis = gemini_analysis(article)
    exposure, match_confidence = match_exposure(analysis["entities"], analysis["event_type"])
    
    # 5-factor risk score
    score = round(0.25 * analysis["severity"] + 0.35 * exposure["dependency_score"] + 0.20 * analysis["urgency"] + 0.10 * analysis["likelihood"] + 0.10 * analysis["confidence"], 1)
    revenue_risk = round(exposure["revenue_weight"] / 100 * 250_000_000 * score / 100, 0)
    impact_path = f"{article.title} -> {exposure['entity_name']} ({exposure['region']}) -> {exposure['notes']}"
    now = datetime.now(timezone.utc).isoformat()
    
    with db() as con:
        event_id = con.execute("""INSERT INTO news_events
          (title, source_url, source_name, published_at, event_type, entities, summary, severity, urgency, likelihood, confidence, status, created_at)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
          (article.title, article.source_url, article.source_name, now, analysis["event_type"],
           json.dumps(analysis["entities"]), analysis["summary"], analysis["severity"],
           analysis["urgency"], analysis["likelihood"], analysis["confidence"], "Open", now)).lastrowid
        
        con.execute("""INSERT INTO event_exposure_map (event_id, exposure_id, match_confidence, impact_path)
            VALUES (?, ?, ?, ?)""", (event_id, exposure["exposure_id"], match_confidence, impact_path))
        
        con.execute("""INSERT INTO risk_scores (event_id, priority_score, priority_label, revenue_at_risk_usd, recommended_action, calculated_at)
          VALUES (?, ?, ?, ?, ?, ?)""", (event_id, score, priority_label(score), revenue_risk, analysis["recommended_action"], now))
        
        # 1. Evaluate Predictive 7-Day Early Warnings
        warning_id = evaluate_early_warnings(con, event_id, analysis["event_type"], analysis["entities"], analysis["severity"], exposure)
        
        # 2. Route Department Responsibility Tasks
        route_department_actions(con, event_id, warning_id, analysis["event_type"], article.title, priority_label(score), exposure)
        
        # 3. Generate Ranked Contingency Options
        generate_contingencies(con, event_id, warning_id, analysis["event_type"], exposure)

    return event_id

@app.on_event("startup")
def startup():
    initialize_database()

@app.get("/")
def home():
    return FileResponse(BASE / "static" / "index.html")

@app.get("/health")
def health():
    return {"status": "ok", "company": "Tesla", "database": "sqlite demo; Exasol schema included", "version": "0.2.0"}

@app.get("/api/dashboard")
def dashboard():
    with db() as con:
        event_rows = con.execute("""SELECT e.event_id, e.title, e.source_name, e.source_url, e.event_type, e.summary, e.published_at,
            r.priority_score, r.priority_label, r.revenue_at_risk_usd, r.recommended_action
            FROM news_events e JOIN risk_scores r ON e.event_id=r.event_id
            ORDER BY r.priority_score DESC, e.event_id DESC""").fetchall()
        
        warning_rows = con.execute("""SELECT * FROM early_warnings WHERE status = 'Active' ORDER BY probability_7d DESC, warning_id DESC""").fetchall()
        
        task_rows = con.execute("""SELECT * FROM mitigation_tasks ORDER BY task_id DESC LIMIT 20""").fetchall()
        
        contingency_rows = con.execute("""SELECT * FROM contingency_options ORDER BY feasibility_rank ASC, option_id DESC LIMIT 20""").fetchall()

    events = [dict(r) for r in event_rows]
    warnings = [dict(r) for r in warning_rows]
    tasks = [dict(r) for r in task_rows]
    contingencies = [dict(r) for r in contingency_rows]

    metrics = {
        "critical": sum(e["priority_label"] == "Critical" for e in events),
        "high": sum(e["priority_label"] == "High" for e in events),
        "open_events": len(events),
        "early_warnings_count": len(warnings),
        "pending_tasks_count": sum(t["status"] != "Resolved" for t in tasks),
        "estimated_revenue_at_risk_usd": sum(e["revenue_at_risk_usd"] for e in events)
    }

    return {
        "company": "Tesla",
        "events": events,
        "early_warnings": warnings,
        "tasks": tasks,
        "contingencies": contingencies,
        "metrics": metrics
    }

@app.get("/api/briefing")
def briefing():
    data = dashboard()
    events = data["events"][:4]
    warnings = data["early_warnings"][:2]
    tasks = [t for t in data["tasks"] if t["status"] != "Resolved"][:3]

    warning_text = ""
    if warnings:
        w = warnings[0]
        warning_text = f"🚨 Proactive Early Warning: {w['probability_7d']}% probability of {w['category']} disruption in {w['region']} ({w['predicted_timeframe']}) affecting {w['target_entity']}. {w['readiness_action']} "
    
    event_text = "No critical risk events detected." if not events else " ".join(
        f"[{e['priority_label']}] {e['title']}: {e['summary']} Next Step: {e['recommended_action']}" for e in events
    )

    task_text = f" Active mitigation: {len(tasks)} cross-department actions assigned (Procurement, Logistics, Legal, Pricing)." if tasks else ""

    summary = (warning_text + event_text + task_text).strip()

    return {
        "company": "Tesla",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "early_warnings": warnings,
        "events": events,
        "top_tasks": tasks
    }

@app.post("/api/events/analyze")
def analyze(article: Article):
    event_id = analyze_and_store(article)
    return {"event_id": event_id, "message": "Article analyzed, early warnings evaluated, and department tasks routed."}

@app.post("/api/tasks/{task_id}/status")
def update_task_status(task_id: int, payload: TaskStatusUpdate):
    with db() as con:
        con.execute("UPDATE mitigation_tasks SET status = ? WHERE task_id = ?", (payload.status, task_id))
    return {"task_id": task_id, "status": payload.status}

@app.post("/api/contingencies/{option_id}/approve")
def approve_contingency(option_id: int):
    with db() as con:
        con.execute("UPDATE contingency_options SET approval_status = 'Approved' WHERE option_id = ?", (option_id,))
    return {"option_id": option_id, "approval_status": "Approved"}

@app.post("/api/demo/load")
def load_demo():
    with db() as con:
        if con.execute("SELECT COUNT(*) FROM news_events").fetchone()[0] > 0:
            return {"message": "Demo events are already loaded."}
    ids = [analyze_and_store(Article(**item)) for item in DEMO_ITEMS]
    return {"message": "Tesla multi-signal demo sequence loaded.", "event_ids": ids}

@app.post("/api/demo/reset")
def reset_demo():
    with db() as con:
        con.execute("DELETE FROM contingency_options")
        con.execute("DELETE FROM mitigation_tasks")
        con.execute("DELETE FROM early_warnings")
        con.execute("DELETE FROM risk_scores")
        con.execute("DELETE FROM event_exposure_map")
        con.execute("DELETE FROM news_events")
    ids = [analyze_and_store(Article(**item)) for item in DEMO_ITEMS]
    return {"message": "Database reset and fresh multi-signal demo sequence loaded.", "event_ids": ids}
