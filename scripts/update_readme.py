"""Refresh the live sections of the profile README.

- KEWR weather: latest METAR from the aviationweather.gov Data API
- Recent activity: latest public GitHub events for the profile owner
"""
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

README = "README.md"
USER = os.environ.get("GH_USER", "thongteevee")
STATION = "KEWR"
UA = {"User-Agent": f"{USER}-profile-readme"}


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def replace_section(text, name, body):
    pattern = re.compile(rf"(<!-- {name}:START -->)(.*?)(<!-- {name}:END -->)", re.S)
    return pattern.sub(lambda m: f"{m.group(1)}\n{body}\n{m.group(3)}", text)


def weather_section():
    data = get_json(f"https://aviationweather.gov/api/data/metar?ids={STATION}&format=json")
    if not data:
        raise ValueError("no METAR returned")
    m = data[0]
    parts = []
    cat = m.get("fltCat")
    if cat:
        parts.append(f"**{cat}**")
    wdir, wspd, wgst = m.get("wdir"), m.get("wspd"), m.get("wgst")
    if wspd is not None:
        if wspd == 0:
            wind = "calm"
        else:
            d = "variable" if wdir in (None, "VRB") else f"{int(wdir):03d}°"
            wind = f"{d} at {wspd} kt" + (f", gusting {wgst}" if wgst else "")
        parts.append(f"wind {wind}")
    if m.get("visib") is not None:
        parts.append(f"visibility {m['visib']} SM")
    if m.get("temp") is not None:
        parts.append(f"{round(m['temp'])}°C")
    if m.get("altim") is not None:
        parts.append(f"altimeter {m['altim'] * 0.02953:.2f} inHg")
    stamp = datetime.now(timezone.utc).strftime("%b %d, %H:%MZ")
    return (
        f"Newark Liberty ({STATION}): " + " · ".join(parts) + "\n\n"
        f"```\n{m.get('rawOb', '').strip()}\n```\n"
        f"<sub>Updated {stamp} from aviationweather.gov</sub>"
    )


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
    for name, fn in (("WEATHER", weather_section), ("ACTIVITY", activity_section)):
        try:
            text = replace_section(text, name, fn())
        except Exception as exc:  # keep the last good content if a source is down
            print(f"{name} skipped: {exc}")
    open(README, "w", encoding="utf-8").write(text)


if __name__ == "__main__":
    main()
