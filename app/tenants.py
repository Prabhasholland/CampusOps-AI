import json
from functools import lru_cache
from pathlib import Path

TENANTS_ROOT = Path(__file__).resolve().parent.parent / "tenants"

# short_name is the real name ("NUST") - it's read by the reasoning model
# (app/prepare.py's prompt), a text model, not TTS, so the actual acronym is
# correct and best there. spoken_name exists separately for the one place
# that's genuinely read aloud by CALL-E: agent_intro, prepended verbatim to
# every task, never paraphrased. That field has been through three spellings
# so far - "NUST" (all-caps got spelled out letter by letter, "N. U. S.
# T."), "Nust" (mixed case fixed the spelling-out but came out "Nist",
# rhyming with "wrist"), "Nuhst" (fixed the vowel, confirmed on live NUST
# calls - then months later still came out "Noost" on a different call).
# Current spelling is "Nahst", confirmed on ElevenLabs TTS directly rather
# than assumed. If it drifts again, that's evidence for a fourth spelling,
# not a reason to revert to an earlier one that already failed differently.
# JSON has no comment syntax, hence this note living here instead.


@lru_cache
def load_tenant(tenant_id: str) -> dict:
    path = TENANTS_ROOT / f"{tenant_id}.json"
    return json.loads(path.read_text(encoding="utf-8"))
