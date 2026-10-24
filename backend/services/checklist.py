"""Builds a household's El Nino checklist from their risk and household.

The rules are plain Python, not AI, so every household always gets a complete,
correct checklist even if the AI is down. The AI (services/ai_plan.py) then
rewrites the wording in the household's language and adds local tips.

Groups:
  now    - do this week, before storms arrive
  kit    - what to have ready at home
  storm  - what to do when a storm or flood warning hits
"""


def _item(id, group, title, why, priority=2, link=None):
    return {"id": id, "group": group, "title": title, "why": why, "priority": priority, "link": link}


def build(risk, household, *, county=None, alert_system=None, nearest_sandbags=None):
    h = household or {}
    level = risk["level"]
    keys = {f["key"]: f for f in risk["factors"] if f["points"] > 0}
    flood_risk = "flood_zone" in keys and keys["flood_zone"]["points"] >= 20 or "elevation" in keys
    items = []

    # ---------- now ----------
    if alert_system:
        items.append(_item("alerts", "now", f"Sign up for {alert_system['name']}",
                           f"{county} County's official emergency alerts by text, call or email. They tell you about evacuations and road closures first.",
                           1, alert_system["url"]))
    else:
        items.append(_item("alerts", "now", "Sign up for your county's emergency alerts",
                           "Official alerts tell you about evacuations and road closures first. Search your county name plus \"emergency alerts.\"", 1))
    items.append(_item("phone_alerts", "now", "Turn on emergency alerts on your phone",
                       "Wireless Emergency Alerts reach your phone even if you never signed up for anything. Check they're on in Settings.", 2))

    if flood_risk or level != "lower":
        where = f" The closest site is {nearest_sandbags['name']}." if nearest_sandbags else ""
        items.append(_item("sandbags", "now", "Get sandbags before the first big storm",
                           "Sandbags at doors and garage openings keep shallow water out. Sites run low once storms start." + where,
                           1 if flood_risk else 2))
        items.append(_item("flood_insurance", "now", "Ask about flood insurance" if not h.get("renter") else "Ask about renters flood coverage",
                           "Regular home and renters insurance usually doesn't cover floods, and most flood policies take 30 days to start.",
                           1 if keys.get("flood_zone", {}).get("points", 0) >= 40 else 2, "https://www.floodsmart.gov"))
        items.append(_item("valuables_up", "now", "Move valuables and papers off the floor",
                           "Put important documents in a waterproof bag and raise electronics and keepsakes off the ground floor.", 2))

    items.append(_item("drains", "now", "Clear gutters and the storm drain by your home",
                       "Clogged drains are a top cause of street flooding. Only clear what you can reach safely, and never during a storm.", 2))
    items.append(_item("family_plan", "now", "Make a family plan",
                       "Agree on a meeting place, an out-of-area contact everyone can text, and two ways out of your neighborhood.", 1))

    if "king_tides" in keys:
        items.append(_item("king_tides", "now", "Mark the king tide dates",
                           keys["king_tides"]["detail"] + " Avoid low shoreline roads and trails on those days.", 2))
    if h.get("hillside"):
        items.append(_item("landslide", "now", "Learn the warning signs of a landslide",
                           "Watch for new cracks in the ground or walls, tilting trees or fences, and sudden muddy water. Leave if you see them during heavy rain.", 1))

    # people who need extra help
    if h.get("older_adult") or h.get("disability"):
        items.append(_item("extra_help", "now", "Plan for anyone who needs extra help",
                           "Decide who will check on them, how they'd leave without help, and keep a list of their medications and doctors.", 1))
    if h.get("medical_device"):
        items.append(_item("medical_power", "now", "Plan power for medical devices",
                           "Get a backup battery, and if you're a PG&E customer, ask about the Medical Baseline program for extra notice before outages.",
                           1, "https://www.pge.com/en/account/billing-and-assistance/financial-assistance/medical-condition-related-programs.html"))
    if h.get("no_car"):
        items.append(_item("ride", "now", "Line up a ride now",
                           "Ask a neighbor, friend or family member now who will drive you if you need to leave. Call or text 211 for help with transportation.", 1))
    if h.get("lives_alone"):
        items.append(_item("buddy", "now", "Pick a check-in buddy",
                           "Choose someone who will call or text you when there's a warning, and who you'll tell when you're safe.", 1))
    if h.get("kids"):
        items.append(_item("kids", "now", "Walk your kids through the plan",
                           "Show them the meeting place and the go-bag, and check your school's emergency pickup plan.", 2))
    if h.get("pets"):
        items.append(_item("pets", "now", "Make a plan for your pets",
                           "Many shelters only take service animals. Find pet-friendly places to stay and pack food, leashes and a carrier.", 2))
    if h.get("renter"):
        items.append(_item("renter_photos", "now", "Photograph your belongings",
                           "Photos make insurance claims much easier. Save your landlord's emergency number too.", 3))
    items.append(_item("neighbor", "now", "Check on a neighbor",
                       "Older neighbors and people living alone are often the last to hear warnings. Swap numbers before storm season.", 3))

    # ---------- kit ----------
    items.append(_item("water", "kit", "Water for 3 days",
                       "One gallon per person per day, plus extra for pets.", 1))
    items.append(_item("food", "kit", "Food that doesn't need cooking", "At least 3 days, plus a manual can opener.", 2))
    items.append(_item("meds", "kit", "A week of medications", "Plus copies of prescriptions.", 1 if (h.get("older_adult") or h.get("disability")) else 2))
    items.append(_item("light", "kit", "Flashlights and a power bank", "Storms knock out power. Keep phones charged when storms are forecast.", 2))
    items.append(_item("docs", "kit", "Important papers in a waterproof bag", "IDs, insurance, medical info, and a written list of phone numbers.", 2))
    items.append(_item("go_bag", "kit", "A go-bag by the door", "Clothes, chargers, cash, masks, a whistle and a copy of your plan, ready to grab.", 2))

    # ---------- storm ----------
    items.append(_item("turn_around", "storm", "Never walk or drive through floodwater",
                       "Six inches of moving water can knock you down, and a foot can sweep a car away. Turn around.", 1))
    items.append(_item("evacuate", "storm", "Leave right away if you're told to evacuate",
                       "Take your go-bag and go. Don't wait to see how bad it gets.", 1))
    items.append(_item("high_ground", "storm", "Move to higher ground if water rises",
                       "Go to a higher floor, never into a closed attic. Call 911 if you're trapped.", 1))
    items.append(_item("outage", "storm", "Stay safe in a power outage",
                       "Never run a generator, grill or camp stove indoors. Stay away from downed power lines.", 2))
    items.append(_item("report", "storm", "Report flooding and blocked drains",
                       "Report it on the map so neighbors can avoid it, and call your city's public works line.", 3))

    order = {"now": 0, "kit": 1, "storm": 2}
    items.sort(key=lambda i: (order[i["group"]], i["priority"]))
    return items
