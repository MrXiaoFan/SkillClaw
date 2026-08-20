@echo off
REM ============================================================
REM  safe-runner.cmd - SkillClaw ???????? (CMD)
REM
REM  *** CC Switch ???? (???????) ***
REM  ???????: ??? exec_command ?? ?/??/??,
REM  ???? CC Switch ? parsing string ?? EOF / ? $ ????
REM  ???? (??????):
REM    "Invalid function_call arguments for 'exec_command': EOF
REM     while parsing a string at line 1 column 866" / ? $ ??
REM
REM  ???? (????? exec_command):
REM    1. ??? exec_command ?? ?/??/?? PowerShell JSON;
REM    2. ????????? $ ?????/??;
REM    3. ??:  cmd /c scripts\ops\safe-runner.cmd <??> <??...>
REM    4. ??????? .py/.ps1 ??????????;
REM    5. ??????? < 200 ??, ?? JSON ??????
REM ============================================================
setlocal
set "RUNNER_DIR=%~dp0"
set "ROOT=%RUNNER_DIR%..\..\"

if "%~1"=="" goto usage
if /I "%~1"=="help"   goto usage
if /I "%~1"=="selftest" goto selftest

REM ---- ???????? scripts ???? .py / .ps1 ----
set "TARGET=%~1"
set "TARGETFULL=%ROOT%%TARGET%"
if not exist "%TARGETFULL%" (
  echo [safe-runner] NOT FOUND: %TARGETFULL%
  goto :eof
)

set "EXT=%~x1"
if /I "%EXT%"==".py" (
  echo [safe-runner] python %TARGET% %2 %3 %4 %5
  pushd "%ROOT%"
  python "%TARGETFULL%" %2 %3 %4 %5
  popd
  goto :eof
)
if /I "%EXT%"==".ps1" (
  echo [safe-runner] powershell -File %TARGET% %2 %3 %4 %5
  pushd "%ROOT%"
  powershell -NoProfile -ExecutionPolicy Bypass -File "%TARGETFULL%" %2 %3 %4 %5
  popd
  goto :eof
)
echo [safe-runner] only .py/.ps1 supported; got: %TARGET%
goto :eof

:usage
echo [safe-runner] usage:
echo   cmd /c scripts\ops\safe-runner.cmd scripts\ops\fix_setpassword_case.py
echo   cmd /c scripts\ops\safe-runner.cmd scripts\ops\fix_setpassword_case.py --apply
echo   cmd /c scripts\ops\safe-runner.cmd scripts\ops\collect_experiments.py
echo  RULE: never turn this into a long/inline PowerShell JSON line, else CC Switch still crashes.
goto :eof

:selftest
echo [safe-runner] selftest OK.
echo [safe-runner] REMEMBER: always call this tool with a SHORT line; never inline long scripts.
goto :eof
