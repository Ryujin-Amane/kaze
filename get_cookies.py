import os
from glob import glob
from os.path import expanduser
from sqlite3 import OperationalError, connect
import instaloader

try:
    from instaloader import ConnectionException, Instaloader
except ModuleNotFoundError:
    raise SystemExit("Instaloader not found.\n  pip install [--user] instaloader")


def get_cookiefile():
    default_cookiefile = {
        "Windows": "~/AppData/Roaming/Mozilla/Firefox/Profiles/*/cookies.sqlite",
        "Darwin": "~/Library/Application Support/Firefox/Profiles/*/cookies.sqlite",
    }.get(importlib.util.find_spec("platform") and __import__("platform").system(), "~/.mozilla/firefox/*/cookies.sqlite")
    cookiefiles = glob(expanduser(default_cookiefile))
    if not cookiefiles:
        raise SystemExit("No Firefox cookies.sqlite file found. Use -c COOKIEFILE.")
    return cookiefiles[0]


def import_session(cookiefile, sessionfile):
    print("Using cookies from {}.".format(cookiefile))
    conn = connect(f"file:{cookiefile}?mode=ro", uri=True)
    try:
        cookie_data = conn.execute(
            "SELECT name, value FROM moz_cookies WHERE host='.instagram.com'"
        )
    except OperationalError:
        cookie_data = conn.execute(
            "SELECT name, value FROM moz_cookies WHERE host LIKE '%instagram.com'"
        )
    instaloader = Instaloader(max_connection_attempts=1)
    
    # Inject cookies into instaloader's requests session
    for name, value in cookie_data:
        instaloader.context._session.cookies.set(name, value, domain=".instagram.com")
        
    try:
        # Check if we are logged in by fetching the current user profile
        username = instaloader.test_login()
        if not username:
            raise SystemExit("Not logged in. Are you logged in to Instagram in Firefox?")
            
        print("Successfully authenticated as {}.".format(username))
        
        # Save session
        instaloader.context.username = username
        instaloader.save_session_to_file(sessionfile)
        print("Session saved to {}.".format(sessionfile or f"session-{username}"))
    except ConnectionException as e:
        raise SystemExit(f"Cookie import failed: {e}")

if __name__ == "__main__":
    import argparse
    import importlib.util
    
    p = argparse.ArgumentParser(description="Extract Instagram session from Firefox")
    p.add_argument("-c", "--cookiefile", help="Path to Firefox cookies.sqlite")
    p.add_argument("-f", "--sessionfile", help="Name of the session file to create")
    args = p.parse_args()
    
    try:
        cookiefile = args.cookiefile or get_cookiefile()
        import_session(cookiefile, args.sessionfile)
    except Exception as e:
        print(f"\nError: {e}")
        print("\nNote: For this script to work easily, you must be logged into Instagram using the FIREFOX web browser.")
        print("If you use Chrome/Edge, you can use the Chrome extension 'EditThisCookie' to export cookies.")
