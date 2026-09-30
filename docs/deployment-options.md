# Deployment Options: Personal App, Reachable Anywhere, Free

**Status:** Undecided. Revisit after the MVP (README + open data questions) is done.
**Written:** 2026-09-30
**Goal:** use the dashboard from my Mac and phone, from anywhere, like an
app, for $0, **without exposing my data to anyone else.**

---

## The one constraint that shapes everything

The app has **no login**. That's intentional for a single-user local tool,
but it means:

> Putting the current app on a public URL would let **anyone** who finds it
> read and change my data.

So every option below either **keeps the app off the public internet** or
**puts a login gate in front of it**. There's no option where it just goes
public as-is.

A second constraint is **storage**. All data lives in one SQLite file
(`data/dashboard.db`). Any hosting choice has to keep that file around
permanently, or the app has to move to a hosted database.

---

## The problem splits into two independent parts

| Part | Question | Options |
|---|---|---|
| **1. App feel** | How does it look and launch on my devices? | PWA (recommended) or native app |
| **2. Access** | How do my devices reach it from anywhere? | Local only / Tailscale / Cloud server / Cloudflare Tunnel |

Any choice in Part 1 works with any choice in Part 2.

---

## Part 1: App feel

### Option 1A: Progressive web app (PWA) ✅ recommended

A PWA is a website that can be **installed like an app**.

- **iPhone/Android:** home-screen icon, opens full-screen with no browser bars.
- **Mac/Windows:** "Install" or "Add to Dock" gives it its own app window.
- **Offline:** can show the last-loaded assignment list without a connection
  (read-only; changes need the server).
- **What it takes:** a web app manifest (name, colors, icon), an icon image,
  and a small service worker script for offline caching. **About an hour.**
  No framework, no app store, no build step.
- **Cost:** $0.

### Option 1B: Native iOS/Android app ❌ not recommended

- Needs Xcode / Android Studio and a separate codebase.
- An iOS app needs a **$99/year** Apple Developer account to install beyond
  a 7-day test.
- For a personal list-and-calendar tool, it gives almost nothing a PWA doesn't.

---

## Part 2: Access from anywhere

### Option 2A: Local only (what we have today)

- Runs on my Mac. Reach it at `http://localhost:8000`.
- `python app.py` listens on **my Mac only** by default, so it's safe on public wifi.
- On **trusted** wifi (home), `python app.py --lan` allows phone access and prints the phone URL.

| ✅ Pros | ❌ Cons |
|---|---|
| Zero setup, $0 | No access away from my Mac / home wifi |
| Nothing exposed | Mac must be on |

### Option 2B: Tailscale ✅ recommended first step

Tailscale is a free private network that connects **only my own devices**
(Mac + phone), encrypted, from anywhere: cell data, public wifi, anywhere.

- Install Tailscale on the Mac and the phone and sign in to the same account.
- The phone opens the dashboard at a private Tailscale address.
- To everyone else on the internet, **it doesn't exist**: no public URL,
  nothing to attack.

| ✅ Pros | ❌ Cons |
|---|---|
| Free for personal use | **Mac must be on** and running the app |
| No code changes | Tailscale app needed on each device |
| Data stays on my Mac (plus iCloud backups) | |
| Very secure: private by design | |
| ~15 minutes to set up | |

### Option 2C: Free cloud server + access gate (always-on)

Run the app 24/7 on a free cloud machine, so my Mac doesn't need to be on.

**Candidates (real servers with permanent storage, so SQLite works):**
- Oracle Cloud "Always Free" VM
- Google Cloud free-tier e2-micro VM

**Avoid, or plan around:** free app-hosting services like Render. They
often **wipe the disk on restart or redeploy**, which would erase my
checkmarks, unless the app moves to a hosted database (e.g. a free
Postgres tier).

**Access gate (required, since there's no login):**
- **Tailscale** on the server (same as 2B, just always-on), or
- **Cloudflare Access**: a free login page in front of the site (e.g.
  one-time code sent to my email). This gives a normal public URL that only
  I can get past.

| ✅ Pros | ❌ Cons |
|---|---|
| Always on, Mac can be off | Most setup work (a few hours) |
| Works from any device | I maintain a Linux server (updates, restarts) |
| $0 if free tier holds | Real seed data + DB must be copied to the server |
| | Backups need a new setup (iCloud backup is Mac-only) |

### Option 2D: Cloudflare Tunnel from my Mac + Cloudflare Access

A middle ground: a real URL (e.g. `dashboard.<my-domain>`) that routes to
the app **running on my Mac**, behind a Cloudflare email login.

| ✅ Pros | ❌ Cons |
|---|---|
| Normal URL, no app needed on phone | **Mac must be on** |
| Free Cloudflare tiers | Needs a domain (~$10/yr) for the nicest setup |
| Login gate included | More moving parts than Tailscale |

---

## Side-by-side

| | Cost | Setup effort | Mac must be on? | Exposure risk | Code changes |
|---|---|---|---|---|---|
| **2A Local only** | $0 | none | yes | none | none |
| **2B Tailscale** | $0 | ~15 min | yes | none | none |
| **2C Cloud + gate** | $0* | a few hours | **no** | low (behind gate) | small (deploy config) |
| **2D Cloudflare Tunnel** | $0–10/yr | ~1 hour | yes | low (behind gate) | none |

\*Free tiers change often. **Re-check current terms before choosing 2C.**
Nothing here was verified against live pricing on 2026-09-30.

---

## Recommended path

1. **Finish the MVP**: README, plus reviewing the open data questions in `PROGRESS.md`.
2. **Add PWA support (1A)**, so it installs on the Mac and phone.
3. **Set up Tailscale (2B)** for access from anywhere, with no public exposure.
4. **Move to a free cloud server (2C)** only if "Mac must be on" becomes
   a real problem in practice.

---

## Questions to answer when deciding

1. Is my Mac usually on (or can it be) when I'd want to check the dashboard?
   → If **yes**, 2B is probably enough. If **no**, look at 2C.
2. Do I want a normal web address, or is "open the app with Tailscale on" fine?
   → A normal URL points to 2C or 2D with Cloudflare Access.
3. Am I willing to maintain a small Linux server?
   → If **no**, avoid 2C.
4. Do I want the data to live only on my own machine?
   → If **yes**, choose 2B or 2D (data never leaves the Mac).

---

## Decision log

_Record the choice here when it's made._

- Part 1 (app feel): —
- Part 2 (access): —
- Date decided: —
- Notes: —
