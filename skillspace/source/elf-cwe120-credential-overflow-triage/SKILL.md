---
name: elf-cwe120-credential-overflow-triage
description: "Use when triaging extracted Linux firmware ELF binaries for CWE-120 buffer-overflow weaknesses specifically in credential and password handling functions. Focuses on functions that process user-supplied passwords, base64-decoded credentials, or authentication parameters which may flow into unsafe strcpy/sprintf sinks. Helps identify high-value targets in web interface binaries where credential parameters like sysPasswd, http_passwd, http_user are handled. NOT for: general CWE-120 triage of non-credential functions (use elf-cwe120-firmware-triage), CGI command injection, Windows PE analysis, or source-code audits."
category: general
---

When triaging extracted firmware/rootfs ELF binaries for CWE-120 (buffer overflow), prioritize credential and password handling functions as high-value attack surface.

1. **Identify credential-handling functions first**
   Before broad scanning, search for functions that process authentication-related parameters:
   \   strings -t x <binary> | grep -iE "passwd|password|http_passwd|http_user|sysPasswd|base64decode|credential|login|auth"
   \   Functions that call websGetVar with credential parameter names are prime candidates - they handle sensitive user-controlled input that may reach unsafe sinks without proper bounds checking.

2. **Trace credential data flow to sinks**
   Credential parameters are often processed through base64decode or direct websGetVar calls before being copied into fixed-size buffers. Focus on:
   - **High signal**: Functions where base64decode output or websGetVar result flows into strcpy, strcat, or sprintf without length validation
   - **Medium signal**: Functions that call apmib_set with credential data - the MIB database write may use unsafe copies internally
   - **Lower signal**: Functions that only call strcmp on credentials (these are comparison, not copy operations)

3. **Prioritize web form handlers with credential parameters**
   In embedded web servers (webs, httpd), form handler functions that process passwords or user credentials are high-value targets because:
   - They accept multiple user-controlled parameters via websGetVar
   - They often use strcpy to copy parameters into stack buffers for error messages or redirect URLs
   - Error handling paths may use sprintf with unvalidated input
   - Credential processing functions tend to handle multiple parameters, increasing the attack surface

4. **Quick triage approach**
   After identifying credential-handling functions:
   \   # Find functions referencing credential strings
   objdump -d <binary> | grep -B5 -A20 "formSet.*Pass|formSet.*Password|formSet.*System|formLogin"
   
   # Check for base64decode + strcpy patterns
   strings <binary> | grep -i "base64|passwd|password"
   \   Focus disassembly analysis on functions where credential parameters flow into strcpy calls, particularly in error-handling or redirect paths where user input is copied without bounds checking.

5. **Filter out benign credential operations**
   Not all credential handling is vulnerable. Treat as lower priority:
   - Functions that only strcmp credentials (comparison, not copy)
   - Functions where credential data is passed to apmib_set with proper length validation
   - Functions that only read credentials for display purposes without copying into fixed-size buffers
   Escalate only functions where credential-adjacent parameters flow into raw strcpy/sprintf calls without bounds checking.
