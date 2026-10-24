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


def _flood_household(risk, household, county, alert_system, nearest_sandbags):
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

    return items


def _alerts_item(county, alert_system, region):
    if alert_system:
        return _item("alerts", "now", f"Sign up for {alert_system['name']}",
                     f"{county} County's official emergency alerts by text, call or email. They tell you about evacuations and road closures first.",
                     1, alert_system["url"])
    where = "your national weather service" if region and region["id"] not in ("california", "pacific-northwest", "us-south") else "your county's emergency alerts"
    return _item("alerts", "now", "Follow official weather warnings",
                 f"Sign up for or follow {where}, so you hear about storms, heat and drought notices first.", 1)


def _drought_household(household, county, alert_system, region):
    """For places where El Nino usually means less rain: heat, water and smoke."""
    h = household or {}
    items = [
        _alerts_item(county, alert_system, region),
        _item("save_water", "now", "Start saving water now",
              "El Niño years often bring less rain here. Fix leaks, store clean water in covered containers, and reuse water where it's safe.", 1),
        _item("heat_plan", "now", "Make a plan for hot days",
              "Know where the coolest place nearby is, and check on older neighbors and anyone living alone when it's very hot.", 1),
        _item("family_plan", "now", "Make a family plan",
              "Agree on a meeting place and a contact everyone can call if phones or power go down.", 2),
        _item("water", "kit", "Drinking water for 3 days", "Four liters (about one gallon) per person per day, plus extra for animals.", 1),
        _item("meds", "kit", "A week of medications", "Heat makes many health conditions worse.", 1 if (h.get("older_adult") or h.get("disability")) else 2),
        _item("light", "kit", "Flashlights and a power bank", "Heat waves can overload power lines.", 2),
        _item("heat_signs", "storm", "Know the signs of heat illness",
              "Dizziness, headache, confusion or very hot skin: move to shade, drink water, cool the body, and get medical help if it doesn't improve.", 1),
        _item("water_rules", "storm", "Follow water limits",
              "If your town limits water use, follow the schedule so wells and tanks last the whole dry season.", 2),
    ]
    if region and region["id"] == "indonesia-australia":
        items.append(_item("smoke", "kit", "Masks for wildfire smoke", "N95-type masks help on smoky days. Keep windows closed when the air is bad.", 2))
    if h.get("older_adult") or h.get("disability"):
        items.append(_item("extra_help", "now", "Plan for anyone who needs extra help",
                           "Heat is most dangerous for older adults and people with health conditions. Decide who checks on them every hot day.", 1))
    if h.get("kids"):
        items.append(_item("kids", "now", "Keep kids safe in the heat", "Water bottles, shade, and no playing outside at the hottest time of day.", 2))
    if h.get("pets"):
        items.append(_item("pets", "now", "Water and shade for pets", "Animals need extra water and shade in hot, dry weather.", 2))
    return items


FARM_INFO = "https://www.farmers.gov/protection-recovery"


def _farm_flood(farm):
    f = farm or {}
    grows = set(f.get("grows") or [])
    items = [
        _item("farm_drainage", "now", "Clear ditches, culverts and drains on your land",
              "Water that can't drain sits on fields and drowns roots. Clear them before the first big storm and check again after each one.", 1),
        _item("farm_chemicals", "now", "Store fuel, fertilizer and pesticides above flood level",
              "Cover them and move them off low ground so floodwater can't wash them into creeks, wells or the Bay.", 1),
        _item("farm_equipment", "now", "Move equipment and feed to higher ground",
              "Tractors, pumps, seed and feed are expensive to replace. Park and store them where water won't reach.", 1 if f.get("creek") else 2),
        _item("farm_soil", "now", "Protect bare soil",
              "Cover crops, straw or mulch keep heavy rain from washing your topsoil away.", 2),
        _item("farm_records", "now", "Take photos and records before storms",
              "Photograph fields, animals, buildings and equipment now. USDA disaster programs ask for proof of what you had.", 1, FARM_INFO),
        _item("farm_insurance", "now", "Check your crop coverage and deadlines",
              "Call your local USDA Service Center about crop insurance or the Noninsured Crop Disaster Assistance Program (NAP) before losses happen.", 2, FARM_INFO),
        _item("farm_advisor", "now", "Talk to your county farm advisor",
              "University of California Cooperative Extension advisors give free, local advice on protecting crops and soil in wet winters.", 3, "https://ucanr.edu"),
        _item("farm_tractor", "storm", "Don't drive tractors or trucks through floodwater",
              "Water hides washed-out roads and ditches. Wait until it drains.", 1),
        _item("farm_after", "storm", "After the storm, document damage before cleanup",
              "Take photos and write down losses right away. Report losses to your USDA Service Center quickly, since some programs have short deadlines.", 1, FARM_INFO),
    ]
    if "livestock" in grows:
        items.append(_item("farm_animals", "now", "Plan where your animals go if water rises",
                           "Pick a high, fenced spot, keep a week of feed and water there, and make sure animals are tagged. The USDA Livestock Indemnity Program helps with animal losses from extreme weather.", 1, FARM_INFO))
    if "orchard" in grows:
        items.append(_item("farm_orchard", "now", "Keep orchard and vineyard rows draining",
                           "Standing water around roots for days can kill trees and vines. Open drainage paths between rows.", 2))
    if "vegetables" in grows or "field" in grows:
        items.append(_item("farm_harvest", "now", "Harvest early what you can",
                           "Bring in ready crops before a big storm instead of risking the whole field.", 2))
    if "nursery" in grows:
        items.append(_item("farm_nursery", "now", "Secure greenhouses and potted plants",
                           "Tie down covers and move pots up off the ground before high winds and flooding.", 2))
    if f.get("workers"):
        items.append(_item("farm_crew", "now", "Make a storm plan with your crew",
                           "No work in flooded fields or near downed power lines. Share the plan and emergency numbers in the languages your workers speak.", 1))
    return items


def _farm_drought(farm, region):
    f = farm or {}
    grows = set(f.get("grows") or [])
    items = [
        _item("drought_water", "now", "Fix and fill water storage now",
              "Repair tanks, ponds and canals before the dry months, and decide which fields get water first if there isn't enough.", 1),
        _item("drought_seed", "now", "Ask about drought-tolerant or short-season seed",
              "Your local agriculture office or cooperative can suggest varieties that need less water or grow faster.", 1),
        _item("drought_timing", "now", "Plan planting for a late or weak monsoon",
              "Follow the seasonal forecast from your national weather office and be ready to plant later or plant less.", 1),
        _item("drought_soil", "now", "Keep moisture in the soil", "Mulch, crop residue and less tilling help soil hold water longer.", 2),
        _item("drought_money", "now", "Plan for a smaller harvest",
              "Talk with your cooperative, bank or local office about crop insurance, loans or support before a bad season.", 2),
        _item("drought_records", "now", "Keep records of your crops and losses", "Aid programs often ask for proof of what you planted and what you lost.", 2),
        _item("drought_heat", "storm", "Work early and rest in the shade on hot days",
              "Heat illness can come on fast in the field. Drink water often and stop if you feel dizzy.", 1),
    ]
    if "livestock" in grows:
        items.append(_item("drought_animals", "now", "Plan fodder and water for your animals",
                           "Store fodder now and know where you'll get water if wells drop.", 1))
    if f.get("workers"):
        items.append(_item("drought_crew", "now", "Protect your workers from heat",
                           "Plan early start times, water, shade and rest breaks for everyone working in the field.", 1))
    return items


def build(risk, household, *, county=None, alert_system=None, nearest_sandbags=None, role="household", farm=None, region=None):
    hazard = risk.get("hazard", "flood")
    if hazard == "drought":
        items = _drought_household(household, county, alert_system, region)
    else:
        items = _flood_household(risk, household, county, alert_system, nearest_sandbags)
    if role == "farmer":
        items += _farm_drought(farm, region) if hazard == "drought" else _farm_flood(farm)
    seen, unique = set(), []
    for i in items:
        if i["id"] not in seen:
            seen.add(i["id"])
            unique.append(i)
    order = {"now": 0, "kit": 1, "storm": 2}
    unique.sort(key=lambda i: (order[i["group"]], i["priority"]))
    return unique
