CREATE SCHEMA IF NOT EXISTS BUSINESSPULSE;

CREATE TABLE IF NOT EXISTS BUSINESSPULSE.TESLA_EXPOSURE (
    exposure_id DECIMAL(18,0) IDENTITY,
    entity_name VARCHAR(200),
    entity_type VARCHAR(40),
    category VARCHAR(40),
    region VARCHAR(100),
    dependency_score DECIMAL(5,2),
    inventory_days DECIMAL(8,2),
    revenue_weight DECIMAL(5,2),
    notes VARCHAR(2000)
);

CREATE TABLE IF NOT EXISTS BUSINESSPULSE.NEWS_EVENTS (
    event_id DECIMAL(18,0) IDENTITY,
    title VARCHAR(1000),
    source_url VARCHAR(2000),
    source_name VARCHAR(200),
    published_at TIMESTAMP,
    event_type VARCHAR(40),
    entities VARCHAR(4000),
    summary VARCHAR(4000),
    severity DECIMAL(5,2),
    urgency DECIMAL(5,2),
    likelihood DECIMAL(5,2),
    confidence DECIMAL(5,2),
    status VARCHAR(30),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS BUSINESSPULSE.EVENT_EXPOSURE_MAP (
    map_id DECIMAL(18,0) IDENTITY,
    event_id DECIMAL(18,0),
    exposure_id DECIMAL(18,0),
    match_confidence DECIMAL(5,2),
    impact_path VARCHAR(4000)
);

CREATE TABLE IF NOT EXISTS BUSINESSPULSE.RISK_SCORES (
    risk_id DECIMAL(18,0) IDENTITY,
    event_id DECIMAL(18,0),
    priority_score DECIMAL(5,2),
    priority_label VARCHAR(20),
    revenue_at_risk_usd DECIMAL(18,2),
    recommended_action VARCHAR(4000),
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS BUSINESSPULSE.EARLY_WARNINGS (
    warning_id DECIMAL(18,0) IDENTITY,
    category VARCHAR(40),
    region VARCHAR(100),
    target_entity VARCHAR(200),
    probability_7d DECIMAL(5,2),
    signal_count DECIMAL(10,0),
    predicted_timeframe VARCHAR(50),
    leading_indicators VARCHAR(4000),
    readiness_action VARCHAR(4000),
    status VARCHAR(30) DEFAULT 'Active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS BUSINESSPULSE.MITIGATION_TASKS (
    task_id DECIMAL(18,0) IDENTITY,
    event_id DECIMAL(18,0),
    warning_id DECIMAL(18,0),
    department VARCHAR(100),
    assigned_role VARCHAR(120),
    priority VARCHAR(20),
    due_date VARCHAR(50),
    action_summary VARCHAR(4000),
    escalation_path VARCHAR(2000),
    status VARCHAR(30) DEFAULT 'Assigned',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS BUSINESSPULSE.CONTINGENCY_OPTIONS (
    option_id DECIMAL(18,0) IDENTITY,
    event_id DECIMAL(18,0),
    warning_id DECIMAL(18,0),
    option_title VARCHAR(1000),
    department VARCHAR(100),
    speed VARCHAR(30),
    cost VARCHAR(30),
    business_benefit VARCHAR(2000),
    feasibility_rank DECIMAL(5,0),
    approval_status VARCHAR(30) DEFAULT 'Proposed',
    notes VARCHAR(2000),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
