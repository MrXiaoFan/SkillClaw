---
name: cisco-iosxe-webui-rootfs-analysis
description: "Map Cisco IOS-XE WebUI architecture from an extracted firmware rootfs by locating nginx/OpenResty configs, Lua handlers, WSMA proxies, and internal endpoints. Use this for CSR1000v or similar IOS-XE images during static attack-surface analysis. NOT for: live device exploitation, ELF binary reverse engineering, or generic Linux firmware review."
category: general
---

When analyzing Cisco IOS-XE firmware WebUI components from an extracted rootfs, always verify file size with `wc -l` or `ls -la` before using the Read tool. Large Lua and nginx configuration files commonly cause timeouts; use Bash with `head`, `tail`, `sed -n 'START,ENDp'`, or `grep -n` instead.

Priority files and directories:
- `/usr/binos/conf/webui.conf` — primary nginx location blocks and aliases
- `/usr/binos/openresty/nginx/conf/nginx.conf` and `http_common.conf` — core OpenResty configuration
- `/usr/binos/openresty/nginx/conf/smgmt2.lua` — session management module (very large; never Read directly)
- `/usr/binos/openresty/nginx/conf/auth_proxy.conf` — authentication proxy configuration
- `/usr/binos/openresty/nginx/conf/pexec.lua` — process execution wrapper
- `/var/scripts/lua/features/` — backend Lua handlers (e.g., `baseHandler.lua`, `uploadFiles.lua`, `downloadFile.lua`, `loginBannerHandler.lua`, `urlMap.lua`)
- `/var/www/` and `/usr/binos/html/` — frontend web content and test pages
- `/usr/binos/bin/iosd` and `/usr/binos/bin/dmiauthd` — backend binaries; run `strings` to extract URI paths, ports, and endpoint mappings
- `/etc/init.d/` and `/etc/rc.d/` — init scripts referencing `nginx`, `wuilogin`, `dmiauthd`, or `confd`

Key architectural patterns:
- Nginx proxies to iosd via internal WSMA endpoints: `/webui_wsma_http` and `/webui_wsma_https` (proxy_pass to `192.168.1.6:$NGX_IOS_HTTP_PORT` and HTTPS variant)
- `/auth_proxy` is internal and forwards to `192.168.1.6:21111`
- `/lua5` rewrites internally to `/webui_wsma_http`
- `/polaris` aliases to `/var/wwwtest` (development/test content)
- `nginx.conf` may dynamically include `/tmp/nginx.conf`

Operational commands:
- Enumerate all Lua handlers: `ls -la /var/scripts/lua/features/*.lua`
- Extract location blocks: `grep -rn "location\|proxy_pass\|alias\|internal" /usr/binos/conf/webui.conf`
- Search for command execution sinks: `grep -rn "os\.execute\|io\.popen\|subprocess" /var/scripts/lua/features/`
- Search for CGI/FCGI handlers: `find /usr/binos/www /var/www -type f \( -name "*.cgi" -o -name "*.fcgi" \)` and `strings /usr/binos/bin/iosd | grep -iE "cgi|fcgi"`
- WSMA references are extremely verbose across the rootfs; always pipe rootfs-wide greps through `head -N` or redirect to a file to avoid output overflow.
