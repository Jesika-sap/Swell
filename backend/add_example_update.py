"""Add one clearly labeled EXAMPLE official update to your San Mateo County community,
so the county page isn't empty in a demo.

Run from the Swell folder (after you've made an account and a plan in San Mateo County):
    python3 backend/add_example_update.py

The post's title starts with "Example:" and its text says it's an example, so nobody
mistakes it for a real message from the county. The information in it is real: it
comes from the City of San Mateo's sandbag page.
To remove it later:  python3 backend/add_example_update.py --remove
"""
import os
import sys
import uuid
import secrets
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402

EMAIL = "example-official@swell.local"
TITLE = "Example: Free sandbags at San Mateo Corporation Yard"
NOTE = ("This is an example of how official updates look in Swell. The details are real: self-serve sandbags, "
        "24/7 through April 30, at 1949 Pacific Blvd, San Mateo. Up to 10 bags per vehicle; bring a shovel. "
        "Source: City of San Mateo, cityofsanmateo.org/4750/Sandbag-Information")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def main():
    db.init()
    county = db.one("SELECT * FROM communities WHERE place_key LIKE ?", ("county:%:San Mateo",))
    if "--remove" in sys.argv:
        db.execute("DELETE FROM reports WHERE title = ?", (TITLE,))
        print("Removed the example update.")
        return
    if not county:
        print("No San Mateo County community yet. In Swell, make a plan for a San Mateo County address,")
        print("create an account, open the Community tab once, then run this again.")
        return
    acct = db.one("SELECT * FROM accounts WHERE email = ?", (EMAIL,))
    if not acct:
        aid = uuid.uuid4().hex[:12]
        db.execute("INSERT INTO accounts (id, name, email, pw_hash, device_id, created_at) VALUES (?,?,?,?,?,?)",
                   (aid, "Example official account", EMAIL, generate_password_hash(secrets.token_urlsafe(24)),
                    "example-official-" + uuid.uuid4().hex[:8], now()))
        acct = db.one("SELECT * FROM accounts WHERE id = ?", (aid,))
    if db.one("SELECT 1 AS x FROM community_members WHERE community_id = ? AND account_id = ?", (county["id"], acct["id"])):
        db.execute("UPDATE community_members SET role = 'official' WHERE community_id = ? AND account_id = ?", (county["id"], acct["id"]))
    else:
        db.execute("INSERT INTO community_members (community_id, account_id, role, joined_at) VALUES (?,?,?,?)",
                   (county["id"], acct["id"], "official", now()))
    if db.one("SELECT 1 AS x FROM reports WHERE title = ? AND status = 'open'", (TITLE,)):
        print("The example update is already there.")
        return
    db.execute("""INSERT INTO reports (id, device_id, kind, title, note, severity, lat, lon, county, photo, ai_checked, created_at, community_id)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
               (uuid.uuid4().hex[:12], acct["device_id"], "other", TITLE, NOTE, 1, 37.5487, -122.3001, county["county"],
                None, 0, now(), county["id"]))
    print(f"Added an example official update to {county['name']}. Refresh the Community tab to see it.")


if __name__ == "__main__":
    main()
