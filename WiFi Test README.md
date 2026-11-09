# wifi_test.py

A small, dependency-free Python script for comparing home network setups side by side: Wi-Fi bands, range extenders, Ethernet, powerline, and so on.

Most speed tests only tell you how fast a connection is. This script also checks whether the data **arrived intact**. Every download is SHA-256 hashed, so silent corruption shows up next to the speed figures.

I wrote it to diagnose a PC whose HTTPS downloads kept aborting with `DECRYPTION_FAILED_OR_BAD_RECORD_MAC` / `SEC_E_DECRYPT_FAILURE` errors. It worked out which connection setup was both fastest and reliable.

---

## Features

- **Labelled scenarios.** Run once per setup ("Extender 2.4GHz", "Router direct", "Ethernet") and compare them afterwards.
- **Integrity checking.** Each download is hashed. Any hash that differs from the others for the same file is flagged as corrupted.
- **Latency and loss.** Pings the default gateway (your router) and `1.1.1.1` (the internet) before each test.
- **Wi-Fi details.** Records SSID, band, channel, signal and link rate where the OS exposes them.
- **HTTP or HTTPS.** HTTPS mode exercises the TLS path, which is where corruption tends to surface as errors.
- **CSV log.** Every run is appended to `wifi_results.csv`, so you can open it in Excel or anything else.
- **Comparison table.** `--compare` summarises all scenarios and picks the best one that had no failures.
- **Cross-platform.** Windows and Linux, Python standard library only. Nothing to `pip install`.

---

## Requirements

- Python 3.8+
- Windows (uses `netsh`, `ping`, PowerShell) or Linux (uses `ip`, `ping`, `nmcli`)

---

## Usage

```bash
python wifi_test.py "Scenario name" [options]
python wifi_test.py --compare
```

On Windows, if `python` isn't recognised, use `py` instead.

### Options

| Option | Default | Description |
|---|---|---|
| `scenario` | — | Label for this test, e.g. `"Extender 5GHz"` |
| `--runs N` | `3` | Number of downloads in this scenario |
| `--size MB` | `50` | Test file size: `10`, `20`, `50` or `100` |
| `--https` | off | Download over HTTPS (from `speed.cloudflare.com`) |
| `--url URL` | — | Use your own download URL instead |
| `--compare` | — | Print a summary of every scenario recorded so far |

### Example workflow

```bash
# Connect to each setup in turn, then run:
python wifi_test.py "Router direct"
python wifi_test.py "Extender 2.4GHz"
python wifi_test.py "Extender 5GHz"
python wifi_test.py "Extender Ethernet"

# Longer HTTPS soak test on the winner
python wifi_test.py "Soak HTTPS Ethernet" --https --runs 15

# See the results
python wifi_test.py --compare
```

---

## What the script does, step by step

### 1. Parse arguments (`main`)
It reads the scenario label and options. With `--compare` it skips testing and goes to the summary (step 7).

### 2. Pick the download URL (`test`)
- **HTTP:** `http://ipv4.download.thinkbroadband.com/<size>MB.zip`
- **HTTPS:** `https://speed.cloudflare.com/__down?bytes=<size in bytes>` (thinkbroadband's download host has no valid HTTPS certificate)
- `--url` overrides both.

### 3. Identify the active connection (`route_info`)
It finds the **default route**, which gives the gateway IP and the interface carrying traffic. This confirms which adapter is in use, which matters when switching between Wi-Fi and Ethernet.
- Windows: `Get-NetRoute -DestinationPrefix 0.0.0.0/0` via PowerShell, lowest metric wins
- Linux: `ip route show default`

### 4. Read Wi-Fi details (`wifi_info`)
- Windows: parses `netsh wlan show interfaces` for SSID, radio type, band, channel, signal and receive rate
- Linux: parses `nmcli -t dev wifi` for the active network
- If no band is reported, it's inferred from the channel (1–14 is 2.4 GHz, otherwise 5 GHz)

> **Windows note:** `netsh` only returns Wi-Fi details when **Location services** is on (Settings → Privacy & security → Location), including *Let desktop apps access your location*. If it's off or blocked by policy, those columns are left blank and everything else still works.

### 5. Measure latency and loss (`ping`)
Sends 20 pings to the gateway and 20 to `1.1.1.1`, and records the average round-trip time and packet loss for each. Comparing the two separates a local Wi-Fi problem from an ISP problem.

### 6. Timed, hashed downloads (`download`)
For each run:
1. Streams the file in 64 KB chunks, feeding every chunk into a SHA-256 hash. The file is **never written to disk**.
2. Shows progress every 5 MB.
3. Times the transfer and works out throughput in **megabits per second**.
4. Checks the byte count against the server's `Content-Length`, which catches truncated transfers.
5. Records any exception (timeout, TLS error, connection reset) as a failure along with its message.

Each run's result is printed straight away:
- `OK` — completed, hash consistent
- `OK but HASH DIFFERS - corrupted data` — completed, but the content differs from an earlier run
- `FAILED: <error>` — aborted

Each run is appended to `wifi_results.csv` and flushed immediately, so results survive if you stop the script partway.

### 7. Compare scenarios (`compare`)
1. Loads every row from `wifi_results.csv`.
2. For each URL, takes the **most common hash** as the correct one. The test file never changes, so any run with a different hash was corrupted.
3. Groups runs by scenario and host, then prints runs, failures, corrupted runs, average and minimum speed, and router and internet latency and loss.
4. Names the **fastest scenario with zero failures and zero corruption** as the best clean result.

---

## Example output

```
=== Extender Ethernet ===
Interface: Ethernet   Gateway: 192.168.0.1
No Wi-Fi details (wired, or Location services off on Windows).
Pinging router and 1.1.1.1 (20 each)...
Router: 2 ms avg, 0% loss   Internet: 13 ms avg, 0% loss
  Download 1/3 (50 MB)...
    35.18 Mbps in 11.9s  OK
  Download 2/3 (50 MB)...
    46.26 Mbps in 9.1s  OK
  Download 3/3 (50 MB)...
    43.45 Mbps in 9.7s  OK
Saved to wifi_results.csv. Run with --compare to see all scenarios.
```

```
Scenario            Host            Band     Signal   Runs Fail Corrupt  Avg Mbps    Min  Router ms/loss   Net ms/loss
----------------------------------------------------------------------------------------------------------------------
Router direct       DESKTOP-PC      2.4 GHz  40%         3    0       0       6.7    5.7            5/0%         13/0%
Extender 2.4GHz     DESKTOP-PC      2.4 GHz  62%         3    0       0      17.5   16.3            4/0%         14/0%
Extender Ethernet   DESKTOP-PC      wired                3    0       0      41.6   35.2            2/0%         13/0%

Best clean result: Extender Ethernet on DESKTOP-PC at 41.6 Mbps avg
Reliability first: a scenario with any Fail/Corrupt is not a fix, however fast.
```

---

## CSV columns

| Column | Meaning |
|---|---|
| `timestamp` | When the run finished |
| `scenario` / `host` | Your label and the machine's hostname |
| `interface` | Adapter carrying the default route |
| `ssid`, `radio`, `band`, `channel`, `signal`, `link_rate` | Wi-Fi details (blank if wired or unavailable) |
| `url`, `run` | Test file and run number |
| `ok`, `error` | Whether the download completed, and the error if not |
| `mbps`, `seconds`, `bytes` | Throughput, duration, bytes received |
| `sha256` | Hash of the downloaded content |
| `gw_loss_pct`, `gw_avg_ms` | Packet loss and latency to the router |
| `net_loss_pct`, `net_avg_ms` | Packet loss and latency to 1.1.1.1 |

---

## Tips and gotchas

- **Close the CSV in Excel before running.** Excel locks the file, and the script will fail with `PermissionError`.
- **Only compare like with like.** Speeds from different servers (HTTP thinkbroadband vs HTTPS Cloudflare) aren't directly comparable, so compare scenarios that used the same URL.
- **Use a new label if a run goes wrong.** Failed rows stay in the CSV and count against that scenario in `--compare`.
- **Intermittent faults need longer tests.** Heat- or load-related problems may take a while to appear, so use `--runs 15` or more.
- **Unplug the other adapter** when testing Ethernet, so traffic can't fall back to Wi-Fi. Check the `Interface:` line.
- **A `CERTIFICATE_VERIFY_FAILED` error is a server setup problem, not network corruption.** The errors that point to corruption are `BAD_RECORD_MAC` / `DECRYPTION_FAILED` / `SEC_E_DECRYPT_FAILURE`.

---

## Licence

MIT. Use it, change it, share it.
