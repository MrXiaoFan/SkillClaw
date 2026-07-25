# Legacy Run Records

`legacy_runs/` 保存已经退出当前主结果集的历史运行产物。

这些内容会保留，但默认只作为**追溯材料**使用，不再参与当前工程状态判断。

## 这里归档什么

- 被后续 revision 替换的旧结果
- 早期 exploratory run
- 未进入当前主结果集的对比跑法
- 临时 confirmation / probe 目录

换句话说，这里保留的是“做过”，不是“当前采用”。

## 当前归档包

- `confirmations_archive_20260719/`
  - 2026-07-19 结构整理时，从当前运行区移出的旧运行目录集合

## 命名约定

归档目录优先使用“案例 + 语义 + 日期”命名，例如：

- `giflib-exploratory-20260627`
- `libxml2-artifact-confirmation-20260707`
- `tcpdump-direct-confirmation-20260702b`

这样即使不打开文件，也能大致看出它属于：

- exploratory 试跑
- revision 修订
- direct 对照
- probe 探测
- confirmation 确认链路

## 使用规则

看归档时请注意三点：

1. 归档中的旧文件名可能仍保留旧时代命名
2. 归档中的路径和字段不保证与当前活跃结构一致
3. 如果当前目录和归档目录冲突，以当前活跃目录为准

## 建议

只有在以下场景才去读这里：

- 需要追溯某次历史实验
- 需要解释某个结果为什么被替换
- 需要为论文补充历史对比证据

如果只是想看当前工程状态，请回到：

- `reports/current/`
- `reports/runs/confirmations/`

