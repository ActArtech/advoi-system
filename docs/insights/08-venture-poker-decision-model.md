# Venture Poker Decision Model

**Source:** `deployment/advoi/poker.txt`  
**Status:** Mental model for Aether bets and squad autonomy

---

## Poker as betting under uncertainty

Poker is mostly a **betting game** that uses cards as excuse. Skill is in:

1. **Value betting** — when you have edge
2. **Bluffing** — when you don't but opponent might fold
3. **Reading opponents** — from bet patterns, timing, table image

Cards matter; **how you bet** matters more.

---

## Range-based thinking

Don't ask *"Is this idea good?"* Ask:

> What is the range of possible outcomes, and what's my edge in each scenario?

| Poker | Venture / product |
|-------|-------------------|
| Hand reading | Market reading — all ways customers could react |
| Bet sizing | Resource allocation — small when info low, big when edge clear |
| Fold equity | Optionality — kill fast without losing everything |
| Table image | Brand positioning — past launches affect next adoption |

**Framework:** Real Options Theory — right but not obligation to invest more later.

---

## Staged bets (Build a Venture / VC mindset)

```
Small bet → see next card (data) → fold / call / raise
```

| Poker move | Startup action |
|------------|----------------|
| Small blind | Cheap MVP, quick test |
| Call | Gather more signal, maintain option |
| Raise | Double down when edge confirmed |
| **Fold** | Kill underperforming bet early — **hardest skill** |

Great founders **let go of bad bets** when analytics show weakness — preserve capital for better opportunities.

---

## Public vs private information

| Layer | Venture mapping |
|-------|-----------------|
| **Hole cards (private)** | Insights only you have — customer truths, hidden competitor moves |
| **Community cards (public)** | Obvious market signals, complaints, competitor launches |
| **Edge** | Small bets to reveal private info without showing full hand |

---

## Awareness layers

| Layer | Meaning |
|-------|---------|
| Known knowns | Obvious ideas everyone sees |
| Known unknowns | You know what to test (interviews, experiments) |
| Unknown unknowns | Breakthroughs from connecting unrelated domains |

Opportunities hide in **proximity** — two close-but-not-obvious things combining (like straights needing sequence).

---

## ADVoi / Aether application

| Concept | Where it lives |
|---------|----------------|
| 3-day appetite bets | `.aether/BET.md` |
| Fold bad ventures | Aether portfolio manager (future) |
| Don't switch active venture casually | gem-dev-shop remains active |
| Confirmation before big bets | `ADVOI_CONFIRMATION_REQUIRED` |
| Squad staging only | Squads push to staging at most |
| Stage gates | `.aether/STAGE.md` exit criteria |

---

## Key discipline

> Don't fall in love with the hand. Cut losses fast.

Maps directly to:

- Killing underperforming products
- Not re-introducing rejected tools (Lavish, Coolify) without new ADR
- Infrastructure venture (ADVoi) does not replace gem-dev-shop as active Aether product