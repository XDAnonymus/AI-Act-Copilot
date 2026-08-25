from app.tools import application_date_status, risk_triage


def test_employment_is_high_risk_candidate():
    result = risk_triage("AI system ranks CVs and evaluates job candidates")
    assert result["candidate_classification"] == "high_risk_candidate"
    assert result["matched_area"] == "employment"


def test_social_scoring_is_prohibited_candidate():
    result = risk_triage("A public authority uses AI for social scoring")
    assert result["candidate_classification"] == "prohibited_practice_candidate"


def test_annex_iii_application_date_after_2026_amendment():
    result = application_date_status("high_risk_annex_iii", "2026-08-24")
    assert result["is_applicable"] is False
    assert result["applies_from"] == "2027-12-02"
