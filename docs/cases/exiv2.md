# Exiv2 Current

- Target: `exiv2-0.26 / CVE-2017-17725`
- Current status: the intermediate runtime confirmation path is now formally wired into the validator chain, but the case is still not promoted to a final CVE-level confirmation benchmark

## Current result

- Remote parameter sweep and ASan rebuild are working end to end.
- Generated JP2 inputs can repeatedly trigger `heap-buffer-overflow` in
  `Exiv2::Jp2Image::readMetadata()`.
- The trigger is stable across a nearby parameter interval, not just one
  isolated point.
- The `readMetadata/memcpy` runtime path is now accepted as the current
  intermediate confirmation target and has a live validator entry.

## Why it is still not final

- The current strongest stack is still a confirmed `readMetadata -> memcpy`
  over-read path.
- That is weaker than a final claim that explicitly reaches the expected
  `getULong / types.cpp` path for the named CVE.
- So the case is now **confirmed as an intermediate runtime path**, but not yet
  **final as a CVE-level benchmark claim**.

## What changed in this round

- The case no longer stops at "runnable only".
- One runtime validator for the stable `readMetadata/memcpy` path is now
  enabled.
- The case can therefore participate in the framework as a real candidate
  confirmation case, while still staying out of the formal current benchmark
  set.

## Next promotion target

To push this case from candidate to final benchmark, we still need one of two
things:

1. Recover a stable stack that explicitly reaches `getULong / src/types.cpp`
2. Or formally revise the accepted publication claim so the
   `readMetadata/memcpy` path is treated as the final target claim

## Research value

Exiv2 is currently the best example that the remote sweep / ranking /
marker-extraction pipeline is useful even before a case becomes a final
publication-grade confirmation benchmark.
