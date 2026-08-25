from datetime import date
from pathlib import Path

import yaml
from langchain_core.tools import tool

from app.config import settings


HIGH_RISK_AREAS = {
    "biometrics": ["biometric", "facial recognition", "emotion recognition"],
    "critical infrastructure": ["critical infrastructure", "electricity grid", "water supply", "road traffic"],
    "education": ["student admission", "exam monitoring", "learning outcome", "education admission"],
    "employment": ["recruit", "candidate", "cv", "resume", "employee performance", "promotion", "termination"],
    "essential services": ["credit score", "creditworthiness", "life insurance", "health insurance", "emergency triage"],
    "law enforcement": ["law enforcement", "police", "criminal evidence", "re-offending"],
    "migration": ["migration", "asylum", "border control", "visa"],
    "justice and democracy": ["judicial", "court decision", "election", "referendum"],
}

PROHIBITED_SIGNALS = {
    "social scoring": ["social scoring"],
    "harmful manipulation": ["subliminal manipulation", "manipulate behaviour", "exploit vulnerability"],
    "certain biometric practices": ["biometric categorisation by race", "predict criminality from profiling"],
    "non-consensual sexual content": ["nudification", "non-consensual sexually explicit"],
}

TRANSPARENCY_SIGNALS = ["chatbot", "deepfake", "synthetic content", "ai-generated content"]


def risk_triage(description: str) -> dict:
    text = description.lower()

    for label, signals in PROHIBITED_SIGNALS.items():
        if any(signal in text for signal in signals):
            return {
                "candidate_classification": "prohibited_practice_candidate",
                "matched_area": label,
                "legal_status": "triage_only",
            }

    matched_high_risk = [
        area
        for area, signals in HIGH_RISK_AREAS.items()
        if any(signal in text for signal in signals)
    ]
    if matched_high_risk:
        return {
            "candidate_classification": "high_risk_candidate",
            "matched_area": matched_high_risk[0],
            "legal_status": "triage_only",
        }

    if any(signal in text for signal in TRANSPARENCY_SIGNALS):
        return {
            "candidate_classification": "transparency_obligations_candidate",
            "matched_area": "Article 50 style transparency",
            "legal_status": "triage_only",
        }

    return {
        "candidate_classification": "no_deterministic_match",
        "matched_area": None,
        "legal_status": "triage_only",
    }


@tool
def risk_triage_tool(description: str) -> dict:
    """Return a deterministic preliminary EU AI Act risk signal for a described use case."""
    return risk_triage(description)


def load_date_rules() -> dict:
    with open(Path(settings.date_rules_file), "r", encoding="utf-8") as file:
        return yaml.safe_load(file)["rules"]


def application_date_status(rule_id: str, as_of: str) -> dict:
    rules = load_date_rules()
    if rule_id not in rules:
        return {"rule_id": rule_id, "error": "unknown_rule_id"}

    rule = rules[rule_id]
    start = date.fromisoformat(rule["applies_from"])
    current = date.fromisoformat(as_of)
    return {
        "rule_id": rule_id,
        "label": rule["label"],
        "applies_from": rule["applies_from"],
        "as_of": as_of,
        "is_applicable": current >= start,
        "source_reference": rule["source_reference"],
        "note": rule.get("note", ""),
    }


@tool
def application_date_tool(rule_id: str, as_of: str) -> dict:
    """Check whether a curated AI Act application date has been reached."""
    return application_date_status(rule_id, as_of)


def select_date_rule_ids(question: str, risk_result: dict | None = None) -> list[str]:
    text = question.lower()
    rules: list[str] = []

    if "general-purpose" in text or "gpai" in text:
        rules.append("gpai_chapter_v")
    if "high-risk" in text or (risk_result or {}).get("candidate_classification") == "high_risk_candidate":
        if any(term in text for term in ["medical device", "machinery", "annex i", "product safety"]):
            rules.append("high_risk_annex_i")
        else:
            rules.append("high_risk_annex_iii")
    if "prohibited" in text or (risk_result or {}).get("candidate_classification") == "prohibited_practice_candidate":
        rules.extend(["chapters_i_ii", "new_prohibitions_2026_amendment"])
    if "transparency" in text or "chatbot" in text or "deepfake" in text:
        rules.append("general_application")
    if not rules:
        rules.append("general_application")

    return list(dict.fromkeys(rules))
