# Case Adapter 约定

`experiment_cases/pocs/` 下的内容不是框架主逻辑，而是把某个具体目标接入统一验证链路的适配层。

目标是让每个 case 都尽量收敛成：

- 一份 case JSON
- 少量输入生成脚本
- 少量 wrapper 脚本
- 尽量复用共享 helper

而不是每个漏洞重新发明一套执行方式。

## 1. 目录职责

每个子目录通常对应一个案例，例如：

- `tcpdump-4.9.1-cve-2018-14469/`
- `libxml2-2.9.4-cve-2017-8872/`
- `exiv2-0.26-cve-2017-17725/`

它们的职责只有一个：

**把这个目标漏洞适配到统一的 validator 与 record 管线里。**

## 2. 推荐最小组成

一个新的 case adapter，优先按下面的最小集合组织：

1. `prepare_artifacts.sh`
   - 负责准备 `artifacts/` 下需要的输入文件或 wrapper
2. `make_poc.py`（可选）
   - 当输入样本需要脚本化生成时使用
3. `run_*.sh` wrapper（可由 `prepare_artifacts.sh` 生成）
   - 负责调用真实目标程序，并把行为转成稳定 marker

不是每个 case 都必须同时有这三者，但尽量不要再额外扩出很多风格不同的入口。

## 3. 和 case JSON 的接口

adapter 不是单独运行的，它要和 `experiment_cases/*.json` 对齐。

通常会在 case JSON 里看到下面几类 validator：

1. `command`
   - 例如先调用 `prepare_artifacts.sh`
2. `artifact_exists`
   - 检查生成的 PoC 或 wrapper 是否存在
3. `artifact_exec`
   - 执行生成的 wrapper，并检查 marker
4. `asan_command`
   - 对真实二进制执行带 sanitizer 的确认

所以 adapter 的输出要尽量稳定，方便上面的 validator 直接消费。

## 4. 当前共享 helper

公共 helper 放在：

- `common/wrapper_markers.sh`

当前已经统一的内容包括：

1. `sc_emit_prepared`
   - 输出 `prepared <path>`
2. `sc_emit_wrapper_mode`
   - 输出 wrapper 当前运行模式、目标与输入
3. `sc_emit_wrapper_ok`
   - 输出稳定成功 marker
4. `sc_emit_target_rc`
   - 输出目标程序标准化返回码 marker

新增 case 时，优先复用这些 helper，而不是自己重新手写 marker 风格。

## 5. 推荐 marker 约定

为了减少 case 之间的风格漂移，建议遵守下面的约定：

1. 产物准备阶段
   - 用 `sc_emit_prepared`
2. wrapper 运行阶段
   - 先输出 `RUN_*` 类 marker，带上 target / input / mode
3. wrapper 成功阶段
   - 输出 `*_OK` 类 marker
4. 真实目标退出码
   - 用 `TARGET_EXECUTION_RC=<rc>`

这样 `artifact_exec` validator 就能尽量共享判断方式。

## 6. 什么不属于 adapter 层

下面这些不应继续塞进 adapter：

1. 通用 validator 逻辑
2. 通用结果汇总逻辑
3. 通用评分逻辑
4. skill feedback 与 gate 逻辑

这些都属于框架层，应该留在：

- `experiment_validation/`
- `experiment_scripts/`

## 7. 当前工程上的收口方向

当前已经在做的收口是：

1. 多个 case 的 `prepare_artifacts.sh` 开始复用共享 marker helper
2. Exiv2 的 wrapper smoke / probe marker 已经抽到公共 helper
3. 新 case 优先走“共享 helper + 薄 adapter”路线

后续如果继续新增 Exiv2、Binutils 等 case，也应尽量沿用这套约定。
