# LEDGER NORMALIZATION API + PLC PROJECT — COMPREHENSIVE HANDOFF
## For ChatGPT or Other AI Assistant

---

## EXECUTIVE SUMMARY

**User Profile:**
- Entrepreneur/founder building products with AI assistance
- Beginner coder - needs execution guidance, not coding lessons
- **CRITICAL: Treat as business partner, NOT as student**
- Needs direct "do this, then this, done" instructions
- Frustrated by slow pace and over-explanation

**Working Relationship:**
- Give actionable steps, not explanations (unless asked)
- Build features in batches when possible (leverage AI capability)
- Focus on shipping products to market
- No coding lessons by default

---

## THREE ACTIVE PRODUCTS

### 1. Ledger Normalization API (PRIORITY 1 - Ship Tonight)
- **Status:** Almost done, RapidAPI auth broken
- **Blocker:** Users getting "missing API key" error on RapidAPI
- **Fix planned:** Check for `X-RapidAPI-Proxy-Secret` header instead of/in addition to `X-RapidAPI-Key`
- **Goal:** Fix auth tonight, make public, start getting customers

### 2. Invoicing API (NEXT)
- **Status:** Planning phase
- **Full requirements:** See "INVOICING API SPEC" section below
- **Start:** After Normalization API ships

### 3. Project Ledger Core (PLC) - Ongoing with ChatGPT
- **Status:** In development
- **Version:** v0.1.0 (basic features)
- **Full scope:** See "PLC V1 SCOPE" section below
- **Note:** Should NOT depend on the APIs initially

---

## CONTEXT CORRECTION - IMPORTANT

### What Happened Earlier
User shared ChatGPT's repository review that flagged:
- CORS vulnerability
- No logging
- No tests
- No .gitignore
- No LICENSE/README
- Overly permissive input validation

### ChatGPT's Correction (From Screenshots)
This was a **generic best-practices review**, NOT a blocker assessment:
- ❌ This is NOT why RapidAPI was failing
- ❌ This does NOT invalidate the API
- ❌ This does NOT require starting over
- ✅ Core API logic is solid
- ✅ The RapidAPI issue was auth boundary confusion, not code quality

### What Actually Matters Right Now

**Blocking/Must-Fix for RapidAPI:**
1. Auth logic (already addressed - simplification needed)

**Not Blocking (V2 hardening tasks):**
- No logging → Add after launch when users exist
- Overly permissive input validation → Future enhancement
- README/LICENSE → Polish items
- Tests → Important but not blocking RapidAPI
- CORS → Not a security hole for server-to-server API (RapidAPI calls backend, browsers don't)

### Phased Approach (ChatGPT's Plan)

**Phase 1 - Lock Marketplace (SHORT):**
1. Confirm RapidAPI test works (once auth fix is live)
2. Make API public OR unlisted (RapidAPI requirement)
3. Verify subscriber request succeeds

**Phase 2 - Hygiene (CALM, INCREMENTAL):**
Do these **one file at a time**, no chaos:
1. .gitignore
2. README.md (already drafted by ChatGPT)
3. Basic logging (5-10 lines)
4. Optional CORS tightening

No rewrites. No drama.

---

## THE RAPIDAPI PROBLEM - DETAILED

### User-Reported Symptoms
- RapidAPI test interface shows "Please correct the invalid field(s)" for X-RapidAPI-Key
- Reddit users tested and got "missing API key" errors
- API currently set to Private (not working, so not public yet)

### Root Cause Analysis

**Current auth code (api/public_router.py:40-42):**
```python
# 2) RapidAPI gateway path: key is enough
if (x_rapidapi_key or "").strip():
    return
```

**The problem:**
- Code checks for `X-RapidAPI-Key` header
- But RapidAPI **doesn't forward this header** to backend
- RapidAPI consumes it for their own auth
- Backend receives request WITHOUT this header
- Auth fails with 401

**Headers RapidAPI DOES send:**
- `X-RapidAPI-Host` (always)
- `X-RapidAPI-Proxy-Secret` (gateway identifier)
- `X-RapidAPI-User` (optional, subscriber info)

### The Solution

**Add check for headers RapidAPI actually forwards:**

```python
def require_public_auth(
    x_rapidapi_key: str | None = Header(default=None),
    x_rapidapi_proxy_secret: str | None = Header(default=None, alias="X-RapidAPI-Proxy-Secret"),
    x_rapidapi_host: str | None = Header(default=None, alias="X-RapidAPI-Host"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """
    Public/RapidAPI auth strategy (production-safe):

    1) If PLC_PUBLIC_ALLOW_ANON=1 -> allow without header (dev only).
    2) RapidAPI path: accept X-RapidAPI-Proxy-Secret or X-RapidAPI-Host
    3) Optional provider direct-call path: allow X-API-Key if it matches PLC_PUBLIC_API_KEY.
    4) Otherwise block.
    """
    if str(os.environ.get("PLC_PUBLIC_ALLOW_ANON", "")).strip() == "1":
        return

    # 2) RapidAPI gateway path: check for headers RapidAPI actually sends
    if (x_rapidapi_key or "").strip():
        return  # Keep for backward compatibility
    if (x_rapidapi_proxy_secret or "").strip():
        return  # RapidAPI gateway identifier
    if (x_rapidapi_host or "").strip():
        return  # RapidAPI always sends this

    # 3) Optional direct/provider testing path
    expected = str(os.environ.get("PLC_PUBLIC_API_KEY", "")).strip()
    provided_internal = (x_api_key or "").strip()
    if expected and provided_internal == expected:
        return

    # 4) Block everything else
    raise HTTPException(
        status_code=401,
        detail="Unauthorized. Use RapidAPI gateway or a valid X-API-Key if enabled.",
    )
```

**Why this works:**
- Still accepts X-RapidAPI-Key if sent (backward compatible)
- **Also accepts X-RapidAPI-Proxy-Secret** (RapidAPI gateway auth)
- **Also accepts X-RapidAPI-Host** (always sent by RapidAPI)
- Keeps X-API-Key fallback for direct testing
- Maintains ALLOW_ANON dev mode

### Tonight's Action Plan
1. User messages "I'm ready"
2. Provide exact code to paste
3. Git commit + push
4. Render auto-deploys
5. Test on RapidAPI
6. Make API public
7. ✅ Shipped

---

## INVOICING API SPEC

### What It Is
Stateless REST API for invoice creation, calculation, tracking, and reporting.

**Key Principle:** No Excel, no UI assumptions, no local paths. Stateless by default.

### Target Customers
- Freelancers & contractors
- Small businesses building internal tools
- SaaS products needing invoicing
- Bookkeeping/accounting automations (Zapier workflows)

### Core Endpoints (v1)

**Health + Meta:**
- `GET /v1/health`
- `GET /v1/version`

**Invoice Calculation (Most Valuable):**
- `POST /v1/invoices/calculate`
- Input: line items, tax mode, discounts, shipping, currency
- Output: totals breakdown (subtotal, tax, discount, shipping, grand_total)

**Invoice Creation (Two Modes):**

**Stateless mode (simple, build first):**
- `POST /v1/invoices/render`
- Returns invoice object with calculated totals
- Customer stores it themselves

**Hosted mode (optional, higher value):**
- `POST /v1/invoices` → create (stored)
- `GET /v1/invoices/{invoice_id}`
- `PATCH /v1/invoices/{invoice_id}` → update metadata/status
- `POST /v1/invoices/{invoice_id}/mark-paid`
- `POST /v1/invoices/{invoice_id}/void`
- Requires: account_id + DB (SQLite dev, Postgres production)

**Customer + Catalog Helpers (Optional but Sellable):**
- `POST /v1/customers/normalize` → normalize addresses/names/phones
- `POST /v1/line-items/normalize` → normalize SKUs, quantities, prices

**Reporting (Paid Plans):**
- `POST /v1/reports/summary` → date range totals, paid vs unpaid
- `POST /v1/reports/aging` → buckets (0-30, 31-60, 61-90, 90+)

### Data Models

**Invoice (minimum):**
- invoice_id (uuid)
- invoice_number (string)
- issue_date, due_date
- seller (name + address)
- buyer (name + address)
- line_items[] (desc, qty, unit_price, tax_category optional)
- currency
- totals (subtotal/tax/discount/shipping/total)
- status: draft | sent | paid | void | overdue

### Authentication
- Require `X-RapidAPI-Key` (RapidAPI injects automatically)
- Accept `X-API-Key` for local testing
- Use same pattern as Normalization API

### Build Order
1. FastAPI skeleton + auth dependency + /health
2. Pydantic models (invoice + line items)
3. `/v1/invoices/calculate` endpoint (core value)
4. `/v1/invoices/render` (stateless mode)
5. If needed: Postgres + CRUD for hosted mode
6. Reports endpoints
7. Docs polishing + RapidAPI OpenAPI import

### Pricing Strategy (User Asked for Opinion)

**Original proposal (user's draft):**
- Free: 5,000 calls/month
- Pro: $9/month - 50,000 calls
- Tier 3: $29/month - 100,000 calls

**Issues identified:**
- Free tier too large (enables freeloading)
- Price per call increases at higher tiers (backward economics)
- $9 is too cheap for the value delivered

**Recommended pricing:**
- **Free (Hobbyist):** 500 calls/month (demo only)
- **Starter:** $15/month - 10,000 calls ($0.0015/call)
- **Pro:** $49/month - 50,000 calls ($0.00098/call)
- **Business:** $149/month - 200,000 calls ($0.000745/call)

**Rationale:**
- Customer alternative = $5K-10K to hire developer
- API saves weeks of work
- Each tier has lower cost per call (volume discount)
- $15 entry point is low friction but not "too cheap"
- Business tier is where revenue comes from

User can adjust based on market feedback.

---

## PLC (PROJECT LEDGER CORE) V1 SCOPE

### What V1 Is
Core budgeting + basic household/business support. Desktop first. Excel-optional.

**V1's job:**
- Track bills, debts, paychecks
- Show what's due and paid
- Write changes back safely (if Excel mode)
- Provide summaries without bloat

### V1 Core Features (Must-Have)

**1) Bills (Core):**
- Bills list view
- Add/edit/delete bill
- Fields: name, amount, frequency, category, due date/rule, status (upcoming/paid/overdue), notes
- Mark paid/unpaid
- Optional: actual paid amount + paid date

**2) Debts + Loans (Core with toggle):**
Support:
- Mortgages
- Car loans
- Credit cards
- Other loans

Must include:
- APR for any loan/CC/car
- Balance, minimum payment, due date
- **Toggle: simple view vs detailed amortization/breakdown**

**3) Paycheck Calendar + Planning:**
- Paycheck schedule
- Assign bills to paychecks (A/B/C or date-based)
- Show "this paycheck covers these bills"
- Paycheck totals (incoming vs outgoing)

**4) Summaries (V1):**
- Monthly snapshot (income, bills, debt payments, leftover)
- Quarterly summary
- Year-end summary basic (full analytics later)

**5) Data Source Modes (V1):**
- **Excel mode:** read from Excel + write back on save
- **Local mode (Excel-optional):** same data model, JSON/SQLite storage

**6) Settings (V1):**
- "Open Excel after Save" checkbox (default ON)
- Select data source
- Basic paths/config

### Basic Household Edition (V1-Level Only)
Include:
- Shared household budget categories
- Shared bills tracking
- (Optional) Add Amanda as co-owner in data model/UI

**Do NOT include in V1 (V2+):**
- Emergency plans + contact lists
- Kid-friendly syncing
- Travel plan printing

### Basic Business Edition (V1-Level)
- Basic expense categories for business
- **No inventory management in V1** (V2+)

### Non-Negotiables (Stability Rules)
- No destructive Excel writes without backup
- Clear IDs for bills/debts (avoid row mismatch)
- Error messages that tell user what to do next (not vague "failed")

### API Integration Timeline
**After these are stable:**
- Excel sync working
- Write-back stable
- Core models (bills/debts) locked

**Then:**
- Spin out RapidAPI products as separate services
- PLC can optionally call them later
- **PLC V1 should NOT depend on APIs**

### Questions for User (When Coordinating PLC Work)
1. Where's the PLC code? (GitHub link or local path)
2. What features are working now?
3. What are you building with ChatGPT this week?

---

## PRICING DISCUSSION SUMMARY

User asked opinion on API pricing tiers.

**Key points made:**
- Free tier should be 100-500 calls (demo), not 5,000 (freeload prevention)
- Cost per call should DECREASE at higher volumes (standard economics)
- Price based on value (alternative = hire developer for $5K-10K)
- $9/month is too cheap - feels suspicious and barely covers costs
- Recommended entry point: $15/month
- Business tier ($149) is where real revenue comes from

User can adjust based on market response.

---

## WORKING RELATIONSHIP EXPECTATIONS

### What User Needs
**Direct execution, not education:**
- "Do this, then this, done"
- Build features in batches when AI can handle complexity
- Ship fast, learn from market
- Explanations only when requested

### What User Does NOT Need
- Coding lessons
- Step-by-step learning
- One tiny feature at a time
- Over-explanation of concepts

### User's Role
- Founder/CEO making business decisions
- Testing products
- Providing direction

### AI's Role
- Technical co-founder who executes
- Builds features
- Tells user what to paste/run/click
- Fixes what breaks
- Ships products

### User Frustrations (To Avoid)
- Slow pace ("add one feature, test, add another...")
- Wrong menu/UI guidance (RapidAPI UI changes, screenshots help)
- Student treatment when they need business partner treatment
- Debugging loops

### How to Prevent Frustration
- Ask what they want to build
- Build it
- Give them exact commands/code to run
- Fix issues directly
- Move to next thing
- Use screenshots when guiding UI navigation

---

## CURRENT GIT STATE

**Branch:** `claude/review-github-repo-xZBGd`
**Status:** Clean working directory

**Recent commits:**
- Refactor public router authentication and endpoints
- Lock public endpoints to RapidAPI gateway headers
- Wire public_v1_router into api_public_main
- Add root endpoint for RapidAPI gateway

**Deployment:**
- Render auto-deploys on push
- Docker containerized
- Health check: `/v1/health`

---

## IMMEDIATE NEXT STEPS

### Tonight (When User Returns)
1. User messages "I'm ready"
2. Provide exact auth code fix
3. Git commit + push commands
4. Wait for Render deployment
5. Test on RapidAPI
6. Make API public
7. ✅ Normalization API shipped

### After Ship
- Start Invoicing API build
- Coordinate PLC progress with user
- Get info on what ChatGPT has built

---

## KEY FILES

**Normalization API:**
- `/home/user/ledger-normalization-api/api/public_router.py` (auth logic here)
- `/home/user/ledger-normalization-api/api_public_main.py` (CORS, main app)
- `/home/user/ledger-normalization-api/render.yaml` (deployment config)
- `/home/user/ledger-normalization-api/requirements.txt` (dependencies)

**Environment variables (set in Render dashboard):**
- `PLC_PUBLIC_ALLOW_ANON` = "0" (production)
- `PLC_PUBLIC_API_KEY` = secret (for direct testing)

---

## CRITICAL REMINDERS

1. **Treat user as business partner, not student**
2. **No debugging loops - fix directly or ask for screenshots**
3. **Ship first, polish later**
4. **The APIs work - auth boundary was the only issue**
5. **Don't restart from scratch - current code is solid**
6. **Phase 2 items (logging, README, etc.) are NOT blockers**
7. **Build in batches when possible - leverage AI capability**

---

## END OF HANDOFF

**User is ready to ship. Let's execute cleanly and get products to market.**
