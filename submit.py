import hashlib
import hmac
import json
import os
from datetime import datetime, timezone

import requests

SIGNING_SECRET = b"hello-there-from-b12"
URL = "https://b12.io/apply/submission"

def iso_timestamp() -> str:
    # ISO 8601 with milliseconds + Z
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def main():
    name = os.environ["B12_NAME"]
    email = os.environ["B12_EMAIL"]
    resume_link = os.environ["B12_RESUME_LINK"]

    # GitHub-provided env vars:
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repo = os.environ["GITHUB_REPOSITORY"]  # e.g. user/b12-apply
    run_id = os.environ["GITHUB_RUN_ID"]

    repository_link = f"{server}/{repo}"
    action_run_link = f"{server}/{repo}/actions/runs/{run_id}"

    payload = {
        "action_run_link": action_run_link,
        "email": email,
        "name": name,
        "repository_link": repository_link,
        "resume_link": resume_link,
        "timestamp": iso_timestamp(),
    }

    # Canonical JSON: sorted keys, compact separators, UTF-8
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    digest = hmac.new(SIGNING_SECRET, body, hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "X-Signature-256": f"sha256={digest}",
    }

    resp = requests.post(URL, data=body, headers=headers, timeout=30)
    resp.raise_for_status()

    data = resp.json()
    receipt = data.get("receipt")
    print(receipt)

if __name__ == "__main__":
    main()
