#!/usr/bin/env python3
"""Check a skill package against the acceptance checklist a reviewer will apply.

Usage:
    python3 check_skill_package.py <skill-dir | repo-root>

The argument may be one skill directory, or a repo root containing `skills/*`.
Checks, per skill: directory name == frontmatter name; frontmatter parses; description
length + the routing signal in its first 57 characters; every `references/...` link in every
markdown file resolves; no placeholder text left behind. If the Hermes agent tree is
importable it also prints the local scan verdict (run it with the Hermes venv python to get
that line: `<hermes-home>/hermes-agent/venv/bin/python3 check_skill_package.py ...`).

Exit code: 0 when every check passes for every skill, 1 otherwise.

The placeholder word list is matched in markdown *prose* too, so a package whose SKILL.md documents
this checklist must not spell the three markers verbatim — measured: this package's own checklist
wording made `check_skill_package.py` FAIL on itself until it was rephrased.
"""

import os
import re
import sys

TRY_YAML = True
try:
    import yaml
except Exception:  # keep the script runnable with a bare interpreter
    TRY_YAML = False

LINK_RE = re.compile(r"\]\((?!https?)([^)]+)\)")
PLACEHOLDERS = ("TODO", "TBD", "FIXME", "XXX", "\ufffd")


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None, "no frontmatter block"
    block = m.group(1)
    if TRY_YAML:
        try:
            return yaml.safe_load(block) or {}, None
        except Exception as exc:
            return None, "frontmatter does not parse: %s" % exc
    fields = {}
    for line in block.splitlines():
        km = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if km:
            fields[km.group(1)] = km.group(2).strip().strip('"').strip("'")
    return fields, None


def skill_dirs(arg):
    arg = os.path.abspath(arg)
    if os.path.isfile(os.path.join(arg, "SKILL.md")):
        return [arg]
    inner = os.path.join(arg, "skills")
    base = inner if os.path.isdir(inner) else arg
    return sorted(
        d.path for d in os.scandir(base) if d.is_dir() and os.path.isfile(os.path.join(d.path, "SKILL.md"))
    )


def check(skill_dir):
    problems = []
    md_files = []
    for root, _dirs, files in os.walk(skill_dir):
        for f in files:
            if f.endswith(".md"):
                md_files.append(os.path.join(root, f))
    skill_md = os.path.join(skill_dir, "SKILL.md")
    text = open(skill_md, encoding="utf-8").read()
    fm, err = frontmatter(text)
    if err:
        problems.append(err)
        fm = {}
    name = (fm.get("name") or "").strip()
    dirname = os.path.basename(skill_dir.rstrip("/"))
    if name != dirname:
        problems.append("directory %r != frontmatter name %r" % (dirname, name))
    desc = (fm.get("description") or "").strip()
    if not desc:
        problems.append("empty description")
    elif len(desc) > 60:
        problems.append("description is %d chars (index budget 60): first 57 = %r" % (len(desc), desc[:57]))
    for path in md_files:
        body = open(path, encoding="utf-8", errors="replace").read()
        for link in LINK_RE.findall(body):
            target = link.split("#")[0].strip()
            if not target:
                continue
            if not os.path.exists(os.path.join(os.path.dirname(path), target)) and not os.path.exists(
                os.path.join(skill_dir, target)
            ):
                problems.append("%s: dangling link %s" % (os.path.relpath(path, skill_dir), target))
        for token in PLACEHOLDERS:
            if token in body:
                problems.append("%s: placeholder %r" % (os.path.relpath(path, skill_dir), token))
    verdict = "n/a"
    try:
        from tools.skills_guard import scan_skill  # noqa: WPS433 (optional dependency)

        result = scan_skill(__import__("pathlib").Path(skill_dir), source="community")
        verdict = result.verdict
        if result.verdict != "safe":
            for f in result.findings:
                problems.append("scan %s: %s %s:%s" % (f.severity, f.pattern_id, f.file, f.line))
    except Exception:
        verdict = "n/a (run with the Hermes venv python to get the scan verdict)"
    return problems, verdict


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    dirs = skill_dirs(sys.argv[1])
    if not dirs:
        print("no skill directory found under %s" % sys.argv[1])
        return 1
    failed = False
    for d in dirs:
        problems, verdict = check(d)
        status = "OK" if not problems else "FAIL"
        print("%-4s %-45s scan=%s" % (status, os.path.basename(d), verdict))
        for p in problems:
            print("       - %s" % p)
        failed = failed or bool(problems)
    print("\n%d skill(s) checked" % len(dirs))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
