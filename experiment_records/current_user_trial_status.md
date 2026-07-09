# 当前用户试用状态

这份说明回答两个问题：

1. 现在能不能站在“Claude + SkillClaw 用户”的角度试案例
2. 试哪些案例最合适，哪些还不适合拿来判断真实效果

## 1. 结论先说

**现在已经可以试。**

但要区分两种目标：

### 1.1 如果你想试“漏洞定位效果”

现在就可以直接试。

推荐先试：

1. `tcpdump-4.9.1-cve-2018-14469`
2. `libarchive-3.8.0-cve-2025-60753`
3. `tcpdump-4.9.1-cve-2017-13031`

这几个 case 的 prompt、评分、validator、artifact 链路都已经比较完整，适合比较：

- `Claude + SkillClaw`
- `Claude + direct baseline`

在文件定位、函数定位、根因解释、证据组织上的差异。

### 1.2 如果你想试“真实动态确认效果”

现在也可以试，但成熟度不完全一样。

- `libarchive-3.8.0-cve-2025-60753`：最适合先试  
  已经是比较完整的 behavior-backed confirmation case。
- `tcpdump-4.9.1-cve-2018-14469`：可以试  
  PoC 生成和 wrapper 执行已经通了。
- `exiv2-0.26-cve-2017-17725`：**可以试工程链路，但还不适合拿来下真实漏洞确认结论**  
  当前已经具备 adapter、smoke、probe、behavior wrapper 标准化，但 PoC 仍未稳定到可宣称“真实确认完成”。

## 2. 当前最推荐的试用顺序

如果你只想以用户视角快速感受一次，我建议这样：

1. 先试 `tcpdump-4.9.1-cve-2018-14469`
   - 这是比较直观的 crafted pcap + wrapper 路线
2. 再试 `libarchive-3.8.0-cve-2025-60753`
   - 这是 behavior-backed confirmation 路线
3. 最后试 `exiv2-0.26-cve-2017-17725`
   - 这更像是在体验“新 case 接入后的工程状态”

## 3. 你现在就能用的 runbook

已经生成好的 runbook：

- `experiment_records/runbook_tcpdump_4.9.1_cve_2018_14469.md`
- `experiment_records/runbook_libarchive_3.8.0_cve_2025_60753.md`
- `experiment_records/runbook_exiv2_0.26_cve_2017_17725.md`

这三份里面已经包含：

1. 目标目录
2. 预期产物
3. build / run 命令
4. SkillClaw 组运行命令
5. direct baseline 运行命令

## 4. 从用户角度，“什么时候算 ready”

### 4.1 现在已经 ready 的部分

对用户来说，下面这些已经 ready：

1. 用 `run_eval_case.py` 跑单个 case
2. 比较 `skillclaw-inline-guarded` 和 `direct-deepseek-guarded`
3. 自动落盘 prompt、raw、score、validation、final record
4. 用 runbook 快速复现推荐命令

也就是说，**你现在已经可以开始试“Claude + SkillClaw 的使用体验和案例结果”了。**

### 4.2 还没有完全 ready 的部分

下面这些还在继续补：

1. Exiv2 的真实稳定 reproducer
2. 更多非 `tcpdump` 案例
3. 更多 ASan-backed 硬确认路径

所以如果你问的是：

“什么时候可以把这些 case 都当成成熟 benchmark 来下最终研究结论？”

答案是：**还没到。**

但如果你问的是：

“什么时候我可以真的用 Claude + SkillClaw 自己跑一遍，看它现在的效果和工程体验？”

答案就是：**现在。**
