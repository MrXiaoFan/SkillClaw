# Confirmation Adapters

`benchmarks/confirmations/` 不是通用框架层，而是“案例接入层”。
这一层只负责一件事：把某个具体漏洞目标接到统一的验证链路里。

## 这一层应该放什么

每个子目录通常对应一个确认案例，例如：

- `giflib-5.1.2-cve-2016-3977/`
- `tcpdump-4.9.1-cve-2018-14469/`
- `libxml2-2.9.4-cve-2017-8872/`
- `exiv2-0.26-cve-2017-17725/`

每个案例目录里只保留少量“与该目标强相关”的适配文件，例如：

1. `prepare_confirmation_artifacts.sh`
   - 生成 `artifacts/` 下的输入、包装脚本或辅助文件
2. `generate_confirmation_input.py`
   - 当输入需要脚本化构造时使用
3. `run_*.sh`
   - 调用真实目标程序，并输出统一 marker

## 和 case JSON 的关系

这一层不是单独运行的，而是由 `benchmarks/cases/*.json` 调用。
常见接入点包括：

- `command`
- `artifact_exists`
- `artifact_exec`
- `asan_command`

也就是说，adapter 层负责“为某个案例补齐输入和执行方式”，
而不是重写整套验证框架。

## 当前共享 helper

- `common/confirmation_helpers.sh`

统一 marker 例如：

- `sc_emit_prepared`
- `sc_emit_wrapper_mode`
- `sc_emit_wrapper_ok`
- `sc_emit_target_rc`

新案例优先复用这些 helper，不再各写一套 marker 风格。

## 不应该继续堆进这一层的内容

下面这些属于框架层，不应继续堆到案例目录里：

- 通用 validator 逻辑
- 通用评分逻辑
- 通用结果汇总逻辑
- 技能反馈与 gate 逻辑
- 纯研究型扫描、候选排序、论文取数工具

这些应分别放在：

- `evaluation/validation/`
- `evaluation/postprocess/`
- `evaluation/reporting/`

## 当前整理原则

我们现在把这一层明确定位为：
`案例相关最小适配层`

也就是只保留“这个漏洞目标非写不可的东西”，
其余全部往通用框架里收。
