# MedSaathi — AI Medication Companion for Elderly & Rural Patients

**Track:** Concierge Agents
**Capstone:** AI Agents: Intensive Vibe Coding Capstone Project

## Problem

In rural and elderly communities, a prescription is often the most dangerous
document a patient holds. Handwritten dosages, medical jargon, and
multi-drug regimens are hard to follow for elderly patients with low health
literacy, limited vision, or no shared language with their doctor. Missed
doses and unnoticed drug interactions are common, and family caregivers who
could catch these risks aren't present at every dosing hour.

## Solution

MedSaathi turns a single photo into ongoing, life-safe care. A family
member photographs the prescription — that's the entire setup. An agent
pipeline then:

1. **Reads** the prescription and extracts every medication, dosage, and frequency.
2. **Checks** the full drug list (new + existing) for dangerous interactions.
3. **Builds** a plain-language dosing schedule.
4. **Translates** it into the patient's own language, in simple, respectful phrasing.
5. **Delivers** recurring reminders via WhatsApp/SMS — no app to install.

If a **high-severity interaction** is found, the pipeline halts before
scheduling or sending anything and surfaces the warning for human review.
Safety gates the whole system.

## Why Agents

This can't be solved with one LLM call. It requires a chain of specialized
reasoning steps with distinct failure modes: misreading a scrawled dosage
is a different risk than missing a drug interaction, which is different
again from mistranslating a warning. Separating these into independent
agents means each stage can be verified, retried, or halted on its own —
not a technical nicety here, but a safety requirement.

## Architecture

```
[Prescription Photo]
        |
        v
[PrescriptionVisionAgent]   -- extracts drug name, dosage, frequency (Claude vision)
        |
        v
[DrugInteractionAgent]      -- checks new + existing meds against interaction DB
        |                       -- HALTS pipeline here if HIGH severity found
        v
[SchedulerAgent]            -- converts frequency text into concrete reminder times
        |
        v
[LocalizationAgent]         -- translates reminders into patient's language (Claude)
        |
        v
[PatientVault]              -- encrypts and stores patient record (Fernet)
        |
        v
[Notification MCP Server]   -- send_reminder tool -> WhatsApp/SMS (Twilio, or simulated)
```

Orchestration lives in `agents/orchestrator.py` (`MedSaathiOrchestrator`),
which chains each agent and enforces the safety halt / consent gate between
stages.

## Course Concepts Demonstrated

| Concept | Where |
|---|---|
| Multi-agent system (ADK-style) | `agents/orchestrator.py` chains 4 independent agents with validated handoffs |
| MCP Server | `mcp_server/notification_server.py` exposes `send_reminder` as an MCP tool |
| Security features | `agents/security.py` — Fernet encryption at rest, PII masking in logs, consent gate |
| Deployability | `Dockerfile` + setup instructions below |
| Agent skills (CLI) | `cli.py` — full command-line interface, incl. a zero-config `--demo` mode |

## Setup

```bash
git clone <your-repo-url>
cd medsaathi
python3 -m venv venv
source venv/bin/activate   # on Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY (and Twilio credentials if you
# want real WhatsApp/SMS delivery instead of simulated).
```

## Running

**Zero-config demo (no API keys needed):**
```bash
python cli.py --demo
```

**Real prescription photo:**
```bash
python cli.py --image ./prescription.jpg \
    --patient-name "Lakshmi Devi" \
    --phone +919876543210 \
    --existing-meds "amlodipine,levothyroxine" \
    --language telugu \
    --consent
```

**Force simulate mode with a real image (no live API calls):**
```bash
python cli.py --image ./prescription.jpg --simulate --consent
```

Results are written to `output/last_run_result.json`. The encrypted
patient record is written to `patient_data/patient_record.enc`.

**Run the MCP server standalone:**
```bash
python mcp_server/notification_server.py
```

**Docker:**
```bash
docker build -t medsaathi .
docker run --env-file .env medsaathi
```

## Security Notes

- Patient records are encrypted at rest with Fernet (`agents/security.py`).
- Phone numbers and patient names are masked before appearing in any log line.
- No record is stored, and no reminder is sent, without an explicit `--consent` flag.
- `.env` is git-ignored — never commit real API keys or Twilio credentials.

## Known Limitations / Next Steps

- The drug interaction database (`data/drug_interactions.json`) is a small
  curated sample for demo purposes — a production version would integrate
  a licensed clinical interaction API (e.g. RxNorm/DrugBank).
- OCR accuracy on handwritten prescriptions varies; the vision agent
  flags uncertain reads with a trailing `?` rather than guessing silently.
- WhatsApp delivery via Twilio requires WhatsApp Business API approval for
  production use; the sandbox number works for testing.
