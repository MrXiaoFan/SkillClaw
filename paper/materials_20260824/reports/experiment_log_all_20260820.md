# 全部已做实验总记录（旧 + 新，含可信度标注）

> 生成：2026-08-20。数据来源：原始 CSV + per-run JSON + handoff。
> 旧实验（ablation_results.csv）含技能泄答案作弊，已被方案 A 推翻；
> 方案 A 与 F9K 族内区分为净化后的可信结果。

## ablation_results.csv — 旧消融（受污染基线，含作弊 oracle）
- 总行数：159
  - `medium-skill`: n=15 YES=2(13.3%) DECOY=0 NO=4 (空=9) cases=5
  - `no-skill`: n=42 YES=1(2.4%) DECOY=18 NO=23 (空=0) cases=14
  - `oracle-skill`: n=40 YES=39(97.5%) DECOY=0 NO=0 (空=1) cases=13
  - `weak-skill`: n=40 YES=3(7.5%) DECOY=19 NO=18 (空=0) cases=14
  - `weak-skill-2`: n=22 YES=4(18.2%) DECOY=0 NO=17 (空=1) cases=7

## ablation_results_rerun_model.csv — 方案A：清洁重跑（可信）
- 总行数：84
  - `no-skill`: n=28 YES=1(3.6%) DECOY=9 NO=18 (空=0) cases=14
  - `oracle-skill`: n=28 YES=10(35.7%) DECOY=1 NO=17 (空=0) cases=14
  - `weak-skill`: n=28 YES=4(14.3%) DECOY=12 NO=12 (空=0) cases=14

## ablation_results_f9k_distinguish_oracle.csv — F9K 族内区分型 oracle（可信）
- 总行数：15
  - `oracle-skill`: n=15 YES=10(66.7%) DECOY=0 NO=5 (空=0) cases=5

## ablation_results_fh451.csv — FH451 五 case 对照（数据无效待排查）
- 总行数：60
  - `no-skill`: n=15 YES=0(0.0%) DECOY=2 NO=1 (空=12) cases=5
  - `oracle-skill`: n=15 YES=0(0.0%) DECOY=0 NO=0 (空=15) cases=5
  - `weak-skill`: n=15 YES=0(0.0%) DECOY=3 NO=0 (空=12) cases=5
  - `weak-skill-2`: n=15 YES=0(0.0%) DECOY=1 NO=2 (空=12) cases=5

## ablation_results_sanity.csv — 冒烟测试（无统计意义）
- 总行数：2
  - `no-skill`: n=1 YES=0(0.0%) DECOY=1 NO=0 (空=0) cases=1
  - `oracle-skill`: n=1 YES=0(0.0%) DECOY=0 NO=1 (空=0) cases=1

---

# 各消融 CSV 的逐 case 明细（可信的两份 + 旧基线）

## ablation_results.csv
### 条件 medium-skill
  - f9k1122-crossband-overflow: {'NO': 2, '': 1}
  - f9k1122-overflow: {'YES': 2, 'NO': 1}
  - f9k1122-setpassword-overflow: {'': 3}
  - f9k1122-setsystemsettings-overflow: {'': 3}
  - f9k1122-wlansetup-overflow: {'NO': 1, '': 2}
### 条件 no-skill
  - f1202-cmdinject: {'NO': 3}
  - f1202-credential-overflow: {'NO': 3}
  - f453-cmdinject: {'DECOY': 2, 'YES': 1}
  - f453-overflow: {'DECOY': 3}
  - f453-qossetting-overflow: {'NO': 1, 'DECOY': 2}
  - f453-routestatic-overflow: {'DECOY': 3}
  - f456-cmdinject: {'DECOY': 3}
  - f9k1122-crossband-overflow: {'NO': 3}
  - f9k1122-overflow: {'NO': 3}
  - f9k1122-setpassword-overflow: {'NO': 3}
  - f9k1122-setsystemsettings-overflow: {'NO': 3}
  - f9k1122-wlansetup-overflow: {'NO': 3}
  - fh451-formWrlExtraSet-overflow: {'DECOY': 2, 'NO': 1}
  - i12-pathtraversal: {'DECOY': 3}
### 条件 oracle-skill
  - f1202-cmdinject: {'YES': 3}
  - f1202-credential-overflow: {'YES': 3}
  - f453-cmdinject: {'YES': 3}
  - f453-overflow: {'YES': 3}
  - f453-qossetting-overflow: {'YES': 3}
  - f453-routestatic-overflow: {'YES': 3}
  - f456-cmdinject: {'YES': 3}
  - f9k1122-crossband-overflow: {'YES': 3}
  - f9k1122-overflow: {'YES': 3}
  - f9k1122-setpassword-overflow: {'': 1, 'YES': 3}
  - f9k1122-setsystemsettings-overflow: {'YES': 3}
  - f9k1122-wlansetup-overflow: {'YES': 3}
  - i12-pathtraversal: {'YES': 3}
### 条件 weak-skill
  - f1202-cmdinject: {'NO': 3}
  - f1202-credential-overflow: {'NO': 3}
  - f453-cmdinject: {'DECOY': 3}
  - f453-overflow: {'DECOY': 3}
  - f453-qossetting-overflow: {'DECOY': 3}
  - f453-routestatic-overflow: {'DECOY': 3}
  - f456-cmdinject: {'DECOY': 3}
  - f9k1122-crossband-overflow: {'NO': 3}
  - f9k1122-overflow: {'YES': 3}
  - f9k1122-setpassword-overflow: {'NO': 3}
  - f9k1122-setsystemsettings-overflow: {'NO': 3}
  - f9k1122-wlansetup-overflow: {'NO': 3}
  - fh451-formWrlExtraSet-overflow: {'DECOY': 1}
  - i12-pathtraversal: {'DECOY': 3}
### 条件 weak-skill-2
  - f1202-cmdinject: {'NO': 3}
  - f1202-credential-overflow: {'NO': 3}
  - f9k1122-crossband-overflow: {'': 1, 'NO': 3}
  - f9k1122-overflow: {'NO': 3}
  - f9k1122-setpassword-overflow: {'YES': 2, 'NO': 1}
  - f9k1122-setsystemsettings-overflow: {'YES': 2, 'NO': 1}
  - f9k1122-wlansetup-overflow: {'NO': 3}

## ablation_results_rerun_model.csv
### 条件 no-skill
  - f1202-cmdinject: {'NO': 2}
  - f1202-credential-overflow: {'NO': 2}
  - f453-cmdinject: {'DECOY': 1, 'NO': 1}
  - f453-overflow: {'NO': 2}
  - f453-qossetting-overflow: {'DECOY': 2}
  - f453-routestatic-overflow: {'NO': 1, 'DECOY': 1}
  - f456-cmdinject: {'DECOY': 2}
  - f9k1122-crossband-overflow: {'NO': 2}
  - f9k1122-overflow: {'NO': 2}
  - f9k1122-setpassword-overflow: {'NO': 2}
  - f9k1122-setsystemsettings-overflow: {'NO': 1, 'YES': 1}
  - f9k1122-wlansetup-overflow: {'NO': 2}
  - fh451-formWrlExtraSet-overflow: {'DECOY': 2}
  - i12-pathtraversal: {'DECOY': 1, 'NO': 1}
### 条件 oracle-skill
  - f1202-cmdinject: {'NO': 2}
  - f1202-credential-overflow: {'NO': 2}
  - f453-cmdinject: {'YES': 2}
  - f453-overflow: {'YES': 2}
  - f453-qossetting-overflow: {'NO': 2}
  - f453-routestatic-overflow: {'YES': 2}
  - f456-cmdinject: {'DECOY': 1, 'YES': 1}
  - f9k1122-crossband-overflow: {'NO': 2}
  - f9k1122-overflow: {'YES': 2}
  - f9k1122-setpassword-overflow: {'NO': 2}
  - f9k1122-setsystemsettings-overflow: {'NO': 2}
  - f9k1122-wlansetup-overflow: {'NO': 2}
  - fh451-formWrlExtraSet-overflow: {'NO': 1, 'YES': 1}
  - i12-pathtraversal: {'NO': 2}
### 条件 weak-skill
  - f1202-cmdinject: {'NO': 1, 'YES': 1}
  - f1202-credential-overflow: {'NO': 2}
  - f453-cmdinject: {'DECOY': 2}
  - f453-overflow: {'DECOY': 1, 'YES': 1}
  - f453-qossetting-overflow: {'DECOY': 2}
  - f453-routestatic-overflow: {'NO': 1, 'DECOY': 1}
  - f456-cmdinject: {'DECOY': 2}
  - f9k1122-crossband-overflow: {'NO': 2}
  - f9k1122-overflow: {'YES': 2}
  - f9k1122-setpassword-overflow: {'NO': 2}
  - f9k1122-setsystemsettings-overflow: {'NO': 2}
  - f9k1122-wlansetup-overflow: {'NO': 2}
  - fh451-formWrlExtraSet-overflow: {'DECOY': 2}
  - i12-pathtraversal: {'DECOY': 2}

## ablation_results_f9k_distinguish_oracle.csv
### 条件 oracle-skill
  - f9k1122-crossband-overflow: {'YES': 3}
  - f9k1122-overflow: {'YES': 3}
  - f9k1122-setpassword-overflow: {'NO': 3}
  - f9k1122-setsystemsettings-overflow: {'YES': 1, 'NO': 2}
  - f9k1122-wlansetup-overflow: {'YES': 3}

---

# 旧专项实验（非消融 CSV）

## reports/current/briefing_20260815/f453_run_table_20260815.csv — F453 16-run 三条件
  - 大小 2754 字节，行数 18
  - 前 6 行预览：
      | run_id,condition,skills,score,funcs,cves,correct,conf,fb,flags,mode,note
      | 260815,no-skill,(none),8.0,formexeCommand,CVE-2018-5767,NO,passed,positive,,inline-override,
      | 260815,force-skill,tenda-httpd-goform-execommand-triage,8.0,formexeCommand,CVE-2018-5767,NO,passed,positive,,inline-override,
      | 260815,force-skill,embedded-cgi-command-injection-triage,6.0,"TendaAte,doSystemCmd",CVE-2018-5767,partial(dsc),passed,neutral,,inline-override,
      | 260815,force-skill,embedded-cgi-command-injection-triage,0.0,,,NO,partial,neutral,,inline-override,
      | 260815,no-skill,(none),8.0,formexeCommand,CVE-2018-5767,NO,passed,positive,,inline,

## reports/current/briefing_20260805/firmware_ablation_runs.csv — firmware2 四条件消融 13-run
  - 大小 4895 字节，行数 18
  - 前 6 行预览：
      | profile,case_id,run_id,score,max_score,score_text,cve_hit,file_hit,function_hit,evidence_hit,root_cause_hit,selected_skills,feedback_decision,confirmation_status,handoff_status,receipt_status,candidates_queued,published_after_validation,validation_followup_status,final_record
      | none,firmware2-login-cgi-cve-2026-2527,firmware2-cmdi-none-20260805a,5.0,10.0,5.0/10.0,False,True,False,True,True,,neutral,passed,,,,,,runtime/imports/remote_vm/firmware2-cmdi-none-20260805a/firmware2-cmdi-none-20260805a-final-enriched.json
      | none,firmware2-login-cgi-cve-2026-2527,firmware2-cmdi-none-20260805b,3.0,10.0,3.0/10.0,False,False,False,True,True,,neutral,passed,,,,,,runtime/imports/remote_vm/firmware2-cmdi-none-20260805b/firmware2-cmdi-none-20260805b-final-enriched.json
      | none,firmware2-login-cgi-cve-2026-2527,firmware2-cmdi-none-20260805c,5.0,10.0,5.0/10.0,False,True,False,True,True,,neutral,passed,,,,,,runtime/imports/remote_vm/firmware2-cmdi-none-20260805c/firmware2-cmdi-none-20260805c-final-enriched.json
      | relevant,firmware2-login-cgi-cve-2026-2527,firmware2-cmdi-relevant-20260805a,5.0,10.0,5.0/10.0,False,True,False,True,True,embedded-cgi-command-injection-triage,neutral,passed,,,,,,runtime/imports/remote_vm/firmware2-cmdi-relevant-20260805a/firmware2-cmdi-relevant-20260805a-final-enriched.json
      | relevant,firmware2-login-cgi-cve-2026-2527,firmware2-cmdi-relevant-20260805b,5.0,10.0,5.0/10.0,False,True,False,True,True,embedded-cgi-command-injection-triage,neutral,passed,,,,,,runtime/imports/remote_vm/firmware2-cmdi-relevant-20260805b/firmware2-cmdi-relevant-20260805b-final-enriched.json

## reports/current/briefing_20260805/firmware_ablation_summary.csv — firmware 汇总
  - 大小 930 字节，行数 10
  - 前 6 行预览：
      | case_id,profile,runs,mean_score,best_score,file_hit_runs,function_hit_runs,selected_skill_set,feedback_decisions,handoff_runs,consumed_runs
      | firmware2-login-cgi-cve-2026-2527,none,3,4.333,5.0,2,0,,neutral,0,0
      | firmware2-login-cgi-cve-2026-2527,relevant,2,5.0,5.0,2,0,embedded-cgi-command-injection-triage,neutral,0,0
      | firmware2-login-cgi-cve-2026-2527,wrong,2,4.5,5.0,2,0,firmware-embedded-lua-shell-extraction,neutral,0,0
      | firmware2-login-cgi-cve-2026-2527,seed,1,5.0,5.0,1,0,embedded-cgi-command-injection-triage,neutral,1,1
      | firmware2-wireless-cgi-cve-2026-2529,none,3,2.667,3.0,0,0,,neutral,1,1

## reports/current/briefing_20260805/closed_loop_proof.csv — 早期闭环证明
  - 大小 6328 字节，行数 17
  - 前 6 行预览：
      | case_id,run_id,selected_skills,feedback_decision,handoff_status,session_id,session_segment_id,receipt_status,candidate_count,uploaded_count,candidates_queued,published_after_validation,validation_followup_status,validation_job_count,validation_decisions,final_record
      | exiv2-0.26-cve-2017-17725,exiv2-paper-20260802a,"source-parser-state-machine-oob, elf-cwe120-plt-analysis",neutral,handed_off,a77ab2b1-2e91-5d93-9a40-40c7ae6ac99f,d16e2c03-53e4-4ac5-a1c0-95559258d781,consumed,2,0,2,0,completed,2,20260802144632-elf-cwe120-plt-analysis-b2dedf3f:rejected; 20260802144739-source-parser-state-machine-oob-8ce3a6c8:rejected,runtime/imports/remote_vm/exiv2-paper-20260802a/exiv2-paper-20260802a-final-enriched.json
      | firmware2-login-cgi-cve-2026-2527,firmware2-login-cgi-cve-2026-2527-blind-skillclaw-inline-guarded-20260805-174210,embedded-cgi-command-injection-triage,negative,handed_off,3b89c3de-515d-59d6-b826-4dd7303eed43,5b4d2460-bb72-43a1-848a-146fbc104aa6,consumed,1,0,1,0,completed,1,20260805094719-embedded-cgi-command-injection-triage-0c6df379:rejected,runtime/imports/remote_vm/firmware_ablation_20260805/firmware2-login-cgi-cve-2026-2527-blind-skillclaw-inline-guarded-20260805-174210/firmware2-login-cgi-cve-2026-2527-blind-skillclaw-inline-guarded-20260805-174210-final-enriched.json
      | firmware2-login-cgi-cve-2026-2527,firmware2-login-seed-20260806a,embedded-cgi-command-injection-triage,neutral,handed_off,7dd504c3-3789-5c4b-a6d4-e74188fa881c,b1d1e89e-dd2e-4c1f-8c1a-b839e708bcf3,consumed,1,0,1,0,completed,1,20260806073000-embedded-cgi-command-injection-triage-eb4ea6ad:rejected,runtime/imports/remote_vm/firmware2-login-seed-20260806a/firmware2-login-seed-20260806a-final-enriched.json
      | firmware2-wireless-cgi-cve-2026-2529,firmware2-wireless-none-20260806a,,neutral,handed_off,a1547d05-3b54-540c-a331-83fb59c4d2bf,caa725f4-bf69-4072-90fd-2946ef539de7,consumed,0,0,0,0,not_needed,0,,runtime/imports/remote_vm/firmware2-wireless-none-20260806a/firmware2-wireless-none-20260806a-final-enriched.json
      | firmware2-wireless-cgi-cve-2026-2529,firmware2-wireless-relevant-20260806a,embedded-cgi-command-injection-triage,negative,handed_off,9037bab7-f5b6-5e40-aef9-008ece272843,7fa84da0-6468-4034-b6de-4f3985f1d61d,consumed,1,0,1,0,completed,1,20260806065640-embedded-cgi-command-injection-triage-11d23c0f:rejected,runtime/imports/remote_vm/firmware2-wireless-relevant-20260806a/firmware2-wireless-relevant-20260806a-final-enriched.json

## reports/current/briefing_20260805/core_benchmarks.csv — 核心 benchmark 清单
  - 大小 1961 字节，行数 8
  - 前 6 行预览：
      | case_id,run_id,score,max_score,score_text,cve_hit,file_hit,function_hit,evidence_hit,root_cause_hit,selected_skills,feedback_decision,confirmation_status,handoff_status,receipt_status,candidates_queued,published_after_validation,final_record
      | giflib-5.1.2-cve-2016-3977,giflib-paper-20260801a,8.0,10.0,8.0/10.0,False,True,True,True,True,"source-parser-state-machine-oob, elf-cwe120-plt-analysis",neutral,passed,handed_off,consumed,1,0,runtime/imports/remote_vm/giflib-paper-20260801a/giflib-paper-20260801a-final-enriched.json
      | libxml2-2.9.4-cve-2017-8872,libxml2-paper-20260801a,8.0,10.0,8.0/10.0,False,True,True,True,True,"source-parser-state-machine-oob, elf-cwe120-plt-analysis",neutral,passed,handed_off,consumed,2,0,runtime/imports/remote_vm/libxml2-paper-20260801a/libxml2-paper-20260801a-final-enriched.json
      | tcpdump-4.9.1-cve-2018-14469,tcpdump-paper-20260801a,2.0,10.0,2.0/10.0,False,False,False,False,True,"source-parser-state-machine-oob, elf-cwe120-plt-analysis",negative,passed,handed_off,consumed,0,0,runtime/imports/remote_vm/tcpdump-paper-20260801a/tcpdump-paper-20260801a-final-enriched.json
      | libarchive-3.8.0-cve-2025-60753,libarchive-paper-20260802a,10.0,10.0,10.0/10.0,True,True,True,True,True,elf-cwe120-plt-analysis,neutral,passed,handed_off,consumed,1,0,runtime/imports/remote_vm/libarchive-paper-20260802a/libarchive-paper-20260802a-final-enriched.json
      | tcpdump-4.9.1-cve-2017-13031,tcpdump13031-paper-20260802a,10.0,10.0,10.0/10.0,True,True,True,True,True,"source-parser-state-machine-oob, elf-cwe120-plt-analysis",positive,passed,handed_off,consumed,1,0,runtime/imports/remote_vm/tcpdump13031-paper-20260802a/tcpdump13031-paper-20260802a-final-enriched.json

---

# 最原始 per-run JSON 全量盘点（runtime/imports/remote_vm）

- 总 runsets：456，总 JSON：3138
  - [exiv2] 6 runsets, 37 final/score json
  - [f1202] 36 runsets, 252 final/score json
  - [f453] 103 runsets, 720 final/score json
  - [f456] 18 runsets, 126 final/score json
  - [f9k] 129 runsets, 903 final/score json
  - [fh451] 15 runsets, 105 final/score json
  - [firmware] 59 runsets, 405 final/score json
  - [giflib] 28 runsets, 174 final/score json
  - [i12] 41 runsets, 287 final/score json
  - [libarchive] 4 runsets, 27 final/score json
  - [libxml] 6 runsets, 38 final/score json
  - [other] 1 runsets, 0 final/score json
  - [tcpdump] 10 runsets, 64 final/score json

---

*本文档由脚本自动汇总生成，逐行数据仍以原始文件为准。*
