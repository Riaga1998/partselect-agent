# PartSelect Parts Assistant

A chat agent for the PartSelect e-commerce site, scoped to **refrigerator and
dishwasher parts**. It helps customers find parts, check model compatibility,
walk through installations, diagnose symptoms, and hand off order/billing issues
to support — and it stays firmly within that scope, declining anything else.

Built for the Instalily case study.

---

## Architecture

```
┌─────────────────────┐      POST /chat       ┌──────────────────────────┐
│  React frontend      │  ───────────────────▶ │  FastAPI backend          │
│  (Create React App)  │   {messages:[...]}    │  (app/main.py)            │
│                      │ ◀───────────────────  │                          │
│  • Chat UI + cards   │   {content,           │  ┌────────────────────┐  │
│  • Product cards     │    tool_calls,        │  │  Agent loop         │  │
│  • Compatibility     │    suggestions}       │  │  (app/agent.py)     │  │
│    banners           │                       │  │  Claude tool-use    │  │
│  • Suggestion chips  │                       │  └─────────┬──────────┘  │
│  • Functional cart   │                       │            │ tools        │
└─────────────────────┘                       │  ┌─────────▼──────────┐  │
                                               │  │  DataStore          │  │
                                               │  │  (app/datastore.py) │  │
                                               │  │  parts.json /       │  │
                                               │  │  models.json        │  │
                                               │  └────────────────────┘  │
                                               └──────────────────────────┘
```

**Agent loop** ([backend/app/agent.py](backend/app/agent.py)): Claude receives the
conversation plus a tool registry, decides which tools to call, we execute them
against the datastore and feed results back, and the loop repeats until Claude
writes a final answer. The model never touches raw data — it only calls tools.

**Tools** (one registry entry = one capability):
`search_parts`, `get_part_details`, `check_compatibility`,
`get_installation_guide`, `troubleshoot`, `escalate_to_support`.

**Data layer** ([backend/app/datastore.py](backend/app/datastore.py)): each public
method maps 1:1 to a tool. The seed catalog is JSON, but the interface is written
so it can be swapped for a real database or a vector store (for semantic part
search) without touching the agent.

**Frontend** ([src/](src/)): a React chat interface in PartSelect branding. Assistant
replies render as markdown prose **plus** structured components derived from the
`tool_calls` the backend returns — product cards, compatibility banners (green /
amber / grey by verdict), a support-handoff card, and agent-generated follow-up
suggestion chips. A client-side cart lets users add parts from any card.

---

## Design decisions

- **Tool-use agent over hardcoded flows.** Adding a capability is adding one tool +
  one datastore method — no branching logic to rewrite. This is the extensibility
  story: the same loop scales from 6 tools to 60.
- **Diagnose-first troubleshooting.** For a symptom, the assistant behaves like a
  repair advisor, not a vending machine: it clarifies ambiguous symptoms, suggests
  free non-part checks first (clean the filter, check the hose, settings), then
  surfaces the right part with *why* it could be the cause, and offers support only
  as a last resort.
- **No fabrication.** Part numbers, prices, and compatibility come only from tool
  results — the model can give general repair advice but cannot invent catalog data.
- **Conversational order handoff.** Order/billing/tracking questions follow a natural
  two-step flow: the assistant asks for the order number if it doesn't have one
  (showing an inline order-number input and step-appropriate chips), then hands off
  to support with that number. It never invents an order status or tracking detail —
  there's no order data, so it routes to humans rather than guessing.
- **`appliance_type` is data, not code.** Scope ("fridge + dishwasher") is enforced
  by the system prompt and by data, not by hardcoded branches — extending to ovens
  later means adding data, not rewriting logic.
- **Structured rendering from `tool_calls`.** The backend already returns full part
  objects and a `CompatibilityResult` with a `compatible: true|false|null` verdict,
  so the frontend renders rich cards/banners without a separate API contract.
- **Suggestion chips are agent-generated** (a cheap Haiku call) and constrained to
  actions the assistant can actually perform.
- **Graceful degradation.** Suggestion generation is non-fatal: any failure returns
  an empty list and the chat continues.

---

## Running locally

### Prerequisites
- Node 18+ and npm
- Python 3.9+
- An Anthropic API key ([console.anthropic.com](https://console.anthropic.com))

### 1. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure the API key
cp env.example .env
# then edit .env and set ANTHROPIC_API_KEY=sk-ant-...

# Run (from the backend/ directory)
uvicorn app.main:app --reload --port 8000
```

The backend serves `POST /chat` and `GET /health` on `http://localhost:8000`.

### 2. Frontend

```bash
# from the repo root
npm install
npm start
```

Open **http://localhost:3000**. The frontend calls the backend at
`http://localhost:8000` (see [src/api/api.js](src/api/api.js)).

---

## Example queries

- *How can I install part number PS11752778?*
- *Is this part compatible with my WDT780SAEM1 model?*
- *The ice maker on my Whirlpool fridge is not working. How can I fix it?*
- *Track my order* → asks for the order number, then hands off to support with it
- *I want a refund on my order* → hands off to support
- *How do I fix my oven?* → politely declines (out of scope)

A broader set of documented test cases (UI + API, with expected results and
ready-to-run curl commands) lives in [test_cases.txt](test_cases.txt).

---

## Project layout

```
backend/
  app/
    main.py        FastAPI server — POST /chat, GET /health
    agent.py       Claude tool-use loop + tool registry + suggestions
    datastore.py   Catalog access; one method per tool
    models.py      Pydantic schema (Part, ApplianceModel, CompatibilityResult)
    data/          parts.json, models.json (seed catalog)
  requirements.txt
  env.example      copy to .env and add your key
src/
  App.js           App shell: PartSelect header, cart state
  api/api.js       fetch wrapper for POST /chat
  components/
    ChatWindow.js  message list, renders cards/chips from tool_calls
    ProductCard.js compatibility banner + add-to-cart
    CartDrawer.js  client-side cart
    SupportCard.js escalation handoff
    Chip.js        suggestion chips
    OrderNumberInput.js  inline order-number entry on a support handoff
```

---

## Possible extensions

- Swap the JSON seed for a real catalog DB + a vector store for semantic part
  search (the `DataStore` interface stays identical).
- Stream responses token-by-token for lower perceived latency.
- Persist the cart and wire a real checkout/order-status backend.
- Add part images (the schema already has `image_url`; the UI falls back to an
  appliance glyph when it's null).
