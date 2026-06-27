---
name: cisco-wsma-enumeration
description: "Describes how to identify Cisco WSMA (webui_wsma_http) during network assessments, including why standard port scans fail to detect it and the correct HTTP/HTTPS endpoints to probe. Use when analyzing Cisco IOS/IOS-XE management plane exposure or troubleshooting why a suspected WSMA service does not appear in SYN scans. NOT for: developing or executing unauthorized exploits, or general non-Cisco web service scanning."
category: general
---

Cisco WSMA (Web Services Management Agent) is referenced as `webui_wsma_http` in configurations, but it is **not a standalone IANA-registered TCP port**. It is a SOAP/XML service that rides on the device's standard HTTP/HTTPS server.

Key facts for reconnaissance:
- **Transport**: TCP 80 and/or 443 on Cisco IOS/IOS-XE devices.
- **Endpoint path**: `/wsma` (and sometimes `/wsma/` or sub-resources).
- **Protocol**: SOAP over HTTP(S); sending a minimal SOAP envelope may elicit a fault response that confirms the endpoint.
- **Banner behavior**: The underlying web server often presents a generic Cisco IOS HTTP server banner or no distinctive banner, so the service is invisible to standard SYN scanning and generic version probes.

Enumeration procedure:
1. Probe the device on **80/TCP and 443/TCP** with HTTP GET and POST requests to `/wsma`.
2. A valid WSMA endpoint typically returns HTTP `200`, `401`, or `403` instead of `404`, and may return a SOAP fault or XML error when probed without a proper SOAP body.
3. Use targeted HTTP discovery rather than port scanning:
   - `curl -k https://<target>/wsma`
   - `curl -k https://<target>/wsma -H "Content-Type: text/xml" -d '<?xml version="1.0"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body></soap:Body></soap:Envelope>'`
4. If the device uses Management Plane Protection (MPP) or VRF-aware HTTP services, the endpoint may be reachable only from specific source addresses or interfaces even when 80/443 is open.

Why port scans miss it:
- No separate daemon port; WSMA is handled by the internal HTTP server.
- Service name strings like `webui_wsma_http` appear in configuration files (e.g., `show ip http server status`) but not in listening socket listings as a unique port.
- ACLs or control-plane policing often restrict the management URL to specific subnets, causing the port to appear closed or filtered during external scanning.

Do not assume a missing open port means WSMA is disabled; verify by sending HTTP probes directly to the `/wsma` path on the device's standard web server.
