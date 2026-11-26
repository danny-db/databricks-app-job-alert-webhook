"""Remove everything setup.py created: bundle resources, the destination and the service principal.

    python scripts/teardown.py --profile <cli-profile> [--target dev]
"""
import argparse
import subprocess

from databricks.sdk import WorkspaceClient

from setup import DESTINATION_NAME, SP_NAME

p = argparse.ArgumentParser()
p.add_argument("--profile", required=True)
p.add_argument("--target", default="dev")
a = p.parse_args()
w = WorkspaceClient(profile=a.profile)

sp = next(iter(w.service_principals.list(filter=f'displayName eq "{SP_NAME}"')), None)
subprocess.run(["databricks", "bundle", "destroy", "--auto-approve", "-t", a.target, "-p", a.profile,
                f"--var=caller_sp_application_id={sp.application_id if sp else 'none'}"], check=True)
for d in w.notification_destinations.list():
    if d.display_name == DESTINATION_NAME:
        w.notification_destinations.delete(d.id); print("deleted destination", d.id)
if sp:
    w.service_principals.delete(sp.id); print("deleted service principal", sp.application_id)
