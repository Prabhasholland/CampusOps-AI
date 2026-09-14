#!/usr/bin/env python3
"""CampusOps AI - Live CALL-E Call Dispatcher & Verification Tool.

Usage:
  # Test against mock transport (no API key needed):
  python scripts/test_live_calle.py --mock --scenario scholarship --phone "+264811234567"

  # Test against real CALL-E phone network:
  python scripts/test_live_calle.py --phone "+1XXXXXXXXXX" --scenario scholarship

  # Multi-party coordination test:
  python scripts/test_live_calle.py --mock --scenario coordination --phone "+264812345678"

  # Custom instruction call:
  python scripts/test_live_calle.py --phone "+1XXXXXXXXXX" --task "Ask the student if they can attend tomorrow's orientation."
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.calle.client import CalleClient, _RealTransport, _MockTransport
from app.calle.schemas import (
    SCHOLARSHIP_VERIFICATION_SCHEMA,
    COORDINATION_SLOT_SCHEMA,
    TRIAGE_SCHEMA,
)
from app.agents.verifier import EvidenceVerifier


# Force UTF-8 on Windows console if possible
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def print_banner():
    print("=" * 70)
    print("  CampusOps AI - CALL-E Live Phone Operations Test Suite")
    print("=" * 70)


def build_scenario_task(
    scenario: str,
    custom_task: Optional[str] = None,
    location: str = "Telangana, India",
) -> tuple[str, dict]:
    """Returns (task_prompt, json_schema) for the selected scenario."""
    location_suffix = (
        f" Location context: {location}. If asked for location, clearly state {location}."
        if location
        else ""
    )

    if custom_task:
        return custom_task + location_suffix, TRIAGE_SCHEMA

    if scenario == "scholarship":
        task = (
            "You are the CampusOps Financial Aid Agent calling the Scholarship Office on behalf of the university. "
            "Inquire about student record #220012345 (Maria Nghipandulwa). "
            "Confirm: 1) Application approval status, 2) Payment disbursement state, "
            "3) Expected payment date or timeline, and 4) Any outstanding action required from the student. "
            "Be professional, concise, and record exact dates and blocker reasons."
            + location_suffix
        )
        return task, SCHOLARSHIP_VERIFICATION_SCHEMA

    elif scenario == "coordination":
        task = (
            "You are the CampusOps Academic Operations Agent calling regarding academic advising coordination. "
            "Coordinate an academic advising meeting regarding course prerequisite waivers for Semester 2. "
            "Propose Tuesday afternoon (2:00 PM) or Wednesday morning (10:00 AM). "
            "Determine the participant's availability, confirmed slot, preferred format (in-person or virtual), "
            "and any specific agenda items."
            + location_suffix
        )
        return task, COORDINATION_SLOT_SCHEMA

    elif scenario == "coordination_faculty":
        task = (
            "You are the CampusOps Academic Operations Agent calling Dr. Johannes Alweendo (Faculty Advisor). "
            "Coordinate an advising session with student Maria Nghipandulwa. "
            "Confirm if Tuesday at 2:00 PM works for the session in FCI Room 302."
            + location_suffix
        )
        return task, COORDINATION_SLOT_SCHEMA

    else:
        task = (
            "You are the CampusOps Institutional Phone Agent. "
            "Contact the recipient, state your identity clearly, answer questions regarding campus operations, "
            "and confirm whether their operational inquiry is resolved."
            + location_suffix
        )
        return task, TRIAGE_SCHEMA


def run_call_test(
    phone: str,
    scenario: str,
    task: Optional[str] = None,
    location: str = "Telangana, India",
    mock: bool = False,
    api_key: Optional[str] = None,
    base_url: str = "https://api.heycall-e.com",
    poll_interval: float = 3.0,
    max_wait: float = 180.0,
    output_json: bool = False,
):
    print_banner()

    effective_key = api_key or os.environ.get("CALLE_API_KEY", "").strip()

    if mock or not effective_key:
        if not mock and not effective_key:
            print("\n[!] No CALLE_API_KEY detected in environment or arguments.")
            print("    Running in Deterministic Mock Mode with high-fidelity institutional scenarios.")
            print("    (To run a live phone call, pass --api-key <YOUR_KEY> or set CALLE_API_KEY in .env)\n")
        transport = _MockTransport()
        is_live = False
    else:
        print(f"\n[+] Initializing Live CALL-E Transport (Base URL: {base_url})")
        print(f"    Target Phone:    {phone}")
        print(f"    Target Location: {location}")
        transport = _RealTransport(effective_key, base_url)
        is_live = True

    task_prompt, schema = build_scenario_task(scenario, task, location=location)


    print(f"\n[1/4] Preparing Operational Task:")
    print(f"  Scenario:  {scenario}")
    print(f"  Task:      {task_prompt[:120]}..." if len(task_prompt) > 120 else f"  Task:      {task_prompt}")
    print(f"  Schema:    {list(schema.get('properties', {}).keys())}")

    # Dispatch Call
    print(f"\n[2/4] Dispatching Call via CALL-E...")
    start_time = time.time()
    try:
        run_id = transport.dispatch(
            task=task_prompt,
            phone=phone,
            result_schema=schema,
        )
    except Exception as exc:
        print(f"\n[ERROR] Failed to dispatch call: {exc}")
        if "401" in str(exc):
            print("  Check your CALLE_API_KEY for validity.")
        elif "429" in str(exc):
            print("  Rate limit reached on CALL-E API.")
        return None

    print(f"  [OK] Call Dispatched Successfully!")
    print(f"  Run ID: {run_id}")

    # Polling Loop
    print(f"\n[3/4] Polling CALL-E for Completion...", flush=True)
    call_result = None
    poll_count = 0

    while time.time() - start_time < max_wait:
        poll_count += 1
        call_result = transport.get_result(run_id)
        status = call_result.status
        elapsed = round(time.time() - start_time, 1)

        print(f"  [{elapsed:4.1f}s] Poll #{poll_count:02d}: Status -> {status}", flush=True)

        norm_status = (status or "").lower().replace(" ", "_")
        if norm_status in ["completed", "failed", "no_answer", "declined", "unknown"]:
            break


        time.sleep(poll_interval)

    total_duration = round(time.time() - start_time, 2)
    print(f"\n  Final Call Status: {call_result.status} (Duration: {total_duration}s)", flush=True)


    # Display Transcripts
    if call_result.transcript:
        print(f"\n[4/4] Call Transcript:")
        for line in call_result.transcript.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.lower().startswith("bot:") or line.lower().startswith("assistant:"):
                speaker, _, text = line.partition(":")
                print(f"  [AI Agent]:  {text.strip()}")
            elif line.lower().startswith("user:") or line.lower().startswith("recipient:"):
                speaker, _, text = line.partition(":")
                print(f"  [Recipient]: {text.strip()}")
            else:
                print(f"  {line}")
    elif call_result.summary:
        print(f"\n[4/4] Call Summary: {call_result.summary}")


    # Run Evidence Verification Engine
    print(f"\n" + "=" * 70)
    print("  Post-Call Evidence Verification Engine Analysis")
    print("=" * 70)

    verifier = EvidenceVerifier()
    if scenario == "scholarship":
        verification = verifier.verify_scholarship(call_result)
    elif scenario in ["coordination", "coordination_faculty"]:
        role = "faculty" if scenario == "coordination_faculty" else "student"
        verification = verifier.verify_coordination_step(call_result, role=role)
    else:
        verification = verifier.verify_general(call_result)

    # Verification Badge
    if verification.status == "VERIFIED":
        v_badge = "[ VERIFIED & RESOLVED ]"
    elif verification.status == "ACTION_REQUIRED":
        v_badge = "[ ACTION REQUIRED / ESCALATE ]"
    else:
        v_badge = f"[ {verification.status} ]"

    print(f"\n  Verification Status: {v_badge}")
    print(f"  Confidence Score:    {int(verification.score * 100)}%")
    print(f"  Recommended Action:  {verification.next_action}")
    print(f"  Verification Notes:  {verification.notes}")

    print(f"\n  Fact Verification Checklist:")
    for item in verification.checklist:
        check_icon = "[PASS]" if item.satisfied else "[FAIL]"
        val_str = f"({item.value})" if item.value is not None else ""
        print(f"    {check_icon:<7} {item.label:<38} {val_str:<25} {item.note}")

    if verification.missing_fields:
        print(f"\n  Missing Critical Facts: {', '.join(verification.missing_fields)}")

    print(f"\n  Structured Data Extracted:")
    print(f"  {json.dumps(call_result.structured_result or {}, indent=4)}")

    if output_json:
        print(f"\nRaw JSON Payload:")
        print(json.dumps(call_result.to_dict(), indent=2))

    print("\n" + "=" * 70)
    print("  Test Run Completed Successfully.")
    print("=" * 70 + "\n")
    return call_result



def main():
    parser = argparse.ArgumentParser(description="CampusOps AI - Live CALL-E Call & Evidence Verification")
    default_phone = os.environ.get("TARGET_PHONE", "+917671900357")
    default_location = os.environ.get("TARGET_LOCATION", "Telangana, India")

    parser.add_argument("--phone", "-p", default=default_phone, help="Target phone number in E.164 format")
    parser.add_argument("--location", "-l", default=default_location, help="Location context for the caller agent")
    parser.add_argument(
        "--scenario", "-s",
        choices=["scholarship", "coordination", "coordination_faculty", "custom", "general"],
        default="scholarship",
        help="Operational scenario to execute",
    )
    parser.add_argument("--task", "-t", default=None, help="Custom task instruction string (if scenario is custom)")
    parser.add_argument("--mock", "-m", action="store_true", help="Force deterministic mock mode")
    parser.add_argument("--api-key", "-k", default=None, help="Explicit CALL-E API key override")
    parser.add_argument("--base-url", default="https://api.heycall-e.com", help="CALL-E base URL")
    parser.add_argument("--poll-interval", type=float, default=3.0, help="Polling interval in seconds")
    parser.add_argument("--max-wait", type=float, default=180.0, help="Max wait timeout in seconds")
    parser.add_argument("--json", action="store_true", help="Output raw JSON results")

    args = parser.parse_args()
    run_call_test(
        phone=args.phone,
        scenario=args.scenario,
        task=args.task,
        location=args.location,
        mock=args.mock,
        api_key=args.api_key,
        base_url=args.base_url,
        poll_interval=args.poll_interval,
        max_wait=args.max_wait,
        output_json=args.json,
    )


if __name__ == "__main__":
    main()

