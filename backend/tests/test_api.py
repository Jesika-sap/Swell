"""Run with:  cd backend && python -m unittest discover tests -v"""
import os
import sys
import tempfile
import unittest
from datetime import date

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, ".."))
os.environ["SQLITE_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["GEMINI_API_KEY"] = "test-key"

import config  # noqa: E402
import db  # noqa: E402
from services import http, risk, checklist, flood  # noqa: E402
from tests import fakes  # noqa: E402

http.fake = fakes.fake
import app as server  # noqa: E402

DEV = {"X-Device-Id": "test-device-0001"}
OTHER = {"X-Device-Id": "someone-else-0002"}
TIDES = server.TIDES


class RiskScoreTests(unittest.TestCase):
    def test_bayfront_home_is_high(self):
        r = risk.score(flood={"level": "high", "zone": "AE", "text": "High-risk flood zone", "source": "FEMA"},
                       elevation=6.2, alerts=[{"event": "Coastal Flood Warning", "kind": "warning", "storm_related": True}],
                       rain={"peak_chance": 90, "summary": "Rain likely"}, county="San Mateo", state="CA",
                       tides=TIDES, today=date(2026, 11, 1))
        self.assertEqual(r["level"], "high")
        self.assertEqual(r["score"], 100)  # capped
        self.assertEqual(r["factors"][0]["key"], "flood_zone")
        self.assertEqual(r["king_tides"][0]["start"], "2026-11-21")

    def test_hillside_home_without_data_is_lower(self):
        r = risk.score(flood={"level": "minimal", "zone": "X", "text": "Outside", "source": "FEMA"}, elevation=180,
                       alerts=[], rain={"peak_chance": 10, "summary": "dry"}, county="San Mateo", state="CA", tides=TIDES)
        self.assertEqual(r["level"], "lower")
        self.assertEqual(r["score"], 5)  # only the El Nino baseline

    def test_past_king_tides_are_dropped(self):
        w = risk.king_tide_windows(TIDES, date(2026, 12, 30))
        self.assertEqual([x["start"] for x in w], ["2027-01-17"])
        self.assertTrue(risk.king_tide_windows(TIDES, date(2027, 1, 20))[0]["active"])

    def test_fema_zone_wording(self):
        self.assertEqual(flood.describe_zone("VE", None, "T")[0], "high")
        self.assertEqual(flood.describe_zone("X", "0.2 PCT ANNUAL CHANCE FLOOD HAZARD", "F")[0], "moderate")
        self.assertEqual(flood.describe_zone("X", "AREA OF MINIMAL FLOOD HAZARD", "F")[0], "minimal")


class ChecklistTests(unittest.TestCase):
    def test_household_needs_add_tasks(self):
        r = {"level": "high", "score": 80, "factors": [{"key": "flood_zone", "points": 40, "detail": ""}]}
        items = checklist.build(r, {"older_adult": True, "no_car": True, "pets": True, "medical_device": True},
                                county="San Mateo", alert_system={"name": "SMC Alert", "url": "u"},
                                nearest_sandbags={"name": "San Mateo Corporation Yard"})
        ids = [i["id"] for i in items]
        for must in ("alerts", "sandbags", "flood_insurance", "extra_help", "ride", "pets", "medical_power", "turn_around"):
            self.assertIn(must, ids)
        self.assertIn("SMC Alert", items[0]["title"])
        self.assertIn("San Mateo Corporation Yard", next(i for i in items if i["id"] == "sandbags")["why"])
        self.assertEqual(len(ids), len(set(ids)))

    def test_low_risk_household_still_gets_basics(self):
        r = {"level": "lower", "score": 5, "factors": [{"key": "el_nino", "points": 5, "detail": ""}]}
        ids = [i["id"] for i in checklist.build(r, {})]
        self.assertNotIn("sandbags", ids)
        for must in ("alerts", "family_plan", "water", "go_bag", "turn_around"):
            self.assertIn(must, ids)


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = server.app.test_client()

    def setUp(self):
        fakes.FAIL.clear()
        fakes.GEMINI_MODE["plan"] = "ok"
        config.GEMINI_API_KEY = "test-key"

    def plan(self, **kw):
        body = {"address": "1 Main St, Foster City, CA", "language": "en", "household": {"older_adult": True}}
        body.update(kw)
        return self.c.post("/api/plan", json=body, headers=DEV)

    def test_health(self):
        self.assertTrue(self.c.get("/api/health").get_json()["ok"])

    def test_bayfront_plan_end_to_end(self):
        res = self.plan()
        self.assertEqual(res.status_code, 201, res.get_json())
        p = res.get_json()
        self.assertEqual(p["place"]["county"], "San Mateo")
        self.assertEqual(p["risk"]["level"], "high")
        self.assertEqual(p["alerts"][0]["event"], "Coastal Flood Warning")
        self.assertEqual(p["help"]["alert_system"]["name"], "SMC Alert")
        self.assertEqual(p["help"]["sandbags"][0]["name"], "San Mateo Corporation Yard")  # closest to Foster City in the fake map
        self.assertLess(p["help"]["sandbags"][0]["miles"], p["help"]["sandbags"][1]["miles"])
        self.assertIn("extra_help", [i["id"] for i in p["checklist"]])
        self.assertEqual(p["missing"], [])
        self.assertTrue(p["summary"])

    def test_spanish_plan(self):
        p = self.plan(language="es").get_json()
        self.assertTrue(p["translated"])
        self.assertTrue(p["checklist"][0]["title"].startswith("ES: "))
        self.assertIn("arena", p["summary"])

    def test_ai_that_drops_a_task_is_rejected(self):
        fakes.GEMINI_MODE["plan"] = "drop"
        p = self.plan(language="es").get_json()
        self.assertFalse(p["translated"])
        self.assertIn("ai", p["missing"])
        self.assertFalse(p["checklist"][0]["title"].startswith("ES: "))

    def test_plan_survives_outages(self):
        fakes.FAIL.update({"hazards.fema.gov", "epqs.nationalmap.gov", "api.weather.gov"})
        fakes.GEMINI_MODE["plan"] = "down"
        res = self.plan(address="100 Murchison Dr, Millbrae, CA")
        self.assertEqual(res.status_code, 201)
        p = res.get_json()
        self.assertEqual(set(p["missing"]) >= {"flood", "elevation", "alerts", "forecast", "ai"}, True)
        self.assertTrue(len(p["checklist"]) > 10)
        self.assertTrue(p["summary"])

    def test_no_ai_key(self):
        config.GEMINI_API_KEY = ""
        p = self.plan(language="es").get_json()
        self.assertFalse(p["translated"])
        self.assertTrue(p["summary"])

    def test_use_my_location(self):
        res = self.c.post("/api/plan", json={"lat": 37.5985, "lon": -122.3872}, headers=DEV)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json()["place"]["city"], "Millbrae")

    def test_bad_inputs(self):
        self.assertEqual(self.c.post("/api/plan", json={"address": "x"}).status_code, 400)  # no device id
        self.assertEqual(self.c.post("/api/plan", json={"address": "nowhere at all"}, headers=DEV).status_code, 400)
        self.assertEqual(self.c.post("/api/plan", json={"lat": 999, "lon": 0}, headers=DEV).status_code, 400)
        self.assertEqual(self.c.post("/api/plan", data="hi", headers=DEV).status_code, 400)

    def test_checklist_progress_and_privacy(self):
        p = self.plan().get_json()
        pid = p["id"]
        self.assertEqual(self.c.post(f"/api/plan/{pid}/check", json={"item_id": "water", "done": True}, headers=DEV).get_json()["done"], 1)
        self.c.post(f"/api/plan/{pid}/check", json={"item_id": "water", "done": True}, headers=DEV)
        again = self.c.get(f"/api/plan/{pid}", headers=DEV).get_json()
        self.assertEqual(again["progress"]["done"], 1)
        self.assertTrue(next(i for i in again["checklist"] if i["id"] == "water")["done"])
        self.assertEqual(self.c.get(f"/api/plan/{pid}", headers=OTHER).status_code, 404)  # other people can't see it
        self.assertIn(pid, [x["id"] for x in self.c.get("/api/plans", headers=DEV).get_json()])
        self.assertEqual(self.c.delete(f"/api/plan/{pid}", headers=DEV).status_code, 200)
        self.assertEqual(self.c.get(f"/api/plan/{pid}", headers=DEV).status_code, 404)

    def test_ai_help_outside_checked_counties(self):
        p = self.plan(address="915 I St, Sacramento, CA").get_json()
        self.assertEqual(p["help"]["sandbags"], [])
        self.assertEqual(p["help"]["ai"]["sites"][0]["verified"], False)
        self.assertEqual(p["help"]["ai"]["sources"][0]["title"], "cityofsacramento.gov")

    def test_news_with_sources(self):
        n = self.c.get("/api/news?county=San%20Mateo&state=CA").get_json()
        self.assertTrue(n["ai"])
        self.assertIn("emergency", n["headline"])
        self.assertEqual(len(n["sources"]), 2)
        self.assertIn("detail", n["enso"])

    def test_reports_flow(self):
        photo = "data:image/jpeg;base64," + "A" * 400
        a = self.c.post("/api/reports/analyze", json={"photo": photo}, headers=DEV).get_json()
        self.assertEqual(a["kind"], "drain")
        res = self.c.post("/api/reports", json={"lat": 37.59, "lon": -122.38, "kind": a["kind"], "title": a["title"],
                                                "severity": a["severity"], "photo": photo, "ai_checked": True}, headers=DEV)
        self.assertEqual(res.status_code, 201)
        rid = res.get_json()["id"]
        near = self.c.get("/api/reports?lat=37.6&lon=-122.39").get_json()
        self.assertIn(rid, [r["id"] for r in near])
        self.assertNotIn("photo", near[0])
        far = self.c.get("/api/reports?lat=34.05&lon=-118.24").get_json()
        self.assertNotIn(rid, [r["id"] for r in far])
        self.assertEqual(self.c.post(f"/api/reports/{rid}/confirm", headers=OTHER).get_json()["confirmations"], 1)
        self.assertEqual(self.c.post(f"/api/reports/{rid}/confirm", headers=OTHER).get_json()["confirmations"], 1)  # once per device
        self.assertTrue(self.c.get(f"/api/reports/{rid}/photo").get_json()["photo"].startswith("data:image/jpeg"))
        bad = self.c.post("/api/reports", json={"lat": 37.59, "lon": -122.38, "photo": "data:text/html,hi"}, headers=DEV)
        self.assertEqual(bad.status_code, 400)

    def test_cache_avoids_repeat_calls(self):
        self.plan(address="2 Main St, Foster City, CA")
        before = len([c for c in fakes.CALLS if "hazards.fema.gov" in c[1]])
        self.plan(address="2 Main St, Foster City, CA")
        after = len([c for c in fakes.CALLS if "hazards.fema.gov" in c[1]])
        self.assertEqual(before, after)

    def test_regions_and_enso(self):
        regions = self.c.get("/api/regions").get_json()["regions"]
        self.assertIn("south-asia", [r["id"] for r in regions])


class FarmAndRegionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = server.app.test_client()

    def setUp(self):
        fakes.FAIL.clear()
        fakes.GEMINI_MODE["plan"] = "ok"
        config.GEMINI_API_KEY = "test-key"

    def test_california_farmer_gets_flood_farm_plan(self):
        p = self.c.post("/api/plan", json={"address": "1 Main St, Foster City, CA", "role": "farmer",
                                           "farm": {"grows": ["livestock", "orchard", "bogus"], "workers": True, "creek": True}}, headers=DEV).get_json()
        ids = [i["id"] for i in p["checklist"]]
        self.assertEqual(p["role"], "farmer")
        self.assertEqual(p["farm"]["grows"], ["livestock", "orchard"])
        for must in ("farm_drainage", "farm_chemicals", "farm_records", "farm_animals", "farm_orchard", "farm_crew", "sandbags"):
            self.assertIn(must, ids)
        self.assertEqual(p["risk"]["hazard"], "flood")
        self.assertIn("livelihood", [f["key"] for f in p["risk"]["factors"]])

    def test_nepal_farmer_gets_drought_plan(self):
        p = self.c.post("/api/plan", json={"address": "Bharatpur, Chitwan, Nepal", "role": "farmer", "language": "ne",
                                           "farm": {"grows": ["field", "livestock"]}}, headers=DEV).get_json()
        self.assertEqual(p["place"]["country"], "NP")
        self.assertEqual(p["risk"]["hazard"], "drought")
        self.assertEqual(p["risk"]["region"]["id"], "south-asia")
        ids = [i["id"] for i in p["checklist"]]
        for must in ("drought_water", "drought_seed", "drought_timing", "drought_animals", "save_water", "heat_plan"):
            self.assertIn(must, ids)
        for never in ("sandbags", "flood_insurance", "king_tides", "farm_drainage"):
            self.assertNotIn(never, ids)
        self.assertEqual(p["missing"], [])  # US-only data isn't "missing" in Nepal
        self.assertIn("np-dhm", [r["id"] for r in p["help"]["country"]])
        self.assertIsNone(p["help"]["alert_system"])
        again = self.c.get(f"/api/plan/{p['id']}", headers=DEV).get_json()
        self.assertEqual(again["place"]["country"], "NP")


class ScanTests(unittest.TestCase):
    def test_scan_adds_tasks_once(self):
        c = server.app.test_client()
        config.GEMINI_API_KEY = "test-key"
        plan = c.post("/api/plan", json={"address": "1 Main St, Foster City, CA"}, headers=DEV).get_json()
        photo = "data:image/jpeg;base64," + "B" * 500
        res = c.post(f"/api/plan/{plan['id']}/scan", json={"photo": photo}, headers=DEV)
        self.assertEqual(res.status_code, 200, res.get_json())
        d = res.get_json()
        self.assertEqual(len(d["added"]), 2)  # the low-confidence guess is dropped
        self.assertEqual(d["added"][0]["title"], "Point the downspout away from the house")  # most urgent first
        self.assertIn("Fix:", d["added"][0]["why"])
        self.assertIn("right corner", d["added"][0]["why"])
        self.assertEqual(d["good"], ["Doormat area is raised above the walkway"])
        self.assertTrue(d["next_photo"])
        self.assertEqual(d["plan"]["checklist"][0]["source"], "scan")
        self.assertEqual(d["plan"]["progress"]["total"], plan["progress"]["total"] + 2)
        again = c.post(f"/api/plan/{plan['id']}/scan", json={"photo": photo}, headers=DEV).get_json()
        self.assertEqual(again["added"], [])  # same photo doesn't add duplicates
        self.assertEqual(c.post(f"/api/plan/{plan['id']}/scan", json={"photo": photo}, headers=OTHER).status_code, 404)


class OrgTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = server.app.test_client()

    def setUp(self):
        fakes.FAIL.clear()
        config.GEMINI_API_KEY = "test-key"

    def test_full_help_flow(self):
        made = self.c.post("/api/orgs", json={"name": "Peninsula Youth Volunteers", "services": ["sandbags", "checks", "nope"],
                                              "address": "100 Murchison Dr, Millbrae, CA", "radius_miles": 20,
                                              "email": "team@example.org", "website": "example.org"})
        self.assertEqual(made.status_code, 201, made.get_json())
        org, key = made.get_json()["org"], made.get_json()["key"]
        self.assertEqual(org["services"], ["sandbags", "checks"])
        self.assertFalse(org["verified"])
        self.assertEqual(org["website"], "https://example.org")
        # people near Foster City see it; people in Sacramento don't
        self.assertIn(org["id"], [o["id"] for o in self.c.get("/api/orgs?lat=37.5585&lon=-122.2711").get_json()])
        self.assertNotIn(org["id"], [o["id"] for o in self.c.get("/api/orgs?lat=38.58&lon=-121.49").get_json()])
        # a household asks for help
        plan = self.c.post("/api/plan", json={"address": "1 Main St, Foster City, CA"}, headers=DEV).get_json()
        self.assertEqual(self.c.post(f"/api/plan/{plan['id']}/help", json={"need": "sandbags", "contact": "x"}, headers=DEV).status_code, 400)
        mine = self.c.post(f"/api/plan/{plan['id']}/help", json={"need": "sandbags", "details": "Garage door", "contact": "650-555-0100"}, headers=DEV).get_json()
        rid = mine[0]["id"]
        self.assertEqual(mine[0]["status"], "open")
        # the org sees it, without contact details until it accepts
        dash = self.c.get(f"/api/orgs/{org['id']}/dashboard", headers={"X-Org-Key": key}).get_json()
        req = next(r for r in dash["requests"] if r["id"] == rid)
        self.assertIsNone(req["contact"])
        self.assertEqual(self.c.get(f"/api/orgs/{org['id']}/dashboard", headers={"X-Org-Key": "wrong"}).status_code, 404)
        acc = self.c.post(f"/api/orgs/{org['id']}/requests/{rid}/accept", headers={"X-Org-Key": key}).get_json()
        self.assertEqual(acc["contact"], "650-555-0100")
        mine = self.c.get(f"/api/plan/{plan['id']}/help", headers=DEV).get_json()
        self.assertEqual(mine[0]["status"], "accepted")
        self.assertEqual(mine[0]["org"]["name"], "Peninsula Youth Volunteers")
        self.c.post(f"/api/orgs/{org['id']}/requests/{rid}/done", headers={"X-Org-Key": key})
        self.assertEqual(self.c.get(f"/api/orgs/{org['id']}/dashboard", headers={"X-Org-Key": key}).get_json()["helped"], 1)
        # a request for a service the org doesn't offer never reaches it
        self.c.post(f"/api/plan/{plan['id']}/help", json={"need": "shelter", "contact": "650-555-0100"}, headers=DEV)
        dash = self.c.get(f"/api/orgs/{org['id']}/dashboard", headers={"X-Org-Key": key}).get_json()
        self.assertNotIn("shelter", [r["need"] for r in dash["requests"]])

    def test_verify_needs_admin_token(self):
        made = self.c.post("/api/orgs", json={"name": "Test Org", "services": ["food"], "lat": 37.6, "lon": -122.4}).get_json()
        oid = made["org"]["id"]
        self.assertEqual(self.c.post(f"/api/orgs/{oid}/verify").status_code, 404)
        config.ADMIN_TOKEN = "secret-admin"
        self.assertEqual(self.c.post(f"/api/orgs/{oid}/verify", headers={"X-Admin-Token": "nope"}).status_code, 404)
        self.assertEqual(self.c.post(f"/api/orgs/{oid}/verify", headers={"X-Admin-Token": "secret-admin"}).status_code, 200)
        o = next(o for o in self.c.get("/api/orgs?lat=37.6&lon=-122.4").get_json() if o["id"] == oid)
        self.assertTrue(o["verified"])
        config.ADMIN_TOKEN = ""

    def test_org_validation(self):
        self.assertEqual(self.c.post("/api/orgs", json={"name": "X", "services": ["food"], "lat": 37, "lon": -122}).status_code, 400)
        self.assertEqual(self.c.post("/api/orgs", json={"name": "Good Name", "services": [], "lat": 37, "lon": -122}).status_code, 400)
        self.assertEqual(self.c.post("/api/orgs", json={"name": "Good Name", "services": ["food"], "email": "bad", "lat": 37, "lon": -122}).status_code, 400)


if __name__ == "__main__":
    unittest.main()


class AccountCommunityTests(unittest.TestCase):
    def test_signup_login_and_family_group(self):
        c = server.app.test_client()
        a = {"X-Device-Id": "acct-device-aaaa1"}
        plan = c.post("/api/plan", json={"address": "1 Main St, Foster City, CA"}, headers=a).get_json()
        res = c.post("/api/account/signup", json={"name": "Jesika", "email": "J@Example.com", "password": "short"}, headers=a)
        self.assertEqual(res.status_code, 400)  # password too short
        res = c.post("/api/account/signup", json={"name": "Jesika", "email": "J@Example.com", "password": "longenough1"}, headers=a)
        self.assertEqual(res.status_code, 201, res.get_json())
        row = db.one("SELECT pw_hash FROM accounts WHERE email = ?", ("j@example.com",))
        self.assertNotIn("longenough1", row["pw_hash"])  # only a hash is stored

        # Logging in on a new phone brings the plan along.
        b = {"X-Device-Id": "new-phone-bbbb2"}
        self.assertEqual(c.post("/api/account/login", json={"email": "j@example.com", "password": "nope"}, headers=b).status_code, 400)
        d = c.post("/api/account/login", json={"email": "j@example.com", "password": "longenough1"}, headers=b).get_json()
        self.assertEqual(d["device_id"], "acct-device-aaaa1")
        b = {"X-Device-Id": d["device_id"]}
        self.assertEqual([p["id"] for p in c.get("/api/plans", headers=b).get_json()], [plan["id"]])

        # County and city communities come from your own plans.
        lst = c.get("/api/communities", headers=b).get_json()
        keys = {s["kind"]: s["key"] for s in lst["suggested"]}
        self.assertIn("county", keys)
        self.assertEqual(c.post("/api/communities/join", json={"key": "county:NY:Kings"}, headers=b).status_code, 400)
        county = c.post("/api/communities/join", json={"key": keys["county"]}, headers=b).get_json()
        c.post("/api/reports", json={"lat": plan["lat"] + 0.01, "lon": plan["lon"], "kind": "drain", "title": "Clogged drain",
                                     "severity": 2, "county": plan["place"]["county"]}, headers=OTHER)
        detail = c.get(f"/api/communities/{county['id']}", headers=b).get_json()
        self.assertEqual(detail["reports"][0]["title"], "Clogged drain")
        self.assertEqual(c.get(f"/api/communities/{county['id']}", headers=OTHER).status_code, 400)  # no account

        # Family group: invite code, no size limit, "I'm safe".
        fam = c.post("/api/communities", json={"name": "Sapkota family"}, headers=b).get_json()
        code = c.get(f"/api/communities/{fam['id']}", headers=b).get_json()["invite_code"]
        for i in range(4):
            h = {"X-Device-Id": f"cousin-device-{i}xx"}
            c.post("/api/account/signup", json={"name": f"Cousin {i}", "email": f"c{i}@example.com", "password": "password123"}, headers=h)
            self.assertEqual(c.post("/api/communities/join", json={"code": code.lower()}, headers=h).status_code, 201)
        h = {"X-Device-Id": "sixth-member-zz"}
        c.post("/api/account/signup", json={"name": "Extra", "email": "x@example.com", "password": "password123"}, headers=h)
        self.assertEqual(c.post("/api/communities/join", json={"code": code}, headers=h).status_code, 201)  # no size limit
        self.assertEqual(c.post("/api/communities/join", json={"code": "WRONG1"}, headers=h).status_code, 400)
        safe = c.post(f"/api/communities/{fam['id']}/safe", json={"safe": True}, headers=b).get_json()
        me = [p for p in safe["people"] if p["you"]][0]
        self.assertTrue(me["safe_at"])
        self.assertEqual(me["places"][0]["total"], plan["progress"]["total"])
