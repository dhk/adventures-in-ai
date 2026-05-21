# Woven — Project Context for Claude Code

## What is Woven?

Woven is a browser-based tool that combines multiple people's LinkedIn connection exports into a single unified network graph. The core value proposition: **find your warmest path to anyone at any company**.

When you pool Dave's connections with Sarah's connections, you can answer questions that neither could answer alone — "who in our combined network knows someone at Stripe, and who should make the introduction?"

## Product Vision

**V1 (current):** A seeded graph that a publisher pre-loads with 2–3 people's LinkedIn data, password-protected and hosted on GitHub Pages. Visitors can upload their own `Connections.csv` to add themselves to the session graph and search for paths from their own node.

**V2 (community enrichment):** Anyone's upload contributes back to a shared persistent graph — a collectively-owned network that grows more valuable as more people contribute. This is the core network-effects business.

**Monetisation direction:**
- The natural B2B wedge is the **team version**: a sales team, VC firm, or recruiting agency all pool their connections into one shared persistent graph. The SDR can tap the CFO's network. Clear subscription story.
- Community enrichment is a known successful model — LinkedIn itself, but owned by the community rather than a rent-extracting platform.
- Premium search: basic (1–2 hop) free, deeper path analysis / export / CRM integration paid.

## Architecture

**Single self-contained HTML file (`index.html`).** No build step, no server, no dependencies beyond two CDN scripts. This was a deliberate choice: easy to host anywhere, easy to export and republish with data baked in.

**Dependencies (CDN):**
- D3.js v7 — force-directed graph simulation and SVG rendering
- PapaParse 5.4 — CSV parsing

**Key data structures (all in-memory, rebuilt on each load):**
```
nodeMap    Map<id, node>      — every person in the graph
adjacency  Map<id, Set<id>>   — bidirectional edge list
edgeData   Map<edgeKey, obj>  — enrichment signals per edge
fileOwners []                 — people who contributed exports
```

Node IDs are `normalizeId(fullName)` — lowercase, trimmed, single-spaced. No persistent IDs exist (LinkedIn doesn't export them).

Edge keys: `id1 < id2 ? "${id1}||${id2}" : "${id2}||${id1}"` — always sorted so A→B and B→A hit the same key.

## Data Enrichment Layers

Files are auto-detected by filename and CSV headers. Each type adds a different layer:

| File | What it adds |
|------|-------------|
| `Connections.csv` | Nodes + bidirectional edges. Owner becomes a file owner node. |
| `Messages.csv` | Edge warmth: message count + recency. Groups by conversation title (= other person's name for 1:1 chats). Skips group chats (titles containing commas). |
| `Recommendations.csv` | `hasRecommendation: true` on the edge — strongest possible signal (+6 warmth score). |
| `Invitations.csv` | `invDir: 'received'/'sent'` — who reached out first. Received = warmer (+1.5). |

**Warmth score formula (0–10):**
- Messages: `min(5, log10(count+1) × 3.5)` + recency bonus (up to +3 for <90 days)
- Recommendation: +6
- Invitation received: +1.5 / sent: +0.5 / has personal note: +0.5

**Enrichment is progressive:** files uploaded after the graph is built are processed immediately and refresh edge visuals without a full rebuild. Only new Connections files require a rebuild.

## Seed / Export / Publish Workflow

1. Open `index.html` locally in a browser
2. Upload LinkedIn CSV exports (Connections required; Messages/Recommendations/Invitations optional)
3. Label each Connections file with the person's name; associate enrichment files with the right owner
4. Click **Build Network Graph**
5. Click **Export Seeded Page** (bottom of left sidebar)
6. Enter a password when prompted (leave blank for none)
7. Download lands as `index.html` — commit it to this repo, push
8. GitHub Pages / Vercel serves the seeded graph to visitors immediately

**How export works:** `exportSeededPage()` fetches the current page source, splices in `SEED_DATA` (full graph state as JSON) and `PASSWORD_HASH` (SHA-256 of the password) as two sentinel constants, and downloads the result. The sentinel constants are named exactly and must not be renamed:
```js
const SEED_DATA = null;         // replaced with {...} on export
const PASSWORD_HASH = '';       // replaced with sha256 hex on export
```

## Password Gate

- SHA-256 hashed via `crypto.subtle` — never transmitted
- Stored in `sessionStorage` so users aren't re-prompted on same-tab refresh
- `PASSWORD_HASH = ''` disables the gate entirely
- Shake animation + clear field on wrong password

## Visitor Flow

Visitors land on the seeded graph (pre-loaded, no uploads needed). A banner shows the seed date. They can upload their own `Connections.csv` to place themselves in the graph and search for paths from their own node. **Session-only — no persistence in V1.**

## Scale Limits

The binding constraint is D3's SVG force simulation, not memory or parsing:

| Nodes | Experience |
|-------|------------|
| < 1,000 | Smooth |
| 1,000–1,500 | Noticeable lag while settling |
| 1,500–3,000 | Slow, sticky interaction |
| > 3,000 | Effectively unusable for the graph view |

The performance warning fires at 1,500 nodes. Company search and BFS path-finding remain fast at any size — they're pure JS, unaffected by rendering.

LinkedIn caps connections at 30,000 per account. Practical seed data: 2–3 people with 500–1,000 connections each, ideally with overlapping networks (reduces unique node count).

**To push past these limits:** swap SVG for Canvas/WebGL (sigma.js, PixiJS), move simulation to a Web Worker, or add viewport culling. Meaningful engineering investment — worth it when this becomes a shared team tool.

## Key Functions

| Function | Purpose |
|----------|---------|
| `buildGraph()` | Full rebuild from all loaded files |
| `loadSeedData(data)` | Restore graph from baked-in JSON — runs on page load if SEED_DATA is non-null |
| `exportSeededPage()` | Fetch source → inject constants → download index.html |
| `initPasswordGate()` | Show overlay if PASSWORD_HASH set and session not authed |
| `computeDegrees()` | BFS from primaryUserId to assign hop counts to all nodes |
| `shortestPath(a, b)` | BFS returning the path array, used for company search results |
| `processEnrichmentFile(entry)` | Dispatch Messages/Recommendations/Invitations to the right parser |
| `refreshEdgeVisuals()` | Re-colour edges after enrichment without rebuilding simulation |
| `renderD3Graph()` | Full D3 rebuild — call after graph data changes |

## What's Not Built Yet (V2 ideas)

- **Persistence:** Users' uploads saving back to a shared graph. Needs a backend (Supabase, Firebase, or a simple edge function). This is the community enrichment model.
- **Real auth:** Cloudflare Access in front of GitHub Pages is the cleanest option — free for ≤50 users, real OAuth, zero code changes.
- **Canvas/WebGL rendering:** Required to support team-scale graphs (10k+ nodes).
- **Alumni detection:** Cross-reference Positions.csv work history against connection companies to surface "you both worked at Acme" intro hooks.
- **CRM export:** Download path results as CSV / push to HubSpot.
- **Warmest-path routing:** Dijkstra weighting edges by 1/warmthScore rather than pure hop-count BFS.

## Deployment

GitHub Pages: enable on `main` branch, root directory. No config file needed for a single HTML file.

The exported `index.html` is the deployable artefact — replace the file in the repo and push to update.
