# 下一批 confirmation case 候选清单

## 1. 筛选原则

下一批 case 不再按“看起来有漏洞”来选，而按当前框架最缺的覆盖能力来选：

1. **优先非 `tcpdump` 项目**
   - 避免当前结论继续被 `tcpdump` 占比拖偏。
2. **优先命令行工具型项目**
   - 便于复用现有 `artifact_exists / artifact_exec / asan_command` 链路。
3. **优先 crafted file 可触发的漏洞**
   - 便于把确认链路落成：PoC 文件 + wrapper 脚本 + validator。
4. **优先可稳定 ASan/崩溃确认的类型**
   - 比纯逻辑确认更硬。

## 2. 第一优先候选：Exiv2

### 2.1 为什么优先

Exiv2 当前是最合适的下一批候选之一，原因有三点：

1. 它本身既是 C++ 库，也是**命令行工具**；
2. 多个公开 CVE 都是 **crafted image -> heap OOB / overflow**；
3. 与当前框架非常贴合，容易落成：
   - 生成恶意图片样本；
   - 调用 `exiv2` 命令行；
   - 检查 ASan / 输出 / exit status。

### 2.2 候选 CVE

#### 候选 A：CVE-2021-29457

依据：

- NVD 说明这是 Exiv2 命令行工具和库中的 heap overflow；
- 触发条件明确提到：对 crafted image 执行 metadata write 操作；
- 对命令行工具来说，需要额外参数如 `insert` 才能触发。  

来源：

- NVD: <https://nvd.nist.gov/vuln/detail/CVE-2021-29457>

适配潜力：

- **很适合做 artifact-confirmation**
- 也有机会做 **ASan-confirmation**

工程意义：

- 这是一个和当前 `giflib/tcpdump/libxml2/libarchive` 都不同的工具链模式；
- 能补一类“读写 metadata 命令行工具”的 case。

#### 候选 B：CVE-2018-17230

依据：

- NVD 说明 Exiv2 v0.26 中 `types.cpp` 存在 heap-based buffer overflow；
- 触发条件为 crafted image file。  

来源：

- NVD: <https://nvd.nist.gov/vuln/detail/CVE-2018-17230>

适配潜力：

- 更偏 **读入恶意图片 -> 命令行解析** 路线；
- 如果写路径太难稳定复现，这类读路径漏洞可能更容易先接入。

#### 候选 C：CVE-2017-17725 / CVE-2018-16336 / CVE-2017-17723

依据：

- 都是 Exiv2 0.26 周期内的 crafted image 导致 OOB read / heap over-read；
- 目标函数明确，且都属于“命令行工具解析恶意图片”的典型模式。  

来源：

- NVD: <https://nvd.nist.gov/vuln/detail/CVE-2017-17725>
- NVD: <https://nvd.nist.gov/vuln/detail/CVE-2018-16336>
- NVD: <https://nvd.nist.gov/vuln/detail/CVE-2017-17723>

适配潜力：

- 适合补 **非 tcpdump / 非 parser-state-machine** 的 OOB 读类 case；
- 也适合测试当前评分与 validator 是否会把“工具型图片解析漏洞”稳定接住。

## 3. 第二优先候选：Binutils

### 3.1 为什么列入候选

Binutils 的优点是：

1. 命令行工具丰富，例如 `objcopy`、`objdump`；
2. crafted object / ELF / binary 输入路径清晰；
3. 对“本地工具处理恶意文件”这类 confirmation 模式很贴合。  

### 3.2 候选 CVE

#### 候选 A：CVE-2025-7545

来源：

- NVD: <https://nvd.nist.gov/vuln/detail/CVE-2025-7545>

NVD 描述要点：

- `objcopy.c:copy_section`
- heap-based buffer overflow

#### 候选 B：CVE-2025-0840

来源：

- NVD: <https://nvd.nist.gov/vuln/detail/CVE-2025-0840>

NVD 描述要点：

- `objdump.c:disassemble_bytes`
- stack-based buffer overflow

### 3.3 当前保留态度

Binutils 很有吸引力，但现阶段先排在 Exiv2 后面，原因是：

1. crafted ELF / object 的最小化构造可能比 crafted image 更麻烦；
2. sanitizer 路线未必比图片工具更容易先跑通；
3. 如果先做 Exiv2，能更快补齐一个新的非 tcpdump 类 confirmation case。

## 4. 当前不建议优先的方向

### 4.1 继续补 tcpdump

原因：

- 已有 2 个 tcpdump case；
- 再补 tcpdump 对当前“项目分布不均衡”的改善有限。

### 4.2 继续深挖 libxml2 同类 case

原因：

- libxml2 当前更偏逻辑确认；
- 继续深挖会把资源投入到同一类 parser-state-machine 分析，而不是扩展确认路径类型。

### 4.3 纯 Web / 浏览器 / 大型桌面应用

原因：

- 当前框架更擅长命令行工具 + crafted input；
- 浏览器 / 桌面 GUI 的构建与确认成本太高，不适合现阶段快速扩样本。

## 5. 当前建议的执行顺序

建议按照下面顺序推进：

1. **先尝试 Exiv2**
   - 首先评估 `CVE-2021-29457`；
   - 如果写路径太不稳定，再退到 Exiv2 0.26 的读路径 OOB case。
2. **如果 Exiv2 路线顺利，再评估 Binutils**
   - 作为下一类“crafted object / binary input”案例。
3. **在新增 1 到 2 个非 tcpdump case 后，再刷新 curated runset**
   - 这样 skill feedback 的变化才更有意义。

## 6. 当前最推荐的下一步

如果只做一个最实际的动作，建议就是：

**下一批 case 先做 Exiv2。**

理由是：

1. 非 tcpdump；
2. 命令行工具；
3. crafted image 路线清楚；
4. 更贴合当前 artifact + wrapper + sanitizer 的实验框架；
5. 更容易把 case 扩展从“少数项目定制化”推进到“同类工具泛化”。
