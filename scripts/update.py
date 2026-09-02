#!/usr/bin/env python3
"""Refresh the live parts of the profile README: the Discord badge (members
online) and the activity card (last 12 months), then recompose the activity
band around the card (scripts/band.py).

Run it from the repo root, then commit what changed:

    python3 scripts/update.py && git add -A && git commit -m "Refresh stats" && git push

Needs: python3 (stdlib only) and the GitHub CLI signed in as the profile
owner (`gh auth status`). Private contributions are counted because the
GraphQL call runs with your own token; nothing is stored in the repo or on
GitHub. Language shares are byte-weighted over repos you own that were
pushed in the last 12 months; organisation repos are left out on purpose.
"""
import collections, datetime, json, re, subprocess, sys, urllib.request, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONT = '-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif'
DISCORD_INVITE = 'SnphaaU'
DISCORD_GUILD = '746155721392914442'
THEME = {'light': dict(fa=.22, g1=.70, g2=.25, s1=.95, s2=.35, sh=.10, tint='#7d8fa6', fg='#3b4552', ink='#1f2933', mut='#5c6773', acc='#3b82f6'),
         'dark':  dict(fa=.16, g1=.22, g2=.04, s1=.45, s2=.08, sh=.35, tint='#ffffff', fg='#d0d7de', ink='#e6edf3', mut='#9aa4b2', acc='#79b8ff')}
DISCORD_PATH = None  # filled from badges/light/discord.svg so the logo never drifts

# ---------- data ----------
def discord_online():
    for url, key in ((f'https://discord.com/api/v10/invites/{DISCORD_INVITE}?with_counts=true', 'approximate_presence_count'),
                     (f'https://discord.com/api/guilds/{DISCORD_GUILD}/widget.json', 'presence_count')):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'profile-readme-updater'}), timeout=15) as r:
                n = json.load(r).get(key)
                if isinstance(n, int): return n
        except Exception as e:
            print(f'discord: {url.split("/")[-1].split("?")[0]} failed: {e}', file=sys.stderr)
    return None

def github_stats():
    q = '{ viewer { contributionsCollection { totalCommitContributions totalPullRequestContributions contributionCalendar { totalContributions weeks { contributionDays { contributionCount date } } } } repositories(first: 100, affiliations: [OWNER], ownerAffiliations: [OWNER], isFork: false) { nodes { nameWithOwner pushedAt languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } } } } } }'
    out = subprocess.run(['gh', 'api', 'graphql', '-f', f'query={q}'], capture_output=True, text=True)
    if out.returncode: sys.exit('gh api graphql failed: ' + out.stderr.strip())
    return json.loads(out.stdout)['data']['viewer']

# ---------- drawing ----------
def glass_defs(uid, W, H, rx, t, blur):
    p = THEME[t]
    return f'''<defs>
<clipPath id="c{uid}"><rect x="1" y="1" width="{W-2}" height="{H-2}" rx="{rx}"/></clipPath>
<linearGradient id="g{uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="{p['g1']}"/><stop offset="1" stop-color="#fff" stop-opacity="{p['g2']}"/></linearGradient>
<linearGradient id="s{uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="{p['s1']}"/><stop offset="1" stop-color="#fff" stop-opacity="{p['s2']}"/></linearGradient>
<filter id="b{uid}" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="{blur}"/></filter>
<filter id="d{uid}" x="-20%" y="-20%" width="140%" height="160%"><feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#000" flood-opacity="{p['sh']}"/></filter>
</defs>'''

def glass_body(uid, W, H, rx, t, glare, ellipse):
    p = THEME[t]
    return f'''<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="{rx}" fill="{p['tint']}" fill-opacity="{p['fa']}" filter="url(#d{uid})"/>
<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="{rx}" fill="url(#g{uid})"/>
<g clip-path="url(#c{uid})">{ellipse.replace('OP', str(glare))}</g>
<rect x="1.5" y="1.5" width="{W-3}" height="{H-3}" rx="{rx-.5}" fill="none" stroke="url(#s{uid})" stroke-width="1"/>'''

def text_width(s): return sum(9.0 if ch.isupper() or ch.isdigit() else 6.2 if ch == ' ' else 7.6 for ch in s)

def discord_badge(t, online):
    p = THEME[t]; label, value = 'DISCORD', (f'{online} ONLINE' if online is not None else None)
    H = 32; lw = text_width(label); vw = text_width(value) if value else 0
    x_logo = 12; x_label = x_logo + 25; x_div = x_label + lw + 10; x_value = x_div + 10
    W = int((x_value + vw + 12) if value else (x_label + lw + 13))
    ell = f'<ellipse cx="{W*0.3:.0f}" cy="2" rx="{W*0.45:.0f}" ry="9" fill="#fff" opacity="OP" filter="url(#b)"/>'
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">', glass_defs('', W, H, 9, t, 6), glass_body('', W, H, 9, t, .5, ell),
         f'<g transform="translate({x_logo} 8) scale(0.6667)"><path d="{DISCORD_PATH}" fill="{p["fg"]}"/></g>',
         f'<text x="{x_label}" y="20.5" font-family="{FONT}" font-size="11.5" font-weight="700" letter-spacing="1.2" fill="{p["fg"]}">{label}</text>']
    if value:
        o.append(f'<line x1="{x_div}" y1="8" x2="{x_div}" y2="{H-8}" stroke="{p["fg"]}" stroke-opacity=".35" stroke-width="1"/>')
        o.append(f'<text x="{x_value}" y="20.5" font-family="{FONT}" font-size="11.5" font-weight="700" letter-spacing="1.2" fill="{p["fg"]}">{value}</text>')
    o.append('</svg>'); return '\n'.join(o)

def activity_card(t, d):
    p = THEME[t]; c = d['contributionsCollection']
    weeks = c['contributionCalendar']['weeks']; wk = [sum(x['contributionCount'] for x in w['contributionDays']) for w in weeks][-52:]
    days = [x for w in weeks for x in w['contributionDays']]; active = sum(1 for x in days if x['contributionCount'] > 0)
    since = (datetime.date.today() - datetime.timedelta(days=365)).isoformat()
    lang = collections.Counter()
    for r in d['repositories']['nodes']:
        if r['pushedAt'][:10] < since: continue
        for e in r['languages']['edges']: lang[(e['node']['name'], e['node']['color'])] += e['size']
    tot = sum(lang.values()) or 1; top = lang.most_common(5)
    W, H, rx = 766, 190, 16
    ell = '<ellipse cx="440" cy="0" rx="260" ry="56" fill="#fff" opacity="OP" filter="url(#b)"/>'
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}">', glass_defs('', W, H, rx, t, 14), glass_body('', W, H, rx, t, .3, ell)]
    stats = [('Contributions', c['contributionCalendar']['totalContributions']), ('Commits', c['totalCommitContributions']), ('Pull requests', c['totalPullRequestContributions']), ('Active days', active)]
    for i, (lab, val) in enumerate(stats):
        x = 28 + i * 118
        o.append(f'<text x="{x}" y="52" font-size="26" font-weight="700" fill="{p["ink"]}" letter-spacing="-.5">{val}</text>')
        o.append(f'<text x="{x}" y="70" font-size="10.5" font-weight="600" fill="{p["mut"]}" letter-spacing="1">{lab.upper()}</text>')
    o.append(f'<text x="28" y="28" font-size="10.5" font-weight="600" fill="{p["mut"]}" letter-spacing="1">LAST 12 MONTHS</text>')
    bx, by, bw, bh = 500, 26, 4.2, 52; mx = max(wk) or 1; gap = (W - 28 - bx) / 52
    for i, v in enumerate(wk):
        hh = max(2, v / mx * bh); x = bx + i * gap; y = by + bh - hh
        o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw}" height="{hh:.1f}" rx="1.5" fill="{p["acc"]}" fill-opacity="{.35+.65*v/mx:.2f}"><animate attributeName="height" from="0" to="{hh:.1f}" dur=".7s" begin="{i*0.012:.3f}s" fill="freeze"/><animate attributeName="y" from="{by+bh}" to="{y:.1f}" dur=".7s" begin="{i*0.012:.3f}s" fill="freeze"/></rect>')
    o.append(f'<text x="{W-28}" y="{by+bh+16}" text-anchor="end" font-size="10.5" font-weight="600" fill="{p["mut"]}" letter-spacing="1">CONTRIBUTIONS PER WEEK</text>')
    lx, ly, lw, lh = 28, 112, W - 56, 8; x = lx
    o.append(f'<text x="28" y="102" font-size="10.5" font-weight="600" fill="{p["mut"]}" letter-spacing="1">LANGUAGES</text>')
    o.append(f'<rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" rx="4" fill="{p["ink"]}" fill-opacity=".08"/>')
    o.append(f'<defs><clipPath id="lb"><rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" rx="4"/></clipPath></defs><g clip-path="url(#lb)">')
    for (n, col), s in top:
        w_ = lw * s / tot; o.append(f'<rect x="{x:.1f}" y="{ly}" width="{w_:.1f}" height="{lh}" fill="{col or "#8b949e"}"/>'); x += w_
    o.append('</g>'); x = 28
    for (n, col), s in top:
        label = f'{n} {s/tot*100:.0f}%'
        o.append(f'<circle cx="{x+5}" cy="{ly+30}" r="5" fill="{col or "#8b949e"}"/><text x="{x+16}" y="{ly+34}" font-size="12" fill="{p["ink"]}">{label}</text>')
        x += 16 + len(label) * 6.8 + 22
    o.append(f'<text x="{W-28}" y="{H-14}" text-anchor="end" font-size="9.5" fill="{p["mut"]}">updated {datetime.date.today().isoformat()}</text>')
    o.append('</svg>'); return '\n'.join(o)

def main():
    global DISCORD_PATH
    DISCORD_PATH = re.search(r' d="([^"]+)"', (ROOT / 'badges/light/discord.svg').read_text()).group(1)
    online = discord_online(); print('discord online:', online)
    d = github_stats(); print('contributions:', d['contributionsCollection']['contributionCalendar']['totalContributions'])
    for t in ('light', 'dark'):
        (ROOT / f'badges/{t}/discord.svg').write_text(discord_badge(t, online))
        (ROOT / f'stats-{t}.svg').write_text(activity_card(t, d))
    print('written: badges/*/discord.svg, stats-light.svg, stats-dark.svg')
    import band
    band.build()

if __name__ == '__main__': main()
