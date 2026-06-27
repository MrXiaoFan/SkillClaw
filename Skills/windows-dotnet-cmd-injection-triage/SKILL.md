---
name: windows-dotnet-cmd-injection-triage
description: "Triage Windows PE executables for OS command injection (CWE-78) when the target is a .NET or Mono managed assembly. Use strings-based sink discovery and available Windows tooling instead of objdump or native-disassembly workflows that are ineffective on CLR binaries. NOT for: native x86/x64 PE without CLR metadata, Linux ELF analysis, or dynamic instrumentation."
category: general
---

- **Identify binary type first**: Run `file <target.exe>`. If output contains `.Net assembly` or `Mono`, stop attempting objdump or native RE toolchains as the primary analysis path.
- **Managed CWE-78 sinks**: In .NET/Mono, OS command injection flows through `System.Diagnostics.Process.Start()` or `ProcessStartInfo` objects. Search IL/metadata for:
  - `System.Diagnostics.Process::Start`
  - `ProcessStartInfo::.ctor`
  - `ProcessStartInfo::set_FileName` / `set_Arguments` / `set_UseShellExecute`
  - Shell intermediaries: `cmd.exe`, `powershell.exe`, `bash.exe`
- **Tool-fallback reconnaissance** (when objdump/dnSpy/ILSpy are unavailable):
  - `strings -n 12 <target.exe> | grep -iE "process\.start|startinfo|cmd\.exe|powershell|arguments|filename"`
  - `dumpbin /imports <target.exe>` if MSVC tools are present
  - Python triage: `python -c "import pefile; pe = pefile.PE('<target.exe>'); print(pe.dump_info())"` or parse the CLR directory for method names
  - If IDA is available: search for string references to shell commands and trace to CLR method call sites
- **Analysis pivot**: Managed command injection usually involves string concatenation into `ProcessStartInfo.Arguments` (via `String.Concat`, `String.Format`, or `+`). Focus taint analysis on the Arguments property rather than direct system calls.
- **Environment note**: On Windows Git Bash/MinGW shells, `objdump` is often missing. Do not loop on package manager installation; immediately fallback to `strings`, `dumpbin`, or Python-based inspection.
