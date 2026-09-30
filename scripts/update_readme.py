"""Refresh the recent activity section of the profile README."""
import json
import os
import re
import urllib.request

README = "README.md"
USER = os.environ.get("GH_USER", "thongteevee")
UA = {"User-Agent": f"{USER}-profile-readme"}


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def replace_section(text, name, body):
    pattern = re.compile(rf"(<!-- {name}:START -->)(.*?)(<!-- {name}:END -->)", re.S)
    return pattern.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(3)}", text)


def describe(e):
    repo = e["repo"]["name"]
    link = f"[{repo}](https://github.com/{repo})"
    p, t = e.get("payload", {}), e["type"]
    if t == "PushEvent":
        n = p.get("size") or len(p.get("commits", [])) or 1
        return f"⬆️ Pushed {n} commit{'s' if n != 1 else ''} to {link}"
    if t == "CreateEvent" and p.get("ref_type") == "repository":
        return f"✨ Created {link}"
    if t == "CreateEvent" and p.get("ref_type") == "branch":
        return f"🌿 Created branch `{p.get('ref')}` in {link}"
    if t == "PullRequestEvent":
        pr = p["pull_request"]
        verb = "Merged" if p.get("action") == "closed" and pr.get("merged") else p.get("action", "").capitalize()
        return f"🔀 {verb} PR [#{pr['number']}]({pr['html_url']}) in {link}"
    if t == "IssuesEvent":
        i = p["issue"]
        return f"📝 {p.get('action', '').capitalize()} issue [#{i['number']}]({i['html_url']}) in {link}"
    if t == "ReleaseEvent":
        return f"🚀 Released {p['release'].get('tag_name', '')} in {link}"
    if t == "WatchEvent":
        return f"⭐ Starred {link}"
    if t == "ForkEvent":
        return f"🍴 Forked {link}"
    return None


def activity_section():
    events = get_json(
        f"https://api.github.com/users/{USER}/events/public?per_page=100",
        {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"} if os.environ.get("GITHUB_TOKEN") else None,
    )
    lines = []
    for e in events:
        if e["repo"]["name"].lower() == f"{USER}/{USER}".lower():
            continue  # skip the profile repo itself
        line = describe(e)
        if line and line not in lines:
            lines.append(line)
        if len(lines) == 5:
            break
    if not lines:
        return "_Nothing public yet this month._"
    return "\n".join(f"{i}. {l}" for i, l in enumerate(lines, 1))


def main():
    text = open(README, encoding="utf-8").read()
    for name, fn in (("ACTIVITY", activity_section),):
        try:
            text = replace_section(text, name, fn())
        except Exception as exc:  # keep the last good content if a source is down
            print(f"{name} skipped: {exc}")
    open(README, "w", encoding="utf-8").write(text)


if __name__ == "__main__":
    main()
