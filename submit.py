#!/usr/bin/env python3
import hashlib
import hmac
import json
import os
import urllib.request
from datetime import datetime, timezone

B12_URL = "https://b12.io/apply/submission"

def iso8601_utc_now_ms() -> str:
  # Example: 2026-02-09T16:59:37.571Z
  return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def canonical_json(payload: dict) -> bytes:
  # Must be compact (no extra whitespace) and keys sorted.
  body_str = json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
  return body_str.encode("utf-8")

def hmac_sha256_hex(key: bytes, msg: bytes) -> str:
  return hmac.new(key, msg, hashlib.sha256).hexdigest()

def main() -> None:
  # Required fields (GitHub Secrets/Variables)
  name = os.environ["B12_NAME"]
  email = os.environ["B12_EMAIL"]
  resume_link = os.environ["B12_RESUME_LINK"]
  repository_link = os.environ["B12_REPOSITORY_LINK"]

  # GitHub Actions context to build the action_run_link
  server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
  repo = os.environ.get("GITHUB_REPOSITORY") # e.g. "user/repo"
  run_id = os.environ.get("GITHUB_RUN_ID")
  if not repo or not run_id:
    raise RuntimeError("Missing GITHUB_REPOSITORY or GITHUB_RUN_ID; is this running inside GitHub Actions?")

  action_run_link = f"{server_url}/{repo}/actions/runs/{run_id}"

  payload = {
    "timestamp": iso8601_utc_now_ms(),
    "name": name,
    "email": email,
    "resume_link": resume_link,
    "repository_link": repository_link,
    "action_run_link": action_run_link,
  }

  body = canonical_json(payload)

  # Signing secret
  signing_secret = os.environ.get("B12_SIGNING_SECRET", "hello-b12").encode("utf-8")
  digest = hmac_sha256_hex(signing_secret, body)
  signature_header = f"sha256={digest}"

  req = urllib.request.Request(
    B12_URL,
    data=body,
    method="POST",
    headers={
      "Content-Type": "application/json; charset=utf-8",
      "X-Signature-256": signature_header,
    },
  )

  try:
    with urllib.request.urlopen(req, timeout=30) as resp:
      resp_body = resp.read().decode("utf-8")
      if resp.status != 200:
        raise RuntimeError(f"Unexpected HTTP {resp.status}: {resp_body}")

      data = json.loads(resp_body)
      receipt = data.get("receipt")
      if not receipt:
        raise RuntimeError(f"No receipt in response: {resp_body}")

      print(f"Receipt: {receipt}")
  except urllib.error.HTTPError as e:
    err_text = e.read().decode("utf-8", errors="replace")
    raise RuntimeError(f"HTTPError {e.code}: {err_text}") from e

if __name__ == "__main__":
  main()
