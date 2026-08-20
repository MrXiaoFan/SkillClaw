import sys, os, csv, json
from collections import Counter, defaultdict
sys.stdout.reconfigure(encoding='utf-8')
ROOT = 'D:/Code/SkillClaw/SkillClaw'
out = []
def w(s=''):
    out.append(str(s))
def load_ablation(fname):
    p = os.path.join(ROOT, 'runtime', 'ablation', 'results', fname)
    with open(p, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

w('# 全部已做实验总记录（旧 + 新，含可信度标注）')
w()
w('> 生成：2026-08-20。数据来源：原始 CSV + per-run JSON + handoff。')
w('> 旧实验（ablation_results.csv）含技能泄答案作弊，已被方案 A 推翻；')
w('> 方案 A 与 F9K 族内区分为净化后的可信结果。')
w()

ablation_files = [
    ('ablation_results.csv', '旧消融（受污染基线，含作弊 oracle）'),
    ('ablation_results_rerun_model.csv', '方案A：清洁重跑（可信）'),
    ('ablation_results_f9k_distinguish_oracle.csv', 'F9K 族内区分型 oracle（可信）'),
    ('ablation_results_fh451.csv', 'FH451 五 case 对照（数据无效待排查）'),
    ('ablation_results_sanity.csv', '冒烟测试（无统计意义）'),
]
for fname, desc in ablation_files:
    rows = load_ablation(fname)
    w('## ' + fname + ' — ' + desc)
    if not rows:
        w('  (文件不存在)'); w(); continue
    w('- 总行数：%d' % len(rows))
    agg = defaultdict(lambda: [Counter(), set()])
    for r in rows:
        agg[r['condition']][0][r.get('correct','')] += 1
        agg[r['condition']][1].add(r.get('case_key',''))
    for cond,(cc,cases) in sorted(agg.items()):
        n = sum(cc.values()); yes = cc.get('YES',0)
        pct = (100.0*yes/n) if n else 0
        w('  - `%s`: n=%d YES=%d(%.1f%%) DECOY=%d NO=%d (空=%d) cases=%d' % (
            cond, n, yes, pct, cc.get('DECOY',0), cc.get('NO',0), cc.get('',0), len(cases)))
    w()
w('---')
w()
w('# 各消融 CSV 的逐 case 明细（可信的两份 + 旧基线）')
w()
detail_files = ['ablation_results.csv', 'ablation_results_rerun_model.csv', 'ablation_results_f9k_distinguish_oracle.csv']
for fname in detail_files:
    rows = load_ablation(fname)
    w('## ' + fname)
    agg = defaultdict(lambda: defaultdict(Counter))
    for r in rows:
        agg[r['condition']][r.get('case_key','')][r.get('correct','')] += 1
    for cond in sorted(agg):
        w('### 条件 ' + cond)
        for k in sorted(agg[cond]):
            w('  - ' + k + ': ' + str(dict(agg[cond][k])))
    w()
w('---')
w()
w('# 旧专项实验（非消融 CSV）')
w()
special = [
    ('reports/current/briefing_20260815/f453_run_table_20260815.csv', 'F453 16-run 三条件'),
    ('reports/current/briefing_20260805/firmware_ablation_runs.csv', 'firmware2 四条件消融 13-run'),
    ('reports/current/briefing_20260805/firmware_ablation_summary.csv', 'firmware 汇总'),
    ('reports/current/briefing_20260805/closed_loop_proof.csv', '早期闭环证明'),
    ('reports/current/briefing_20260805/core_benchmarks.csv', '核心 benchmark 清单'),
]
for rel, desc in special:
    p = os.path.join(ROOT, rel)
    w('## ' + rel + ' — ' + desc)
    if not os.path.isfile(p):
        w('  (不存在)'); w(); continue
    with open(p, encoding='utf-8-sig') as f:
        content = f.read()
    w('  - 大小 %d 字节，行数 %d' % (len(content), content.count('\n')+1))
    w('  - 前 6 行预览：')
    for ln in content.splitlines()[:6]:
        w('      | ' + ln)
    w()
w('---')
w()
w('# 最原始 per-run JSON 全量盘点（runtime/imports/remote_vm）')
w()
rv = os.path.join(ROOT, 'runtime', 'imports', 'remote_vm')
subs = {}
if os.path.isdir(rv):
    for name in os.listdir(rv):
        p = os.path.join(rv, name)
        if os.path.isdir(p):
            njson = len([f for f in os.listdir(p) if f.endswith('.json')])
            subs[name] = njson
w('- 总 runsets：%d，总 JSON：%d' % (len(subs), sum(subs.values())))
from collections import defaultdict as _dd
g = _dd(list)
for name,n in subs.items():
    for k in ['giflib','f453','f1202','f456','fh451','f9k','firmware','tcpdump','libxml','libarchive','exiv2','i12']:
        if k in name: g[k].append((name,n)); break
    else: g['other'].append((name,n))
for k,v in sorted(g.items()):
    w('  - [%s] %d runsets, %d final/score json' % (k, len(v), sum(n for _,n in v)))
w()
w('---')
w()
w('*本文档由脚本自动汇总生成，逐行数据仍以原始文件为准。*')
w()
print('\n'.join(out))
outpath = os.path.join(ROOT, 'reports', 'current', 'experiment_log_all_20260820.md')
os.makedirs(os.path.dirname(outpath), exist_ok=True)
with open(outpath, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print('WROTE', outpath, len(out), 'lines')