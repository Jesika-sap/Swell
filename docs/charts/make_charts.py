import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle
GF="fonts/"  # Lato .ttf files from github.com/google/fonts (ofl/lato)
for f in ["Lato-Regular.ttf","Lato-Bold.ttf","Lato-Black.ttf"]: fm.fontManager.addfont(GF+f)
plt.rcParams.update({"font.family":"Lato","font.size":15})
OUT=""  # writes the PNGs next to this script
NAVY="#0B3349"; INK="#16222C"; MUTED="#4E5D69"; TEAL="#0E7486"; LIGHT="#8FC1CB"; AMBER="#E2892A"; GOLD="#ECB868"; BG="#FAFAFA"

def base(w=9, h=4.2, bg=BG):
    fig, ax = plt.subplots(figsize=(w, h), dpi=200)
    fig.patch.set_facecolor(bg); ax.set_facecolor(bg)
    for s in ["top","right","left"]: ax.spines[s].set_visible(False)
    return fig, ax

# 1. Nepal monsoon rain (dark slide)
fig, ax = base(bg=NAVY)
labels=["30-year average","2015 (El Niño year)"]; vals=[100,74.2]
bars=ax.barh(labels, vals, color=["#5E8FA3", GOLD], height=0.55)
ax.set_xlim(0,118); ax.invert_yaxis()
for b,v in zip(bars, vals):
    ax.text(v+2, b.get_y()+b.get_height()/2, f"{v:g}%", va="center", color="white", fontsize=22, fontweight="black")
ax.tick_params(axis="y", colors="white", labelsize=16, length=0); ax.tick_params(axis="x", colors="#9FB6C3", labelsize=12)
ax.spines["bottom"].set_color("#3B5B6E")
ax.set_xlabel("Monsoon rain in Nepal, June 10 to Aug 15 (% of normal)", color="#C9DEE5", fontsize=13, labelpad=10)
ax.yaxis.set_tick_params(pad=10)
fig.tight_layout(); fig.savefig(OUT+"nepal-2015-rain.png", facecolor=NAVY); plt.close(fig)

# 2. Strong El Ninos since 1950 + forecast
fig, ax = base(w=8.6, h=4.6)
seasons=["’57","’65","’72","’82","’87","’91","’97","’15","’23"]
peaks=[1.81,1.98,2.12,2.23,1.70,1.71,2.40,2.75,2.06]
very={3,6,7}
cols=[TEAL if i in very else LIGHT for i in range(9)]
x=list(range(9))
ax.bar(x, peaks, color=cols, width=0.68)
for i,v in enumerate(peaks): ax.text(i, v+0.05, f"{v:.1f}", ha="center", fontsize=13, fontweight="bold", color=INK)
ax.add_patch(Rectangle((9-0.34,0),0.68,2.5, fill=False, ls=(0,(4,3)), lw=2, ec=AMBER))
ax.text(9, 2.55, "2.5+?", ha="center", fontsize=13, fontweight="black", color=AMBER)
ax.set_xticks(x+[9]); ax.set_xticklabels(seasons+["’26\nforecast"], fontsize=13, color=MUTED)
ax.set_ylim(0,3.75); ax.set_yticks([0,1,2,3]); ax.tick_params(axis="y", colors=MUTED, labelsize=12, length=0)
ax.grid(axis="y", color="#E3E8EC"); ax.set_axisbelow(True); ax.spines["bottom"].set_color("#C9D3DA")
ax.set_ylabel("Peak °C warmer than normal", color=MUTED, fontsize=12)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=TEAL,label="Very strong"),Patch(color=LIGHT,label="Strong"),Patch(fill=False,ec=AMBER,ls="--",label="This winter: NOAA gives 83% odds of 2.5+ (Oct–Dec)")],
          loc="upper left", frameon=False, fontsize=11.5, ncol=3, columnspacing=1.2, handlelength=1.4)
fig.tight_layout(); fig.savefig(OUT+"strong-el-ninos.png", facecolor=BG); plt.close(fig)

# 3. Cost
fig, ax = base()
labels=["1982–83","1997–98","2023–24 (projected)"]; vals=[4.1,5.7,3.0]; cols=[TEAL,NAVY,LIGHT]
bars=ax.barh(labels, vals, color=cols, height=0.55); ax.invert_yaxis(); ax.set_xlim(0,6.8)
for b,v in zip(bars, vals): ax.text(v+0.08, b.get_y()+b.get_height()/2, f"${v:g} trillion", va="center", fontsize=20, fontweight="black", color=INK)
ax.tick_params(axis="y", labelsize=16, length=0, colors=INK); ax.tick_params(axis="x", labelsize=12, colors=MUTED)
ax.spines["bottom"].set_color("#C9D3DA")
ax.set_xlabel("World income lost in the 5 years after each El Niño ($ trillions)", color=MUTED, fontsize=13, labelpad=10)
fig.tight_layout(); fig.savefig(OUT+"el-nino-cost.png", facecolor=BG); plt.close(fig)

# 4. FEMA preparedness actions
fig, ax = base(w=8.4, h=4.6)
acts=[("Gathered emergency supplies",48),("Made a plan",37),("Made home safer",36),("Signed up for alerts",36),("Saved money for emergencies",32),
      ("Learned evacuation routes",31),("Insured and documented property",30),("Safeguarded documents",30),("Tested a family contact plan",18),
      ("Practiced drills",15),("Got involved in community",14),("Planned with neighbors",12)]
names=[a for a,_ in acts]; vals=[v for _,v in acts]
cols=[AMBER if n in ("Made a plan","Planned with neighbors") else LIGHT for n in names]
bars=ax.barh(names, vals, color=cols, height=0.7); ax.invert_yaxis(); ax.set_xlim(0,58)
for b,v in zip(bars, vals): ax.text(v+0.8, b.get_y()+b.get_height()/2, f"{v}%", va="center", fontsize=12, fontweight="bold", color=INK)
ax.tick_params(axis="y", labelsize=12, length=0, colors=INK); ax.tick_params(axis="x", labelsize=11, colors=MUTED)
ax.spines["bottom"].set_color("#C9D3DA")
ax.set_xlabel("% of Americans who did this to prepare in the past year (2023)", color=MUTED, fontsize=12, labelpad=8)
fig.tight_layout(); fig.savefig(OUT+"fema-preparedness.png", facecolor=BG); plt.close(fig)
print("ok")
