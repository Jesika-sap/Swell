"""el-nino-cost-v3.png: world income lost after strong El Ninos.
Source: Callahan & Mankin, "Persistent effect of El Nino on global economic growth," Science (2023),
as reported by Dartmouth College / ScienceDaily (May 18, 2023)."""
import os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyBboxPatch
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "fonts")
for f in ["Lato-Regular.ttf", "Lato-Bold.ttf", "Lato-Black.ttf"]:
    fm.fontManager.addfont(os.path.join(FONTS, f))
plt.rcParams.update({"font.family": "Lato"})
INK="#16222C"; MUTED="#5A6873"; NAVY="#0B3349"; TEAL="#0E7486"; LIGHT="#A9CDD4"; BG="#FAFAFA"

rows = [("1982–83", 4.1, TEAL, "lost in the 5 years after", False),
        ("1997–98", 5.7, NAVY, "lost in the 5 years after", False),
        ("2023–24", 3.0, LIGHT, "projected to be lost by 2029", True)]
fig, ax = plt.subplots(figsize=(13, 4.3), dpi=200)
fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
ax.set_xlim(-2.2, 9.6); ax.set_ylim(-0.42, 2.72); ax.axis("off")
for i, (label, v, col, sub, proj) in enumerate(rows):
    y = 2.3 - i * 1.05
    ax.text(-0.25, y + 0.08, label, ha="right", va="center", fontsize=24, fontweight="bold", color=INK)
    ax.text(-0.25, y - 0.27, "El Niño", ha="right", va="center", fontsize=14, color=MUTED)
    bar = FancyBboxPatch((0, y - 0.3), v, 0.6, boxstyle="round,pad=0,rounding_size=0.12",
                         fc=col, ec=NAVY if proj else "none", lw=1.6 if proj else 0, ls=(0, (4, 3)) if proj else "-")
    ax.add_patch(bar)
    ax.text(v + 0.18, y + 0.1, ("up to $3 trillion" if proj else f"${v:.1f} trillion"), va="center", fontsize=26, fontweight="black", color=INK)
    ax.text(v + 0.18, y - 0.25, sub, va="center", fontsize=14, color=MUTED)

fig.subplots_adjust(left=0.01, right=0.99, top=0.98, bottom=0.02)
fig.savefig(os.path.join(HERE, "el-nino-cost-v3.png"), facecolor=BG)
print("ok")
