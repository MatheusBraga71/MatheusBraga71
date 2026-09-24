"""Generate standalone profile cards using only GitHub's API and Python stdlib."""

import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!, $cursor: String) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first: 50, after: $cursor, ownerAffiliations: OWNER,
                 privacy: PUBLIC, isFork: false) {
      pageInfo { hasNextPage endCursor }
      nodes {
        languages(first: 100) {
          pageInfo { hasNextPage }
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def fetch_data(login, token, today):
    start = today - timedelta(days=364)
    variables = {"login": login, "from": f"{start}T00:00:00Z",
                 "to": f"{today}T23:59:59Z", "cursor": None}
    repositories = []
    collection = None
    while True:
        request = Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": QUERY, "variables": variables}).encode(),
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json", "User-Agent": "profile-stats"},
        )
        with urlopen(request, timeout=60) as response:
            payload = json.load(response)
        if payload.get("errors"):
            raise RuntimeError(f"GitHub GraphQL errors: {payload['errors']}")
        user = payload["data"]["user"]
        if not user:
            raise RuntimeError(f"GitHub user not found: {login}")
        if collection is None:
            collection = user["contributionsCollection"]
        page = user["repositories"]
        repositories.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        variables["cursor"] = page["pageInfo"]["endCursor"]
    return collection, repositories


def text(x, y, value, size=14, color="#c9d1d9", weight=400, anchor="start"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{escape(str(value))}</text>')


def card(title, subtitle, body, width=430, height=220):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">'
        f'<title id="title">{escape(title)}</title><desc id="desc">{escape(subtitle)}</desc>'
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="10" '
        'fill="#0d1117" stroke="#30363d"/>'
        '<g font-family="Segoe UI,Arial,sans-serif">'
        + text(24, 34, title, 18, "#58a6ff", 600)
        + text(24, 55, subtitle, 10, "#8b949e") + body + '</g></svg>\n'
    )


def icon(kind, x, y, color="#58a6ff"):
    paths = {
        "commit": '<circle cx="8" cy="8" r="3"/><path d="M0 8h5m6 0h5"/>',
        "pull": '<circle cx="4" cy="3" r="2"/><circle cx="4" cy="13" r="2"/>'
                '<circle cx="13" cy="13" r="2"/><path d="M4 5v6m9 0V6a3 3 0 0 0-3-3H8m2-2L8 3l2 2"/>',
        "issue": '<circle cx="8" cy="8" r="6"/><path d="M8 4v5m0 2v1"/>',
        "review": '<path d="M2 2h12v9H8l-4 3v-3H2zM5 6l2 2 4-4"/>',
        "flame": '<path d="M8 0C9 5 14 5 14 10a6 6 0 0 1-12 0c0-3 2-5 3-6'
                 ' 0 3 1 4 2 4C9 6 9 3 8 0Z"/>',
    }
    return (f'<g transform="translate({x} {y})" fill="none" stroke="{color}" '
            f'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{paths[kind]}</g>')


def calendar_days(collection, today):
    counts = {day["date"]: day["contributionCount"]
              for week in collection["contributionCalendar"]["weeks"]
              for day in week["contributionDays"]}
    return [(today - timedelta(days=offset),
             counts.get((today - timedelta(days=offset)).isoformat(), 0))
            for offset in range(364, -1, -1)]


def streaks(days):
    longest = run = 0
    for _, count in days:
        run = run + 1 if count else 0
        longest = max(longest, run)
    # An unfinished day does not break yesterday's streak.
    completed = days if days[-1][1] else days[:-1]
    current = 0
    for _, count in reversed(completed):
        if not count:
            break
        current += 1
    return current, longest


def render_cards(collection, repositories, today):
    days = calendar_days(collection, today)
    period = f'Last 365 days · Updated {today} UTC'
    contributions = collection["contributionCalendar"]["totalContributions"]
    rows = [
        ("commit", "Total commits", collection["totalCommitContributions"]),
        ("pull", "Pull requests", collection["totalPullRequestContributions"]),
        ("issue", "Issues opened", collection["totalIssueContributions"]),
        ("review", "Code reviews", collection["totalPullRequestReviewContributions"]),
    ]
    body = ''
    for i, (kind, label, value) in enumerate(rows):
        y = 88 + i * 29
        body += icon(kind, 25, y - 12) + text(52, y, label, 13, weight=600)
        body += text(257, y, f'{value:,}', 13, weight=600, anchor="end")
    # A contributions badge, not a made-up global rank or progress score.
    body += '<circle cx="346" cy="124" r="43" fill="#111d2e" stroke="#1f6feb" stroke-width="3"/>'
    body += text(346, 133, f'{contributions:,}', 30, "#58a6ff", 600, "middle")
    body += text(346, 184, 'Contributions', 11, "#8b949e", anchor="middle")
    cards = {"github-stats.svg": card("GitHub Stats", period, body)}

    languages = Counter()
    colors = {}
    palette = ["#f1e05a", "#b07219", "#3572a5", "#f34b7d", "#3178c6", "#563d7c", "#e34c26", "#ff3e00"]
    for repo in repositories:
        if repo["languages"]["pageInfo"]["hasNextPage"]:
            raise RuntimeError("Repository exceeds 100 languages; refusing partial totals")
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            languages[name] += edge["size"]
            color = edge["node"].get("color")
            if color and re.fullmatch(r"#[0-9a-fA-F]{6}", color):
                colors[name] = color
    total = sum(languages.values())
    top = languages.most_common(8)
    body = '<defs><clipPath id="language-bar"><rect x="24" y="76" width="382" height="9" rx="4.5"/></clipPath></defs>'
    body += '<rect x="24" y="76" width="382" height="9" rx="4.5" fill="#30363d"/>'
    offset = 24
    for i, (language, size) in enumerate(top):
        color = colors.get(language, palette[i % len(palette)])
        width = size / total * 382 if total else 0
        body += (f'<rect x="{offset:.3f}" y="76" width="{width:.3f}" height="9" '
                 f'fill="{color}" clip-path="url(#language-bar)"/>')
        offset += width
        x, y = 30 + (i % 2) * 200, 113 + (i // 2) * 27
        body += f'<circle cx="{x}" cy="{y - 4}" r="4.5" fill="{color}"/>'
        label = language if len(language) <= 19 else language[:18] + '…'
        body += text(x + 12, y, label, 11, weight=600)
        body += text(x + 170, y, f'{size / total:.1%}' if total else '0.0%', 10, "#8b949e", anchor="end")
        body += f'<desc>{escape(language)}: {size / total:.1%}</desc>' if total else ''
    if not total:
        body += text(24, 120, "No public language data available.", 12, "#8b949e")
    cards["top-languages.svg"] = card("Most Used Languages", "Public repositories · By code size · Excluding forks", body)

    current, longest = streaks(days)
    start = days[0][0].strftime('%b %d, %Y')
    end = today.strftime('%b %d, %Y')
    body = '<path d="M293 82v91M587 82v91" stroke="#30363d"/>'
    body += text(147, 121, f'{contributions:,}', 36, "#e6edf3", 600, "middle")
    body += text(147, 151, 'Total contributions', 14, "#c9d1d9", 600, "middle")
    body += text(147, 177, f'{start} – {end}', 10, "#8b949e", anchor="middle")
    body += '<circle cx="440" cy="115" r="43" fill="none" stroke="#f0883e" stroke-width="2.5"/>'
    body += '<rect x="424" y="67" width="32" height="20" fill="#0d1117"/>'
    body += icon('flame', 432, 67, '#f0883e')
    body += text(440, 128, current, 34, "#e6edf3", 600, "middle")
    body += text(440, 179, 'Current streak', 14, "#f0883e", 600, "middle")
    body += text(440, 197, 'consecutive days', 10, "#8b949e", anchor="middle")
    body += text(733, 121, longest, 36, "#e6edf3", 600, "middle")
    body += text(733, 151, 'Longest streak', 14, "#c9d1d9", 600, "middle")
    body += text(733, 177, 'Within the last 365 days', 10, "#8b949e", anchor="middle")
    cards["github-streak.svg"] = card("GitHub Streak", period, body, width=880, height=220)

    recent = days[-30:]
    peak = max(1, max(count for _, count in recent))
    body = '<defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#58a6ff" stop-opacity="0.28"/><stop offset="1" stop-color="#58a6ff" stop-opacity="0.02"/></linearGradient></defs>'
    body += text(854, 34, f'{sum(count for _, count in recent):,} contributions', 12, "#8b949e", anchor="end")
    ticks = sorted({0, peak // 2, peak})
    for tick in ticks:
        y = 218 - tick / peak * 134
        body += f'<path d="M52 {y:.2f}H850" stroke="#21262d" stroke-dasharray="3 5"/>'
        body += text(39, y + 4, tick, 10, "#8b949e", anchor="end")
    coords = [(52 + i * 798 / 29, 218 - count / peak * 134) for i, (_, count) in enumerate(recent)]
    line = 'M' + ' L'.join(f'{x:.2f} {y:.2f}' for x, y in coords)
    body += f'<path d="{line} L850 218 L52 218Z" fill="url(#area)"/>'
    body += f'<path d="{line}" fill="none" stroke="#58a6ff" stroke-width="2.5" stroke-linejoin="round"/>'
    for i, ((day, count), (x, y)) in enumerate(zip(recent, coords)):
        body += (f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="#0d1117" stroke="#58a6ff" stroke-width="1.5">'
                 f'<title>{day}: {count} contributions</title></circle>')
        if i in (0, 7, 14, 21, 29):
            body += text(x, 243, day.strftime('%b %d'), 10, "#8b949e", anchor="middle")
    cards["contribution-activity.svg"] = card(
        "Contribution Activity", f'Last 30 days · Updated {today} UTC', body, width=880, height=270)
    return cards


def version_card_links(readme, cards):
    """Change each image URL only when its SVG content changes."""
    for filename, svg in cards.items():
        version = hashlib.sha256(svg.encode("utf-8")).hexdigest()[:16]
        pattern = rf'(src="\./assets/{re.escape(filename)})(?:\?[^"\s]*)?"'
        readme, count = re.subn(pattern, rf'\g<1>?v={version}"', readme)
        if count != 1:
            raise ValueError(f"Expected exactly one README image for {filename}; found {count}")
    return readme


def main():
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("Set GH_TOKEN; GitHub Actions supplies github.token automatically.")
    today = datetime.now(timezone.utc).date()
    collection, repositories = fetch_data(os.environ["PROFILE_USERNAME"], token, today)
    # Complete every request and render before touching the previous good images.
    cards = render_cards(collection, repositories, today)
    readme_path = ROOT / "README.md"
    readme = version_card_links(readme_path.read_text(encoding="utf-8"), cards)
    output = ROOT / "assets"
    output.mkdir(exist_ok=True)
    for filename, svg in cards.items():
        (output / filename).write_text(svg, encoding="utf-8")
    readme_path.write_text(readme, encoding="utf-8")
    print(f"Generated {len(cards)} cards from {len(repositories)} public repositories.")


if __name__ == "__main__":
    main()
