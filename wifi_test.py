#!/usr/bin/env python3
"""
wifi_test.py - compare connection scenarios on the same machine.

Each run records: active interface, Wi-Fi SSID/band/channel/signal, ping to the
router and to the internet, and N timed downloads of a test file. Every
download is SHA-256 hashed so silent corruption shows up, not just speed.
Results append to wifi_results.csv next to this script.

Usage (Windows or Linux, standard library only):
    python wifi_test.py "Extender 2.4GHz"
    python wifi_test.py "Extender 5GHz"
    python wifi_test.py "Router direct"
    python wifi_test.py "Extender Ethernet"
    python wifi_test.py --compare          # summary table of all scenarios

Options:
    --runs N      downloads per scenario (default 3)
    --size MB     test file size: 10, 20, 50, 100 (default 50)
    --https       use HTTPS instead of HTTP (tests the TLS errors you saw);
                  downloads from speed.cloudflare.com
    --url URL     use your own download URL instead

Windows: signal/band info needs Location services ON (Settings > Privacy & security).
"""
import argparse
import csv
import hashlib
import platform
import re
import socket
import statistics
import subprocess
import sys
import time
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path

RESULTS = Path(__file__).with_name("wifi_results.csv")
IS_WIN = platform.system() == "Windows"
FIELDS = [
    "timestamp", "scenario", "host", "interface", "ssid", "radio", "band",
    "channel", "signal", "link_rate", "url", "run", "ok", "error", "mbps",
    "seconds", "bytes", "sha256", "gw_loss_pct", "gw_avg_ms",
    "net_loss_pct", "net_avg_ms",
]


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              errors="replace", timeout=180).stdout
    except Exception:
        return ""


def route_info():
    """Return (gateway IP, interface carrying the default route)."""
    if IS_WIN:
        ps = ("$r = Get-NetRoute -DestinationPrefix '0.0.0.0/0' | "
              "Sort-Object RouteMetric | Select-Object -First 1; "
              "\"$($r.NextHop)|$($r.InterfaceAlias)\"")
        out = run(["powershell", "-NoProfile", "-Command", ps]).strip()
        gw, _, iface = out.partition("|")
        return gw, iface
    m = re.search(r"default via (\S+) dev (\S+)", run(["ip", "route", "show", "default"]))
    return (m.group(1), m.group(2)) if m else ("", "")


def wifi_info():
    info = dict(ssid="", radio="", band="", channel="", signal="", link_rate="")
    if IS_WIN:
        out = run(["netsh", "wlan", "show", "interfaces"])
        patterns = {
            "ssid": r"^\s*SSID\s*:\s*(.+)$",
            "radio": r"^\s*Radio type\s*:\s*(.+)$",
            "band": r"^\s*Band\s*:\s*(.+)$",
            "channel": r"^\s*Channel\s*:\s*(.+)$",
            "signal": r"^\s*Signal\s*:\s*(.+)$",
            "link_rate": r"^\s*Receive rate \(Mbps\)\s*:\s*(.+)$",
        }
        for key, pat in patterns.items():
            m = re.search(pat, out, re.M)
            if m:
                info[key] = m.group(1).strip()
    else:
        out = run(["nmcli", "-t", "-f", "ACTIVE,SSID,CHAN,RATE,SIGNAL", "dev", "wifi"])
        for line in out.splitlines():
            if line.startswith("yes:"):
                p = line.split(":")
                info.update(ssid=":".join(p[1:-3]), channel=p[-3],
                            link_rate=p[-2], signal=p[-1] + "%")
                break
    if info["channel"] and not info["band"]:
        try:
            info["band"] = "2.4 GHz" if int(info["channel"]) <= 14 else "5 GHz"
        except ValueError:
            pass
    return info


def ping(host, count=20):
    if not host:
        return "", ""
    cmd = ["ping", "-n" if IS_WIN else "-c", str(count), host]
    out = run(cmd)
    loss = re.search(r"(\d+(?:\.\d+)?)% (?:packet )?loss", out)
    avg = (re.search(r"Average = (\d+)ms", out) if IS_WIN
           else re.search(r"= [\d.]+/([\d.]+)/", out))
    return (loss.group(1) if loss else ""), (avg.group(1) if avg else "")


def download(url, timeout=30):
    h = hashlib.sha256()
    total = 0
    step = 5 * 1024 * 1024
    next_mark = step
    start = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "wifi_test/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            expected = r.headers.get("Content-Length")
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                h.update(chunk)
                total += len(chunk)
                if total >= next_mark:
                    print(f"\r    {total // 1048576} MB", end="", flush=True)
                    next_mark += step
        secs = time.perf_counter() - start
        print("\r", end="")
        if expected and int(expected) != total:
            return False, f"short read {total}/{expected}", total, secs, h.hexdigest()
        return True, "", total, secs, h.hexdigest()
    except Exception as e:
        print("\r", end="")
        return False, f"{type(e).__name__}: {e}"[:200], total, time.perf_counter() - start, ""


def test(scenario, runs, size, https, url=None):
    if not url:
        if https:
            # thinkbroadband's download host has no valid HTTPS cert; Cloudflare does
            url = f"https://speed.cloudflare.com/__down?bytes={size * 1048576}"
        else:
            url = f"http://ipv4.download.thinkbroadband.com/{size}MB.zip"
    gw, iface = route_info()
    w = wifi_info()

    print(f"\n=== {scenario} ===")
    print(f"Interface: {iface or '?'}   Gateway: {gw or '?'}")
    if w["ssid"]:
        print(f"Wi-Fi: {w['ssid']}  {w['band']}  ch {w['channel']}  "
              f"signal {w['signal']}  link {w['link_rate']} Mbps  {w['radio']}")
    else:
        print("No Wi-Fi details (wired, or Location services off on Windows).")

    print("Pinging router and 1.1.1.1 (20 each)...")
    gl, ga = ping(gw)
    nl, na = ping("1.1.1.1")
    print(f"Router: {ga or '?'} ms avg, {gl or '?'}% loss   "
          f"Internet: {na or '?'} ms avg, {nl or '?'}% loss")

    new_file = not RESULTS.exists()
    with RESULTS.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, FIELDS)
        if new_file:
            writer.writeheader()
        hashes = []
        for i in range(1, runs + 1):
            print(f"  Download {i}/{runs} ({size} MB)...")
            ok, err, n, secs, digest = download(url)
            mbps = round(n * 8 / secs / 1e6, 2) if secs else 0
            note = "OK" if ok else f"FAILED: {err}"
            if ok:
                hashes.append(digest)
                if len(set(hashes)) > 1:
                    note = "OK but HASH DIFFERS - corrupted data"
            print(f"    {mbps} Mbps in {secs:.1f}s  {note}")
            writer.writerow(dict(
                timestamp=datetime.now().isoformat(timespec="seconds"),
                scenario=scenario, host=socket.gethostname(), interface=iface,
                url=url, run=i, ok=ok, error=err, mbps=mbps,
                seconds=round(secs, 1), bytes=n, sha256=digest,
                gw_loss_pct=gl, gw_avg_ms=ga, net_loss_pct=nl, net_avg_ms=na, **w))
            f.flush()
    print(f"Saved to {RESULTS.name}. Run with --compare to see all scenarios.")


def compare():
    if not RESULTS.exists():
        sys.exit("No results yet - run a scenario first.")
    with RESULTS.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # The test file never changes, so the most common hash per URL is the good one.
    good_hash = {}
    for url in {r["url"] for r in rows}:
        c = Counter(r["sha256"] for r in rows
                    if r["url"] == url and r["ok"] == "True" and r["sha256"])
        if c:
            good_hash[url] = c.most_common(1)[0][0]

    groups = {}
    for r in rows:
        groups.setdefault((r["scenario"], r["host"]), []).append(r)

    hdr = (f"{'Scenario':<20}{'Host':<16}{'Band':<9}{'Signal':<8}{'Runs':>5}"
           f"{'Fail':>5}{'Corrupt':>8}{'Avg Mbps':>10}{'Min':>7}"
           f"{'Router ms/loss':>16}{'Net ms/loss':>14}")
    print("\n" + hdr + "\n" + "-" * len(hdr))
    ranked = []
    for (sc, host), rs in groups.items():
        ok = [r for r in rs if r["ok"] == "True"]
        speeds = [float(r["mbps"]) for r in ok]
        corrupt = sum(1 for r in ok if good_hash.get(r["url"]) not in (None, r["sha256"]))
        fail = len(rs) - len(ok)
        avg = statistics.mean(speeds) if speeds else 0.0
        low = min(speeds) if speeds else 0.0
        last = rs[-1]
        band = last["band"] or ("wired" if not last["ssid"] else "?")
        print(f"{sc[:19]:<20}{host[:15]:<16}{band[:8]:<9}{last['signal'][:7]:<8}"
              f"{len(rs):>5}{fail:>5}{corrupt:>8}{avg:>10.1f}{low:>7.1f}"
              f"{(last['gw_avg_ms'] or '?') + '/' + (last['gw_loss_pct'] or '?') + '%':>16}"
              f"{(last['net_avg_ms'] or '?') + '/' + (last['net_loss_pct'] or '?') + '%':>14}")
        ranked.append((fail + corrupt == 0, avg, sc, host))

    clean = sorted([r for r in ranked if r[0]], key=lambda r: -r[1])
    print()
    if clean:
        print(f"Best clean result: {clean[0][2]} on {clean[0][3]} at {clean[0][1]:.1f} Mbps avg")
    else:
        print("No scenario finished without failures or corruption yet.")
    print("Reliability first: a scenario with any Fail/Corrupt is not a fix, however fast.")


def main():
    ap = argparse.ArgumentParser(description="Compare connection scenarios.")
    ap.add_argument("scenario", nargs="?", help='label, e.g. "Extender 5GHz"')
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--size", type=int, default=50, choices=[10, 20, 50, 100])
    ap.add_argument("--https", action="store_true")
    ap.add_argument("--url", help="custom download URL (overrides --size/--https)")
    ap.add_argument("--compare", action="store_true")
    a = ap.parse_args()
    if a.compare:
        compare()
    elif a.scenario:
        test(a.scenario, a.runs, a.size, a.https, a.url)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
