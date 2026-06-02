"""
PartSelect agent loop — the core of the submission.

Claude receives a message and a set of tools. It decides which tools to call,
calls them (we execute and return results), and repeats until it has enough
to write a final answer. That loop is what makes this "agentic."

Tool registry lives in TOOLS. Adding a new capability = adding one entry here.
"""
import json
import os
from typing import Optional
from anthropic import Anthropic
from dotenv import load_dotenv

from .datastore import store
from .models import ApplianceType

load_dotenv()

client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = "claude-sonnet-4-6"
# Cheap, fast model for the throwaway follow-up-chip generation step.
SUGGESTIONS_MODEL = "claude-haiku-4-5-20251001"

SYSTEM_PROMPT = """You are the PartSelect Parts Assistant — a specialist in refrigerator and dishwasher parts only.

You help customers:
- Find parts by symptom, name, or part number
- Check whether a part fits their appliance model
- Walk through installation steps
- Diagnose what part to replace for a given symptom
- Connect with customer support for orders, billing, or returns

SCOPE RULES — strictly enforced:
- Only answer questions about refrigerators and dishwashers.
- If a question is about a different appliance (oven, washer, dryer, etc.) or is completely unrelated (weather, coding, etc.), politely decline and offer to help with fridges or dishwashers instead.
- For order tracking, order status, billing, refunds, returns, or damaged items: you cannot look these up yourself and must never invent an order status, date, or tracking detail. If the customer hasn't given an order number yet, ask for it conversationally first. Once you have an order number (now or from earlier in the chat), use the escalate_to_support tool to hand off to the support team with that number. Never try to resolve order/billing issues yourself.

TROUBLESHOOTING APPROACH — diagnose first, sell second:
You are a repair assistant, not just a parts catalog. When a customer describes a symptom:
1. CLARIFY if the symptom is ambiguous. Ask one or two focused questions that change the diagnosis (e.g. "Is the top rack dirty or the whole load?", "Did this start after a recent install?", "Any unusual noise or error code?", "What's your model number?"). Don't interrogate — ask only what genuinely narrows it down.
2. NON-PART CAUSES FIRST. Many issues are not a broken part. Offer the free checks before recommending a purchase — e.g. clean the filter/strainer, check for a kinked or clogged drain hose, confirm the cycle/settings, clear spray-arm holes, check water supply, reset/power-cycle. These are general repair knowledge and are fine to give without a tool.
3. SURFACE THE LIKELY PART(S). Whenever you discuss which part might be at fault, you MUST call the troubleshoot tool first and base your answer on what it returns — do not describe parts from memory. Give the free checks AND the tool-backed part(s) in the same reply, so the customer sees a real, in-stock option with a price next to the DIY advice. EXPLAIN WHY each returned part could be the culprit and how to tell if it's the one — symptoms that point to it, a quick test they can do. The goal is the RIGHT part, not the most parts. Never mention a part name or number you did not get from a tool.
4. SUPPORT IS A LAST RESORT. Offer to connect them with support only after the self-help path — frame it as "if those checks don't fix it" or "if you'd rather have a person help." Don't lead with escalation for a repairable symptom.

RESPONSE STYLE:
- Be concise and helpful. Customers are usually mid-repair.
- When you find a part, always include the PS number, price, and compatibility.
- When you find multiple candidate parts for a symptom, list them — diagnosing is collaborative.
- Never fabricate part numbers, prices, or compatibility. Those come only from tool results. General repair/maintenance advice (cleaning, settings, checks) does not require a tool and is encouraged.
"""

# --------------------------------------------------------------------------
# Tool definitions — what Claude can "see" and choose to call
# --------------------------------------------------------------------------
TOOLS = [
    {
        "name": "search_parts",
        "description": "Search the parts catalog by keyword, symptom, or category. Use this when the user describes a problem or asks for a type of part.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search terms, e.g. 'ice maker not working' or 'door shelf bin'"},
                "appliance_type": {"type": "string", "enum": ["refrigerator", "dishwasher"], "description": "Filter to one appliance type if known"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_part_details",
        "description": "Get full details for a specific part by its PS number, including price, installation steps, difficulty, and compatible models.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ps_number": {"type": "string", "description": "The PartSelect part number, e.g. PS11752778"}
            },
            "required": ["ps_number"]
        }
    },
    {
        "name": "check_compatibility",
        "description": "Check whether a specific part is compatible with a specific appliance model number. Always call this when the user asks about fit.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ps_number": {"type": "string", "description": "The PartSelect part number"},
                "model_number": {"type": "string", "description": "The appliance model number, e.g. WDT780SAEM1"}
            },
            "required": ["ps_number", "model_number"]
        }
    },
    {
        "name": "get_installation_guide",
        "description": "Get step-by-step installation instructions for a part, including difficulty level and estimated time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ps_number": {"type": "string", "description": "The PartSelect part number"}
            },
            "required": ["ps_number"]
        }
    },
    {
        "name": "troubleshoot",
        "description": "Given a symptom, return the parts most likely responsible. Use this for diagnostic questions like 'my ice maker stopped working'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symptom": {"type": "string", "description": "The problem description, e.g. 'ice maker not making ice'"},
                "appliance_type": {"type": "string", "enum": ["refrigerator", "dishwasher"]},
                "brand": {"type": "string", "description": "Appliance brand if mentioned, e.g. Whirlpool"}
            },
            "required": ["symptom"]
        }
    },
    {
        "name": "escalate_to_support",
        "description": "Hand off to human customer support. Use for billing, refunds, damaged orders, returns, or anything that isn't a parts/repair question.",
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Brief description of the issue"},
                "order_id": {"type": "string", "description": "Order number if the user mentioned one"}
            },
            "required": ["reason"]
        }
    }
]


# --------------------------------------------------------------------------
# Tool executor — maps tool names to real datastore calls
# --------------------------------------------------------------------------
def execute_tool(name: str, inputs: dict) -> dict:
    if name == "search_parts":
        app_type = ApplianceType(inputs["appliance_type"]) if "appliance_type" in inputs else None
        results = store.search_parts(inputs["query"], appliance_type=app_type)
        return {"parts": [p.model_dump() for p in results]}

    if name == "get_part_details":
        part = store.get_part(inputs["ps_number"])
        if not part:
            return {"error": f"Part {inputs['ps_number']} not found."}
        return part.model_dump()

    if name == "check_compatibility":
        result = store.check_compatibility(inputs["ps_number"], inputs["model_number"])
        return result.model_dump()

    if name == "get_installation_guide":
        part = store.get_part(inputs["ps_number"])
        if not part:
            return {"error": f"Part {inputs['ps_number']} not found."}
        return {
            "ps_number": part.ps_number,
            "name": part.name,
            "difficulty": part.install_difficulty,
            "time_mins": part.install_time_mins,
            "steps": part.install_steps,
            "video_url": part.install_video_url,
        }

    if name == "troubleshoot":
        app_type = ApplianceType(inputs["appliance_type"]) if "appliance_type" in inputs else None
        parts = store.parts_for_symptom(
            inputs["symptom"], appliance_type=app_type, brand=inputs.get("brand")
        )
        return {"candidate_parts": [p.model_dump() for p in parts]}

    if name == "escalate_to_support":
        return {
            "escalated": True,
            "reason": inputs["reason"],
            "order_id": inputs.get("order_id"),
            "contact": {
                "phone": "1-866-319-8402",
                "email": "CustomerService@PartSelect.com",
                "hours": "until midnight EST"
            }
        }

    return {"error": f"Unknown tool: {name}"}


# --------------------------------------------------------------------------
# Follow-up suggestion chips
# --------------------------------------------------------------------------
def generate_suggestions(conversation: list[dict], answer: str) -> list[str]:
    """Ask a cheap model for 2-3 short follow-up chips the user is likely to tap next.

    Non-fatal: any failure (API error, bad JSON, wrong shape) returns [] so the
    chat never breaks just because suggestions couldn't be produced.
    """
    # Only the plain text turns matter for context here; tool-use turns carry
    # non-string content the suggestion model doesn't need.
    history = [
        m for m in conversation
        if isinstance(m.get("content"), str)
    ]
    prompt = (
        "Based on the conversation so far and the assistant's latest reply, propose "
        "2-3 SHORT follow-up actions the user is most likely to want next, phrased as "
        "things they would tap (max ~5 words each), e.g. \"How do I install this?\", "
        "\"Check fit for my model\", \"Track my order\". Stay within refrigerator and "
        "dishwasher parts help.\n"
        "Only suggest actions this assistant can actually perform: finding parts, "
        "checking compatibility, installation steps, troubleshooting symptoms, and "
        "order/support handoff. Do NOT suggest watching videos, viewing images, "
        "live chat, or anything not offered above.\n\n"
        f"Assistant's latest reply:\n{answer}\n\n"
        "Return ONLY a JSON array of strings, nothing else. Example: "
        '["How do I install this?", "Find a cheaper option"]'
    )
    try:
        resp = client.messages.create(
            model=SUGGESTIONS_MODEL,
            max_tokens=200,
            messages=history + [{"role": "user", "content": prompt}],
        )
        text = next((b.text for b in resp.content if hasattr(b, "text")), "").strip()
        # Strip code fences if the model wrapped the JSON.
        if text.startswith("```"):
            text = text.strip("`").lstrip("json").strip()
        data = json.loads(text)
        if isinstance(data, list):
            chips = [str(s).strip() for s in data if str(s).strip()]
            return chips[:3]
    except Exception:
        pass
    return []


def is_asking_for_order_number(text: str) -> bool:
    """Heuristic: is the assistant's reply requesting an order number?"""
    t = text.lower()
    return "order number" in t or "order #" in t or "order id" in t


def step_suggestions(tool_calls_log: list[dict], answer: str) -> Optional[list[str]]:
    """Deterministic, step-appropriate chips based on the turn's state.

    Returns a fixed chip list when the turn calls for specific next actions
    (a support handoff, or the assistant asking for an order number). Returns
    None to fall back to the LLM-generated suggestions.
    """
    tools_used = {c["tool"] for c in tool_calls_log}

    # Already handed off to support -> offer onward actions, not "enter it again".
    if "escalate_to_support" in tools_used:
        return ["Find a part instead", "Troubleshoot an issue", "Check part compatibility"]

    # Assistant is asking for an order number (no handoff yet) -> help provide it.
    if is_asking_for_order_number(answer):
        return ["I don't have my order number", "Find a part instead", "Troubleshoot an issue"]

    return None


# --------------------------------------------------------------------------
# Agent loop
# --------------------------------------------------------------------------
def run_agent(conversation: list[dict]) -> dict:
    """
    Runs the Claude tool-use loop for one user turn.

    `conversation` is the full message history in Anthropic format:
        [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]

    Returns the final assistant response as:
        {"role": "assistant", "content": "<text>", "tool_calls": [...], "suggestions": [...]}
    """
    messages = list(conversation)
    tool_calls_log = []

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Claude is done — return the text answer
        if response.stop_reason == "end_turn":
            text = next(
                (block.text for block in response.content if hasattr(block, "text")), ""
            )
            suggestions = step_suggestions(tool_calls_log, text)
            if suggestions is None:
                suggestions = generate_suggestions(conversation, text)
            return {
                "role": "assistant",
                "content": text,
                "tool_calls": tool_calls_log,
                "suggestions": suggestions,
            }

        # Claude wants to call tools — execute each one and feed results back
        if response.stop_reason == "tool_use":
            # Append Claude's tool-use turn to the conversation
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    tool_calls_log.append({"tool": block.name, "input": block.input, "result": result})
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })

            # Feed all results back in one user turn (Anthropic's required format)
            messages.append({"role": "user", "content": tool_results})
            # Loop — Claude will now reason over the results and either answer or call more tools
