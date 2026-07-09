#!/usr/bin/env bash

sc_emit_prepared() {
  local path="$1"
  echo "prepared ${path}"
}

sc_emit_wrapper_mode() {
  local label="$1"
  local target="$2"
  local input_path="$3"
  local mode="$4"
  echo "${label} target=${target} input=${input_path} ${mode}=1" >&2
}

sc_emit_wrapper_ok() {
  local marker="$1"
  local detail="$2"
  echo "${marker} ${detail}" >&2
}

sc_emit_target_rc() {
  local rc="$1"
  echo "TARGET_EXECUTION_RC=${rc}" >&2
}
