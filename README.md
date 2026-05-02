# Comprehensive Analysis of 6 Security Indicators

**How IPQualityScore (IPQS) uses these flags to determine bot or malicious activity**

---

## Table of Contents

1. [Overview of VPNs and Their Relevance to Bot Detection](#overview-of-vpns-and-their-relevance-to-bot-detection)
2. [The 6 Security Indicators](#the-6-security-indicators)
3. [IPQS API Field Mapping](#ipqs-api-field-mapping)
4. [How the Risk Score Is Calculated](#how-the-risk-score-is-calculated)
5. [Example Walk-through](#example-walk-through)
6. [Code Documentation](#code-documentation)
7. [How to Run](#how-to-run)
8. [Sample Output](#sample-output)

---

## Overview of VPNs and Their Relevance to Bot Detection

A Virtual Private Network (VPN) is a technological solution that allows a secure, encrypted connection to be made between a user's computer — regardless of location — and a VPN server run by a VPN supplier (De, B. 2023).

**Anonymity & Privacy:** VPNs have long been used for legitimate purposes such as remote login, accessing geo-restricted content, and protecting data on public hotspots.

**Abuse Potential:** Malicious actors often use VPNs to mask the origin of bot traffic, evade rate limiting, and conduct attacks while being difficult to blacklist.

**Detection Challenges:** VPN IPs may come from commercial providers like NordVPN or ExpressVPN, which display properties like high user concentration, shared networks, or datacenter IP connectivity. In bot detection software such as IPQualityScore, the `vpn` flag helps identify whether the IP is associated with a known VPN (Irish et al., 2023). The `vpn` flag on its own does not indicate bot use, but it is a multiplier in bot detection — particularly in conjunction with other indicators such as a high fraud score, use of a proxy, or irregular user behavior.

---

## The 6 Security Indicators

### 1. `is_vpn` — Virtual Private Network Detection

| Field | Details |
|-------|---------|
| **Indicator** | `is_vpn: true` |
| **Definition** | The IP address belongs to a known commercial or private VPN provider |
| **Detection Method** | ASN and IP range ownership analysis · Provider database matching · Traffic pattern profiling (high user density per IP) |
| **Legitimate Use Cases** | Privacy protection, remote work, bypassing geo-restrictions |
| **Malicious Use Cases** | Hiding botnet origin · Evading IP bans · Simulating users from multiple countries |
| **Bot Correlation** | High when combined with non-residential `connection_type`, high `fraud_score`, or mismatched User-Agent |
| **Risk Level** | Medium alone → High in context |

> **Example:** A scraper using residential VPNs to rotate IPs across 50 countries → `is_vpn=true`, `connection_type=Hosting`, `abuse_velocity=high` → Confirmed bot

---

### 2. `is_proxy` — Anonymous Proxy Server

| Field | Details |
|-------|---------|
| **Indicator** | `is_proxy: true` |
| **Definition** | The IP operates as an open or anonymous proxy (HTTP/SOCKS5) allowing traffic forwarding |
| **Detection Method** | Active port scanning (80, 8080, 3128, etc.) · Known proxy provider databases · Historical forwarding behavior |
| **Types** | Public proxies, elite proxies, datacenter proxies |
| **Legitimate Use** | Rare — mostly enterprise reverse proxies (not flagged) |
| **Malicious Use** | Botnets for scraping · CAPTCHA solving farms · Credential stuffing |
| **Bot Correlation** | Very High — 90%+ of malicious bots use proxies |
| **Risk Level** | High — almost always malicious in public context |

> **IPQS Note:** `is_proxy=true` triggers immediate suspicion. Even with a low `fraud_score`, it is treated as a red flag.

---

### 3. `is_tor` — Tor Exit Node

| Field | Details |
|-------|---------|
| **Indicator** | `is_tor: true` |
| **Definition** | The IP is a Tor network exit node — the final relay before reaching the destination |
| **Detection Method** | Real-time sync with the Tor Project's official exit node list |
| **Legitimate Use** | Anonymity for activists, journalists, whistleblowers |
| **Malicious Use** | Automated abuse via Tor bots · Dark pool scraping · DDoS coordination |
| **Bot Correlation** | Extremely High in volume traffic — Tor is rate-limited and unsuitable for high-frequency bots, but low-volume malicious automation is common |
| **Risk Level** | Very High — nearly all Tor traffic in analytics should be filtered |

> **Important:** `is_tor=true` → Block by default in analytics systems.

---

### 4. `is_hosting` — Datacenter / Hosting Provider

| Field | Details |
|-------|---------|
| **Indicator** | `is_hosting: true` |
| **Definition** | The IP belongs to a cloud, VPS, or dedicated server provider |
| **Detection Method** | ASN classification · BGP routing data · Reverse DNS patterns (e.g., `ec2-...amazonaws.com`) |
| **Legitimate Use** | Web servers, APIs, CDNs, enterprise tools |
| **Malicious Use** | Bot farms on cheap VPS · Scraping clusters · Fraud rings using cloud IPs |
| **Bot Correlation** | High — especially when paired with a mobile User-Agent, no referrer, or high request velocity |
| **Risk Level** | High in user-facing contexts (e.g., downloads, views) |

> **Key Insight:** A mobile User-Agent from a hosting IP = near-certain bot.

---

### 5. `is_abuse` — Recent Abuse Reports

| Field | Details |
|-------|---------|
| **Indicator** | `is_abuse: true` |
| **Definition** | The IP has been reported for abuse in the last 30 days (spam, scraping, brute-force, etc.) |
| **Detection Method** | IPQS Fraud Network (community + partner reports) · Honeypot traps · Partner API feedback loop |
| **Severity Levels** | Tied to `abuse_velocity`: low, medium, high |
| **Bot Correlation** | Direct evidence of malicious automation |
| **Risk Level** | High — especially if `abuse_velocity=high` |

> **Example:** An IP with 47 scraping reports in 24 hours → `is_abuse=true`, `abuse_velocity=high` → Active bot

---

### 6. `is_relay` — Email or Traffic Relay Service

| Field | Details |
|-------|---------|
| **Indicator** | `is_relay: true` |
| **Definition** | The IP belongs to an email relay, CDN edge, or traffic forwarding service |
| **Detection Method** | Known relay ASN/IP ranges · Header analysis · Service fingerprinting |
| **Legitimate Use** | Email delivery, CDN caching, privacy relays |
| **Malicious Use** | Abusing free tiers for bot traffic · Hiding origin via Apple Private Relay · Spam relay chains |
| **Bot Correlation** | Moderate to High — depends on service |
| **Risk Level** | Context-dependent |

> **Special Case:** Apple iCloud Private Relay (`is_relay=true`) is increasingly used by real users on iOS.

---

## IPQS API Field Mapping

| Security Indicator | IPQS API Field | Value → `true` |
|--------------------|----------------|-----------------|
| `is_vpn` | `vpn` | `true` |
| `is_proxy` | `proxy` | `true` |
| `is_tor` | `tor` | `true` |
| `is_hosting` | `connection_type` | `"Hosting"`, `"Business"`, `"Cloud"` |
| `is_abuse` | `recent_abuse` | `true` |
| `is_relay` | `relay` (or inferred from `connection_type` + ASN) | `true` or detected |

---

## How the Risk Score Is Calculated

The script uses **AbstractAPI IP-Intelligence** as the primary source and **ip-api.com** as a fallback. Because of that, there is no `fraud_score` field in the API responses (De, B. 2023). Instead, the risk metric is computed from the 6 security flags returned by AbstractAPI:

```python
is_vpn     = security.get("is_vpn", False)
is_proxy   = security.get("is_proxy", False)
is_tor     = security.get("is_tor", False)
is_hosting = security.get("is_hosting", False)
is_abuse   = security.get("is_abuse", False)
is_relay   = security.get("is_relay", False)
```

**Scoring logic:**

```python
"is_bot":          any(flags)                                # True if at least one flag is True
"risk_score":      risk_score                                # Numeric value (0–120)
"classification":  "BOT DETECTED" if is_bot else "NOT A BOT"
```

Each flag that is `True` adds **20 points**. If `False`, it adds 0.

**Why 20 points per flag?**
- **Simplicity** — easy to understand and audit
- **Equal weighting** — each anonymity/abuse signal is considered equally dangerous
- **Range 0–120** — provides a clear scale (0 = no risk, 120 = maximum risk)

---

## Example Walk-through

Given this AbstractAPI response:

```json
{
  "ip_address": "66.249.80.196",
  "security": {
    "is_vpn": false,
    "is_proxy": true,
    "is_tor": false,
    "is_hosting": true,
    "is_abuse": false,
    "is_relay": false
  }
}
```

| Flag | Value | Points |
|------|-------|--------|
| `is_vpn` | `false` | 0 |
| `is_proxy` | `true` | 20 |
| `is_tor` | `false` | 0 |
| `is_hosting` | `true` | 20 |
| `is_abuse` | `false` | 0 |
| `is_relay` | `false` | 0 |

**Result:** `risk_score = 40` · `is_bot = True` · `classification = "BOT DETECTED"`

---

## Code Documentation

### 1. Imports & Type Hints

```python
import json
import requests
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
import time
```

Loads standard libraries for JSON handling, HTTP requests, UUID generation, UTC-aware timestamps, type hints, and rate-limit delays.

### 2. Configuration Constants

```python
ABSTRACT_API_KEY = "YOUR_API_KEY_HERE"
ABSTRACT_ENDPOINT = "https://ip-intelligence.abstractapi.com/v1/"
IPAPI_ENDPOINT = "http://ip-api.com/json/{ip}?fields=status,country,regionName,city,isp,org,proxy,hosting"
REQUEST_DELAY = 1.1  # seconds – respect free-tier rate limits
```

### 3. Embedded SOLR Sample JSON

The script embeds a sample SOLR statistics JSON containing 10 records for testing. IPs include Google crawlers, Cloudflare, Microsoft (Bing), and residential connections.

### 4. `load_solr_docs()`

Parses the embedded JSON string and extracts the `docs` list from the SOLR response.

### 5. `extract_unique_ips(docs)`

Builds a deduplicated, sorted list of IP addresses from the SOLR docs using a set for automatic deduplication.

### 6. `get_ip_data_from_abstract(ip_address)`

Sends a GET request to AbstractAPI with a 10-second timeout. Returns the JSON payload or `None` on failure.

### 7. `get_ip_data_from_ipapi(ip_address)`

Queries ip-api.com for country, city, ISP, etc. as a fallback. Returns `None` on error.

### 8. `classify_ip(abstract_data, ipapi_data)`

The core classification function:
1. Extracts the 6 security flags from AbstractAPI's response
2. Computes `risk_score` (20 pts per active flag, range 0–120)
3. Determines `is_bot` (any flag `True` → bot)
4. Fills in geo/ISP fallbacks from ip-api.com
5. Adds timestamps and UUIDs
6. Returns a complete report dictionary

### 9. `print_individual_report(report)`

Pretty-prints a bordered block for a single IP showing UID, location, ISP, security flags, risk score, and classification.

### 10. `print_summary_table(reports)`

Prints a compact one-line-per-IP table plus a final bot-count summary with percentage.

### 11. `main()`

Orchestrates the full pipeline: load data → extract IPs → loop through each IP → call APIs → classify → print per-IP and summary → write JSON report to disk.

### 12. Entry-Point Guard

```python
if __name__ == "__main__":
    main()
```

Runs `main()` only when the file is executed directly.

---

## How to Run

### Prerequisites

- Python 3.6+

### Installation

```bash
pip install requests
```

### Execution

```bash
python Main.py
```

---

## Sample Output

```
[*] Loading SOLR sample statistics data …
[*] Found 10 records → extracting unique IPs …
[*] 7 distinct IP addresses to analyse.
```

### Per-IP Results

| IP | BOT | Score | Flags |
|----|-----|-------|-------|
| `102.140.205.7` | NO | 0 | — |
| `2a06:98c0:3600::103` | YES | 40 | hosting, relay |
| `52.167.144.219` | YES | 40 | hosting, relay |
| `66.249.80.196` | YES | 40 | hosting, relay |
| `66.249.80.201` | YES | 40 | hosting, relay |
| `69.160.14.238` | NO | 0 | — |
| `74.125.214.99` | YES | 40 | hosting, relay |

**Summary:** 5/7 IPs classified as BOT (71.4%)

### Individual Report Example

```
==================================================
UID            : USR-FB7608
IP             : 102.140.205.7
Country / City : Kenya / Nairobi
ISP            : Wananchi Group (K) LTD
Domain / DNS   : wananchi.com
Type           : isp
------------------------------
Security Flags:
  is_vpn      : False
  is_proxy    : False
  is_tor      : False
  is_hosting  : False
  is_abuse    : False
  is_relay    : False
------------------------------
Risk Score     : 0/120
Bot?           : False → NOT A BOT
==================================================
```


