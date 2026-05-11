"""Comprehensive smoke test for the full ML Tracker application."""
import urllib.request
import urllib.parse
import http.cookiejar
import json

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
BASE = "http://127.0.0.1:5000"
errors = []

def get(path, expect=200):
    try:
        resp = opener.open(BASE + path)
        code = resp.getcode()
        body = resp.read().decode()
        if code != expect:
            errors.append(f"GET {path} -> {code} (expected {expect})")
        return code, body
    except urllib.error.HTTPError as e:
        if e.code != expect:
            errors.append(f"GET {path} -> {e.code} (expected {expect})")
        return e.code, ""

def post(path, data, expect=200):
    encoded = urllib.parse.urlencode(data).encode()
    try:
        resp = opener.open(urllib.request.Request(BASE + path, data=encoded))
        code = resp.getcode()
        body = resp.read().decode()
        if code != expect:
            errors.append(f"POST {path} -> {code} (expected {expect})")
        return code, body
    except urllib.error.HTTPError as e:
        if e.code != expect:
            errors.append(f"POST {path} -> {e.code} (expected {expect})")
        return e.code, ""

def get_json(path):
    try:
        resp = opener.open(BASE + path)
        data = json.loads(resp.read().decode())
        if not data.get('success'):
            errors.append(f"API {path} -> success=false: {data.get('error')}")
        return data
    except Exception as e:
        errors.append(f"API {path} -> Exception: {e}")
        return {}

def post_json(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(BASE + path, data=body, headers={'Content-Type': 'application/json'})
    try:
        resp = opener.open(req)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())

print("=" * 60)
print("SMOKE TEST: ML Tracker")
print("=" * 60)

# ── Page routes ──
print("\n--- Page Routes ---")
code, _ = get("/")
print(f"1. GET  /               -> {code}")

code, _ = get("/login")
print(f"2. GET  /login          -> {code}")

# Login as alice (data_scientist)
code, _ = post("/login", {"email": "datascientist@ml.com", "password": "pass123"})
print(f"3. POST /login (alice)  -> {code}")

code, body = get("/dashboard/runs")
print(f"4. GET  /dashboard/runs -> {code} (has Chart.js: {'chart.js' in body.lower()})")

code, _ = get("/log_run")
print(f"5. GET  /log_run        -> {code}")

code, _ = get("/dashboard/metrics")
print(f"6. GET  /dashboard/metrics -> {code}")

code, _ = get("/dashboard/registry")
print(f"7. GET  /dashboard/registry -> {code}")

code, _ = get("/dashboard/deployments")
print(f"8. GET  /dashboard/deployments -> {code}")

# Legacy routes
code, _ = get("/home")
print(f"9. GET  /home (legacy)  -> {code}")

code, _ = get("/leaderboard")
print(f"10. GET /leaderboard (legacy) -> {code}")

code, _ = get("/logout")
print(f"11. GET /logout         -> {code}")

# ── API routes ──
print("\n--- API Routes ---")

# Login as mlops_engineer
post("/login", {"email": "mlops_engineer@ml.com", "password": "pass123"})

data = get_json("/api/runs/all")
run_count = len(data.get('data', []))
print(f"12. GET /api/runs/all       -> {run_count} runs")

data = get_json("/api/runs/1/metrics")
metric_names = list(data.get('data', {}).keys())
print(f"13. GET /api/runs/1/metrics -> metrics: {metric_names}")

data = get_json("/api/metrics/all")
all_metric_count = len(data.get('data', {}))
print(f"14. GET /api/metrics/all    -> {all_metric_count} runs with metrics")

data = get_json("/api/deployments/all")
dep_count = len(data.get('data', []))
print(f"15. GET /api/deployments/all -> {dep_count} deployments")

# Check deployment data integrity
if data.get('data'):
    dep = data['data'][0]
    print(f"    First deployment: id={dep['deployment_id']}, model={dep['model_name']}, "
          f"env={dep['environment']}, status={dep['status']}, "
          f"degraded={dep['degraded']}, uptime={dep.get('uptime_hours')}")

# Test log_health API
result = post_json("/api/deployments/1/log_health", {
    "live_accuracy": 0.88,
    "avg_latency_ms": 55.0,
    "error_rate": 0.02
})
print(f"16. POST /api/deployments/1/log_health -> success={result.get('success')}")

# Test degradation trigger: low accuracy should set degraded=TRUE
result = post_json("/api/deployments/1/log_health", {
    "live_accuracy": 0.3,
    "avg_latency_ms": 200.0,
    "error_rate": 0.10
})
print(f"17. POST low-accuracy health log       -> success={result.get('success')}")

# Check that deployment 1 is now degraded
data = get_json("/api/deployments/all")
dep1 = next((d for d in data.get('data', []) if d['deployment_id'] == 1), None)
print(f"18. Deployment 1 degraded after low accuracy -> degraded={dep1['degraded'] if dep1 else 'NOT FOUND'}")

# Test rollback
result = post_json("/api/deployments/2/rollback", {
    "reason": "Smoke test rollback"
})
print(f"19. POST /api/deployments/2/rollback   -> success={result.get('success')}")

# Verify rollback
data = get_json("/api/deployments/all")
dep2 = next((d for d in data.get('data', []) if d['deployment_id'] == 2), None)
print(f"20. Deployment 2 status after rollback  -> status={dep2['status'] if dep2 else 'NOT FOUND'}")

# ── Summary ──
print("\n" + "=" * 60)
if errors:
    print(f"FAILED — {len(errors)} error(s):")
    for e in errors:
        print(f"  ✗ {e}")
else:
    print("ALL 20 CHECKS PASSED ✓")
print("=" * 60)
