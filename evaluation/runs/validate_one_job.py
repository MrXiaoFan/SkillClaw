import asyncio, json, logging, sys, os
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
os.chdir(r"D:\Code\SkillClaw\SkillClaw")
sys.path.insert(0, r"D:\Code\SkillClaw\SkillClaw")

from skillclaw.config_store import ConfigStore
from skillclaw.replay_gate_worker import ReplayGateWorker
from skillclaw.replay_gate_store import ReplayGateStore

JOB_ID = "20260815160333-firmware-embedded-lua-shell-extraction-5a67d3be"

async def main():
    cs = ConfigStore()
    cfg = cs.to_skillclaw_config()
    store = ReplayGateStore.from_config(cfg)
    worker = ReplayGateWorker(cfg)

    job = store.load_job(JOB_ID)
    if not job:
        print(f"Job not found: {JOB_ID}")
        sys.exit(1)

    print(f"Job: {JOB_ID}")
    print(f"Candidate: {job.get('candidate_skill_name')}")
    print(f"Action: {job.get('proposed_action')}")
    print(f"Replay cases: {len(job.get('replay_cases', []))}")
    print(f"real_rerun_enabled: {getattr(cfg, 'real_rerun_enabled', False)}")
    print(f"real_rerun_vm_host: {getattr(cfg, 'real_rerun_vm_host', '')}")
    print(f"real_rerun_skillclaw_url: {getattr(cfg, 'real_rerun_skillclaw_url', '')}")
    print()
    print("Starting validation (this may take up to 9 minutes for real_rerun)...")

    result = await worker._validate_job(job)

    print("\n=== Validation Result ===")
    print(json.dumps(result, indent=2, default=str, ensure_ascii=False))

    user_alias = cfg.sharing_user_alias or "Fan"
    store.save_result(JOB_ID, user_alias, result)
    print(f"\nResult saved as user: {user_alias}")
    print(f"Accepted: {result.get('accepted')}")
    print(f"Score: {result.get('score')}")
    print(f"Threshold: {result.get('threshold')}")

asyncio.run(main())
