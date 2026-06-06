import subprocess
import socket

print("=" * 50)
print("SYSTEM NETWORK REPORT")
print("=" * 50)

# Hostname
hostname = socket.gethostname()
print(f"Hostname            : {hostname}")

# IP Address(es)
try:
    ip_addresses = subprocess.check_output(
        ["hostname", "-I"],
        text=True
    ).strip()

    print(f"IP Address(es)      : {ip_addresses}")

except Exception as e:
    print(f"IP Address(es)      : Error ({e})")

# Default Gateway
try:
    route = subprocess.check_output(
        ["ip", "route"],
        text=True
    )

    gateway = "Unknown"

    for line in route.splitlines():
        if line.startswith("default"):
            gateway = line.split()[2]
            break

    print(f"Default Gateway     : {gateway}")

except Exception as e:
    print(f"Default Gateway     : Error ({e})")

# DNS Server
try:
    dns_server = "Unknown"

    with open("/etc/resolv.conf") as f:
        for line in f:
            if line.startswith("nameserver"):
                dns_server = line.split()[1]
                break

    print(f"DNS Server          : {dns_server}")

except Exception as e:
    print(f"DNS Server          : Error ({e})")

# Internet Connectivity Test
try:
    subprocess.check_output(
        ["ping", "-c", "4", "8.8.8.8"],
        text=True
    )

    internet_status = "OK"

except Exception:
    internet_status = "FAILED"

print(f"Internet Connection : {internet_status}")

print("=" * 50)
print("Report Complete")
print("=" * 50)
