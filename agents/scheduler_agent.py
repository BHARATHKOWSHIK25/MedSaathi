"""
scheduler_agent.py
--------------------
Stage 3 of the pipeline: converts free-text frequency instructions
("twice daily after meals") into concrete daily reminder times, and builds
the plain-language message that will eventually be localized and sent.
"""

from .base import Agent

FREQUENCY_MAP = {
    "once daily": ["08:00"],
    "once daily in the morning": ["08:00"],
    "once daily after breakfast": ["08:30"],
    "once daily at night": ["21:00"],
    "twice daily": ["08:00", "20:00"],
    "twice daily after meals": ["08:30", "20:30"],
    "three times daily": ["08:00", "14:00", "20:00"],
    "three times daily after meals": ["08:30", "14:30", "20:30"],
    "every 8 hours": ["06:00", "14:00", "22:00"],
    "every 12 hours": ["08:00", "20:00"],
}

DEFAULT_TIMES = ["09:00"]  # fallback if frequency text isn't recognized


class SchedulerAgent(Agent):
    name = "scheduler_agent"

    def run(self, medications: list[dict]) -> list[dict]:
        schedule = []
        for med in medications:
            freq_key = med["frequency"].strip().lower()
            times = FREQUENCY_MAP.get(freq_key, DEFAULT_TIMES)
            if freq_key not in FREQUENCY_MAP:
                self.logger.warning(
                    "Unrecognized frequency '%s' for %s - using default reminder time",
                    med["frequency"],
                    med["name"],
                )

            schedule.append(
                {
                    "medication": med["name"],
                    "dosage": med["dosage"],
                    "times": times,
                    "duration": med.get("duration", "ongoing"),
                    "plain_message": (
                        f"Time to take your {med['name']} ({med['dosage']}). "
                        f"{med['frequency'].capitalize()}."
                    ),
                }
            )
        return schedule
