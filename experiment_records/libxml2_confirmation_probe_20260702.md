# libxml2 confirmation probe (2026-07-02)

## Goal

Check whether `libxml2-2.9.4-cve-2017-8872` can be promoted from a pure
revision-study case to a confirmation case with a deterministic crash path.

## Probe variants

### 1. Static-file `xmllint_asan` attempts

Tested several small tail patterns with:

```bash
ASAN_OPTIONS=abort_on_error=1:symbolize=1 ./.libs/xmllint_asan --html --recover <input>
```

Candidates included:

- `<!-`
- `<![-`
- `<!--`
- `<!`
- the current artifact-style input ending with `  <!-`

Observed behavior:

- parser errors were reported as expected
- no `AddressSanitizer` marker was emitted
- no crash was observed

### 2. `xmllint_asan --push --pushsmall 1`

Tested the current generated input with:

```bash
ASAN_OPTIONS=abort_on_error=1:symbolize=1 ./.libs/xmllint_asan --html --push --pushsmall 1 --recover artifacts/libxml2-cve-2017-8872-input.html
```

Observed behavior:

- parser completed with exit code `1`
- no ASan output

### 3. Custom push-parser harness linked against local `libxml2.so.2.9.4`

Built two temporary ASan harnesses:

- a direct chunked `htmlCreatePushParserCtxt/htmlParseChunk` driver
- a file-based driver that mimics `xmllint` push mode (first 4 bytes, then 1-byte chunks)

Important validation:

- the second harness was explicitly linked against:
  - `~/skillclaw-eval/libxml2-2.9.4/.libs/libxml2.so.2.9.4`
- `ldd` confirmed it used the local build rather than the system libxml2

Observed behavior:

- no ASan crash for the current candidate input
- no `htmlParseTryOrFinish`-framed sanitizer report

## Engineering conclusion

As of 2026-07-02, `libxml2-2.9.4-cve-2017-8872` should remain a
**revision-study case**, not a full confirmation case.

The current repo state supports:

- localization
- root-cause validation
- bundle-script confirmation of the weak `avail` guard

But it does **not** yet support a deterministic crash-backed confirmation
artifact comparable to the `giflib` pipeline.

## Action

- keep `artifact_exists`, `artifact_exec`, and `asan_command` disabled for this case
- only enable them after a deterministic reproducer is added
