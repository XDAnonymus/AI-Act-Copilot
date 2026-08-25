import json
import re
from datetime import date
from time import perf_counter

from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

from app.config import settings
from app.rag_graph import build_rag_graph
from app.retrieval import Retriever
from app.schemas import AgentDecision, AgentState
from app.tools import application_date_tool, risk_triage_tool, select_date_rule_ids


SCOPE_TERMS = [
    "ai act",
    "artificial intelligence act",
    "high-risk",
    "high risk",
    "provider",
    "deployer",
    "prohibited",
    "transparency",
    "annex",
    "article",
    "recruit",
    "credit score",
    "biometric",
    "gpai",
    "general-purpose ai",
    "mesterséges intelligencia",
    "mi-rendszer",
    "mi rendszer",
]


def trace_entry(node: str, started: float, details: dict | None = None) -> dict:
    return {
        "node": node,
        "duration_ms": round((perf_counter() - started) * 1000, 2),
        "details": details or {},
    }


def fallback_decision(question: str) -> AgentDecision:
    text = question.lower()
    in_scope = any(term in text for term in SCOPE_TERMS)
    if not in_scope:
        return AgentDecision(
            in_scope=False,
            intent="out_of_scope",
            research_tasks=[],
            reason="Fallback router found no EU AI Act related signal.",
        )

    if any(term in text for term in ["when", "date", "effective", "mikor", "hatályba", "from what date"]):
        intent = "timeline_question"
    elif any(term in text for term in ["prohibited", "tiltott"]):
        intent = "prohibited_practice_check"
    elif any(term in text for term in ["high-risk", "high risk", "kockázat", "risk"]):
        intent = "risk_assessment"
    elif any(term in text for term in ["definition", "scope", "provider", "deployer", "outside the eu", "third country", "personal non-professional", "fogalma", "hatály"]):
        intent = "scope_check"
    elif any(term in text for term in ["obligation", "requirement", "transparency", "kötelezetts", "előírás", "átláthatóság"]):
        intent = "obligation_check"
    else:
        intent = "general_research"

    return AgentDecision(
        in_scope=True,
        intent=intent,
        research_tasks=[question],
        needs_risk_tool=intent in {"risk_assessment", "prohibited_practice_check"},
        needs_date_tool=intent == "timeline_question" or "high-risk" in text,
        reason="Deterministic fallback routing.",
    )


def route_after_classify(state: AgentState) -> str:
    return "plan" if state.get("decision", {}).get("in_scope") else "finalize"


def route_after_verify(state: AgentState) -> str:
    return "research" if state.get("verification", {}).get("needs_retry") else "finalize"


def build_agent_graph(retriever: Retriever | None = None):
    retriever = retriever or Retriever()
    rag_graph = build_rag_graph(retriever)
    llm = ChatOllama(
        model=settings.llm_model,
        base_url=settings.ollama_base_url,
        temperature=0,
    )
    decision_llm = llm.with_structured_output(AgentDecision)

    def classify(state: AgentState) -> dict:
        started = perf_counter()
        question = state["question"]
        try:
            decision = decision_llm.invoke(
                [
                    (
                        "system",
                        "You route requests for an EU AI Act compliance research assistant. "
                        "Decide whether the request is in scope, choose the intent, and create "
                        "one to three independent research tasks. Intent definitions: "
                        "scope_check = scope, definitions or operator roles; risk_assessment = "
                        "high-risk or risk classification; obligation_check = duties, requirements "
                        "or transparency; timeline_question = application/effective dates; "
                        "prohibited_practice_check = Article 5 style prohibited practices; "
                        "general_research = other in-scope AI Act research. Set needs_risk_tool for "
                        "classification/prohibited-practice questions and needs_date_tool only when "
                        "dates or staged application are relevant. Do not answer the user's question.",
                    ),
                    ("human", question),
                ]
            )
        except Exception:
            decision = fallback_decision(question)

        trace = state.get("trace", []) + [
            trace_entry(
                "classify",
                started,
                {"intent": decision.intent, "in_scope": decision.in_scope},
            )
        ]
        return {
            "intent": decision.intent,
            "decision": decision.model_dump(),
            "trace": trace,
        }

    def plan(state: AgentState) -> dict:
        started = perf_counter()
        tasks = [task.strip() for task in state["decision"].get("research_tasks", []) if task.strip()]
        if not tasks:
            tasks = [state["question"]]
        tasks = list(dict.fromkeys(tasks))[: settings.max_research_tasks]
        trace = state.get("trace", []) + [
            trace_entry("plan", started, {"task_count": len(tasks)})
        ]
        return {"research_tasks": tasks, "trace": trace}

    def research(state: AgentState) -> dict:
        started = perf_counter()
        tasks = list(state.get("research_tasks", []))
        top_k = settings.retrieval_top_k
        if state.get("retry_count", 0) > 0:
            tasks.append(f"Relevant EU AI Act legal provisions for: {state['question']}")
            top_k += 4

        collected: dict[str, dict] = {}
        for task in tasks:
            result = rag_graph.invoke({"query": task, "top_k": top_k})
            for item in result.get("evidence", []):
                existing = collected.get(item["chunk_id"])
                if not existing or item.get("score", 0.0) > existing.get("score", 0.0):
                    collected[item["chunk_id"]] = item

        ranked = sorted(collected.values(), key=lambda item: item.get("score", 0.0), reverse=True)
        evidence = []
        for index, item in enumerate(ranked[: settings.max_evidence], start=1):
            evidence.append({**item, "citation_id": f"S{index}"})

        trace = state.get("trace", []) + [
            trace_entry(
                "research",
                started,
                {"queries": len(tasks), "evidence_count": len(evidence)},
            )
        ]
        return {"evidence": evidence, "trace": trace}

    def run_tools(state: AgentState) -> dict:
        started = perf_counter()
        results: list[dict] = []
        decision = state.get("decision", {})
        risk_result: dict | None = None

        if decision.get("needs_risk_tool"):
            risk_result = risk_triage_tool.invoke({"description": state["question"]})
            results.append({"tool": "risk_triage_tool", "result": risk_result})

        if decision.get("needs_date_tool"):
            for rule_id in select_date_rule_ids(state["question"], risk_result):
                result = application_date_tool.invoke(
                    {"rule_id": rule_id, "as_of": state.get("as_of", date.today().isoformat())}
                )
                results.append({"tool": "application_date_tool", "result": result})

        trace = state.get("trace", []) + [
            trace_entry("tools", started, {"tool_calls": len(results)})
        ]
        return {"tool_results": results, "trace": trace}

    def answer(state: AgentState) -> dict:
        started = perf_counter()
        evidence_blocks = []
        for item in state.get("evidence", []):
            location = f"page {item.get('page')}"
            if item.get("section"):
                location += f", {item['section']}"
            evidence_blocks.append(
                f"[{item['citation_id']}] {item['title']} ({location})\n{item['text']}"
            )

        tool_text = json.dumps(state.get("tool_results", []), ensure_ascii=False, indent=2)
        evidence_text = "\n\n".join(evidence_blocks)
        prompt = f"""
User question:
{state['question']}

Deterministic tool results:
{tool_text}

Retrieved evidence:
{evidence_text}
""".strip()

        response = llm.invoke(
            [
                (
                    "system",
                    "You are an EU AI Act compliance research copilot. Answer in the same "
                    "language as the user's question. Use only the supplied evidence for legal "
                    "or regulatory claims. Cite every material legal claim with the supplied "
                    "citation IDs, for example [S1]. Tool results are preliminary deterministic "
                    "triage and must be confirmed against retrieved legal evidence. Clearly state "
                    "uncertainty when evidence is incomplete. Be concise and practical. Do not "
                    "present the response as legal advice.",
                ),
                ("human", prompt),
            ]
        )
        draft = response.content if isinstance(response.content, str) else str(response.content)
        trace = state.get("trace", []) + [trace_entry("answer", started)]
        return {"draft_answer": draft.strip(), "trace": trace}

    def verify(state: AgentState) -> dict:
        started = perf_counter()
        evidence = state.get("evidence", [])
        valid_ids = {item["citation_id"] for item in evidence}
        cited_ids = set(re.findall(r"\[(S\d+)\]", state.get("draft_answer", "")))
        unknown_ids = sorted(cited_ids - valid_ids)
        valid_citations = sorted(cited_ids & valid_ids)

        problems = []
        if len(evidence) < 1:
            problems.append("no_retrieved_evidence")
        if not valid_citations:
            problems.append("no_valid_citation")
        if unknown_ids:
            problems.append("unknown_citation_ids")

        can_retry = state.get("retry_count", 0) < settings.max_retries
        needs_retry = bool(problems) and can_retry
        retry_count = state.get("retry_count", 0) + (1 if needs_retry else 0)
        verification = {
            "passed": not problems,
            "needs_retry": needs_retry,
            "problems": problems,
            "valid_citations": valid_citations,
            "unknown_citations": unknown_ids,
        }
        trace = state.get("trace", []) + [
            trace_entry("verify", started, {"passed": verification["passed"], "problems": problems})
        ]
        return {
            "verification": verification,
            "retry_count": retry_count,
            "trace": trace,
        }

    def finalize(state: AgentState) -> dict:
        started = perf_counter()
        decision = state.get("decision", {})
        if not decision.get("in_scope", True):
            final_answer = (
                "This prototype is limited to EU AI Act compliance research. "
                "Please ask about AI Act scope, risk classification, obligations, prohibited "
                "practices, transparency, or application dates."
            )
        else:
            draft = state.get("draft_answer", "I could not produce a grounded answer.")
            cited = set(re.findall(r"\[(S\d+)\]", draft))
            sources = [item for item in state.get("evidence", []) if item["citation_id"] in cited]
            if not sources:
                sources = state.get("evidence", [])[:3]

            source_lines = []
            for item in sources:
                location = f"p. {item.get('page')}" if item.get("page") else ""
                section = f", {item['section']}" if item.get("section") else ""
                source_lines.append(
                    f"- [{item['citation_id']}] {item['title']} ({location}{section}) - {item['url']}"
                )

            warning = ""
            if not state.get("verification", {}).get("passed", False):
                warning = "\n\n**Evidence warning:** automatic citation verification did not fully pass."

            final_answer = (
                f"{draft}{warning}\n\n### Sources used\n"
                + "\n".join(source_lines)
                + "\n\n*Preliminary compliance research only; not legal advice.*"
            )

        trace = state.get("trace", []) + [trace_entry("finalize", started)]
        return {"final_answer": final_answer, "trace": trace}

    builder = StateGraph(AgentState)
    builder.add_node("classify", classify)
    builder.add_node("plan", plan)
    builder.add_node("research", research)
    builder.add_node("tools", run_tools)
    builder.add_node("answer", answer)
    builder.add_node("verify", verify)
    builder.add_node("finalize", finalize)

    builder.add_edge(START, "classify")
    builder.add_conditional_edges(
        "classify",
        route_after_classify,
        {"plan": "plan", "finalize": "finalize"},
    )
    builder.add_edge("plan", "research")
    builder.add_edge("research", "tools")
    builder.add_edge("tools", "answer")
    builder.add_edge("answer", "verify")
    builder.add_conditional_edges(
        "verify",
        route_after_verify,
        {"research": "research", "finalize": "finalize"},
    )
    builder.add_edge("finalize", END)
    return builder.compile()
