# AI WRITING ANTI-PATTERNS

Patterns discovered through iterative evaluation of AI-generated novel
chapters. These are the specific failure modes that survive prompt
engineering and surface-level slop detection. They are structural, not
lexical -- you won't catch them with word lists.

This document supplements ANTI-SLOP.md (which covers word-level slop).

---

## 1. THE OVER-EXPLAIN

**The #1 problem.** The narrator restates what a scene already showed.

A character's hands shake. The dialogue goes silent. The scene lands.
Then the narrator adds: "He was afraid." Or worse: a full paragraph
analyzing what the shaking hands meant.

**Detection:** After every emotional beat, check: does the next
paragraph explain what just happened? If yes, cut it.

**Rule:** If a scene shows it, the narrator doesn't say it. Trust
the image, the gesture, the silence.

---

## 2. TRIADIC LISTING

AI defaults to groups of three: "X. Y. Z." or "X and Y and Z."

Sensory descriptions: "Linseed oil. Cold bronze. The faint char..."
Options: "He could go left. He could go right. He could stay."
Adjectives: "warm and clean and simple"

**Detection:** Search for three consecutive fragments or three items
joined by "and." More than 2 per chapter is a pattern.

**Fix:** Combine two items. Cut one. Use a different number. Two is
often stronger than three.

---

## 3. NEGATIVE-ASSERTION REPETITION

"He did not look back."
"He did not think about the room."
"He did not say what he meant."

Each one is fine. Five in a chapter is a tic.

**Rule:** Max 1 per chapter. Replace with: active alternatives
("The door stayed closed"), or just cut (let the absence speak).

---

## 4. CATALOGING-BY-THINKING

"He thought about X. He thought about Y. He thought about Z."

AI compresses reflection into a list of topics the character
considers. Real interiority is messier -- one thought bleeds into
another, gets interrupted, loops back.

**Fix:** Replace with: the thought itself as a fragment ("The two
years. The wrong-pitched bells."), a physical action, or dialogue.

---

## 5. THE SIMILE CRUTCH

"the way X did Y" -- used 4-8 times per chapter.

AI reaches for simile when it doesn't trust the image. Most of these
can be cut entirely. The image is already there.

**Rule:** Max 2 "the way" similes per chapter. If you need the
comparison, vary the construction. "Like" is fine. Direct metaphor
("his words were bronze -- heavy, functional") is better.

---

## 6. SECTION BREAK AS RHYTHM CRUTCH

AI uses "---" breaks to avoid writing transitions. A chapter with
5 section breaks is 5 vignettes, not a chapter.

**Rule:** Max 2 per chapter, for genuine time/location jumps. Force
continuous prose for everything else.

---

## 7. PARAGRAPH LENGTH UNIFORMITY

AI paragraphs cluster at 4-6 sentences, especially in middle
sections. The variation that appears at chapter openings and closings
flattens in the middle.

**Fix:** Deliberately include 1-2 sentence paragraphs for impact
and 6+ sentence paragraphs for building. Never 3+ consecutive
paragraphs of similar length.

---

## 8. PREDICTABLE EMOTIONAL ARCS

Beats arrive on schedule. If the outline says "curiosity → discovery
→ dread," the chapter delivers exactly that in exactly that order
with no deviation. Real chapters have moments that arrive early,
late, or sideways.

**Fix:** Include one moment per chapter that surprises: a character
saying the wrong thing, an emotion arriving before its trigger, a
beat that interrupts another beat.

---

## 9. REPETITIVE CHAPTER ENDINGS

AI finds a closing pattern and reuses it. In this novel: 4 chapters
ended with "Cass outside, listening to his father work."

**Rule:** No two chapters end with the same structural move. Each
ending belongs to THAT chapter specifically.

---

## 10. BALANCED ANTITHESIS IN DIALOGUE

"I'm not saying X. I'm saying Y."
"Not X, but Y."
"There's a difference."
"Those are different things."

AI loves this rhetorical formula. It sounds clever the first time.
By the third character using it, they all sound like the same person.

**Detection:** Check that no two characters share this sentence
structure. If multiple characters use it, they're not distinct.

---

## 11. DIALOGUE AS WRITTEN PROSE

Characters speak in complete, polished sentences. No one stumbles,
interrupts, trails off, or says something slightly wrong.

A 14-year-old does not speak in epigrams. A 60-year-old merchant
does not deliver thesis statements.

**Fix:** Dialogue should sound like speech. Include: false starts,
interruptions, trailing off, saying the wrong word, not finishing
a thought. At least one imperfect line per scene.

---

## 12. SCENE-SUMMARY IMBALANCE

AI defaults to summary when a scene would be more engaging. "The
morning passed" skips what could be a 200-word interaction that
reveals character.

**Rule:** 70%+ of each chapter should be in-scene (moment by moment,
with dialogue and action). Summary is for time compression only.

---

## EVALUATION NOTES

---

## 13. META-VOCABULARY CONTAMINATION

**POV characters use real-world publishing/genre vocabulary to describe their own
situation.** This is a dead giveaway that the writer (or LLM) stopped thinking
in-character and started thinking in-structure.

Examples:
- "This feels like an isekai premise." — A character in a fantasy world should
  not know what "isekai" means.
- "I'm clearly the protagonist here." — Protagonist is a structural role, not an
  in-world identity.
- "This must be the inciting incident." / "There's too much plot armor." /
  "The author really wants this scene to work."
- "The chapter ended on a cliffhanger." — Characters don't know what chapters are.

**The only exception:** works that are explicitly metafictional (a character who
knows they're in a story, a novel about writing a novel, a fourth-wall-breaking
comedy).

**Rule:** If the character's thought or dialogue contains a word that refers to
a structural element of fiction (genre name, narrative role, publishing term,
writing process), rewrite it in in-world terms. "This is exactly what my book
predicted" instead of "This is exactly like my genre." "I feel like a pawn in
someone's scheme" instead of "I feel like a side character."

---

## 14. COPULA AVOIDANCE

**AI replaces "is/was/has" with fancier verbs:** "serves as," "stands as,"
"acts as," "functions as," "features," "boasts." The effect is stiff and
indirect — the sentence takes a detour when it could state the thing.

Examples:
- "His voice serves as a warning" → "His voice warns"
- "The room features a carved oak table" → "A carved oak table filled the room"
- "The system stands as a testament to..." → "The system proves..."

**Detection:** Search for "serves as," "stands as," "acts as," "functions as,"
"features," "boasts." Each one is a sentence that could be tightened.

**Rule:** Replace every copula-avoidance verb with a direct verb or "is."
The fancier word never adds information — it only adds distance.

---

## 15. SYNONYM CYCLING

**AI avoids repeating a name by cycling through epithets:** "Bob walked in.
The tall man sat down. The engineer pulled out a chair." Each variant is
grammatically correct but the cumulative effect is evasive — the narrator
won't commit to a single identity for the character.

Real narration picks one name/title and uses it consistently, with "he/she"
in between. Cycling epithets to avoid repetition reads as AI-hesitant.

**The exception:** deliberate POV shifts where the epithet reflects how
the viewpoint character sees the person in that moment (e.g., "Father"
vs "the old man" depending on mood).

**Detection:** In any scene with 2+ named characters, count distinct
references to the same character (name, pronoun, epithet). If 3+ different
epithets are used for one character in a single scene, flag it.

**Rule:** Pick one name or title per character per scene. Use it and
pronouns. Only switch epithets when the POV character's relationship to
them changes.

---

## 16. GENERIC CAPSTONE

**A sentence that sounds meaningful but says nothing specific.** Almost
always the last sentence of a paragraph or scene: "The future looked
bright." "Everything had changed." "Nothing would ever be the same."

These aren't wrong — they're just empty. They could end any chapter in
any novel. A good ending sentence belongs to THAT chapter specifically.

**Detection:** Highlight any sentence that could close a Wikipedia article.
Test: swap the ending between two chapters — if neither loses anything,
both are generic capstones.

**Fix:** Replace with either (a) a specific image that embodies the change,
(b) a character action that proves the change, or (c) just cut it — let
the scene's last beat land without commentary.

---

## 17. AUTHORITY FRAMING

**A rhetorical throat-clear before the actual claim:** "At its core, what
the artifact represented was..." "The truth is, she had always known."
"What matters is whether he trusts you." "The fact remains that..."

These are verbal crutches — they tell the reader "this next part is
important" instead of letting the content speak. The framed claim is
always weaker than the direct version.

**Detection:** Search for paragraph-initial "At its core,", "The truth
is,", "What matters is,", "The fact is/remains,". Each one can be deleted
without changing the meaning.

**Fix:** Cut the framing and start with the claim. "The artifact
represented..." "She had always known." "Whether he trusts you."

---

These patterns are invisible to standard slop detection (word lists,
regex). They require either:

1. **Adversarial editing** -- ask a judge to cut 500 words and
   classify what it cuts. OVER-EXPLAIN type dominates every time.

2. **Comparative ranking** -- head-to-head matchups between chapters
   force discrimination the judge can't avoid. Produces a true rank
   order. Swiss-style Elo tournament works well with 4 rounds.

3. **Sentence-level grading** -- flag every sentence as STRONG /
   FINE / WEAK / CUT. The distribution matters more than the average.

Standard 1-10 scoring collapses to a 2-point band regardless of
rubric calibration. Avoid absolute scoring for revision work.
