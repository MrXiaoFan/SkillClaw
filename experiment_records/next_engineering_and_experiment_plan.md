# 下一步工程与实验计划

## 1. 当前实验面覆盖情况

截至目前，已经纳入动态验证闭环或确认链路的 case 有 5 个：

1. `giflib-5.1.2 / CVE-2016-3977`
2. `tcpdump-4.9.1 / CVE-2017-13031`
3. `tcpdump-4.9.1 / CVE-2018-14469`
4. `libxml2-2.9.4 / CVE-2017-8872`
5. `libarchive-3.8.0 / CVE-2025-60753`

## 2. 当前覆盖面的优点

现有 case 已经覆盖了几种不同确认路径：

1. **ASan 直接崩溃确认**
   - 代表：`giflib`
2. **PoC 产物 + wrapper 脚本确认**
   - 代表：`tcpdump-2017-13031`、`tcpdump-2018-14469`
3. **逻辑确认强于 sanitizer 确认**
   - 代表：`libxml2`
4. **输入/规则/执行脚本型确认**
   - 代表：`libarchive`

这说明当前框架已经不只支持一种“崩溃即确认”的单一路线。

## 3. 当前覆盖面的主要不足

虽然已经跑通 5 个 case，但从研究和工程复用角度，仍然存在三个明显问题。

### 3.1 项目分布还不均衡

目前 5 个 case 中：

- `tcpdump` 占 2 个；
- `libxml2`、`giflib`、`libarchive` 各 1 个。

这意味着当前结论仍然容易受少数项目特性影响。

### 3.2 确认路径还偏 case-specific

当前很多确认路径仍然依赖：

- case 自带 `prepare_artifacts.sh`
- case 自带 `make_poc.py`
- case 自带 wrapper 脚本

这说明框架已经能承载动态验证，但“更通用的确认模板”还没有完全沉淀出来。

### 3.3 sanitizer-confirmation 覆盖还不够强

目前：

- `giflib` 的 sanitizer 路线较强；
- `libxml2` 更偏逻辑确认；
- `tcpdump` 两个 case 更偏 artifact + output marker；
- `libarchive` 更偏输入/规则构造确认。

所以当前还不能说框架已经充分覆盖了“可稳定崩溃、可稳定 ASan 命中”的多样化项目。

## 4. 下一步实验主线

下一步不建议继续补抽象说明，而建议围绕三个方向推进。

### 4.1 方向一：继续补 confirmation case

目标：

- 让 case 数量继续增加；
- 降低当前结论对少数项目的依赖；
- 让不同漏洞类型、不同确认方式都至少有 2 个以上样本。

优先顺序建议：

1. **先补新的非 tcpdump case**
   - 避免继续把项目分布压在 tcpdump 上。
2. **优先补能稳定 ASan/UBSan 命中的 case**
   - 让动态验证闭环更“硬”。
3. **再补需要 artifact/script 逻辑确认的 case**
   - 用来验证框架对“非 crash 型确认”的泛化能力。

### 4.2 方向二：把 confirmation 模板进一步通用化

目标：

- 不再让每个 case 都像一套新的定制工程；
- 把当前已经出现的确认模式沉淀成更稳定的模板。

建议优先抽象的确认模板有：

1. **PoC 生成模板**
   - 输入：目标格式、必要字段、ground truth
   - 输出：可执行 PoC artifact
2. **wrapper 执行模板**
   - 输入：目标程序、PoC 输入、参数
   - 输出：统一 stdout/stderr/exit status
3. **sanitizer 检查模板**
   - 输入：marker、stack pattern、target frame
   - 输出：标准化 validation 结果
4. **logic-confirmation 模板**
   - 输入：期望状态、期望 marker、路径约束
   - 输出：标准化 confirmation 结果

### 4.3 方向三：把关注点逐步从“定位”推向“PoC 生成与验证”

当前工程已经表明，仅仅比较“文件/函数是否命中”是不够的。  
下一步更值得做的是：

1. agent 是否能生成可执行确认输入；
2. 生成的 artifact 是否真的能跑；
3. validation 是否能自动判断“确认成功/失败”；
4. feedback 是否能把这些结果反作用到 skill。

也就是说，接下来更强的实验问题不应只是：

- “Skill 是否帮助定位漏洞？”

而应逐步变成：

- “Skill 是否帮助 agent 生成并验证可执行确认产物？”

## 5. 下一步工程开发任务

基于上面的实验方向，建议直接落成以下工程任务。

### 任务 A：新增 2 到 3 个 confirmation case

最低目标：

1. 1 个稳定 sanitizer-confirmation case
2. 1 个稳定 artifact-confirmation case
3. 1 个非 tcpdump / 非 libxml2 项目 case

完成标准：

- case JSON 补齐
- prompt 可直接打印
- validator 可直接跑
- final record 可直接产出

### 任务 B：补一层 confirmation 模板抽象

建议优先从以下位置抽象：

- `experiment_cases/pocs/*`
- `artifact_exists / artifact_exec / asan_command`
- `prepare-confirmation-artifacts` 这一类 command validator

目标不是消灭 case 脚本，而是减少重复样板。

### 任务 C：做一次多 case 批跑

在新增 case 之后，直接使用：

- `experiment_scripts/run_case_batch.py`

跑一组统一 manifest，验证：

1. 批跑是否稳定；
2. final records 是否格式一致；
3. `refresh_curated_reports.py` 是否能直接接住新样本。

## 6. 下一步最实际的执行顺序

建议按下面这个顺序推进：

1. 先选定下一批 2 到 3 个 case；
2. 为每个 case 明确确认路径：
   - sanitizer
   - artifact
   - logic confirmation
3. 写 case JSON 和 PoC/prepare 脚本；
4. 跑单 case；
5. 接入 batch manifest；
6. 刷新最新矩阵和 feedback；
7. 再看当前 skill feedback 是否随着 case 扩展发生变化。

## 7. 当前最适合的工作重心

现阶段最值得强调的是：

**结构整改已经完成，接下来应把时间重新投到 case 扩展、confirmation 强化和 PoC/validation 产物上。**

如果继续停留在框架描述层，收益会快速下降；  
而一旦 case 数量和确认路径丰富起来，后面的工程结论和研究结论都会更站得住。
