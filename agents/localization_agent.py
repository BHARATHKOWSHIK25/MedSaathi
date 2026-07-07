"""
localization_agent.py
------------------------
Stage 4 of the pipeline: translates plain-language reminder messages into
the patient's preferred language, using simple, respectful phrasing
appropriate for elderly readers (short sentences, no jargon).

Falls back to a small canned translation table in --simulate mode so the
pipeline runs without an API key.
"""

import os

from .base import Agent, with_retry

LOCALIZATION_PROMPT_TEMPLATE = """Translate the following medication reminder
into {language}. Use simple, warm, respectful phrasing suitable for an
elderly reader with limited literacy. Keep it to one short sentence.
Respond with ONLY the translated sentence, nothing else.

Message: "{message}"
"""

# Minimal canned translations for demo mode (Hindi and Telugu as examples).
_DEMO_TRANSLATIONS = {
    "hindi": "अपनी दवा {medication} ({dosage}) लेने का समय हो गया है।",
    "telugu": "మీ మందు {medication} ({dosage}) తీసుకోవాల్సిన సమయం అయ్యింది.",
    "english": "{medication}, {dosage} — time to take your medicine.",
}


class LocalizationAgent(Agent):
    name = "localization_agent"

    def __init__(self, simulate: bool = False):
        super().__init__(simulate=simulate)
        self._client = None
        if not simulate:
            import anthropic

            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "ANTHROPIC_API_KEY is not set. Run with --simulate for a demo."
                )
            self._client = anthropic.Anthropic(api_key=api_key)

    @with_retry(max_attempts=3)
    def run(self, schedule: list[dict], language: str) -> list[dict]:
        localized = []
        for item in schedule:
            if self.simulate:
                template = _DEMO_TRANSLATIONS.get(language.lower(), _DEMO_TRANSLATIONS["english"])
                translated = template.format(medication=item["medication"], dosage=item["dosage"])
            else:
                translated = self._translate(item["plain_message"], language)

            localized.append({**item, "localized_message": translated, "language": language})
        return localized

    def _translate(self, message: str, language: str) -> str:
        prompt = LOCALIZATION_PROMPT_TEMPLATE.format(language=language, message=message)
        response = self._client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in response.content if block.type == "text").strip()
