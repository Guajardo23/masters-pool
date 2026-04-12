"""Generate a static HTML leaderboard site for the Masters Pool.

Usage:
    python generate_site.py                  # Pre-tournament or projected from standings.json
    python generate_site.py --final          # Use earnings.json as final results

Data files (same directory):
    standings.json   - nightly updates: golfer positions + round info
    earnings.json    - final earnings (after Sunday)

standings.json format:
{
    "round": "Round 1",
    "status": "Complete",
    "golfers": {
        "Scottie Scheffler": {"position": "T3", "score": "-4", "today": "-4"},
        "Rory McIlroy": {"position": "12", "score": "-1", "today": "-1"},
        "Jordan Spieth": {"position": "MC", "score": "+6", "today": ""}
    }
}

position values: "1", "T3", "T15", "MC", "WD", "DQ", "CUT"
"""
import json, os, sys
from datetime import datetime

# ── Pool Data ──────────────────────────────────────────────
entries = [
    ("JJ",      ["Scottie Scheffler", "Rory McIlroy", "Jordan Spieth", "Tommy Fleetwood", "Justin Rose"]),
    ("Pat",     ["Scottie Scheffler", "Rory McIlroy", "Jon Rahm", "Xander Schauffele", "Tommy Fleetwood"]),
    ("Brandon", ["Cameron Young", "Bryson DeChambeau", "Jon Rahm", "Matt Fitzpatrick", "Rory McIlroy"]),
    ("Josh",    ["Scottie Scheffler", "Ludvig Åberg", "Bryson DeChambeau", "Jon Rahm", "Cameron Young"]),
    ("Billy",   ["Scottie Scheffler", "Xander Schauffele", "Matt Fitzpatrick", "Jon Rahm", "Ludvig Åberg"]),
    ("Milo",    ["Rory McIlroy", "Justin Rose", "Patrick Reed", "Tommy Fleetwood", "Jacob Bridgeman"]),
    ("Ben",     ["Scottie Scheffler", "Ludvig Åberg", "Matt Fitzpatrick", "Jacob Bridgeman", "Tommy Fleetwood"]),
    ("Gabe",    ["Jon Rahm", "Tommy Fleetwood", "Xander Schauffele", "Bryson DeChambeau", "Ludvig Åberg"]),
    ("Paul",    ["Marco Penge", "Justin Rose", "Jake Knapp", "Maverick McNealy", "Russell Henley"]),
    ("Geoff",   ["Rory McIlroy", "Jon Rahm", "Akshay Bhatia", "Bryson DeChambeau", "Brooks Koepka"]),
    ("Benny",   ["Scottie Scheffler", "Jon Rahm", "Bryson DeChambeau", "Rory McIlroy", "Xander Schauffele"]),
    ("Nick",    ["Ludvig Åberg", "Xander Schauffele", "Jon Rahm", "Tommy Fleetwood", "Cameron Young"]),
    ("Brian",   ["Patrick Reed", "Jon Rahm", "Xander Schauffele", "Akshay Bhatia", "Justin Rose"]),
]

# ── 2026 Masters purse: $22.5M total. Actual payouts from PGA Tour ──
PAYOUT = {
    1: 4500000, 2: 2430000, 3: 1530000, 4: 1080000, 5: 900000,
    6: 810000, 7: 753750, 8: 697500, 9: 652500, 10: 607500,
    11: 562500, 12: 517500, 13: 472500, 14: 427500, 15: 405000,
    16: 382500, 17: 360000, 18: 337500, 19: 315000, 20: 292500,
    21: 270000, 22: 252000, 23: 234000, 24: 216000, 25: 198000,
    26: 180000, 27: 173250, 28: 166500, 29: 159750, 30: 153000,
    31: 146250, 32: 139500, 33: 132750, 34: 127125, 35: 121500,
    36: 115875, 37: 110250, 38: 105750, 39: 101250, 40: 96750,
    41: 92250, 42: 87750, 43: 83250, 44: 78750, 45: 74250,
    46: 69750, 47: 65250, 48: 61650, 49: 58500, 50: 56700,
}
MC_PAYOUT = 25000  # all professionals who miss the cut get $25K

def parse_position(pos_str):
    if not pos_str:
        return None
    pos_str = pos_str.strip().upper()
    if pos_str in ("MC", "CUT", "WD", "DQ"):
        return None
    return int(pos_str.replace("T", ""))

def compute_projected_earnings(standings):
    """Compute earnings for each golfer using tie-splitting rules.
    
    For ties: pool the payouts for the tied positions and split evenly.
    E.g., two players T5 → pool 5th ($900K) + 6th ($810K) = $1.71M → $855K each.
    """
    # Group golfers by position
    from collections import defaultdict
    pos_groups = defaultdict(list)
    no_position = []
    mc_golfers = []

    for name, gdata in standings.items():
        pos_str = gdata.get("position", "").strip().upper()
        if not pos_str:
            no_position.append(name)
        elif pos_str in ("MC", "CUT", "WD", "DQ"):
            mc_golfers.append(name)
        else:
            pos_num = int(pos_str.replace("T", ""))
            pos_groups[pos_num].append(name)

    earnings_map = {}

    for pos_num, names in pos_groups.items():
        count = len(names)
        # Pool payouts for positions pos_num through pos_num + count - 1
        total_pool = 0
        for i in range(count):
            p = pos_num + i
            total_pool += PAYOUT.get(p, PAYOUT.get(50, 56700))
        per_player = int(total_pool / count)
        for name in names:
            earnings_map[name] = per_player

    for name in mc_golfers:
        earnings_map[name] = MC_PAYOUT

    # Golfers with no position (haven't teed off) get $0
    for name in no_position:
        earnings_map[name] = 0

    return earnings_map

# ── Load data files ────────────────────────────────────────
base_dir = os.path.dirname(os.path.abspath(__file__))
final_mode = "--final" in sys.argv

standings = {}
round_info = ""
round_status = ""
standings_file = os.path.join(base_dir, "standings.json")
if os.path.exists(standings_file):
    with open(standings_file, "r", encoding="utf-8") as f:
        sdata = json.load(f)
    standings = sdata.get("golfers", {})
    round_info = sdata.get("round", "")
    round_status = sdata.get("status", "")

earnings = {}
earnings_file = os.path.join(base_dir, "earnings.json")
if os.path.exists(earnings_file):
    with open(earnings_file, "r", encoding="utf-8") as f:
        earnings = json.load(f)

# ── Determine mode ─────────────────────────────────────────
use_projected = bool(standings) and not final_mode and not earnings
use_final = bool(earnings) or final_mode

# Pre-compute projected earnings with tie-splitting
projected_map = {}
if use_projected:
    projected_map = compute_projected_earnings(standings)

# ── Calculate totals ───────────────────────────────────────
results = []
for name, picks in entries:
    pick_details = []
    total = 0
    for golfer in picks:
        if use_final:
            amt = earnings.get(golfer, 0)
        elif use_projected:
            amt = projected_map.get(golfer, 0)
        else:
            amt = 0
        gdata = standings.get(golfer, {})
        pick_details.append({
            "golfer": golfer,
            "amount": amt,
            "position": gdata.get("position", ""),
            "score": gdata.get("score", ""),
            "today": gdata.get("today", ""),
        })
        total += amt
    results.append({"name": name, "picks": pick_details, "total": total})

results.sort(key=lambda x: x["total"], reverse=True)

for i, r in enumerate(results):
    if i == 0:
        r["rank"] = 1
    elif r["total"] == results[i - 1]["total"]:
        r["rank"] = results[i - 1]["rank"]
    else:
        r["rank"] = i + 1

has_data = use_projected or use_final
updated = datetime.now().strftime("%B %d, %Y at %I:%M %p")

# ── Helpers ────────────────────────────────────────────────
def fmt_money(amt):
    if amt == 0:
        return "-"
    return f"${amt:,.0f}"

def rank_badge(rank):
    if rank == 1: return '<span class="rank gold">\U0001f947</span>'
    if rank == 2: return '<span class="rank silver">\U0001f948</span>'
    if rank == 3: return '<span class="rank bronze">\U0001f949</span>'
    return f'<span class="rank">{rank}</span>'

def pos_badge(pos):
    if not pos:
        return ""
    up = pos.strip().upper()
    if up in ("MC", "CUT"):
        return '<span class="pos mc">MC</span>'
    if up in ("WD", "DQ"):
        return f'<span class="pos mc">{up}</span>'
    num = parse_position(pos)
    if num and num <= 1:
        return f'<span class="pos pos-leader">{pos}</span>'
    if num and num <= 10:
        return f'<span class="pos pos-top10">{pos}</span>'
    return f'<span class="pos">{pos}</span>'

def score_display(score, today):
    parts = []
    if score:
        parts.append(score)
    if today:
        parts.append(f"({today})")
    return " ".join(parts)

# ── Banner ─────────────────────────────────────────────────
if use_final:
    banner_text = "\u26f3 Final Results"
    banner_class = "status-banner final"
elif use_projected:
    label = round_info or "In Progress"
    if round_status:
        label += f" \u2014 {round_status}"
    banner_text = f"\u26f3 Projected Standings: {label}"
    banner_class = "status-banner projected"
else:
    banner_text = "\u26f3 Tournament starts Thursday. Earnings will be updated throughout the weekend."
    banner_class = "status-banner"

money_label = "Projected" if use_projected else "Total"

# ── Build HTML ──────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>2026 Masters Pool</title>
<style>
  :root {{
    --masters-green: #006747;
    --dark-green: #004d35;
    --masters-yellow: #f2c75c;
    --bg: #f8f9fa;
    --card-bg: #ffffff;
    --text: #1a1a1a;
    --text-muted: #6c757d;
    --border: #dee2e6;
    --red: #dc3545;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg); color: var(--text); min-height: 100vh;
  }}
  .header {{
    background: linear-gradient(135deg, var(--masters-green), var(--dark-green));
    color: white; padding: 2rem 1rem; text-align: center;
  }}
  .header h1 {{ font-size: 2rem; font-weight: 700; margin-bottom: 0.25rem; }}
  .header .subtitle {{ font-size: 1rem; opacity: 0.85; }}
  .header .year {{
    font-size: 3rem; font-weight: 800;
    color: var(--masters-yellow); letter-spacing: 2px;
  }}
  .container {{ max-width: 960px; margin: 0 auto; padding: 1.5rem 1rem; }}
  .updated {{ text-align: center; color: var(--text-muted); font-size: 0.85rem; margin-bottom: 1rem; }}

  .status-banner {{
    background: var(--masters-yellow); color: #333;
    text-align: center; padding: 0.7rem;
    font-weight: 600; font-size: 0.95rem;
    border-radius: 8px; margin-bottom: 1.5rem;
  }}
  .status-banner.projected {{ background: #d4edda; color: #155724; }}
  .status-banner.final {{ background: var(--masters-green); color: white; font-size: 1.1rem; }}

  /* Leaderboard */
  .leaderboard {{
    width: 100%; border-collapse: collapse;
    background: var(--card-bg); border-radius: 12px;
    overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    margin-bottom: 2rem;
  }}
  .leaderboard th {{
    background: var(--masters-green); color: white;
    padding: 0.75rem 1rem; text-align: left;
    font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px;
  }}
  .leaderboard th.money {{ text-align: right; }}
  .leaderboard td {{
    padding: 0.65rem 1rem; border-bottom: 1px solid var(--border); font-size: 0.95rem;
  }}
  .leaderboard td.money {{
    text-align: right; font-weight: 700;
    font-variant-numeric: tabular-nums; font-size: 1rem;
    color: var(--masters-green);
  }}
  .leaderboard tr:last-child td {{ border-bottom: none; }}
  .leaderboard tr:hover {{ background: #f0faf0; }}
  .leaderboard tr.top {{ background: #f0f9f0; }}
  .rank {{
    display: inline-block; min-width: 2rem;
    text-align: center; font-weight: 700; font-size: 1.1rem;
  }}
  .contestant-name {{ font-weight: 600; font-size: 1.05rem; }}
  .best-golfer {{ color: var(--text-muted); font-size: 0.8rem; margin-left: 0.5rem; }}

  /* Pick cards */
  .picks-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(310px, 1fr));
    gap: 1rem; margin-bottom: 2rem;
  }}
  .pick-card {{
    background: var(--card-bg); border-radius: 10px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06); overflow: hidden;
  }}
  .pick-card-header {{
    background: var(--masters-green); color: white;
    padding: 0.6rem 1rem; display: flex;
    justify-content: space-between; align-items: center;
  }}
  .pick-card-header .name {{ font-weight: 700; font-size: 1.05rem; }}
  .pick-card-header .total {{ font-weight: 600; color: var(--masters-yellow); }}
  .pick-card-header .rank-num {{
    background: var(--masters-yellow); color: #333;
    border-radius: 50%; width: 1.6rem; height: 1.6rem;
    display: inline-flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 0.8rem; margin-right: 0.5rem;
  }}
  .pick-card table {{ width: 100%; border-collapse: collapse; }}
  .pick-card td {{
    padding: 0.45rem 0.75rem; border-bottom: 1px solid #f0f0f0; font-size: 0.88rem;
  }}
  .pick-card tr:last-child td {{ border-bottom: none; }}
  .pick-card .golfer-name {{ font-weight: 500; }}
  .pick-card .score {{ color: var(--text-muted); text-align: center; min-width: 4rem; white-space: nowrap; }}
  .pick-card .score.under-par {{ color: var(--red); font-weight: 600; }}
  .pick-card .pick-amt {{
    text-align: right; font-variant-numeric: tabular-nums;
    color: var(--text-muted); min-width: 5rem;
  }}
  .pick-card .pick-amt.has-earnings {{ color: var(--masters-green); font-weight: 600; }}

  .pos {{
    display: inline-block; background: #e9ecef;
    border-radius: 4px; padding: 0.1rem 0.4rem;
    font-size: 0.75rem; font-weight: 700; margin-right: 0.35rem;
    min-width: 2rem; text-align: center;
  }}
  .pos.pos-leader {{ background: var(--masters-yellow); color: #333; }}
  .pos.pos-top10 {{ background: #d4edda; color: #155724; }}
  .pos.mc {{ background: #f8d7da; color: #721c24; }}

  .commentary {{
    background: linear-gradient(135deg, #004d35, #006747);
    color: white; border-radius: 12px; padding: 2rem;
    margin-bottom: 2rem; line-height: 1.7;
    font-family: Georgia, 'Times New Roman', serif;
  }}
  .commentary h2 {{
    color: var(--masters-yellow); font-size: 1.4rem;
    margin-bottom: 1rem; font-style: italic;
  }}
  .commentary .champion {{
    color: var(--masters-yellow); font-weight: 700;
  }}
  .commentary .jab {{
    color: #f8d7da; font-style: italic;
  }}
  .commentary .sign-off {{
    margin-top: 1rem; font-size: 0.85rem;
    opacity: 0.7; text-align: right;
  }}

  .footer {{
    text-align: center; color: var(--text-muted);
    font-size: 0.8rem; padding: 2rem 0;
  }}

  @media (max-width: 600px) {{
    .header h1 {{ font-size: 1.4rem; }}
    .header .year {{ font-size: 2rem; }}
    .picks-grid {{ grid-template-columns: 1fr; }}
    .leaderboard th, .leaderboard td {{ padding: 0.5rem 0.5rem; font-size: 0.85rem; }}
  }}
</style>
</head>
<body>

<div class="header">
  <div class="year">2026</div>
  <h1>Masters Pool</h1>
  <div class="subtitle">Augusta National Golf Club</div>
</div>

<div class="container">
  <div class="updated">Last updated: {updated}</div>
  <div class="{banner_class}">{banner_text}</div>

{'''  <div class="commentary">
    <h2>"A tradition unlike any other..."</h2>
    <p>
      And so, as the Georgia sun sets on Augusta National, a champion emerges from the azaleas.
      <span class="champion">JJ Guajardo</span> has done it. With a masterful portfolio
      anchored by Rory McIlroy\'s historic back-to-back green jacket performance and the
      ever-steady Scottie Scheffler finishing solo second, JJ\'s picks proved to be nothing
      short of brilliant. Justin Rose\'s quietly magnificent T3 finish sealed the deal;
      a $8.56 million combined haul that will be very difficult to top.
    </p>
    <p>
      Pat and Benny gave valiant efforts, carried by the McIlroy-Scheffler tandem, but
      in the end, it was JJ\'s faith in Rose and the shrewd late swap of Bryson DeChambeau
      for Jordan Spieth that made all the difference.
    </p>
    <p class="jab">
      For the record, JJ\'s victory is purely the result of superior golf knowledge
      and has absolutely nothing to do with the fact that he also happened to run the pool,
      build the website, and calculate the payouts. Nothing at all. Move along.
    </p>
    <p class="sign-off">\u2014 The 18th Tower, Augusta National</p>
  </div>\n''' if use_final else ''}
  <h2 style="margin-bottom:0.75rem;">Leaderboard</h2>
  <table class="leaderboard">
    <thead>
      <tr>
        <th style="width:3rem;">#</th>
        <th>Contestant</th>
        <th class="money">{money_label} Earnings</th>
      </tr>
    </thead>
    <tbody>
"""

for r in results:
    top_class = ' class="top"' if r["rank"] <= 3 and has_data else ""
    badge = rank_badge(r["rank"]) if has_data else str(r["rank"])
    if has_data:
        best = max(r["picks"], key=lambda p: p["amount"])
        best_note = f'<span class="best-golfer">Best: {best["golfer"]}</span>' if best["amount"] > 0 else ""
    else:
        best_note = ""
    html += f"""      <tr{top_class}>
        <td>{badge}</td>
        <td><span class="contestant-name">{r['name']}</span>{best_note}</td>
        <td class="money">{fmt_money(r['total'])}</td>
      </tr>
"""

html += """    </tbody>
  </table>

  <h2 style="margin-bottom:0.75rem;">Picks</h2>
  <div class="picks-grid">
"""

for r in results:
    html += f"""    <div class="pick-card">
      <div class="pick-card-header">
        <span><span class="rank-num">{r['rank']}</span><span class="name">{r['name']}</span></span>
        <span class="total">{fmt_money(r['total'])}</span>
      </div>
      <table>
"""
    for p in r["picks"]:
        amt_class = "pick-amt has-earnings" if p["amount"] > 0 else "pick-amt"
        pos_html = pos_badge(p["position"])
        sc = score_display(p["score"], p["today"])
        sc_class = "score under-par" if p.get("score", "").startswith("-") else "score"
        html += f'        <tr><td class="golfer-name">{pos_html}{p["golfer"]}</td>'
        if use_projected or use_final:
            html += f'<td class="{sc_class}">{sc}</td>'
        html += f'<td class="{amt_class}">{fmt_money(p["amount"])}</td></tr>\n'
    html += """      </table>
    </div>
"""

html += f"""  </div>

  <div class="footer">
    {len(entries)} contestants &middot; 5 picks each &middot; highest combined earnings wins<br>
    {"Projected earnings based on current leaderboard position and $20M purse" if use_projected else ""}
  </div>
</div>

</body>
</html>"""

out_path = os.path.join(base_dir, "index.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Saved: {out_path}")
print(f"Mode: {'PROJECTED' if use_projected else 'FINAL' if use_final else 'PRE-TOURNAMENT'}")
if use_projected:
    print(f"Round: {round_info} - {round_status}")
    print(f"Top 3: {', '.join(r['name'] + ' ' + fmt_money(r['total']) for r in results[:3])}")
