# Exiv2 case 预选结论

## 1. 预选目标

当前目标不是立刻把 Exiv2 case 全部接完，而是先回答：

**如果下一批只先接 1 个 Exiv2 case，应该优先选哪个 CVE。**

## 2. 预选范围

这次优先比较了以下候选：

1. `CVE-2021-29457`
2. `CVE-2018-17230`
3. `CVE-2017-17725`
4. `CVE-2018-16336`

## 3. 选择标准

当前不是按漏洞严重性排序，而是按是否更适合接入现有实验框架排序。

优先标准有四个：

1. 是否是 **命令行工具直接处理 crafted file**；
2. 是否更容易形成：
   - PoC 输入
   - wrapper 脚本
   - `artifact_exec`
   - `asan_command`
3. 是否能减少额外前置条件；
4. 是否更容易形成稳定 confirmation。

## 4. 候选比较

### 4.1 `CVE-2021-29457`

来源：

- NVD: <https://nvd.nist.gov/vuln/detail/CVE-2021-29457>
- Exiv2 GitHub Security Advisory: <https://github.com/Exiv2/exiv2/security/advisories/GHSA-v74w-h496-cgqm>

公开描述要点：

- Exiv2 是命令行工具和 C++ 库；
- 漏洞是 heap overflow；
- 触发条件是：**向 crafted image 写入 metadata**。

当前判断：

- 这个 case 的优点是描述清楚，版本也较新；
- 但它的触发路径不是“直接读入恶意图片”；
- 它需要命令行进入 **write metadata** 路线。

这意味着：

1. 确认脚本要额外构造写操作命令；
2. 不只是“`./bin/exiv2 file`”这种简单模式；
3. 稳定复现门槛会更高。

结论：

- **适合作为后续第二批 Exiv2 case**
- **不适合作为第一个 Exiv2 接入样本**

### 4.2 `CVE-2018-17230`

来源：

- NVD: <https://nvd.nist.gov/vuln/detail/CVE-2018-17230>
- CVE Record: <https://www.cve.org/CVERecord?id=CVE-2018-17230>

公开描述要点：

- `Exiv2::ul2Data` in `types.cpp`
- Exiv2 `v0.26`
- heap-based buffer overflow
- 触发条件：crafted image file

当前判断：

- 这个候选已经比 `CVE-2021-29457` 更贴近当前框架；
- 因为它看起来更像“读取 crafted image 即可触发”。

问题在于：

- 公开描述里没有像 issue / advisory 一样直接给出明显的命令行触发线索；
- 当前还缺少“最小 PoC 文件和 CLI 路径”层面的直接信号。

结论：

- **是可行候选**
- 但当前作为第一优先，证据不如 `CVE-2017-17725` 直接

### 4.3 `CVE-2017-17725`

来源：

- NVD: <https://nvd.nist.gov/vuln/detail/CVE-2017-17725>
- GitHub issue #188: <https://github.com/Exiv2/exiv2/issues/188>

公开描述要点：

- Exiv2 `0.26`
- `Exiv2::getULong` in `types.cpp`
- integer overflow leading to heap-based buffer over-read
- crafted image file 可触发

额外有价值的信息：

- GitHub issue 直接提到：
  - heap-based buffer overflow in `getULong`
  - crafted TIFF file
  - 运行方式形如 `./bin/exiv2 poc_3.tiff`

这对我们特别重要，因为它意味着：

1. 触发路径很可能是**命令行直接读取恶意 TIFF**
2. 更贴合当前已有的：
   - `expected_artifacts`
   - `artifact_exists`
   - `artifact_exec`
   - `asan_command`
3. 不需要先进入 metadata write、export、rewrite 等额外分支

结论：

- **当前最适合作为第一个 Exiv2 confirmation case**

### 4.4 `CVE-2018-16336`

来源：

- NVD: <https://nvd.nist.gov/vuln/detail/CVE-2018-16336>
- Debian Tracker: <https://security-tracker.debian.org/tracker/CVE-2018-16336>

公开描述要点：

- `Exiv2::Internal::PngChunk::parseTXTChunk`
- Exiv2 `v0.26`
- heap-based buffer over-read
- crafted image file

当前判断：

- 这个候选也属于“读取 crafted image -> 解析文本块”的路径；
- 理论上也适合当前框架。

但和 `CVE-2017-17725` 相比：

1. 当前公开线索没有 `issue #188` 那样直接出现可执行命令；
2. PNG text chunk 的最小化样本构造，未必比 TIFF 更省力。

结论：

- **可以作为 Exiv2 第二梯队候选**

## 5. 当前预选结论

如果下一步只接 1 个 Exiv2 case，当前建议优先顺序是：

1. **`CVE-2017-17725`**
2. `CVE-2018-17230`
3. `CVE-2018-16336`
4. `CVE-2021-29457`

## 6. 为什么优先 `CVE-2017-17725`

核心原因只有一句话：

**它最像我们现在已经跑通的 confirmation 模式。**

也就是：

- crafted input 文件
- 命令行工具直接读取
- wrapper 脚本可控
- sanitizer 路线有希望

而不是：

- 需要进入写 metadata 的特殊命令分支；
- 需要更多前置状态或附加操作。

## 7. 下一步建议

下一步就不再继续做 Exiv2 候选讨论，而建议直接开始这三件事：

1. 选定 `CVE-2017-17725` 作为第一优先 Exiv2 case；
2. 为它起草 case JSON 结构；
3. 规划 PoC artifact 形态：
   - `artifacts/poc-cve-2017-17725.tiff`
   - `artifacts/run_exiv2_poc.sh`

如果后续发现 TIFF 路线在本地或远端构造成本过高，再退回到：

- `CVE-2018-17230`
- 或 `CVE-2018-16336`

但当前不建议先从 `CVE-2021-29457` 开始。
