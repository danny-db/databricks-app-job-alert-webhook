"""
alert-receiver: a Databricks App that receives Databricks job alerts over an OAuth webhook destination.

How the call is authenticated (nothing to code for it here):
  1. Databricks gets an M2M token for the caller service principal from <workspace>/oidc/v1/token.
  2. It POSTs the alert to <app-url>/alert with "Authorization: Bearer <token>".
  3. The Databricks Apps proxy validates the token and checks the SP has CAN_USE on this app,
     then forwards the request with X-Forwarded-Email = the caller's identity (the SP's application ID).
This app adds one more check: only the expected service principal may post alerts.
"""
import datetime as dt
import html
import json
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

app = FastAPI(title="alert-receiver")

ALLOWED_CALLERS = {c.strip() for c in os.getenv("ALLOWED_ALERT_CALLERS", "").split(",") if c.strip()}
HOST = os.getenv("DATABRICKS_HOST", "")            # set by Databricks Apps; used to build run links
if HOST and not HOST.startswith("http"):
    HOST = f"https://{HOST}"
ALERTS: list[dict] = []                            # demo only: in-memory, resets on restart (use Lakebase or a Delta table in production)


@app.post("/alert")
async def receive_alert(request: Request):
    caller = request.headers.get("x-forwarded-email", "")
    if ALLOWED_CALLERS and caller not in ALLOWED_CALLERS:
        raise HTTPException(status_code=403, detail="caller is not an allowed alert sender")

    payload = await request.json()
    job, run = payload.get("job", {}), payload.get("run", {})
    alert = {
        "received_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "event_type": payload.get("event_type"),
        "job_id": job.get("job_id"),
        "job_name": job.get("name"),
        "run_id": run.get("run_id"),
        "run_url": f"{HOST}/jobs/{job.get('job_id')}/runs/{run.get('run_id')}" if HOST and run.get("run_id") else None,
        "caller": caller,
        "payload": payload,
    }
    ALERTS.append(alert)
    print("ALERT", json.dumps(alert), flush=True)  # visible in the app's Logs tab

    # >>> Put your alert handling here: route to on-call, open a ticket, write to a table, call an LLM to triage, ...
    return {"ok": True}


@app.get("/api/alerts")
def list_alerts():
    return list(reversed(ALERTS[-50:]))


EVENT_COLOUR = {"jobs.on_failure": "#FF3621", "jobs.on_success": "#00A972", "jobs.on_start": "#2272B4"}


def _row(a: dict) -> str:
    esc = lambda v: html.escape(str(v))           # job names are user-set: always escape
    run = f'<a href="{esc(a["run_url"])}" target="_blank">{esc(a["run_id"])}</a>' if a["run_url"] else esc(a["run_id"])
    colour = EVENT_COLOUR.get(a["event_type"], "#1B3139")
    return (f"<tr><td>{esc(a['received_at'])}</td>"
            f"<td><b style='color:{colour}'>{esc(a['event_type'])}</b></td>"
            f"<td>{esc(a['job_name'])}</td><td>{run}</td><td><code>{esc(a['caller'])}</code></td></tr>")


@app.get("/", response_class=HTMLResponse)
def home():
    rows = "".join(_row(a) for a in reversed(ALERTS[-50:])) or "<tr><td colspan=5>No alerts yet. Run the demo job.</td></tr>"
    return f"""<html><head><title>alert-receiver</title><meta http-equiv="refresh" content="10">
<style>body{{font-family:-apple-system,Helvetica,sans-serif;margin:32px;color:#1B3139}}table{{border-collapse:collapse;width:100%}}
td,th{{border-bottom:1px solid #EEEDE9;padding:8px;text-align:left;font-size:14px}}th{{background:#F9F7F4}}</style></head>
<body><h2>Databricks job alerts received</h2><p>Delivered by an OAuth webhook destination. Auto-refreshes every 10 seconds.</p>
<table><tr><th>Received (UTC)</th><th>Event</th><th>Job</th><th>Run</th><th>Sent by</th></tr>{rows}</table></body></html>"""
