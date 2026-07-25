# 下一批 confirmation case 候选清单

## 1. 筛选原则

下一批 case 不再按“看起来像有漏洞”来选，而是按当前框架最缺的覆盖能力来选：

1. 优先非 `tcpdump` 项目  
   避免当前结论继续被 `tcpdump` 占比拉偏。
2. 优先命令行工具型目标  
   便于复用现有 `artifact_exists / artifact_exec / asan_command` 链路。
3. 优先 crafted file 可触发的漏洞  
   便于把确认链路落成：PoC 文件 + wrapper 脚本 + validator。
4. 优先可稳定用 ASan 或明确行为标记确认的类型  
   比纯逻辑确认更硬。

## 2. 第一优先候选：Exiv2

### 2.1 为什么优先

Exiv2 当前是最适合作为下一批 case 的目标之一，原因有三点：

1. 它既是 C++ 项目，也是命令行工具。
2. 多个公开 CVE 都是 crafted image 导致的 OOB / overflow。
3. 它和当前框架很贴合，容易落成：
   - 生成恶意图片样本
   - 调用 `exiv2` 命令行
   - 检查 ASan、输出和退出状态

### 2.2 候选 CVE

#### 候选 A：CVE-2021-29457

依据：

- NVD 描述为 Exiv2 命令行工具和库中的 heap overflow
- 触发条件明确提到对 crafted image 执行 metadata write 操作
- 对命令行工具来说，这类场景有机会做成 `artifact-confirmation`

意义：

- 能补一个不同于 `giflib / tcpdump / libxml2 / libarchive` 的工具链模式
- 更接近“读写 metadata 的命令行工具”这一类 confirmation case

#### 候选 B：CVE-2018-17230

依据：

- NVD 提到 Exiv2 0.26 的 `types.cpp` 存在 heap-based buffer overflow
- 触发条件是 crafted image file

意义：

- 更偏“读取恶意图片 -> 命令行解析”的路径
- 如果 write 路径太难稳定复现，read 路径可能更适合先接入

#### 候选 C：CVE-2017-17725 / CVE-2018-16336 / CVE-2017-17723

依据：

- 都属于 Exiv2 0.26 周期内 crafted image 导致的 OOB read / heap over-read
- 目标函数较明确，且都属于“命令行工具解析恶意图片”的典型模式

意义：

- 适合补“非 tcpdump、非 parser-state-machine”的 OOB 读类 case
- 也适合检验当前 validator 是否能稳定接住这类工具型图片解析漏洞

## 3. 第二优先候选：Binutils

### 3.1 为什么列入候选

Binutils 的优点是：

1. 命令行工具丰富，例如 `objcopy`、`objdump`
2. crafted object / ELF / binary 输入路径清晰
3. 很适合“本地工具处理恶意文件”的 confirmation 模式

### 3.2 候选 CVE

#### 候选 A：CVE-2025-7545

关注点：

- `objcopy.c:copy_section`
- heap-based buffer overflow

#### 候选 B：CVE-2025-0840

关注点：

- `objdump.c:disassemble_bytes`
- stack-based buffer overflow

### 3.3 当前保留态度

Binutils 很有吸引力，但现阶段排在 Exiv2 后面，原因是：

1. crafted ELF / object 的最小化构造通常比 crafted image 更麻烦
2. sanitizer 路线未必比图片工具更容易先跑通
3. 先补 Exiv2 能更快增加一个新的非 `tcpdump` confirmation case

## 4. 当前不建议优先的方向

### 4.1 继续补 tcpdump

原因：

- 已经有 2 个 `tcpdump` case
- 再补 `tcpdump` 对“目标分布不均衡”的改善有限

### 4.2 继续深挖 libxml2 同类 case

原因：

- 当前 `libxml2` 更偏逻辑确认
- 再投入资源容易继续停留在同一类 parser-state-machine 路线

### 4.3 纯 Web / 浏览器 / 大型桌面应用

原因：

- 当前框架更适合命令行工具 + crafted input
- GUI 目标的构建、驱动和确认成本更高

## 5. 建议执行顺序

建议按下面顺序推进：

1. 先做 Exiv2  
   优先评估 `CVE-2021-29457`；如果写路径不稳定，再退到 Exiv2 0.26 的读路径 OOB case。
2. 如果 Exiv2 进展顺利，再评估 Binutils  
   作为下一类“crafted object / binary input”案例。
3. 在新增 1 到 2 个非 `tcpdump` case 后，再刷新 current runset  
   这样 skill feedback 的变化才更有解释力。

## 6. 当前最推荐的下一步

如果只做一个最实际的动作，建议就是：

**下一批 case 先做 Exiv2。**

理由是：

1. 非 `tcpdump`
2. 命令行工具
3. crafted image 路线清晰
4. 更贴合当前 `artifact + wrapper + sanitizer` 的实验框架
5. 更容易把 case 扩展从“少数项目定制化”推进到“同类工具泛化”

