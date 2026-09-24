"""Render a local preview from a GitHub data snapshot, without publishing anything."""

import json
from datetime import date
from pathlib import Path

from generate_profile import ROOT, render_cards


def main():
    output = ROOT / '.preview'
    snapshot = json.loads((output / 'profile-data.json').read_text(encoding='utf-8'))
    cards = render_cards(snapshot['collection'], snapshot['repositories'],
                         date.fromisoformat(snapshot['date']))
    for name, svg in cards.items():
        (output / name).write_text(svg, encoding='utf-8')
    page = '''<!doctype html>
<html lang="pt-BR"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Matheus Braga | Preview dos cards</title>
<style>
* { box-sizing: border-box; }
body { margin: 0; background: #0d1117; color: #e6edf3; font-family: Segoe UI, Arial, sans-serif; }
main { max-width: 960px; margin: 32px auto; padding: 0 40px 32px; }
header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 26px; }
h1 { font-size: 20px; margin: 0 0 5px; font-weight: 600; }
header p { margin: 0; color: #8b949e; font-size: 12px; }
.badge { color: #8b949e; border: 1px solid #30363d; padding: 5px 10px; border-radius: 20px; font-size: 11px; }
h2 { font-size: 18px; margin: 24px 0 16px; padding-bottom: 10px; border-bottom: 1px solid #21262d; }
.row { display: flex; gap: 20px; }
.row img { width: calc((100% - 20px) / 2); }
img { width: 100%; height: auto; display: block; }
footer { font-size: 11px; color: #8b949e; margin-top: 18px; }
@media(max-width: 620px) { main { padding: 0 16px; } .row { flex-direction: column; } .row img { width: 100%; } }
</style>
<main>
<header><div><h1>Matheus Braga</h1><p>GitHub profile cards</p></div><span class="badge">PRÉVIA LOCAL</span></header>
<h2>GitHub Stats</h2>
<div class="row"><img src="github-stats.svg" alt="GitHub Stats"><img src="top-languages.svg" alt="Most Used Languages"></div>
<h2>GitHub Streak</h2><img src="github-streak.svg" alt="GitHub Streak">
<h2>Contribution Activity</h2><img src="contribution-activity.svg" alt="Contribution Activity">
<footer>Dados reais do GitHub. Prévia local; nenhuma alteração publicada.</footer>
</main></html>'''
    (output / 'index.html').write_text(page, encoding='utf-8')
    print(f'Preview ready: {output / "index.html"}')


if __name__ == '__main__':
    main()
