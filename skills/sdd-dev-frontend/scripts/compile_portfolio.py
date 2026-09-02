#!/usr/bin/env python3
"""Compile a Story's validation portfolio from facts, not from prose.

Inputs are all facts the agent already has: the TaskPacket and 用例追溯 table in
`tasks.md`, the mechanical floor from `classify_diff.py`, the frozen R/F rows in
`dev-baseline.md`, and any triggers that needed code reading to identify. The
rule table lives in `portfolio-rules.json`; this file only loads and applies it.

What this replaces is the agent reading validation-policy.md twice per Story and
hand-mapping triggers → modules → roles → dimensions. Risk *identification* for
the judgement triggers stays with the agent (`--trigger`); everything downstream
of identification is deterministic here.

Exit codes: 0 compiled; 2 input error; 3 monotonicity violated against --previous.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
TIERS = ("lite", "standard")
SCOPES = ("S1_COMPONENT", "S2_PAGE", "S3_STORY")
METHODS = ("test_case", "restore_contract", "quality_gate", "manual_acceptance")
STATES = ("hover", "focus", "disabled", "selected", "loading", "empty", "overflow", "long-copy", "large-list")
DEFAULT_RULES = Path(__file__).with_name("portfolio-rules.json")


class PortfolioError(RuntimeError):
    pass


# ---------------------------------------------------------------- markdown facts

def parse_task_packet(markdown: str) -> dict[str, str]:
    """`**TaskPacket:** k=v | k=v` → dict. Empty values stay empty strings."""
    match = re.search(r"^\*\*TaskPacket:\*\*\s*(.+)$", markdown, re.M)
    if not match:
        raise PortfolioError("tasks.md has no **TaskPacket:** line")
    packet: dict[str, str] = {}
    for cell in match.group(1).split("|"):
        cell = cell.strip()
        if not cell:
            continue
        if "=" not in cell:
            raise PortfolioError(f"TaskPacket cell without '=': {cell!r}")
        key, _, value = cell.partition("=")
        packet[key.strip()] = value.strip()
    return packet


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[,，]", value) if item.strip()]


def parse_table(markdown: str, heading: str) -> list[dict[str, str]]:
    """Rows of the first pipe table under `## <heading>`, keyed by header cell text."""
    section = re.search(rf"^##\s+{re.escape(heading)}\s*$(.*?)(?=^##\s|\Z)", markdown, re.M | re.S)
    if not section:
        return []
    lines = [line.strip() for line in section.group(1).splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return []
    header = [cell.strip() for cell in lines[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != len(header):
            raise PortfolioError(f"table under '{heading}' has a row with {len(cells)} cells, header has {len(header)}: {line}")
        rows.append(dict(zip(header, cells)))
    return rows


def parse_claims(markdown: str) -> list[dict[str, str]]:
    """用例追溯 is the single author of scope/method; anything malformed stops here."""
    rows = parse_table(markdown, "用例追溯")
    claims: list[dict[str, str]] = []
    for row in rows:
        at = row.get("AT", "")
        if not at or at.startswith("<!--") or at.startswith("AT-..."):
            continue
        scope = row.get("验证范围", "")
        method = row.get("验证方法", "")
        if scope not in SCOPES:
            raise PortfolioError(f"{at}: 验证范围 must be one of {list(SCOPES)}, got {scope!r}")
        if method not in METHODS:
            raise PortfolioError(f"{at}: 验证方法 must be one of {list(METHODS)}, got {method!r}")
        if method == "quality_gate":
            raise PortfolioError(f"{at}: quality_gate does not produce an AT; drop the row")
        claims.append({"id": at, "scope": scope, "method": method, "task": row.get("Task", "")})
    return claims


ROW_ID = re.compile(r"^\|\s*((?:R|F)[1-6]-\d+)\s*\|", re.M)


def parse_frozen_rows(markdown: str | None) -> set[str]:
    """R/F row ids present in a frozen QA baseline (`| R1-2 | ... |`)."""
    if not markdown:
        return set()
    section = markdown.split("## QA 基线", 1)
    body = section[1] if len(section) == 2 else markdown
    return set(ROW_ID.findall(body))


# ------------------------------------------------------------------ compilation

def load_rules(path: Path) -> dict[str, Any]:
    try:
        rules = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise PortfolioError(f"cannot read rules {path}: {error}") from error
    if rules.get("schema_version") != SCHEMA_VERSION:
        raise PortfolioError(f"rules schema_version must be {SCHEMA_VERSION}")
    return rules


def known_triggers(rules: dict[str, Any]) -> set[str]:
    return set().union(*rules["triggers"].values())


def collect_triggers(
    rules: dict[str, Any],
    packet: dict[str, str],
    diff_facts: dict[str, Any] | None,
    agent_triggers: list[str],
    narrowed: dict[str, str],
) -> tuple[list[str], dict[str, list[str]], list[dict[str, str]]]:
    known = known_triggers(rules)
    sources: dict[str, set[str]] = {}

    def add(trigger: str, source: str) -> None:
        if trigger not in known:
            raise PortfolioError(f"unknown risk trigger {trigger!r} from {source}")
        sources.setdefault(trigger, set()).add(source)

    for trigger in split_csv(packet.get("risk_triggers", "")):
        add(trigger, "plan")
    floor = set((diff_facts or {}).get("risk_triggers", {}).keys())
    for trigger in floor:
        add(trigger, "diff")
    for trigger in agent_triggers:
        add(trigger, "agent")

    narrowing: list[dict[str, str]] = []
    for trigger, reason in narrowed.items():
        if trigger not in floor:
            raise PortfolioError(f"--narrow {trigger}: only diff-derived floor triggers can be narrowed")
        if sources.get(trigger, set()) - {"diff"}:
            raise PortfolioError(f"--narrow {trigger}: also asserted by plan or agent, cannot narrow")
        sources.pop(trigger, None)
        narrowing.append({"trigger": trigger, "reason": reason})

    ordered = sorted(sources)
    return ordered, {key: sorted(value) for key, value in sources.items()}, narrowing


def derive_facts(
    packet: dict[str, str],
    diff_facts: dict[str, Any] | None,
    frozen_rows: set[str],
    claims: list[dict[str, str]],
) -> dict[str, bool]:
    states = set(split_csv(packet.get("required_states", "")))
    unknown_states = states - set(STATES)
    if unknown_states:
        raise PortfolioError(f"required_states has unknown values {sorted(unknown_states)}")
    routes = split_csv(packet.get("affected_routes", ""))
    changed = [item.get("path", "") for item in (diff_facts or {}).get("changed_files", [])]
    shared_evidence = {
        fact["evidence"] for fact in (diff_facts or {}).get("risk_triggers", {}).get("shared-boundary", [])
    }
    style_suffixes = (".css", ".scss", ".sass", ".less", ".styl")
    shared_style = any(path.endswith(style_suffixes) and path in shared_evidence for path in changed)
    prefixes = {row.split("-")[0] for row in frozen_rows}
    return {
        "cross_page": len(routes) >= 2,
        "shared_style": shared_style,
        "overflow_state": bool(states & {"overflow", "long-copy", "large-list"}),
        "frozen_r": any(prefix.startswith("R") for prefix in prefixes),
        "frozen_r5": "R5" in prefixes,
        "frozen_r6": "R6" in prefixes,
        "has_f3": "F3" in prefixes,
        "has_s3_claim": any(claim["scope"] == "S3_STORY" for claim in claims),
    }


def compute_tier(rules: dict[str, Any], packet: dict[str, str], triggers: list[str], changed_files: int | None) -> dict[str, Any]:
    cfg = rules["tier"]
    restore_tasks = split_csv(packet.get("restore_tasks", ""))
    blocking = sorted(set(triggers) & set(cfg["blocking_triggers"]))
    if changed_files is None:
        raise PortfolioError("file count unknown: pass --diff-facts or --plan-files; lite is never granted by default")
    files = changed_files
    over_limit = files > cfg["max_changed_files"]
    lite = not restore_tasks and not blocking and not over_limit
    return {
        "value": "lite" if lite else "standard",
        "restore_tasks": restore_tasks,
        "blocking_triggers": blocking,
        "changed_files": files,
        "max_changed_files": cfg["max_changed_files"],
    }


def select_modules(
    rules: dict[str, Any],
    triggers: list[str],
    facts: dict[str, bool],
    rebuttals: set[str],
    claims: list[dict[str, str]],
) -> list[str]:
    trigger_set = set(triggers)
    scopes = {claim["scope"] for claim in claims}
    selected: list[str] = []
    for name, rule in rules["modules"].items():
        if rule.get("all_modules"):
            # Derived module (self-test follows story); order in the rules file matters.
            hit = all(module in selected for module in rule["all_modules"])
        else:
            hit = bool(rule.get("always"))
            hit = hit or bool(trigger_set & set(rule.get("any_trigger", [])))
            hit = hit or bool(scopes & set(rule.get("any_claim_scope", [])))
            hit = hit or any(rebuttal[0] in rule.get("any_rebuttal_prefix", []) for rebuttal in rebuttals)
            # Facts are gates, not triggers: visual without a frozen R row selects render but not review-restore.
            if rule.get("all_facts") and not all(facts.get(fact) for fact in rule["all_facts"]):
                hit = False
            if rule.get("any_fact") and not any(facts.get(fact) for fact in rule["any_fact"]):
                hit = False
        if hit:
            selected.append(name)
    return selected


def assign_dimensions(
    rules: dict[str, Any],
    modules: list[str],
    triggers: list[str],
    facts: dict[str, bool],
    rebuttals: set[str],
    frozen_rows: set[str],
    states: set[str],
    agent_dimensions: dict[str, set[str]],
    reg_rows: list[str],
) -> dict[str, list[str]]:
    trigger_set = set(triggers)
    out: dict[str, list[str]] = {}
    for role in rules["review_roles"]:
        if role not in modules:
            continue
        table = rules["dimensions"][role]
        chosen: set[str] = set()
        if table.get("_from") == "f_rows_and_reg":
            chosen = {row for row in frozen_rows if row.startswith("F")} | set(reg_rows)
        else:
            for dimension, rule in table.items():
                hit = False
                if rule.get("frozen_rows"):
                    hit = any(row.startswith(rule["frozen_rows"] + "-") for row in frozen_rows)
                hit = hit or bool(trigger_set & set(rule.get("any_trigger", [])))
                hit = hit or any(facts.get(fact) for fact in rule.get("any_fact", []))
                hit = hit or bool(states & set(rule.get("any_state", [])))
                hit = hit or (rule.get("rebuttal") in rebuttals)
                if hit:
                    chosen.add(dimension)
        extra = agent_dimensions.get(role, set())
        if table.get("_from") != "f_rows_and_reg":
            unknown = extra - set(table)
            if unknown:
                raise PortfolioError(f"--dimension {role}: unknown dimensions {sorted(unknown)}")
        chosen |= extra
        # A rebutted dimension can never be left unassigned: the diff already contradicts its skip_when.
        for dimension, rule in table.items():
            if dimension.startswith("_"):
                continue
            if rule.get("rebuttal") in rebuttals:
                chosen.add(dimension)
        out[role] = sorted(chosen, key=_dimension_key)
    return out


def _dimension_key(value: str) -> tuple[str, int, int]:
    match = re.match(r"^([A-Z]+)(\d+)(?:-(\d+))?$", value)
    if not match:
        return (value, 0, 0)
    return (match.group(1), int(match.group(2)), int(match.group(3) or 0))


def profile_rank(rules: dict[str, Any], profile: str) -> int:
    order = rules["execution_profile"]["order"]
    if profile not in order:
        raise PortfolioError(f"unknown execution profile {profile!r}; expected one of {order}")
    return order.index(profile)


def required_profile(rules: dict[str, Any], claim: dict[str, str], triggers: list[str]) -> str:
    """How strong an environment this claim needs before it may be PROVEN.

    The rule is deliberately coarse: component/page claims are provable against mocks,
    story-scope claims need the formal contract, and story-scope claims behind auth or
    write need the live seam. Anything finer is the agent's call via --profile, and
    that call can only raise the bar.
    """
    cfg = rules["execution_profile"]
    method = claim["method"]
    if method in cfg["by_method"]:
        return cfg["by_method"][method]
    table = cfg["test_case"]
    base = table[claim["scope"]]
    if claim["scope"] == "S3_STORY":
        rule = table["S3_STORY_with_any_trigger"]
        if set(triggers) & set(rule["triggers"]):
            return rule["profile"]
    return base


def attach_claim_modules(
    rules: dict[str, Any],
    claims: list[dict[str, str]],
    modules: list[str],
    triggers: list[str],
    raised_profiles: dict[str, str],
) -> list[dict[str, Any]]:
    cfg = rules["claim_modules"]
    known = {claim["id"] for claim in claims}
    unknown = set(raised_profiles) - known
    if unknown:
        raise PortfolioError(f"--profile names unknown claims {sorted(unknown)}")
    out = []
    for claim in claims:
        wanted = list(cfg[claim["method"]])
        if claim["scope"] == "S3_STORY":
            wanted += cfg["scope_S3_STORY_adds"]
        attached = [module for module in wanted if module in modules]
        profile = required_profile(rules, claim, triggers)
        if claim["id"] in raised_profiles:
            raised = raised_profiles[claim["id"]]
            if profile_rank(rules, raised) < profile_rank(rules, profile):
                raise PortfolioError(
                    f"--profile {claim['id']}={raised} is below the derived {profile}; profiles can only be raised"
                )
            profile = raised
        out.append({
            "id": claim["id"],
            "verification_scope": claim["scope"],
            "verification_method": claim["method"],
            "task": claim["task"],
            "modules": attached,
            "required_profile": profile,
            "status": "UNVERIFIED",
        })
    return out


def previous_snapshot(previous: dict[str, Any]) -> dict[str, Any]:
    """What the monotonicity check compared against, kept inside the new portfolio.

    The Phase 0 file is overwritten in place by Phase C, so this is the only record
    of what the initial portfolio was. Only the compared fields are kept; nesting an
    older `previous` would grow without bound and nobody reads two generations back.
    """
    return {
        "phase": previous.get("phase"),
        "tier": previous["tier"]["value"],
        "modules": list(previous["modules"]),
        "review_roles": list(previous["review_roles"]),
        "required_profiles": {
            claim["id"]: claim.get("required_profile", "mock") for claim in previous.get("claims", [])
        },
    }


def check_monotonic(previous: dict[str, Any], current: dict[str, Any]) -> list[str]:
    problems = []
    if previous["tier"]["value"] == "standard" and current["tier"]["value"] == "lite":
        problems.append("tier downgraded standard → lite; only lite → standard is allowed")
    missing = set(previous["modules"]) - set(current["modules"])
    if missing:
        problems.append(f"modules dropped from previous portfolio: {sorted(missing)}")
    dropped_roles = set(previous["review_roles"]) - set(current["review_roles"])
    if dropped_roles:
        problems.append(f"review roles dropped: {sorted(dropped_roles)}")
    order = ["mock", "contract", "live"]
    before = {claim["id"]: claim.get("required_profile", "mock") for claim in previous.get("claims", [])}
    for claim in current.get("claims", []):
        prior = before.get(claim["id"])
        if prior and order.index(claim["required_profile"]) < order.index(prior):
            problems.append(f"{claim['id']} required_profile lowered {prior} → {claim['required_profile']}")
    return problems


def compile_portfolio(
    rules: dict[str, Any],
    tasks_md: str,
    *,
    phase: str,
    diff_facts: dict[str, Any] | None = None,
    qa_baseline_md: str | None = None,
    agent_triggers: list[str] | None = None,
    narrowed: dict[str, str] | None = None,
    agent_dimensions: dict[str, set[str]] | None = None,
    reg_rows: list[str] | None = None,
    plan_file_count: int | None = None,
    raised_profiles: dict[str, str] | None = None,
) -> dict[str, Any]:
    packet = parse_task_packet(tasks_md)
    claims = parse_claims(tasks_md)
    frozen_rows = parse_frozen_rows(qa_baseline_md)
    triggers, sources, narrowing = collect_triggers(rules, packet, diff_facts, agent_triggers or [], narrowed or {})
    facts = derive_facts(packet, diff_facts, frozen_rows, claims)
    rebuttals = set((diff_facts or {}).get("skip_rebuttals", {}).keys())
    changed = len(diff_facts["changed_files"]) if diff_facts is not None else plan_file_count
    tier = compute_tier(rules, packet, triggers, changed)
    modules = select_modules(rules, triggers, facts, rebuttals, claims)
    states = set(split_csv(packet.get("required_states", "")))
    dimensions = assign_dimensions(
        rules, modules, triggers, facts, rebuttals, frozen_rows, states, agent_dimensions or {}, reg_rows or []
    )
    roles = [role for role in rules["review_roles"] if role in modules]
    return {
        "schema_version": SCHEMA_VERSION,
        "phase": phase,
        "tier": tier,
        "risk_triggers": triggers,
        "trigger_sources": sources,
        "portfolio_narrowed": narrowing,
        "facts": facts,
        "modules": modules,
        "review_roles": roles,
        "review_dimensions": dimensions,
        "claims": attach_claim_modules(rules, claims, modules, triggers, raised_profiles or {}),
        "previous": None,
    }


# ---------------------------------------------------------------------- output

def render_markdown(portfolio: dict[str, Any]) -> str:
    tier = portfolio["tier"]
    lines = [
        f"执行档位：**{tier['value']}**（还原 Task：{', '.join(tier['restore_tasks']) or '无'}；"
        f"阻断触发器：{', '.join(tier['blocking_triggers']) or '无'}；文件数：{tier['changed_files']}/{tier['max_changed_files']}）",
        "",
        "| 风险触发器 | 来源 | 模块 | 独立检视与维度 | 依赖声明 |",
        "| --- | --- | --- | --- | --- |",
    ]
    dims = "；".join(f"{role}: {', '.join(d)}" for role, d in portfolio["review_dimensions"].items()) or "无"
    claims = ", ".join(f"{claim['id']}({claim['required_profile']})" for claim in portfolio["claims"]) or "无"
    triggers = ", ".join(portfolio["risk_triggers"]) or "无"
    sources = "；".join(f"{t}: {'/'.join(s)}" for t, s in portfolio["trigger_sources"].items()) or "—"
    lines.append(f"| {triggers} | {sources} | {', '.join(portfolio['modules'])} | {dims} | {claims} |")
    if portfolio["portfolio_narrowed"]:
        lines += ["", "收窄（署名）：" + "；".join(f"{n['trigger']} — {n['reason']}" for n in portfolio["portfolio_narrowed"])]
    return "\n".join(lines) + "\n"


def parse_kv_list(values: list[str], flag: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in values:
        if "=" not in item:
            raise PortfolioError(f"{flag} expects key=value, got {item!r}")
        key, _, value = item.partition("=")
        if not value.strip():
            raise PortfolioError(f"{flag} {key}: value must not be empty")
        out[key.strip()] = value.strip()
    return out


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tasks", required=True, help="tasks.md with TaskPacket and 用例追溯")
    p.add_argument("--phase", choices=("initial", "final"), required=True)
    p.add_argument("--rules", default=str(DEFAULT_RULES))
    p.add_argument("--diff-facts", help="classify_diff.py output; required for --phase final")
    p.add_argument("--qa-baseline", help="dev-baseline.md; frozen R/F rows are read from its QA 基线 section")
    p.add_argument("--trigger", action="append", default=[], help="agent-judged trigger; repeatable")
    p.add_argument("--narrow", action="append", default=[], help="trigger=reason; only diff-derived floor triggers")
    p.add_argument("--dimension", action="append", default=[], help="role=D1,D2 extra dimensions the agent judged applicable")
    p.add_argument("--reg", action="append", default=[], help="REG row id selected for self-test; repeatable")
    p.add_argument("--profile", action="append", default=[], help="AT=mock|contract|live to raise a claim's required execution profile")
    p.add_argument("--plan-files", type=int, help="file count from the plan when there is no diff yet")
    p.add_argument("--previous", help="earlier portfolio JSON; enforces lite→standard and module growth only, and is kept as `previous` in the output (may be the same path as --out)")
    p.add_argument("--out", help="write portfolio JSON here")
    p.add_argument("--markdown", action="store_true", help="print the dev-baseline.md 验证组合 table to stdout")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        rules = load_rules(Path(args.rules))
        tasks_md = Path(args.tasks).read_text(encoding="utf-8")
        diff_facts = json.loads(Path(args.diff_facts).read_text(encoding="utf-8")) if args.diff_facts else None
        if args.phase == "final" and diff_facts is None:
            raise PortfolioError("--phase final requires --diff-facts")
        qa = Path(args.qa_baseline).read_text(encoding="utf-8") if args.qa_baseline else None
        agent_dims = {
            role: set(split_csv(values))
            for role, values in parse_kv_list(args.dimension, "--dimension").items()
        }
        portfolio = compile_portfolio(
            rules, tasks_md,
            phase=args.phase,
            diff_facts=diff_facts,
            qa_baseline_md=qa,
            agent_triggers=args.trigger,
            narrowed=parse_kv_list(args.narrow, "--narrow"),
            agent_dimensions=agent_dims,
            reg_rows=args.reg,
            plan_file_count=args.plan_files,
            raised_profiles=parse_kv_list(args.profile, "--profile"),
        )
        if args.previous:
            previous = json.loads(Path(args.previous).read_text(encoding="utf-8"))
            problems = check_monotonic(previous, portfolio)
            if problems:
                for problem in problems:
                    print(f"monotonicity: {problem}", file=sys.stderr)
                return 3
            portfolio["previous"] = previous_snapshot(previous)
    except (PortfolioError, OSError, ValueError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    text = json.dumps(portfolio, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    if args.markdown:
        print(render_markdown(portfolio), end="")
    elif not args.out:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
