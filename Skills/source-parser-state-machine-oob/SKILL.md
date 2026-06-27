---
name: source-parser-state-machine-oob
description: "Find out-of-bounds reads/writes in C/C++ parser state machines by tracing cursor/end/availability guards, lookahead reads, chunked parsing, and parser-growth macros. Use for source-level parser vulnerabilities in XML/HTML/protocol/file-format parsers such as libxml2-style cur/end/avail bugs. NOT for pure ELF dangerous-function triage, generic web vulnerabilities, or IDA-only sink enumeration."
category: vulnerability-research
---

# source-parser-state-machine-oob

## Purpose

Locate real parser boundary bugs in source code by following parser state variables, lookahead reads, and guard dominance. This skill is intended for cases where a binary or source tree contains parser code and the likely vulnerability is an out-of-bounds read/write caused by insufficient checks around `cur`, `end`, `avail`, input buffers, chunked parsing, or lookahead macros.

## CRITICAL RULES

1. Do not stop at PLT imports, `strcpy`, `strcat`, `sprintf`, or raw `memcpy` results. Treat those as coarse hints only.
2. First identify parser state variables: `cur`, `end`, `base`, `avail`, `input->cur`, `input->end`, `ctxt->input`, lexer/parser context structs, and chunked input buffers.
3. For every lookahead read such as `cur[1]`, `cur[2]`, `in->cur[3]`, `NXT(n)`, or macro-expanded pointer access, verify that a sufficient guard dominates the access.
4. A guard after the read does not protect the read. Guard dominance matters more than the existence of a nearby check.
5. Required length is usually highest accessed offset plus one. For example, `cur[3]` requires at least 4 available bytes before the access.
6. Prefer source evidence over generic binary import evidence. Use binary tools only to confirm the compiled target and reachable caller path.
7. If the finding does not match a concrete guarded/unguarded access pattern, label it uncertain instead of presenting it as confirmed.

## Workflow

### 1. Identify Parser Files And State Variables

Run broad source searches first:

```bash
grep -RIn "cur\[[0-9]\]\|in->cur\[[0-9]\]\|input->cur\[[0-9]\]\|ctxt->input\|avail <\|avail >\|end - .*cur\|GROW\|SKIP\|NEXT\|NXT\|CUR" . 2>/dev/null | head -200
```

Then narrow to parser files:

```bash
find . -type f \( -name "*parser*.c" -o -name "*parse*.c" -o -name "*lexer*.c" -o -name "*.c" \) \
  | xargs grep -l -E "cur\[[0-9]\]|input->cur|avail|end.*cur|NXT|CUR|GROW" 2>/dev/null
```

### 2. Extract Candidate Lookahead Sites

Prioritize accesses with offset 2 or higher and chunked parsing code:

```bash
grep -RIn "cur\[[2-9]\]\|in->cur\[[2-9]\]\|input->cur\[[2-9]\]\|NXT([2-9])" . 2>/dev/null
```

For each candidate, inspect at least 40 lines before and after:

```bash
sed -n '<start>,<end>p' <file>
```

Check whether there is a dominating guard before the read:

```c
avail >= N
end - cur >= N
cur + N <= end
input->end - input->cur >= N
```

### 3. libxml2-Oriented Checks

When analyzing libxml2-style trees, inspect these targets first because historical bugs often hide in parser chunking, dictionaries, and validity formatting:

```bash
grep -n "htmlParseTryOrFinish\|xmlSnprintfElementContent\|xmlDictComputeFastKey\|xmlDictAddString" HTMLparser.c valid.c dict.c 2>/dev/null
grep -n "in->cur\[2\]\|in->cur\[3\]\|avail < 4\|avail < 3\|avail < 2" HTMLparser.c 2>/dev/null
sed -n '5580,5625p' HTMLparser.c 2>/dev/null
grep -n "xmlSnprintfElementContent" valid.c 2>/dev/null
grep -n "xmlDictComputeFastKey\|xmlDictAddString" dict.c 2>/dev/null
```

If the task references libxml2 2.9.x and an OOB read, strongly compare candidates against:

- `HTMLparser.c` chunked parser lookahead and `htmlParseTryOrFinish`
- `valid.c` recursive content-model formatting
- `dict.c` dictionary key hashing / insertion

### 4. Reachability And Binary Confirmation

Confirm the analyzed binary and connect source functions to compiled symbols or callers:

```bash
file <binary>
readelf -sW <binary_or_library> | grep -E "<function>|htmlParse|xmlParse|xmlDict|xmlSnprintf"
nm -an <binary_or_library> 2>/dev/null | grep -E "<function>|htmlParse|xmlParse|xmlDict|xmlSnprintf"
objdump -t <binary_or_library> 2>/dev/null | grep -E "<function>|htmlParse|xmlParse|xmlDict|xmlSnprintf"
```

Static functions may be absent by exact name. In that case, identify exported callers such as `htmlParseChunk`, `htmlReadMemory`, `xmlReadMemory`, or library entry points used by the CLI tool.

### 5. Evidence Format

For each strong candidate, record:

```json
{
  "file": "HTMLparser.c",
  "function": "htmlParseTryOrFinish",
  "access": "in->cur[3]",
  "required_available_bytes": 4,
  "guard_before_access": "avail < 4 check before read / missing / after read",
  "attacker_control": "input HTML/XML bytes via parser buffer",
  "reachability": "xmllint -> libxml2 parser entry -> function",
  "confidence": "high|medium|low",
  "why_not_false_positive": "guard dominance and reachable input path"
}
```

## Exit Gate

Before finalizing, answer all of these:

1. What is the exact source file and function?
2. What exact read/write can cross the boundary?
3. What input controls the pointer or size?
4. How many bytes must be available before the access?
5. Is the sufficient guard before or after the access?
6. Is there a reachable parser entry point from the tested binary/library?
7. Is the claim aligned with an official advisory, patch pattern, or reproducible source-level evidence?

If any answer is missing, report the finding as a candidate, not a confirmed vulnerability.

## Do Not

- Do not invoke Claude Code local `Skill(...)`; SkillClaw skills are server-side prompt guidance.
- Do not claim success solely because dangerous functions appear in imports.
- Do not ignore source-level parser macros; expand or inspect them when they hide pointer arithmetic.
