# Fixtures

Raw `GET /v1/calls/{id}` JSON bodies saved from real CALL-E calls, used to
replay real output against Ringback's parsing/validation logic offline —
see `../replay_fixture.py`.

Save each `get_call_run` response here as-is, named for what it demonstrates:

- `happy_path_proof_of_reg.json` — a resolvable call that completes cleanly
- `voicemail.json` / `no_answer.json` — a terminal state with no structured result
- `off_script_question.json` — the call where you asked something outside the task
- anything that surprised you — the surprise is the point of saving it

One JSON body per file, exactly as returned by the API. No editing.
