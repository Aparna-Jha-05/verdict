# Invoice Intelligence Pipeline

Vision-first invoice extraction wrapped in **two deterministic verification
layers** and a **human approval gate**. A user drops in a PDF, scan, or phone
photo; a vision-language model reads it directly (no OCR) into structured JSON
with per-field confidence and bounding boxes; then two layers that **never call
an LLM** run — a *validation layer* (totals reconcile, dates valid, fields
present) and a *fraud/tamper layer* (PDF metadata forensics, vendor bank-detail
changes, semantic near-duplicate detection). Low-confidence documents are
auto-escalated to a stronger model before a human sees them. The human reviews
each field with its source box highlighted on the image, sees red flags with
plain-English reasons, edits if needed, and approves — firing a mock downstream
action and writing to the ledger.

> The differentiator is not "an LLM reads a PDF." It's the deterministic layers
> and the approval gate wrapped around the model.

---

## Architecture

```
upload (PDF/PNG/JPG)
   │
   ├─ ingest.py     normalize to a page image; read PDF metadata
   │
   ├─ route.py      "intelligent inference layering"
   │     ├─ extract.py   default vision model → schema-constrained JSON
   │     ├─ validate.py  deterministic correctness checks   ← NO LLM
   │     ├─ (escalate on low confidence / parse fail / extraction-type error)
   │     └─ fraud.py + dedup.py  deterministic fraud checks  ← NO LLM
   │
   └─ human approval gate → mock action + CSV + ledger write + embedding index
```

**Hard architectural rule:** `validate.py`, `fraud.py`, and `dedup.py` never
call an LLM. Fraud results are always *flags for human review* — never
"authentic", "verified", or "safe to pay".

---

## Backend (FastAPI)

### Setup
```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # then put your AIPIPE_TOKEN in .env
```

### Generate demo data + seed the ledger
```bash
python make_samples.py      # writes sample_data/invoices/*
python seed.py              # pre-loads the "prior" invoices checks 4 & 5 need
```

### Run
```bash
uvicorn main:app --reload --port 8000
```

### Endpoints
| Method | Route      | Purpose                                                        |
|--------|------------|----------------------------------------------------------------|
| POST   | `/process` | ingest → extract → route → validate → fraud → dedup            |
| POST   | `/approve` | write ledger, record vendor→bank, index embedding, mock action |
| GET    | `/log`     | approved invoices (powers duplicate + bank-history checks)     |
| POST   | `/match`   | STRETCH three-way match vs `pos.json` + `receipts.json`        |
| GET    | `/health`  | Render health check                                            |

`AIPIPE_TOKEN` is read from the environment only — never hardcoded. Confirm a
live **vision-capable** model name from AI Pipe's model list and set
`AIPIPE_VISION_MODEL` / `AIPIPE_ESCALATION_MODEL` if the defaults differ.

---

## Frontend (Next.js)

```bash
cd frontend
npm install
cp .env.local.example .env.local   # point NEXT_PUBLIC_API_BASE at the backend
npm run dev                        # http://localhost:3000
```

One screen, cosmic aesthetic:
- **Uploader** — drag-drop + one-click sample chips.
- **DocViewer** — renders the page image with bounding boxes; hovering a field
  highlights its box and vice-versa. Degrades to source text if boxes are weak.
- **FieldReview** — editable glass cards with confidence badges + source on hover.
- **ValidationPanel** — correctness checklist; failures are loud.
- **FraudPanel** — flags tagged "flag for review", never "authentic".
- **ApproveBar** — enabled after you've viewed the fraud panel; approve → mock
  action + CSV download + success animation. `model:` and `escalated` badges up top.

---

## Deploy

- **Backend → Render:** `backend/render.yaml` blueprint (Docker). Set
  `AIPIPE_TOKEN` and `CORS_ORIGINS` (your Vercel URL) as env vars. After deploy,
  run `make_samples.py` + `seed.py` once via a shell, or seed on startup.
- **Frontend → Vercel:** import `frontend/`, set `NEXT_PUBLIC_API_BASE` to the
  Render URL.

Deploy the backend skeleton early (step 1) and the frontend at step 8 — a
deployed product at 70% beats a local one at 95%.

---

## 90-second demo script

1. **Clean PDF** → fields populate, green confidence, boxes drawn; hover "Total"
   → its box lights up. *"It shows its work, on the document itself."*
2. **Phone photo** → `⚡ escalated` badge → extracts correctly. *"Vision-first,
   and we route to a stronger model by confidence, not brute force."*
3. **Wrong total** → extraction succeeds but validation throws a red flag with
   the reason. *"The model believed the document. Our deterministic layer didn't."*
4. **Changed bank account** → fraud panel flags the bank change vs vendor
   history. *"The most common real-world invoice fraud — it never reaches payment."*
5. **Near-duplicate** → semantic dedup flags it despite the altered number.
   *"Exact-match checks miss this. Embeddings don't."*
6. **Approve a clean one** → mock action fires, CSV downloads, it's logged, and
   it now blocks future duplicates. *"Human-approved, logged, and self-defending."*

---

## Sample invoices (`backend/sample_data/invoices/`)

| File                | Demonstrates                                           |
|---------------------|--------------------------------------------------------|
| `clean.pdf`         | happy path — everything reconciles, high confidence    |
| `photo_scan.jpg`    | skewed/noisy photo → escalation → correct extraction   |
| `wrong_total.pdf`   | validation catch (subtotal + tax ≠ total)              |
| `changed_bank.pdf`  | fraud catch — bank account differs from seeded history |
| `near_duplicate.pdf`| semantic dedup catch — one-digit-different number      |
| `no_po.pdf`         | STRETCH three-way match — no matching purchase order   |

`seed.py` pre-loads the prior Meridian Logistics and Stellar Freight invoices
that scenarios 4 and 5 compare against.
