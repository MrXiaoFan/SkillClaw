# 当前案例成熟度矩阵

这份文件用于说明当前基准集的成熟度，不记录某一次具体运行细节。

## 成熟度层级

- `exploratory`
  - 只有方向，链路还不稳定
- `runnable`
  - 能跑通统一 runner，但确认性证据还不够强
- `confirmed`
  - 已有稳定确认链路，可作为候选确认案例
- `current`
  - 已进入当前主 benchmark 结果集

## 分级层级

- `engineering-only`
  - 只用于工程调试
- `candidate`
  - 候选案例，暂不进入主结果集
- `current-confirmation`
  - 已进入当前确认结果集
- `publication-ready`
  - 可以直接进入论文或汇报表格

## 当前规则

- `runset_manifest.json`
  - 代表当前工程主结果集
- `publication/runset_manifest.json`
  - 代表论文候选子集

“能跑通”不等于“能作为论文主结论”。

## 当前案例状态

| case | maturity | tier | evidence | in_current | publication_ready | note |
| --- | --- | --- | --- | --- | --- | --- |
| `giflib-5.1.2 / CVE-2016-3977` | `current` | `publication-ready` | `asan-backed` | yes | yes | 当前最完整的端到端确认案例 |
| `tcpdump-4.9.1 / CVE-2017-13031` | `confirmed` | `current-confirmation` | `behavior-backed` | yes | no | 已有稳定确认链路，但动态证据仍偏弱 |
| `tcpdump-4.9.1 / CVE-2018-14469` | `confirmed` | `current-confirmation` | `behavior-backed` | yes | no | 语义型输入确认已跑通 |
| `libxml2-2.9.4 / CVE-2017-8872` | `confirmed` | `current-confirmation` | `logic-confirm` | yes | no | 逻辑确认链已成型，但强度还不够 |
| `libarchive-3.8.0 / CVE-2025-60753` | `confirmed` | `publication-ready` | `behavior-backed` | yes | yes | 当前最干净的非崩溃型确认案例 |
| `exiv2-0.26 / CVE-2017-17725` | `confirmed` | `candidate` | `intermediate-confirmed-path` | no | no | 已启用中间运行时确认路径，但仍未拿到最终 `getULong / types.cpp` 级证据 |
