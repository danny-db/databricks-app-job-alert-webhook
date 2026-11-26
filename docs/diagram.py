"""Architecture diagram: Databricks job alerts -> OAuth webhook destination -> Databricks App."""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

NAVY, RED, GREY, GREEN, AMBER, BLUE, SAND = "#1B3139", "#FF3621", "#EEEDE9", "#00A972", "#F5A623", "#2272B4", "#F9F7F4"
fig, ax = plt.subplots(figsize=(15, 8)); ax.set_xlim(0, 15); ax.set_ylim(0, 8); ax.axis("off")


def box(x, y, w, h, t, s="", fc="white", ec=NAVY, fs=11):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12", fc=fc, ec=ec, lw=1.7))
    ax.text(x + w / 2, y + h / 2 + (0.2 if s else 0), t, ha="center", va="center", fontsize=fs, weight="bold", color=NAVY)
    if s: ax.text(x + w / 2, y + h / 2 - 0.22, s, ha="center", va="center", fontsize=8.6, color=NAVY)


def arrow(x1, y1, x2, y2, c=NAVY, ls="-", label="", lx=0, ly=0.14, num=None):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", color=c, lw=1.8, linestyle=ls))
    if label: ax.text((x1 + x2) / 2 + lx, (y1 + y2) / 2 + ly, label, ha="center", fontsize=8.8, color=c)
    if num:
        ax.add_patch(plt.Circle(((x1 + x2) / 2 + lx, (y1 + y2) / 2 + max(ly, 0) + 0.32), 0.17, color=c))
        ax.text((x1 + x2) / 2 + lx, (y1 + y2) / 2 + max(ly, 0) + 0.32, num, ha="center", va="center", fontsize=8.5, color="white", weight="bold")


ax.text(0.2, 7.6, "Databricks job alerts delivered to a Databricks App with an OAuth webhook destination", fontsize=14, weight="bold", color=NAVY)
ax.text(0.2, 7.25, "Tested end to end on Databricks, 26 Nov 2026. Same setup on AWS, Azure and GCP.", fontsize=9.5, color="grey")

# Workspace boundary
ax.add_patch(FancyBboxPatch((0.2, 0.9), 14.6, 6.0, boxstyle="round,pad=0.02,rounding_size=0.15", fc=SAND, ec=GREY, lw=1.4))
ax.text(0.45, 6.6, "Databricks workspace", fontsize=10, weight="bold", color="grey")

# Control plane services
box(0.5, 4.4, 2.5, 1.3, "Lakeflow Job", "on_start / on_success / on_failure\n(pipelines: run as a job task)")
box(4.0, 4.4, 2.8, 1.3, "Notification destination", "Webhook, auth mode = OAuth\nclient ID + secret, token URL, scope", ec=BLUE)
box(4.0, 1.5, 2.8, 1.3, "Workspace OAuth", "/oidc/v1/token\nclient_credentials, all-apis", ec=AMBER)
box(8.25, 4.4, 2.3, 1.3, "Apps front door", "validates token +\nCAN_USE on the app", ec=BLUE)
box(11.9, 4.4, 2.6, 1.3, "alert-receiver app", "POST /alert  ·  UI at /\nallow-list check on caller", ec=RED)
box(8.1, 1.5, 2.6, 1.3, "Service principal", "alert-webhook-caller\nCAN_USE on the app only", ec=GREEN)
box(11.9, 1.5, 2.6, 1.3, "Your handling", "on-call, ticket, table,\nLLM triage ...", fc="white", ec=GREY)

arrow(3.0, 5.05, 4.0, 5.05, label="run event", num="1")
arrow(5.15, 4.4, 5.15, 2.8, c=AMBER, label="get M2M token", lx=-0.85, ly=0, num="2")
arrow(5.65, 2.8, 5.65, 4.4, c=AMBER, label="access token", lx=0.85, ly=0)
arrow(6.8, 5.05, 8.25, 5.05, c=BLUE, label="POST /alert\nBearer <token>", ly=-0.55, num="3")
arrow(10.55, 5.05, 11.9, 5.05, c=BLUE, label="caller ID\nin header", ly=-0.55, num="4")
arrow(13.2, 4.4, 13.2, 2.8, c=GREY, ls="--")
ax.plot([9.4, 9.4], [2.8, 4.4], color=GREEN, lw=1.5, ls=":"); ax.text(9.5, 3.35, "identity of\nthe caller", fontsize=8.5, color=GREEN)

# Deployed by
ax.text(0.6, 3.5, "Deployed by the bundle", fontsize=9.5, weight="bold", color=NAVY)
ax.text(0.6, 2.35, "databricks.yml\n  · app + CAN_USE grant\n  · demo job + webhook_notifications\nscripts/setup.py\n  · service principal + secret\n  · OAuth destination", fontsize=8.6, color=NAVY, family="monospace", va="bottom")

# Footer: the problem it solves
ax.text(0.2, 0.45, "Why OAuth: the Apps front door accepts only Databricks OAuth tokens. A Basic-auth webhook is redirected to login (302) and never reaches the app.",
        fontsize=9.5, color=RED)
plt.savefig("docs/architecture.png", dpi=170, bbox_inches="tight", facecolor="white")
print("saved docs/architecture.png")
