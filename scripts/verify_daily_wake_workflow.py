#!/usr/bin/env python3
"""Fail-closed static contract for GitHub-hosted OIDC Daily wake handoff."""
from __future__ import annotations

import subprocess
from pathlib import Path

import yaml


def require(condition: bool, label: str) -> None:
    if not condition:
        raise SystemExit(f"DAILY WAKE CI CONTRACT FAILED: {label}")


signal_path = Path(".github/workflows/daily-published-wake.yml")
publish_path = Path(".github/workflows/publish-radar-staging.yml")
signal = yaml.load(signal_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
publisher = yaml.load(publish_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
require(isinstance(signal, dict) and isinstance(publisher, dict), "YAML mapping")
require(set(signal["on"]) == {"workflow_dispatch"}, "must dispatch only, never push/PR")
require(signal["permissions"] == {"id-token": "write"}, "no resource or private token permissions")
require(signal["jobs"]["signal"]["runs-on"] == "ubuntu-latest", "GitHub-hosted identity only")
require(signal["jobs"]["signal"]["if"] == "github.ref == 'refs/heads/main'", "main-only job")
require(not any("uses" in step for step in signal["jobs"]["signal"]["steps"]), "zero third-party actions")
inputs = signal["on"]["workflow_dispatch"]["inputs"]
require(set(inputs) == {"report_date", "public_commit", "mode"}, "exact allowed inputs")
require(inputs["mode"]["default"] == "check", "manual test must not enqueue by default")
require(set(inputs["mode"]["options"]) == {"check", "enqueue"}, "only two allowed modes")
signal_script = signal["jobs"]["signal"]["steps"][0]["run"]
require("ACTIONS_ID_TOKEN_REQUEST_TOKEN" in signal_script, "OIDC token request")
require("audience=carni-ai-news-wake" in signal_script, "exact audience")
require("https://qbsovyjwnxmryokekypf.supabase.co/functions/v1/daily-published-wake" in
        str(signal["jobs"]["signal"]["steps"][0]["env"]), "exact receiver")
require("checkout" not in signal_script and "GITHUB_TOKEN" not in signal_script,
        "no checkout or hidden GitHub token")
subprocess.run(["bash", "-n"], input=signal_script, text=True, check=True)

steps = publisher["jobs"]["publish"]["steps"]
apply = next(step for step in steps if step.get("name") == "Apply exact verified bundle to current main")
telegram = next(step for step in steps if step.get("name") == "Dispatch Telegram and IndexNow after bot push")
wake = next(step for step in steps if step.get("name") == "Signal Daily to Supabase after confirmed public push")
require("git push origin HEAD:main" in apply["run"], "verified push exists")
require(apply["run"].index("git push origin HEAD:main") <
        apply["run"].index("PUBLIC_COMMIT=${public_commit}"), "public SHA captured after push")
require("always()" in wake["if"] and "PUBLISHED_KIND == 'Daily'" in wake["if"],
        "wake attempts independent of Telegram success and only after real Daily")
require(steps.index(wake) > steps.index(telegram), "signal runs after distribution step")
require("mode=enqueue" in wake["run"] and "daily-published-wake.yml" in wake["run"],
        "explicit bounded dispatch")
require("gh workflow run telegram.yml" in telegram["run"], "legacy distribution retained")
subprocess.run(["bash", "-n"], input=apply["run"], text=True, check=True)
subprocess.run(["bash", "-n"], input=wake["run"], text=True, check=True)
print("DAILY WAKE CI CONTRACT: PASS")
