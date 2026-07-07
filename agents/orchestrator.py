"""
orchestrator.py
------------------
The multi-agent coordinator (ADK-style pattern). Chains:

    PrescriptionVisionAgent
        -> DrugInteractionAgent
            -> SchedulerAgent
                -> LocalizationAgent
                    -> NotificationDispatcher (calls the MCP notification server)

Each stage's output is validated before being passed to the next. If the
interaction agent flags a HIGH severity warning, the pipeline halts before
scheduling/sending anything and surfaces the warning for human review -
this is the core safety behavior of the whole system.
"""

import json
import os

from .interaction_agent import DrugInteractionAgent
from .localization_agent import LocalizationAgent
from .scheduler_agent import SchedulerAgent
from .security import ConsentRequiredError, PatientVault, mask_name, mask_phone
from .vision_agent import PrescriptionVisionAgent


class MedSaathiOrchestrator:
    def __init__(self, simulate: bool = False):
        self.simulate = simulate
        self.vision_agent = PrescriptionVisionAgent(simulate=simulate)
        self.interaction_agent = DrugInteractionAgent(simulate=simulate)
        self.scheduler_agent = SchedulerAgent(simulate=simulate)
        self.localization_agent = LocalizationAgent(simulate=simulate)

    def run(
        self,
        image_path: str,
        patient_name: str,
        phone: str,
        existing_medications: list[str],
        language: str,
        consent_given: bool,
        vault_path: str = "patient_data/patient_record.enc",
    ) -> dict:
        print(f"\n[1/5] Reading prescription for patient {mask_name(patient_name)}...")
        extraction = self.vision_agent.run(image_path)
        new_meds = extraction["medications"]
        print(f"      Extracted {len(new_meds)} medication(s): "
              f"{', '.join(m['name'] for m in new_meds)}")

        print("\n[2/5] Checking for drug interactions...")
        interaction_result = self.interaction_agent.run(new_meds, existing_medications)
        if interaction_result["warnings"]:
            for w in interaction_result["warnings"]:
                print(f"      ⚠ [{w['severity'].upper()}] {w['drugs'][0]} + {w['drugs'][1]}: {w['description']}")
        else:
            print("      No known interactions found.")

        if not interaction_result["safe_to_proceed"]:
            print("\n🛑 HIGH severity interaction detected. Halting pipeline for physician/pharmacist review.")
            return {
                "status": "halted_for_review",
                "interaction_result": interaction_result,
                "extraction": extraction,
            }

        print("\n[3/5] Building dosing schedule...")
        schedule = self.scheduler_agent.run(new_meds)
        for item in schedule:
            print(f"      {item['medication']} ({item['dosage']}) at {', '.join(item['times'])}")

        print(f"\n[4/5] Translating reminders into {language}...")
        localized_schedule = self.localization_agent.run(schedule, language)

        print("\n[5/5] Storing patient record securely and queuing reminders...")
        try:
            vault = PatientVault(storage_path=vault_path)
            vault.save(
                {
                    "patient_name": patient_name,
                    "phone": phone,
                    "existing_medications": existing_medications,
                    "current_schedule": localized_schedule,
                },
                consent_given=consent_given,
            )
            print(f"      Patient record encrypted and saved ({mask_phone(phone)}).")
        except ConsentRequiredError as exc:
            print(f"      🛑 {exc}")
            return {"status": "consent_required", "extraction": extraction}

        dispatch_results = self._dispatch_reminders(localized_schedule, phone)

        return {
            "status": "success",
            "extraction": extraction,
            "interaction_result": interaction_result,
            "localized_schedule": localized_schedule,
            "dispatch_results": dispatch_results,
        }

    def _dispatch_reminders(self, localized_schedule: list[dict], phone: str) -> list[dict]:
        """Calls the notification MCP tool logic directly for demo purposes.

        In a full MCP client/host setup, this would instead be an MCP tool
        call over the `mcp` client session to `notification_server.py`. The
        underlying send_reminder function is identical either way - see
        mcp_server/notification_server.py.
        """
        import sys

        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from mcp_server.notification_server import send_reminder

        results = []
        for item in localized_schedule:
            for time_str in item["times"]:
                result = send_reminder(
                    phone=phone,
                    message=f"[{time_str}] {item['localized_message']}",
                    channel="whatsapp",
                )
                results.append({"medication": item["medication"], "time": time_str, **result})
                print(f"      → {item['medication']} @ {time_str}: {result['status']}")
        return results
