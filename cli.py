"""Minimal CLI to run one applicant through the pipeline end to end and
print the rendered report.

    ANTHROPIC_API_KEY=... python cli.py <username> --rules rules.txt --register register.txt

This produces a real, evidence-cited document that makes claims about a
real person's conduct. Only point this at an actual moderator applicant
who is actually being considered, with actual subreddit rules -- this is
not a toy to run against arbitrary usernames out of curiosity.
"""

from __future__ import annotations

import argparse
import json
import sys

from mod_vetting.orchestrator import run_job
from mod_vetting.render import render_markdown
from mod_vetting.storage import Storage


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("username", help="Reddit username of the applicant (no u/ prefix)")
    parser.add_argument("--rules", required=True, help="Path to a text file with the subreddit's rules")
    parser.add_argument("--register", required=True, help="Path to a text file describing the sub's house style/register")
    parser.add_argument("--comment-cap", type=int, default=1000)
    parser.add_argument("--post-cap", type=int, default=100)
    parser.add_argument("--db", default="mod_vetting.sqlite3")
    parser.add_argument("--json", action="store_true", help="Print the raw JSON report instead of Markdown")
    args = parser.parse_args()

    rules = open(args.rules, encoding="utf-8").read()
    register_notes = open(args.register, encoding="utf-8").read()

    storage = Storage(args.db)
    report = run_job(
        storage=storage,
        applicant_username=args.username,
        rules=rules,
        register_notes=register_notes,
        applicant_meta={
            "username": args.username,
            "account_age_days": 0,  # TODO: compute from fetched history's earliest item
            "sub_tenure_days": 0,   # TODO: requires knowing when they joined the target sub, not available from Arctic Shift
            "comments_in_sub": 0,   # TODO: requires knowing the target subreddit to filter against
            "subs_modded": 0,       # TODO: requires a moderator-list lookup, not implemented
        },
        comment_cap=args.comment_cap,
        post_cap=args.post_cap,
    )

    if "blocked_reason" in report:
        print(f"Job {report['job_id']} stopped: {report['blocked_reason']}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(report, indent=2) if args.json else render_markdown(report))


if __name__ == "__main__":
    main()
