"""Mark an organization as verified (the Swell team checked who they are).

Run from the Swell folder after the group has signed up in the Help tab:
    backend/.venv/bin/python backend/verify_org.py "SVYCA"
It matches any organization whose name contains the words you type.
To undo:  backend/.venv/bin/python backend/verify_org.py "SVYCA" --undo
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print('Type part of the organization\'s name, like:  backend/.venv/bin/python backend/verify_org.py "SVYCA"')
        return
    db.init()
    rows = db.query("SELECT id, name, verified FROM orgs WHERE LOWER(name) LIKE ?", (f"%{args[0].lower()}%",))
    if not rows:
        print(f'No organization with "{args[0]}" in its name yet. Sign it up first: Help tab > Join as an organization.')
        return
    value = 0 if "--undo" in sys.argv else 1
    for r in rows:
        db.execute("UPDATE orgs SET verified = ? WHERE id = ?", (value, r["id"]))
        print(f'{"Verified" if value else "Un-verified"}: {r["name"]}')


if __name__ == "__main__":
    main()
