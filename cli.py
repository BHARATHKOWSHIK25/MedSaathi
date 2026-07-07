#!/usr/bin/env python3
"""
cli.py
-------
Command-line interface for MedSaathi (course concept: Agent skills / CLI).

Usage examples:

    # Full demo, no API keys required:
    python cli.py --demo

    # Real run with a photographed prescription:
    python cli.py --image ./prescription.jpg \\
        --patient-name "Lakshmi Devi" \\
        --phone +919876543210 \\
        --existing-meds "amlodipine,levothyroxine" \\
        --language telugu \\
        --consent

    # Force simulate mode even with a real image (no API calls made):
    python cli.py --image ./prescription.jpg --simulate --consent
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv

from agents.orchestrator import MedSaathiOrchestrator

load_dotenv()

DEMO_IMAGE_PLACEHOLDER = "demo_prescription.jpg"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="MedSaathi - AI medication companion for elderly & rural patients."
    )
    parser.add_argument("--image", type=str, help="Path to the prescription photo.")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run a full canned demo end-to-end with no API keys or image required.",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Force simulate mode (no live API calls) even if --image is provided.",
    )
    parser.add_argument("--patient-name", type=str, default="Demo Patient")
    parser.add_argument("--phone", type=str, default="+910000000000")
    parser.add_argument(
        "--existing-meds",
        type=str,
        default="",
        help="Comma-separated list of medications the patient already takes.",
    )
    parser.add_argument("--language", type=str, default="hindi")
    parser.add_argument(
        "--consent",
        action="store_true",
        help="Confirms patient/family consent to store medication data. Required to proceed.",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    simulate = args.simulate or args.demo
    image_path = args.image or DEMO_IMAGE_PLACEHOLDER

    if args.demo:
        print("=" * 60)
        print("MedSaathi DEMO MODE - no API keys required")
        print("=" * 60)
        args.patient_name = args.patient_name or "Lakshmi Devi"
        args.existing_meds = args.existing_meds or "amlodipine,levothyroxine"
        args.consent = True

    if not args.consent:
        print(
            "🛑 Consent is required to run this pipeline. Re-run with --consent "
            "once patient/family consent has been recorded.",
            file=sys.stderr,
        )
        sys.exit(1)

    existing_meds = [m.strip() for m in args.existing_meds.split(",") if m.strip()]

    orchestrator = MedSaathiOrchestrator(simulate=simulate)
    result = orchestrator.run(
        image_path=image_path,
        patient_name=args.patient_name,
        phone=args.phone,
        existing_medications=existing_meds,
        language=args.language,
        consent_given=args.consent,
    )

    print("\n" + "=" * 60)
    print(f"Pipeline finished with status: {result['status']}")
    print("=" * 60)

    os.makedirs("output", exist_ok=True)
    with open("output/last_run_result.json", "w") as f:
        json.dump(result, f, indent=2)
    print("Full result written to output/last_run_result.json")


if __name__ == "__main__":
    main()
