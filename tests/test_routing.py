from app.agent_graph import fallback_decision, route_after_classify, route_after_verify


def test_fallback_routes_high_risk_question():
    decision = fallback_decision("Is AI recruitment high-risk under the AI Act?")
    assert decision.in_scope is True
    assert decision.intent == "risk_assessment"


def test_out_of_scope_routes_to_finalize():
    state = {"decision": {"in_scope": False}}
    assert route_after_classify(state) == "finalize"


def test_verification_retry_route():
    assert route_after_verify({"verification": {"needs_retry": True}}) == "research"
    assert route_after_verify({"verification": {"needs_retry": False}}) == "finalize"
