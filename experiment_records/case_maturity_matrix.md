# 当前 case 成熟度矩阵

这份表的目标不是描述漏洞细节，而是回答三个工程问题：

1. 目前有哪些 case 已经接入统一闭环
2. 每个 case 现在停在什么确认层级
3. 下一步最该补哪一类能力

## 1. 总览

| case | 目标程序 | 当前确认层级 | validator 状态 | 当前结论 |
| --- | --- | --- | --- | --- |
| `giflib-5.1.2 / CVE-2016-3977` | `gif2rgb` | artifact + ASan | 6 / 6 启用 | 已形成较完整动态确认 |
| `tcpdump-4.9.1 / CVE-2017-13031` | `tcpdump` | artifact | 5 启用，1 占位 | 已跑通 PoC 执行，ASan 路径未补 |
| `tcpdump-4.9.1 / CVE-2018-14469` | `tcpdump` | prepare + artifact | 6 启用，1 占位 | 已跑通 PoC 生成与执行，ASan 路径未补 |
| `libxml2-2.9.4 / CVE-2017-8872` | 本地 harness | logic-confirm + bundle | 8 启用，1 占位 | 已形成逻辑确认闭环，缺 ASan 硬确认 |
| `libarchive-3.8.0 / CVE-2025-60753` | `bsdtar` | behavior-backed artifact | 8 / 8 启用 | 已形成行为确认闭环 |
| `exiv2-0.26 / CVE-2017-17725` | `exiv2` | scaffold + smoke/probe | 9 启用，3 禁用 | 已接入 adapter 骨架，尚未完成真实行为确认 |

## 2. 分层解释

为避免把“跑通脚本”和“完成动态验证闭环”混为一谈，当前把 case 大致分成五层：

1. `scaffold`
   - case JSON、ground truth、prepare 脚本和最小 validator 已接入
2. `prepare + artifact`
   - 已能稳定生成输入文件和 wrapper，并通过 `artifact_exists`
3. `artifact execution`
   - 已能通过 `artifact_exec` 验证真实 wrapper 行为
4. `behavior-backed`
   - 已能用超时、返回码、输出 marker 等行为信号做确认
5. `ASan-backed`
   - 已能用 sanitizer 输出做更硬的动态确认

## 3. 各 case 当前状态

### 3.1 giflib-5.1.2 / CVE-2016-3977

- 已启用 validator：6 / 6
- 已具备：
  - `content_match`
  - `source_contains`
  - `artifact_exists`
  - `artifact_exec`
  - `asan_command`
- 当前判断：
  - 是目前最接近“完整动态确认”的 case 之一

### 3.2 tcpdump-4.9.1 / CVE-2017-13031

- 已启用 validator：5
- 占位 validator：1 个 `asan_command`
- 已具备：
  - ground truth 命中
  - pcap 生成
  - wrapper 执行
- 当前缺口：
  - 还没有补成 sanitizer-backed 路径

### 3.3 tcpdump-4.9.1 / CVE-2018-14469

- 已启用 validator：6
- 占位 validator：1 个 `asan_command`
- 已具备：
  - `prepare_artifacts`
  - pcap 存在校验
  - wrapper 执行校验
- 当前缺口：
  - 和 `2017-13031` 类似，仍缺 ASan 硬确认

### 3.4 libxml2-2.9.4 / CVE-2017-8872

- 已启用 validator：8
- 占位 validator：1 个 `asan_command`
- 已具备：
  - logic confirmation
  - bundle_script
  - 生成输入与确认脚本
- 当前判断：
  - 说明框架不仅能接“PoC 文件 -> 目标程序”路径，也能接 harness / logic-confirm 路径
- 当前缺口：
  - 缺 sanitizer-backed 路线

### 3.5 libarchive-3.8.0 / CVE-2025-60753

- 已启用 validator：8 / 8
- 已具备：
  - `prepare_artifacts`
  - 多输入产物校验
  - wrapper 执行
  - timeout / return-code 行为确认
- 当前判断：
  - 是当前最完整的 behavior-backed confirmation case

### 3.6 exiv2-0.26 / CVE-2017-17725

- 已启用 validator：9
- 禁用 validator：3
  - `generated-poc-input-executes`
  - `generated-wrapper-behavior`
  - `asan-poc-placeholder`
- 已具备：
  - case JSON 与 ground truth
  - `prepare_artifacts`
  - wrapper smoke / probe
  - 共享 marker helper
- 当前判断：
  - 已经不是空 scaffold，而是“可运行 adapter 骨架”
  - 但还不能算完成动态确认闭环
- 下一步关键点：
  - 找到可稳定触发的真实行为 marker
  - 再决定是否补 ASan 路径

## 4. 当前工程上的直接结论

### 4.1 已经证明的事

当前工程已经证明：

1. 框架能接多种确认模式  
   包括 `artifact_exec`、logic-confirm、bundle-script、behavior-backed。
2. shell adapter 不是完全散的  
   共享 helper 已经开始复用。
3. 非 `tcpdump` 目标已经不止一个  
   `giflib / libxml2 / libarchive / exiv2` 都已进入框架。

### 4.2 还不能夸大的事

当前还不能直接说：

1. 所有 case 都完成了强动态验证
2. Exiv2 已经完成真实漏洞确认
3. 当前闭环已经对任意新目标具备低成本迁移能力

这些都还需要后续补 case 和补确认强度。

## 5. 下一步最优先补什么

从成熟度矩阵看，最值得优先补的是：

1. 让 `exiv2` 从 `smoke/probe` 进入真实 behavior-backed confirmation
2. 给至少一个 `tcpdump` 或 `libxml2` case 补上 ASan 路径
3. 再新增一个非 `tcpdump` 工具型 case，例如 Exiv2 新 CVE 或 Binutils

这样工程上就能同时补：

- case 多样性
- 动态确认强度
- adapter 通用性
