"""Renders an assembled report (report.py) to Markdown for a human
reviewer. Build order step 7."""

from __future__ import annotations


def render_markdown(report: dict) -> str:
    lines = []
    a = report["applicant"]
    lines.append(f"# Moderator vetting report: u/{a['username']}")
    lines.append("")

    gate = report.get("_human_gate", {"blocked": False, "reasons": []})
    if gate["blocked"]:
        lines.append("> **BLOCKED -- requires a named human before this report can circulate.**")
        for r in gate["reasons"]:
            lines.append(f"> - {r}")
        lines.append("")
    else:
        lines.append("_Renders to `awaiting_human` per spec section 8 -- this pipeline produces evidence "
                      "and computed scores, not a decision, regardless of gate status._")
        lines.append("")

    lines.append("## Applicant")
    lines.append(f"- Account age: {a['account_age_days']} days")
    lines.append(f"- Tenure in sub: {a['sub_tenure_days']} days")
    lines.append(f"- Comments in sub: {a['comments_in_sub']}")
    lines.append(f"- Subs modded: {a['subs_modded']}")
    lines.append("")

    lines.append("## Scores")
    lines.append("| Category | Level | Anchor | Findings |")
    lines.append("|---|---|---|---|")
    for category, score in report["scores"].items():
        lines.append(f"| {category} | {score['level']} | {score['anchor']} | {len(score['finding_ids'])} |")
    lines.append("")

    triggered_hard_fails = [hf for hf in report["hard_fails"] if hf["triggered"]]
    lines.append("## Hard fails")
    if triggered_hard_fails:
        for hf in triggered_hard_fails:
            lines.append(f"- **{hf['code']}** ({len(hf['finding_ids'])} finding(s))")
    else:
        lines.append("None triggered.")
    lines.append("")

    lines.append(f"## Findings ({len(report['findings'])})")
    for f in report["findings"]:
        level_str = f"level {f['level']}" if f["level"] is not None else "(binary/no level)"
        lines.append(f"### {f['category']} -- {level_str}")
        lines.append(f"> {f['quote']}")
        lines.append(f"- [{f['permalink']}]({f['permalink']}) -- r/{f.get('subreddit', '')}")
        if f.get("context_note"):
            lines.append(f"- Context: {f['context_note']}")
        if f.get("register_note"):
            lines.append(f"- Register: {f['register_note']}")
        lines.append("")

    lines.append("## Recommendation")
    lines.append(report["recommendation"]["text"])
    lines.append("")

    p = report["provenance"]
    lines.append("## Provenance")
    lines.append(f"- Comments fetched: {p['comments_fetched']}")
    lines.append(f"- Comments flagged: {p['comments_flagged']}")
    lines.append(f"- Findings upheld: {p['findings_upheld']}")
    lines.append(f"- Findings dropped (ungrounded): {p['findings_dropped_ungrounded']}")
    lines.append(f"- Purge after: {p['purge_after']}")
    lines.append("")
    lines.append(f"Contract: `{report['contract']['rubric_version']}` / `{report['contract']['prompt_template_hash']}`")

    return "\n".join(lines)
