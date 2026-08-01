---
name: cwe120-targeted-binary-ida-scan
description: "Use when a user asks about a specific binary (e.g., /usr/bin/tcpdump) in the CWE-120 firmware triage dataset. First verify the binary's presence in /tmp/cwe120_phase1/phase2_mandatory.json and obtain its array index; if absent, report clearly that it is not in the Phase 2 mandatory list rather than assuming omission. If present, invoke ida_batch_fast.py with `-s INDEX -n 1` using that exact index. NOT for: broad batch scanning of the entire dataset or generic binary analysis outside the CWE-120 firmware triage workflow."
category: general
---

When asked to verify or analyze a **specific binary** within the CWE-120 firmware triage dataset:

1. **Check presence in the mandatory list.** Query `/tmp/cwe120_phase1/phase2_mandatory.json` for the exact path or basename:
   bash
   python3 -c "
   import json
   with open('/tmp/cwe120_phase1/phase2_mandatory.json') as f:
       data = json.load(f)
   for i, r in enumerate(data):
       if 'BINARY_NAME' in r['path']:
           print(f'Index: {i}, Path: {r[\"path\"]}, Score: {r[\"risk_score\"]}, Reasons: {r[\"phase2_reasons\"]}')
   "
   
   - If **no matches** are returned, state explicitly that the binary is **not present** in the Phase 2 mandatory list. Do not claim it was "missed" or "omitted" unless you have separate evidence.
   - If multiple matches exist, list them and ask the user to clarify.

2. **Target the correct index.** The `ida_batch_fast.py` script accepts a **start index** (`-s`) and count (`-n`), not a binary name. If the binary is present at array index `i`, invoke:
   bash
   python3 /tmp/ida_batch_fast.py /tmp/cwe120_phase1/phase2_mandatory.json -s i -n 1
   

3. **Do not create downstream tasks** (e.g., urgent IDA deep analysis, exploitability checks) for binaries that are absent from `phase2_mandatory.json`. Absence means the binary did not satisfy the Phase 2.1 entry criteria or was not identified in Phase 1.
