"""
vision_agent.py
----------------
Stage 1 of the pipeline: reads a photographed prescription and extracts
structured medication data (name, dosage, frequency, instructions).

Uses Claude's vision capability via the Anthropic API. In --simulate mode
(no API key required), it returns a realistic canned extraction so the rest
of the pipeline, CLI, and demo video can run end-to-end without live
credentials.
"""

import base64
import json
import os

from .base import Agent, with_retry

EXTRACTION_PROMPT = """You are a medical prescription reading assistant.
Look at this prescription image and extract every medication listed.

Respond with ONLY valid JSON, no other text, in this exact shape:
{
  "medications": [
    {
      "name": "drug name, lowercase",
      "dosage": "e.g. 500mg",
      "frequency": "e.g. twice daily after meals",
      "duration": "e.g. 10 days, or 'ongoing' if not specified",
      "raw_instruction_text": "the instruction as written on the prescription"
    }
  ],
  "prescribing_doctor": "name if visible, else null",
  "notes": "any other relevant handwritten notes, else null"
}

If any field is unreadable, use your best clinical judgement and mark
uncertain fields with a trailing '?' rather than guessing silently.
"""

# Used only when running with --simulate / --demo, so the pipeline can be
# demoed without an Anthropic API key.
DEMO_EXTRACTION = {
    "medications": [
        {
            "name": "metformin",
            "dosage": "500mg",
            "frequency": "twice daily after meals",
            "duration": "ongoing",
            "raw_instruction_text": "Metformin 500mg BD after food",
        },
        {
            "name": "lisinopril",
            "dosage": "10mg",
            "frequency": "once daily in the morning",
            "duration": "ongoing",
            "raw_instruction_text": "Lisinopril 10mg OD morning",
        },
        {
            "name": "aspirin",
            "dosage": "75mg",
            "frequency": "once daily after breakfast",
            "duration": "ongoing",
            "raw_instruction_text": "Tab. Aspirin 75mg OD after breakfast",
        },
    ],
    "prescribing_doctor": "Dr. R. Kumar",
    "notes": "Review blood pressure in 4 weeks",
}


class PrescriptionVisionAgent(Agent):
    name = "vision_agent"

    def __init__(self, simulate: bool = False):
        super().__init__(simulate=simulate)
        self._client = None
        if not simulate:
            import anthropic  # imported lazily so --simulate never needs the package configured

            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "ANTHROPIC_API_KEY is not set. Run with --simulate for a "
                    "demo, or set the key in your .env file."
                )
            self._client = anthropic.Anthropic(api_key=api_key)

    @with_retry(max_attempts=3)
    def run(self, image_path: str) -> dict:
        if self.simulate:
            self.logger.info("SIMULATE mode: returning canned prescription extraction")
            return DEMO_EXTRACTION

        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        media_type = "image/jpeg"
        if image_path.lower().endswith(".png"):
            media_type = "image/png"

        response = self._client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {"type": "text", "text": EXTRACTION_PROMPT},
                    ],
                }
            ],
        )

        text = "".join(block.text for block in response.content if block.type == "text")
        text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(text)
