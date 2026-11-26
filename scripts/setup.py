"""
One-shot setup: service principal -> app -> OAuth webhook destination -> job wired to it.
Safe to re-run: it reuses the service principal and destination if they already exist.

    pip install "databricks-sdk>=0.40"
    python scripts/setup.py --profile <cli-profile> [--target dev]

Needs: workspace admin (to create the service principal and the notification destination).
The client secret is created and handed straight to the destination. It is never printed or written to disk.
"""
import argparse
import json
import subprocess

from databricks.sdk import WorkspaceClient

SP_NAME = "alert-webhook-caller"
DESTINATION_NAME = "alert-receiver-oauth"


def sh(*args: str) -> str:
    print("$", " ".join(args))
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def bundle(cmd: list[str], a, **variables) -> str:
    var_args = [f"--var={k}={v}" for k, v in variables.items()]
    return sh("databricks", "bundle", *cmd, "-t", a.target, "-p", a.profile, *var_args)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--profile", required=True)
    p.add_argument("--target", default="dev")
    a = p.parse_args()
    w = WorkspaceClient(profile=a.profile)
    host = w.config.host.rstrip("/")

    # 1. The identity the webhook authenticates as.
    sp = next(iter(w.service_principals.list(filter=f'displayName eq "{SP_NAME}"')), None) \
        or w.service_principals.create(display_name=SP_NAME)
    print(f"1. service principal {SP_NAME}: {sp.application_id}")

    # 2. Deploy the app (CAN_USE for the SP comes from resources/app.yml) and start it.
    bundle(["deploy"], a, caller_sp_application_id=sp.application_id)
    bundle(["run", "alert_receiver"], a, caller_sp_application_id=sp.application_id)
    summary = json.loads(bundle(["summary", "-o", "json"], a, caller_sp_application_id=sp.application_id))
    app_url = w.apps.get(summary["resources"]["apps"]["alert_receiver"]["name"]).url
    print(f"2. app running: {app_url}")

    # 3. OAuth webhook destination: Databricks fetches an M2M token for the SP before every call.
    existing = next((d for d in w.notification_destinations.list() if d.display_name == DESTINATION_NAME), None)
    if existing:
        dest_id = existing.id
        print(f"3. destination exists, reusing: {dest_id}")
    else:
        secret = w.api_client.do("POST", f"/api/2.0/accounts/servicePrincipals/{sp.id}/credentials/secrets", body={})
        dest = w.api_client.do("POST", "/api/2.0/notification-destinations", body={
            "display_name": DESTINATION_NAME,
            "config": {"generic_webhook": {
                "url": f"{app_url}/alert",
                "oauth_client_id": sp.application_id,
                "oauth_client_secret": secret["secret"],
                "oauth_token_url": f"{host}/oidc/v1/token",
                "oauth_scopes": ["all-apis"],
            }},
        })
        dest_id = dest["id"]
        print(f"3. destination created: {dest_id}")

    # 4. Redeploy so the demo job's webhook_notifications point at the real destination.
    bundle(["deploy"], a, caller_sp_application_id=sp.application_id, alert_destination_id=dest_id)
    print("4. demo job wired to the destination")

    print(f"""
Done. Next:
  databricks bundle run alert_demo_job -t {a.target} -p {a.profile} \\
      --var=caller_sp_application_id={sp.application_id} --var=alert_destination_id={dest_id}
  Then open {app_url} and watch jobs.on_start, then jobs.on_failure, arrive.""")


if __name__ == "__main__":
    main()
