## Ablation Profiles

This directory contains minimal skill subsets used for controlled benchmark runs.

- `cgi_cmdi_seed_dispatch/`
  - only a weak seed version of the embedded CGI command-injection triage skill
  - used to test whether evolve can improve a branch-first firmware workflow
- `cgi_cmdi_relevant/`
  - only the embedded CGI command-injection triage skill
- `cgi_cmdi_wrong_firmware_lua/`
  - a firmware-related but task-mismatched Lua-extraction skill
- `cgi_cmdi_none/`
  - intentionally empty profile for no-skill runs

For controlled local ablations, copy one profile into `skillspace/live/` and let SkillClaw
refresh from the live directory. Do not use the internal reload endpoint for ablation
switching because it can repopulate `live/` from shared state.
