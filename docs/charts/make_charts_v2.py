"""Charts for the Swell deck, drawn from official data.
oni-timeline.png  <- oni.csv (NOAA CPC Oceanic Nino Index, cpc.ncep.noaa.gov/data/indices/oni.ascii.txt)
el-nino-cost-v2.png <- Callahan & Mankin, Science 2023 (via Dartmouth and ScienceDaily)"""
import csv, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "fonts")
for f in ["Lato-Regular.ttf", "Lato-Bold.ttf", "Lato-Black.ttf"]:
    fm.fontManager.addfont(os.path.join(FONTS, f))
plt.rcParams.update({"font.family": "Lato"})
NAVY="#0B3349"; INK="#16222C"; MUTED="#5A6873"; TEAL="#0E7486"; LIGHT="#8FC1CB"; RED="#D2553C"; BLUE="#4D86B8"; BG="#FAFAFA"; AMBER="#E2892A"

# ---- 1. ONI timeline 1950-2026
rows = list(csv.reader(open(os.path.join(HERE, "oni.csv"))))[1:]
xs, ys = [], []
for r in rows:
    y = int(r[0])
    for i, v in enumerate(r[1:]):
        if v:
            xs.append(y + (i + 1) / 12); ys.append(float(v))
fig, ax = plt.subplots(figsize=(13, 4.6), dpi=200)
fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
ax.fill_between(xs, ys, 0.5, where=[v >= 0.5 for v in ys], color=RED, alpha=0.9, interpolate=True, lw=0)
ax.fill_between(xs, ys, -0.5, where=[v <= -0.5 for v in ys], color=BLUE, alpha=0.85, interpolate=True, lw=0)
ax.plot(xs, ys, color="#33414C", lw=0.8)
for lv, ls in [(0.5, "--"), (-0.5, "--")]:
    ax.axhline(lv, color="#9AA7B0", lw=0.9, ls=ls)
ax.axhline(0, color="#C9D3DA", lw=0.8)
ax.set_xlim(1950, 2028); ax.set_ylim(-2.3, 3.3)
for s in ["top", "right"]: ax.spines[s].set_visible(False)
ax.spines["left"].set_color("#C9D3DA"); ax.spines["bottom"].set_color("#C9D3DA")
ax.tick_params(colors=MUTED, labelsize=12, length=0)
ax.set_ylabel("°C warmer or cooler than normal\n(central Pacific Ocean)", color=MUTED, fontsize=11.5)
def note(x, y, t, c=INK, dy=0.32, ha="center"):
    ax.annotate(t, (x, y), (x, y + dy), ha=ha, fontsize=12, fontweight="bold", color=c,
                arrowprops=dict(arrowstyle="-", color="#9AA7B0", lw=0.8))
note(1983.1, 2.14, "1982–83\n+2.1", dy=0.45)
note(1998.0, 2.37, "1997–98\n+2.4", dy=0.35)
ax.annotate("2015–16\n+2.6", (2016.0, 2.59), (2011.6, 2.55), ha="center", fontsize=12, fontweight="bold", color=INK, arrowprops=dict(arrowstyle="-", color="#9AA7B0", lw=0.8))
ax.scatter([2026 + 8/12], [2.16], s=70, color=AMBER, zorder=5, edgecolor="white", lw=1.5)
ax.annotate("2026: +2.2 and rising\n(Jul–Sep, NOAA)", (2026 + 8/12, 2.16), (2027.9, 2.75), ha="right", fontsize=12.5,
            fontweight="black", color=AMBER, arrowprops=dict(arrowstyle="-", color=AMBER, lw=1))
ax.text(1951, 2.95, "El Niño: +0.5°C or more", color=RED, fontsize=12, fontweight="bold", va="center")
ax.text(1951, 2.6, "La Niña: −0.5°C or less", color=BLUE, fontsize=12, fontweight="bold", va="center")
fig.tight_layout(); fig.savefig(os.path.join(HERE, "oni-timeline.png"), facecolor=BG); plt.close(fig)

# ---- 2. Cost: global losses + how much smaller economies were
fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.8), dpi=200, gridspec_kw={"width_ratios": [1.25, 1]})
fig.patch.set_facecolor(BG)
for ax in (a1, a2):
    ax.set_facecolor(BG)
    for s in ["top", "right", "left"]: ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color("#C9D3DA"); ax.tick_params(colors=INK, length=0)
labels = ["1982–83", "1997–98", "2023–24\n(projected to 2029)"]; vals = [4.1, 5.7, 3.0]
b = a1.barh(labels, vals, color=[TEAL, NAVY, LIGHT], height=0.58); a1.invert_yaxis(); a1.set_xlim(0, 7.2)
for r, v in zip(b, vals):
    a1.text(v + 0.1, r.get_y() + r.get_height() / 2, f"${v:g} trillion", va="center", fontsize=17, fontweight="black", color=INK)
a1.tick_params(axis="y", labelsize=14); a1.tick_params(axis="x", labelsize=11, colors=MUTED)
a1.set_title("World income lost in the 5 years after each El Niño", loc="left", fontsize=14, fontweight="bold", color=INK, pad=12)
names = ["United States", "Peru", "Indonesia"]; pct = [3, 10, 10]
b2 = a2.barh(names, pct, color=[LIGHT, RED, RED], height=0.58); a2.invert_yaxis(); a2.set_xlim(0, 14)
for r, v, t in zip(b2, pct, ["about 3%", "more than 10%", "more than 10%"]):
    a2.text(v + 0.25, r.get_y() + r.get_height() / 2, t, va="center", fontsize=15, fontweight="black", color=INK)
a2.tick_params(axis="y", labelsize=14); a2.set_xticks([])
a2.set_title("How much smaller each economy was in 2003,\nbecause of the 1997–98 El Niño", loc="left", fontsize=14, fontweight="bold", color=INK, pad=12)
fig.tight_layout(w_pad=4); fig.savefig(os.path.join(HERE, "el-nino-cost-v2.png"), facecolor=BG); plt.close(fig)
print("ok")
