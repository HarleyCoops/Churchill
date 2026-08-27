# Seeing the package as an adventure

This brief starts from a launch of [Readme.md](../Readme.md) as a sequential walk
([adventure.html](adventure.html)). It does not add historical claims. It asks what a visitor
still cannot *do* or *feel*, even though the evidence is already in the repository.

The rule does not change: every public sentence still traces to the
[Ground Truth Ledger](ground-truth-ledger.md).

---

## What the Readme already is

The Readme is not a file listing. It already has an adventure spine:

1. An object — six Cassell volumes and a Chartwell note dated 6 December 1946.
2. A person — Colonel Bryan Charles Fairfax, C.M.G.
3. A route — five Somme phases the ledger can document (extreme right, 1 July, Trones Wood, Guillemont, evacuation).
4. A connection — five overlapping threads that explain why Churchill’s reply is not a stranger’s courtesy.
5. A physical test — first-edition marks the visitor can check against photographs.
6. Two open cases — Fairfax’s missing “kind letter,” and the thin Canadian-government provenance.

The problem is presentation. Those beats are published as a long scroll, then split again across
a portal of equal cards, a deck, a map, a gallery, and a flythrough. A visitor can graze. They
cannot yet *travel*.

---

## What we already have (the kit)

| Adventure job | Existing piece | Where it lives |
|---|---|---|
| The door | Letter in Volume I | `Images/Signature2.JPG`, `Images/signature.JPG` |
| The protagonist | Fairfax biography and portrait | Readme; `Images/ColFairfax.jpeg`; ledger #1–7 |
| The ground | 1916 source-map crops | `docs/assets/nls-source-maps/` |
| Occupying a place | Leaflet route + Chartwell jump | `research/somme-battlefield-map.html` |
| Years | 1873–1950 milestones | `research/provenance-timeline.html` |
| Object ritual | Close-ups of jacket, edges, set | `research/artifact-gallery.html` |
| Voice | Stanley, de Coutard, Congreve | `TextExtract.md`; 89th Brigade PDF |
| Rules of the world | No claim without a source | `research/ground-truth-ledger.md` |
| Cinematic pacing | Travel / settle / card / orbit | `terrain_data/build_cinematic_flythrough.py` |
| Told version | Reconstruction deck | `presentations/fairfax-churchill-deck/` |
| Live mystery | Archive search for Fairfax’s letter | `fairfax_letter_finder.py` |
| Afterlife of the object | Auction, vault, valuation | Readme provenance; `research/valuation-brief.html` |

This is enough material for an adventure. It is not yet arranged as one.

---

## What we need to *see*

These are the gaps that keep the package a dossier.

### 1. One door

The research portal currently offers six destinations of equal weight. An adventure has a start.

Needed: a first step that is always the letter, then a forced next beat. `adventure.html` is
that door. The portal and the Readme should point here first, not treat the walk as another card
in a grid.

### 2. Memory between rooms

Map, gallery, timeline, and deck do not know which chapter sent you. Landing on the map from
“Trones Wood” should open on that pin. Landing from Chartwell should not dump the visitor on
Maricourt. Every room needs a “return to the walk” that resumes the next chapter.

Needed: query or hash handoff (`?beat=trones`, `#guillemont`) and a persistent “you are here”
across the HTML surfaces.

### 3. Examine mode for the letter

The note is short enough to be seen whole, and strange enough to repay a desk:

- Chartwell / Westerham 93 stationery
- handwritten “Dear Captain Fairfax”
- typed “Thank you for your kind letter.”
- typed addressee “Colonel Bryan Fairfax, C.M.G.”
- punch hole
- the 25s. NET jacket flap in the same photograph

The gallery shows these as frames in a grid. The adventure needs a single-object lamp: one
surface, callouts, no competing cards.

### 4. Stand on each Somme beat

The Readme already writes July 1916 as five phases. The flythrough plan already thinks in
travel, settle, hold with a card, orbit, push in. The HTML does not.

Needed, per beat, and only where the ledger allows a place:

- the NLS crop (documentary, not a reconstruction)
- the verbatim sentence
- the map pin
- the memorial photograph only at Maricourt
- a hold long enough to read

No invented route lines. Source-map crops stay crops.

### 5. The missing letter as a quest, not a script

The adventure has a live unknown: Fairfax’s letter to Churchill. The finder tool already
queries archives. Visitors never see a result, a silence, or a next search from inside the
story.

Needed: a chapter that reports the state of the hunt (last query, last empty result, where
the Churchill papers live) without turning absence into a plot twist.

### 6. Return to the object

After Guillemont and the “absolute shadow” passage, the 1946 note has to be read again. That
return is the destination. The visitor should leave knowing:

- who Fairfax was
- why Churchill answering him is documented, not guessed
- what the six volumes physically are
- what remains lost (the other letter; the government file)

---

## Recommended next build

Keep this first launch thin. The next construction, if approved, is one increment:

**Beat-aware exits from `adventure.html` into the map and the gallery.**

- Somme chapters open `somme-battlefield-map.html` on the matching marker.
- The letter chapter opens a dedicated examine view, or a gallery filter already scrolled to
  the note.
- Each of those pages grows a “continue the walk” link back to the next chapter.

Do not rebuild the deck, the flythrough, or the finder until the walk can hand a visitor from
chapter to place and back again.

Out of scope for that increment: audio, new historical narrative, reconstructed routes,
valuation redesign.

---

## Constraint

If a future page needs a sentence that cannot point at a ledger row, it does not ship. The
adventure is a way of walking evidence, not a way of decorating it.
