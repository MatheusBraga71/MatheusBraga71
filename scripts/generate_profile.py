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
          edges { size node { name } }
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


def text(x, y, value, size=14, color="#c9d1d9"):
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}">'
            f'{escape(str(value))}</text>')


def card(title, subtitle, body, width=460, height=200):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">'
        f'<title id="title">{escape(title)}</title><desc id="desc">{escape(subtitle)}</desc>'
        f'<rect width="{width}" height="{height}" rx="12" fill="#0d1117"/>'
        '<g font-family="Segoe UI,Arial,sans-serif">'
        + text(24, 32, title, 20, "#58a6ff")
        + text(24, 54, subtitle, 11, "#8b949e") + body + '</g></svg>\n'
    )


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
    period = f'Last 365 days | Updated {today} UTC'
    rows = [
        ("Contributions", collection["contributionCalendar"]["totalContributions"]),
        ("Commits", collection["totalCommitContributions"]),
        ("Pull requests", collection["totalPullRequestContributions"]),
        ("Issues", collection["totalIssueContributions"]),
        ("Code reviews", collection["totalPullRequestReviewContributions"]),
    ]
    body = ''.join(text(24, 82 + i * 23, label) + text(365, 82 + i * 23, f'{value:,}')
                   for i, (label, value) in enumerate(rows))
    cards = {"github-stats.svg": card("GitHub Stats", period, body)}

    languages = Counter()
    for repo in repositories:
        if repo["languages"]["pageInfo"]["hasNextPage"]:
            raise RuntimeError("Repository exceeds 100 languages; refusing partial totals")
        for edge in repo["languages"]["edges"]:
            languages[edge["node"]["name"]] += edge["size"]
    total = sum(languages.values())
    body = ''
    for i, (language, size) in enumerate(languages.most_common(8)):
        x, y = 24 + (i % 2) * 218, 83 + (i // 2) * 30
        body += text(x, y, f'{language}: {size / total:.1%}', 12)
        body += f'<rect x="{x}" y="{y + 5}" width="{190 * size / total:.2f}" height="4" rx="2" fill="#58a6ff"/>'
    if not total:
        body = text(24, 105, "No public language data available.")
    cards["top-languages.svg"] = card(
        "Most Used Languages", "By bytes | Public owned repositories, excluding forks", body)

    current, longest = streaks(days)
    body = ''
    for x, value, label in [(24, current, "Current streak"),
                             (224, longest, "Longest in period"),
                             (424, sum(count > 0 for _, count in days), "Active days")]:
        body += text(x, 106, value, 30, "#58a6ff") + text(x, 136, label)
    cards["github-streak.svg"] = card("GitHub Streak", period, body, width=650, height=160)

    recent = days[-30:]
    peak = max(1, max(count for _, count in recent))
    body = text(24, 78, f'{sum(count for _, count in recent):,} contributions | Daily peak: {peak if any(c for _, c in recent) else 0}', 12)
    body += '<line x1="30" y1="210" x2="750" y2="210" stroke="#30363d"/>'
    for i, (day, count) in enumerate(recent):
        height = count / peak * 115
        body += (f'<rect x="{30 + i * 24}" y="{210 - height:.2f}" width="16" '
                 f'height="{height:.2f}" rx="3" fill="#58a6ff">'
                 f'<title>{day}: {count} contributions</title></rect>')
        if i % 7 == 0:
            body += text(30 + i * 24, 232, day.strftime("%d/%m"), 10)
    cards["contribution-activity.svg"] = card(
        "Contribution Activity", f'Last 30 days | Updated {today} UTC', body, width=780, height=250)
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
