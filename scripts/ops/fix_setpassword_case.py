# -*- coding: utf-8 -*-
"""
Setpassword case 作废脚本 (fix_setpassword_case.py)

背景: f9k1122-webs-overflow-formSetPassword.json 是 formSetSystemSettings.json 的复制件,
     从未从真实 vul4 样本派生; 在 vul5 二进制上找 formSetPassword 这个不存在的分歧目标,
     因此其 0 命中是数据集 bug, 不能作为 skill 盲区的证据。用户已确认走"作废"路径 (A)。

CC Switch JSON 提醒:
   - 请勿把本脚本内容长内联到 exec_command; 请直接:  python scripts/ops/fix_setpassword_case.py
   - 需要看方案时:  python scripts/ops/fix_setpassword_case.py   (不带参数只打印 plan)
   - 真正生效:     python scripts/ops/fix_setpassword_case.py --apply
   - 任何使用本脚本的会话都不得改写为长/内联 PowerShell JSON 命令行,
     以免 CC Switch 在 parsing string 中途 EOF/吞 $ 导致会话中断。
"""
import json, sys, io, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

TARGET = "benchmarks/cases/f9k1122-webs-overflow-formSetPassword.json"

def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def save(p, o):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(o, f, ensure_ascii=False, indent=2)
        f.write("\n")

def main():
    ap = argparse.ArgumentParser(description="Invalidate the defective setpassword case (path A).")
    ap.add_argument("--apply", action="store_true", help="Actually write the invalidation; without it, only print a plan.")
    args = ap.parse_args()

    c = load(TARGET)
    print("case_id:", c.get("case_id"))
    print("current notes:", c.get("notes"))
    b0 = c.get("benchmark", {})
    print("current include_in_current_runs:", b0.get("include_in_current_runs"))
    print("current publication_ready:", b0.get("publication_ready"))
    print()

    if not args.apply:
        print("[plan] 未加 --apply, 仅预览. 将执行以下编辑:")
        print("  1. benchmark.publication_ready = False")
        print("  2. benchmark.include_in_current_runs = False")
        print("  3. benchmark.tier_note = 数据集复制缺陷说明")
        print("  4. notes += 作废说明")
        print("  5. confirmation.promotion_blockers += 数据集复制缺陷")
        print("  (ground_truth/validators/blind_workspace 保持原样, 以便缺陷可审计)")
        return

    note = ("| INVALIDATED (2026-08-20, path A): this case is a byte-identical copy of "
            "f9k1122-webs-overflow-formSetSystemSettings except case_id/notes; never derived from "
            "real vul4; ground_truth/validators/blind_workspace point to vul5/formSetSystemSettings. "
            "Removed from current runs and publication until re-derived from vul4.")
    c["notes"] = (c.get("notes", "").rstrip() + " " + note)

    b = c.setdefault("benchmark", {})
    b["publication_ready"] = False
    b["include_in_current_runs"] = False
    b["tier_note"] = ("DATASET COPY DEFECT (2026-08-20): duplicate of formSetSystemSettings case; "
                      "not a real formSetPassword sample; do not use for skill-ablation or paper "
                      "as a skill-blindness claim until re-derived from vul4.")

    conf = c.setdefault("confirmation", {})
    pb = conf.setdefault("promotion_blockers", [])
    tag = "DATASET COPY DEFECT (2026-08-20): duplicate of formSetSystemSettings case--not a real vul4 formSetPassword"
    if tag not in pb:
        pb.append(tag)

    save(TARGET, c)
    print("[done] invalidated:", TARGET)
    print("  include_in_current_runs -> False, publication_ready -> False")
    print("  notes / promotion_blockers updated; original fields kept for audit.")

if __name__ == "__main__":
    main()
