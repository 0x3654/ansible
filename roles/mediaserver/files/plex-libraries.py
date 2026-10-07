#!/usr/bin/env python3
"""Idempotently ensure plex library sections exist with exact locations.

Usage: plex-libraries.py <Preferences.xml> <base-url> '<libraries-json>'
  libraries-json: [{"name","type","agent","scanner","language","locations":[...]}]

Creates missing sections, PUTs updated location lists when they drift,
triggers a refresh for anything touched. Empty locations are fine - plex
just shows nothing until the disks arrive.
"""
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


def die(msg):
    print(json.dumps({"failed": True, "msg": msg}))
    sys.exit(1)


def main():
    prefs_path, base, libs_json = sys.argv[1], sys.argv[2], sys.argv[3]
    try:
        token = re.search(r'PlexOnlineToken="([^"]+)"', open(prefs_path).read()).group(1)
    except (OSError, AttributeError):
        die("no PlexOnlineToken in %s (server not claimed yet?)" % prefs_path)

    def req(method, path):
        r = urllib.request.Request(base + path, method=method)
        r.add_header("X-Plex-Token", token)
        r.add_header("Accept", "application/json")
        try:
            with urllib.request.urlopen(r, timeout=20) as resp:
                body = resp.read().decode("utf-8", "replace")
                try:
                    return json.loads(body), resp.status
                except ValueError:
                    return {"_raw": body[:120]}, resp.status  # POST/PUT answer in XML
        except urllib.error.HTTPError as e:
            return {"_status": e.code}, e.code

    sections = None
    for _ in range(10):  # plex may still be booting after a redeploy
        body, code = req("GET", "/library/sections")
        if code == 200:
            sections = body["MediaContainer"]["Directory"]
            break
        if code == 401:
            die("401 from plex API - token not accepted")
        time.sleep(3)
    if sections is None:
        die("plex did not answer /library/sections in 30s")

    events = []
    for lib in json.loads(libs_json):
        sec = next((s for s in sections if s["type"] == lib["type"]), None)
        have = sorted(l["path"] for l in (sec or {}).get("Location", []))
        want = sorted(lib["locations"])
        if sec is not None and have == want:
            continue
        q = urllib.parse.urlencode({
            "name": lib["name"], "type": lib["type"], "agent": lib["agent"],
            "scanner": lib["scanner"], "language": lib["language"]})
        for p in lib["locations"]:
            q += "&location=" + urllib.parse.quote(p, safe="")
        if sec is None:
            body, code = req("POST", "/library/sections?" + q)
            events.append("created %s -> %d locations (http %s)" % (lib["name"], len(want), code))
        else:
            body, code = req("PUT", "/library/sections/%s?%s" % (sec["key"], q))
            events.append("updated %s: %d -> %d locations (http %s)" % (lib["name"], len(have), len(want), code))
        if code not in (200, 201):
            die("library %s: plex returned http %s (%s)" % (lib["name"], code, body))
        req("POST", "/library/sections/%s/refresh" % sec["key"] if sec else
            "/library/sections/all/refresh")

    print(json.dumps({"changed": events}, ensure_ascii=False))


if __name__ == "__main__":
    main()
