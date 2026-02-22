# Sales Visual Spec

Three production-ready visual definitions for the Churchill–Fairfax first edition set. Every element traces to a ledger entry in `ground-truth-ledger.md`. No speculation.

---

## Visual 1: Provenance Timeline Card

**Format**: Horizontal timeline, 1873–1950 (Fairfax's life), with milestone dots and source citations below each event.

**Design**: Clean horizontal bar, left-to-right chronological. Each milestone gets a dot, date label, event text, and small-caps source citation. Two colour zones: military career (1900–1916) and Churchill connection (1946–1950).

### Timeline Events

| Date | Event | Ledger # | Source |
|------|-------|----------|--------|
| 12 Sep 1873 | Bryan Charles Fairfax born | 1 | Readme.md line 36 |
| 1900 | Boxer Uprising service, China | 4 | Readme.md line 36 |
| 28 Jun 1916 | General Congreve visits: "if you cannot manage it, no other troops can" | 43 | TextExtract.md line 15 (89th Bde p.129) |
| 1 Jul 1916, 6:25am | Attack launched at Maricourt; Fairfax advances arm-in-arm with Commandant Lepetit | 12, 14 | 89th Bde p.131; Readme.md line 47 |
| 11 Jul 1916 | French Colonel de Coutard names Fairfax: "ses hautes qualites militaires" | 15 | 89th Bde p.134 |
| Mid-Jul 1916 | Fairfax holds Trones Wood under fire: "could hold on" | 16 | 89th Bde p.143 |
| Night of 29 Jul 1916 | Gassed on way to Guillemont assembly position | 17 | TextExtract.md line 29 |
| 30 Jul 1916 | Attacks at Guillemont despite gas poisoning | 18, 19 | TextExtract.md lines 31, 49 |
| After 30 Jul 1916 | Stanley orders Fairfax to leave: "went to an absolute shadow" | 19 | TextExtract.md line 49 |
| Aug 1916 | Evacuated to England | 22 | Readme.md line 105 |
| 1916 | Awarded C.M.G. for wartime service | 7 | Readme.md line 36 |
| 6 Dec 1946 | Churchill writes from Chartwell: "Dear Colonel Fairfax" | 26, 27 | signature.JPG; FC line 34 |
| 1948 | "The Gathering Storm" first published by Cassell | 28 | FirstPublished.JPG |
| 29 Jan 1950 | Fairfax dies in Toronto | 39 | Readme.md line 38 |

### Production Notes

- Dimensions: 1200 x 400px landscape card, suitable for print and web
- Font: serif for dates, sans-serif for event text
- Source citations in 7pt below each milestone
- Optional: sepia/parchment background texture
- Inset photo: ColFairfax.jpeg at left margin, signature.JPG at right margin

---

## Visual 2: Unit/Location Map with Cited Markers

**Format**: Topographic map of the Somme sector (Maricourt–Guillemont corridor) with dated markers. Inset of Chartwell, Kent.

### Map Extent

Primary: ~49.97N to 50.01N, ~2.75E to 2.85E (Maricourt to Guillemont, ~5km corridor)
Inset: Chartwell, Westerham, Kent (51.2537N, 0.0814E)

### Markers (each references a ledger entry)

| # | Label | Coordinates (approx.) | Date | Ledger # | Source |
|---|-------|-----------------------|------|----------|--------|
| A | Brigade HQ — "pit southwest of Maricourt" | 49.985N, 2.785E | Jun 1916 | 10 | 89th Bde p.121 |
| B | Maricourt — attack launch point | 49.9875N, 2.7912E | 1 Jul 1916 | 12 | 89th Bde p.131 |
| C | Maricourt Memorial | 49.9875N, 2.7912E | — | 40, 41 | Readme.md line 114 (49 59'15.0"N 2 47'28.3"E) |
| D | Montauban | 49.993N, 2.806E | 1 Jul 1916 | — | 89th Bde context |
| E | Briqueterie — objective taken | 49.990N, 2.810E | 1 Jul 1916 | 13 | 89th Bde p.131 |
| F | Bernafay Wood | 49.993N, 2.825E | Jul 1916 | — | TE line 115 |
| G | Trones Wood — "Fairfax was in the wood... could hold on" | 49.990N, 2.830E | Mid-Jul 1916 | 16 | 89th Bde p.143 |
| H | Assembly position — Fairfax gassed | 49.983N, 2.840E | Night of 29 Jul | 17 | TE line 29 |
| I | Guillemont — attack in fog, "couldn't see ten yards" | 49.982N, 2.845E | 30 Jul 1916 | 18, 19, 21 | TE lines 31, 47, 49 |
| J | Chartwell, Kent (inset) | 51.2537N, 0.0814E | 6 Dec 1946 | 26 | Readme.md line 126 |

### Blender Camera Path (for fly-through animation)

Fairfax's documented movement sequence, sourced only from the 89th Brigade text:

1. **Ailly-sur-Somme** (HQ, May 1916) — p.119
2. **Vaux** (17th Bn HQ, late May) — p.119
3. **Southwest of Maricourt** (Brigade HQ pit, June) — p.121
4. **Maricourt sector** (attack launch, 1 Jul 6:25am) — p.131
5. **Briqueterie** (objective taken, 1 Jul) — p.131
6. **Trones Wood** (mid-July, holding position) — p.143
7. **Assembly position near Guillemont** (gassed, night of 29 Jul) — TE line 29
8. **Guillemont attack** (fought despite gas, 30 Jul) — TE line 49
9. **Evacuated** (ordered to leave, early Aug) — TE line 49

Camera: low-altitude (~200m), slow dolly from marker A to marker I, pausing at each waypoint. Overlay date + source page at each pause.

### Production Notes

- Base map: OpenStreetMap or period trench map overlay
- Marker style: numbered circles with date labels
- Dotted line connecting A→I showing Fairfax's movement
- Inset (Chartwell) in bottom-right corner with "6 December 1946" label
- Scale bar and north arrow required
- All marker labels include page/line citation in small text

---

## Visual 3: Artifact Close-Up Sequence with Authenticated Captions

**Format**: 8 frames, each with one image and one fact-only caption. Suitable for slideshow, print catalogue, or web gallery.

### Frame Sequence

| Frame | Image | Caption | Ledger # |
|-------|-------|---------|----------|
| 1 | Images/signature.JPG | **Churchill's letter to Colonel Fairfax.** "Chartwell, Westerham, Kent. 6 December, 1946. Dear Colonel Fairfax..." Original signed letter from Winston Churchill, affixed to Volume I. | 26, 27 |
| 2 | Images/FirstPublished.JPG | **First edition copyright page.** "First Published 1948. Cassell and Company Ltd." No mention of later printings — confirms first edition, first printing. | 28, 34 |
| 3 | Images/Price.JPG | **First issue dust jacket price.** "25s. NET" — the correct price for Volumes I–IV, the most visible external sign of a first issue jacket. | 29 |
| 4 | Images/hero.JPG | **Complete six-volume set.** Cassell first edition, black cloth boards with gilt spine titles. All volumes present with original dust jackets. | 31 |
| 5 | Images/TopEdgeVolume1.jpeg | **Red top edge, Volume I.** Hallmark of first printing. Some fading is typical; this copy retains pronounced colour. | 32 |
| 6 | Images/ColFairfax.jpeg | **Colonel Bryan Charles Fairfax, C.M.G.** Obituary confirming rank, decorations, and identity. Born 12 September 1873, died 29 January 1950, Toronto. | 39, 47 |
| 7 | MonumenImages/memorial2.jpg | **Maricourt memorial plaque.** "1er juillet 1916" — at the site where Fairfax and Commandant Lepetit advanced arm-in-arm. Coordinates: 49 59'15.0"N 2 47'28.3"E. | 40, 41, 14 |
| 8 | *[Text panel — quote from 89th Brigade]* | **French citation naming Fairfax, 11 July 1916.** "...les relations si cordiales entretenues avec leur chef le Colonel Fairfax ont permis de remarquer ses hautes qualites militaires et ont fait regretter l'eloignement de ce chef brillant et de son magnifique Bataillon." — Colonel de Coutard, 89th Brigade history, p.134. | 15 |

### Production Notes

- Each frame: single image occupying 70% of frame area, caption below
- Caption font: serif, 14pt body, bold title line
- Background: off-white (#f5f2eb) or dark charcoal (#2a2a2a) depending on presentation context
- Frame 8 is text-only (styled as a period document or letterhead) since it quotes the 89th Brigade PDF
- For print: 8.5 x 11" portrait, one frame per page
- For web: horizontal carousel with swipe navigation
- All captions cite ledger entry numbers for traceability
