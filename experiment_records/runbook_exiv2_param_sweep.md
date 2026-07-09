# Runbook: Exiv2 Parameter Sweep

这份 runbook 用于在远端 Exiv2 0.26 环境里执行 JP2 / ICC-profile 参数扫描，并把结果记录成统一的 JSONL 与 Markdown 总结。

## 1. 目标

目标不是一次就“证明 CVE 已稳定复现”，而是找出最可能稳定命中的参数组合，重点观察：

- `EXIV2_JP2_ICC_PATH_OK`
- `EXIV2_ASAN_OOB_OK`
- `TARGET_EXECUTION_RC=`
- `AddressSanitizer`
- `Jp2Image::readMetadata`
- `getULong`

## 2. 默认扫描计划

默认扫描矩阵已经生成在：

- `experiment_records/exiv2_param_sweep_plan.md`

当前默认组合：

- `icc_size = 4, 5, 6, 7, 8, 12`
- `colr_method = 2`
- `width = 1`
- `height = 1`

## 3. 远端准备

在远端 VM 的 Exiv2 目录中：

```bash
cd /home/li/skillclaw-eval/exiv2-0.26
test -x ./bin/exiv2 || make -j4
```

如果有 ASan 版本，优先准备：

```bash
test -x ./bin/exiv2_asan || true
```

## 4. 单次组合执行模板

下面是一组参数的标准模板：

```bash
cd /home/li/skillclaw-eval/exiv2-0.26
EXIV2_ICC_SIZE=5 EXIV2_COLR_METHOD=2 EXIV2_JP2_WIDTH=1 EXIV2_JP2_HEIGHT=1 \
  bash ../experiment_cases/pocs/exiv2-0.26-cve-2017-17725/prepare_artifacts.sh

bash artifacts/run_exiv2_poc.sh > artifacts/exiv2-sweep.stdout 2> artifacts/exiv2-sweep.stderr

python3 ../experiment_scripts/utils/record_exiv2_sweep_result.py \
  --icc-size 5 \
  --colr-method 2 \
  --width 1 \
  --height 1 \
  --stdout-file artifacts/exiv2-sweep.stdout \
  --stderr-file artifacts/exiv2-sweep.stderr \
  --returncode $? \
  --label exiv2-icc5-colr2 \
  --out ~/skillclaw-eval/runs/exiv2-sweep/exiv2_sweep_results.jsonl
```

注意：

- `record_exiv2_sweep_result.py` 应该在 `run_exiv2_poc.sh` 执行后立刻调用
- 如果 shell 里要稳妥保留退出码，建议先存到变量

更稳妥的写法：

```bash
cd /home/li/skillclaw-eval/exiv2-0.26
EXIV2_ICC_SIZE=5 EXIV2_COLR_METHOD=2 EXIV2_JP2_WIDTH=1 EXIV2_JP2_HEIGHT=1 \
  bash ../experiment_cases/pocs/exiv2-0.26-cve-2017-17725/prepare_artifacts.sh

set +e
bash artifacts/run_exiv2_poc.sh > artifacts/exiv2-sweep.stdout 2> artifacts/exiv2-sweep.stderr
RC=$?
set -e

python3 ../experiment_scripts/utils/record_exiv2_sweep_result.py \
  --icc-size 5 \
  --colr-method 2 \
  --width 1 \
  --height 1 \
  --stdout-file artifacts/exiv2-sweep.stdout \
  --stderr-file artifacts/exiv2-sweep.stderr \
  --returncode "${RC}" \
  --label exiv2-icc5-colr2 \
  --out ~/skillclaw-eval/runs/exiv2-sweep/exiv2_sweep_results.jsonl
```

## 5. 默认六组命令

推荐先跑这六组：

### 5.1 ICC size = 4

```bash
cd /home/li/skillclaw-eval/exiv2-0.26
EXIV2_ICC_SIZE=4 EXIV2_COLR_METHOD=2 EXIV2_JP2_WIDTH=1 EXIV2_JP2_HEIGHT=1 bash ../experiment_cases/pocs/exiv2-0.26-cve-2017-17725/prepare_artifacts.sh
set +e
bash artifacts/run_exiv2_poc.sh > artifacts/exiv2-sweep.stdout 2> artifacts/exiv2-sweep.stderr
RC=$?
set -e
python3 ../experiment_scripts/utils/record_exiv2_sweep_result.py --icc-size 4 --colr-method 2 --width 1 --height 1 --stdout-file artifacts/exiv2-sweep.stdout --stderr-file artifacts/exiv2-sweep.stderr --returncode "${RC}" --label exiv2-icc4-colr2 --out ~/skillclaw-eval/runs/exiv2-sweep/exiv2_sweep_results.jsonl
```

### 5.2 ICC size = 5

```bash
cd /home/li/skillclaw-eval/exiv2-0.26
EXIV2_ICC_SIZE=5 EXIV2_COLR_METHOD=2 EXIV2_JP2_WIDTH=1 EXIV2_JP2_HEIGHT=1 bash ../experiment_cases/pocs/exiv2-0.26-cve-2017-17725/prepare_artifacts.sh
set +e
bash artifacts/run_exiv2_poc.sh > artifacts/exiv2-sweep.stdout 2> artifacts/exiv2-sweep.stderr
RC=$?
set -e
python3 ../experiment_scripts/utils/record_exiv2_sweep_result.py --icc-size 5 --colr-method 2 --width 1 --height 1 --stdout-file artifacts/exiv2-sweep.stdout --stderr-file artifacts/exiv2-sweep.stderr --returncode "${RC}" --label exiv2-icc5-colr2 --out ~/skillclaw-eval/runs/exiv2-sweep/exiv2_sweep_results.jsonl
```

### 5.3 ICC size = 6

```bash
cd /home/li/skillclaw-eval/exiv2-0.26
EXIV2_ICC_SIZE=6 EXIV2_COLR_METHOD=2 EXIV2_JP2_WIDTH=1 EXIV2_JP2_HEIGHT=1 bash ../experiment_cases/pocs/exiv2-0.26-cve-2017-17725/prepare_artifacts.sh
set +e
bash artifacts/run_exiv2_poc.sh > artifacts/exiv2-sweep.stdout 2> artifacts/exiv2-sweep.stderr
RC=$?
set -e
python3 ../experiment_scripts/utils/record_exiv2_sweep_result.py --icc-size 6 --colr-method 2 --width 1 --height 1 --stdout-file artifacts/exiv2-sweep.stdout --stderr-file artifacts/exiv2-sweep.stderr --returncode "${RC}" --label exiv2-icc6-colr2 --out ~/skillclaw-eval/runs/exiv2-sweep/exiv2_sweep_results.jsonl
```

### 5.4 ICC size = 7

```bash
cd /home/li/skillclaw-eval/exiv2-0.26
EXIV2_ICC_SIZE=7 EXIV2_COLR_METHOD=2 EXIV2_JP2_WIDTH=1 EXIV2_JP2_HEIGHT=1 bash ../experiment_cases/pocs/exiv2-0.26-cve-2017-17725/prepare_artifacts.sh
set +e
bash artifacts/run_exiv2_poc.sh > artifacts/exiv2-sweep.stdout 2> artifacts/exiv2-sweep.stderr
RC=$?
set -e
python3 ../experiment_scripts/utils/record_exiv2_sweep_result.py --icc-size 7 --colr-method 2 --width 1 --height 1 --stdout-file artifacts/exiv2-sweep.stdout --stderr-file artifacts/exiv2-sweep.stderr --returncode "${RC}" --label exiv2-icc7-colr2 --out ~/skillclaw-eval/runs/exiv2-sweep/exiv2_sweep_results.jsonl
```

### 5.5 ICC size = 8

```bash
cd /home/li/skillclaw-eval/exiv2-0.26
EXIV2_ICC_SIZE=8 EXIV2_COLR_METHOD=2 EXIV2_JP2_WIDTH=1 EXIV2_JP2_HEIGHT=1 bash ../experiment_cases/pocs/exiv2-0.26-cve-2017-17725/prepare_artifacts.sh
set +e
bash artifacts/run_exiv2_poc.sh > artifacts/exiv2-sweep.stdout 2> artifacts/exiv2-sweep.stderr
RC=$?
set -e
python3 ../experiment_scripts/utils/record_exiv2_sweep_result.py --icc-size 8 --colr-method 2 --width 1 --height 1 --stdout-file artifacts/exiv2-sweep.stdout --stderr-file artifacts/exiv2-sweep.stderr --returncode "${RC}" --label exiv2-icc8-colr2 --out ~/skillclaw-eval/runs/exiv2-sweep/exiv2_sweep_results.jsonl
```

### 5.6 ICC size = 12

```bash
cd /home/li/skillclaw-eval/exiv2-0.26
EXIV2_ICC_SIZE=12 EXIV2_COLR_METHOD=2 EXIV2_JP2_WIDTH=1 EXIV2_JP2_HEIGHT=1 bash ../experiment_cases/pocs/exiv2-0.26-cve-2017-17725/prepare_artifacts.sh
set +e
bash artifacts/run_exiv2_poc.sh > artifacts/exiv2-sweep.stdout 2> artifacts/exiv2-sweep.stderr
RC=$?
set -e
python3 ../experiment_scripts/utils/record_exiv2_sweep_result.py --icc-size 12 --colr-method 2 --width 1 --height 1 --stdout-file artifacts/exiv2-sweep.stdout --stderr-file artifacts/exiv2-sweep.stderr --returncode "${RC}" --label exiv2-icc12-colr2 --out ~/skillclaw-eval/runs/exiv2-sweep/exiv2_sweep_results.jsonl
```

## 6. 扫描完成后的汇总

跑完后在远端执行：

```bash
python3 ../experiment_scripts/utils/summarize_exiv2_sweep.py \
  ~/skillclaw-eval/runs/exiv2-sweep/exiv2_sweep_results.jsonl \
  --out ~/skillclaw-eval/runs/exiv2-sweep/exiv2_sweep_summary.md
```

## 7. 当前判断规则

优先关注下面几类结果：

1. 同时命中
   - `EXIV2_JP2_ICC_PATH_OK`
   - `EXIV2_ASAN_OOB_OK`
   - `TARGET_EXECUTION_RC=`
2. 或者命中
   - `AddressSanitizer`
   - `Jp2Image::readMetadata`
   - `getULong`

如果某组参数能稳定命中这几类 marker，就可以进入下一步：

- 评估是否把 `generated-wrapper-behavior` 从禁用改成启用

## 8. 产物建议

建议至少保留下面两个文件：

- `~/skillclaw-eval/runs/exiv2-sweep/exiv2_sweep_results.jsonl`
- `~/skillclaw-eval/runs/exiv2-sweep/exiv2_sweep_summary.md`

这样后续可以直接把 sweep 结果接入实验记录或论文材料整理。
