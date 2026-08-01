# Voice Profile

This file has two parts:
1. **Guardrails** -- universal rules to avoid AI-generated slop. These
   apply to ALL voices and are non-negotiable.
2. **Voice Identity** -- the specific voice for THIS novel. Generated
   during the foundation phase. Could be anything: dense and mythic,
   spare and brutal, warm and whimsical. The voice emerges from the
   story's needs.

---

## Part 1: Guardrails (permanent, all novels)

These are the cliff edges. Stay away from them regardless of voice.

### Tier 1: Banned words -- kill on sight

These are statistically overrepresented in LLM output vs. human writing.
If one appears, rewrite the sentence. No exceptions.

| Kill this         | Use instead                                    |
|-------------------|------------------------------------------------|
| delve             | dig into, examine, look at                     |
| utilize           | use                                            |
| leverage (verb)   | use, take advantage of                         |
| facilitate        | help, enable, make possible                    |
| elucidate         | explain, clarify                               |
| embark            | start, begin                                   |
| endeavor          | effort, try                                    |
| encompass         | include, cover                                 |
| multifaceted      | complex, varied                                |
| tapestry          | (describe the actual thing)                    |
| testament to      | shows, proves, demonstrates                    |
| paradigm          | model, approach, framework                     |
| synergy           | (delete the sentence and start over)           |
| holistic          | whole, complete, full-picture                  |
| catalyze          | trigger, cause, spark                          |
| juxtapose         | compare, contrast, set against                 |
| nuanced (filler)  | (cut it -- if it's nuanced, show how)          |
| realm             | area, field, domain                            |
| landscape (metaphorical) | field, space, situation                 |
| myriad            | many, lots of                                  |
| plethora          | many, a lot                                    |

### Tier 2: Suspicious in clusters

Fine alone. Three in one paragraph = rewrite that paragraph.

robust, comprehensive, seamless, cutting-edge, innovative, streamline,
empower, foster, enhance, elevate, optimize, pivotal, intricate,
profound, resonate, underscore, harness, navigate (metaphorical),
cultivate, bolster, galvanize, cornerstone, game-changer, scalable

### Tier 3: Filler phrases -- delete on sight

These add zero information. The sentence is always better without them.

- "It's worth noting that..." -> just state it
- "It's important to note that..." -> just state it
- "Importantly, ..." / "Notably, ..." / "Interestingly, ..." -> just state it
- "Let's dive into..." / "Let's explore..." -> start with the content
- "As we can see..." -> they can see
- "Furthermore, ..." / "Moreover, ..." / "Additionally, ..." -> and, also, or just start
- "In today's [fast-paced/digital/modern] world..." -> delete the clause
- "At the end of the day..." -> delete
- "It goes without saying..." -> then don't say it
- "When it comes to..." -> just talk about the thing
- "One might argue that..." -> argue it or don't
- "Not just X, but Y" -> restructure (the #1 LLM rhetorical crutch)

### Tic families -- density is the tell (permanent, all novels)

These constructions are normal ONCE. They betray machine origin when they
cluster. Max allowances per chapter below. Past that, rewrite with varied
syntax.

**1. "not X, but Y" (bare form).** "It did not arrive as sound, but as a
blow." "Not a melody, not a hum, but a deep vibration." Max 1 per chapter.
Variants all count: "not X so much as Y", "not X, not Y[, but Z]",
"X was not Y, but Z". Replace with direct statement: "The throne was
singing. A bone-level vibration, not a melody."

**2. Stacked negation ("not X, not Y").** "Not loudly. Not the way they did
when..." Max 1 per chapter. Restructure to name what it IS, not what it
isn't, or use a single negation.

**3. The abstract-noun frame ("the X of Y").** "the sound of", "the shape
of", "the weight of", "the color of", "the feel of", "the taste of",
"the music of", "the language of" used as a rhetorical device ("the sound
of something waiting to be told what to be"). Max 2 per chapter, and only
when literal ("the weight of the axe"). If the phrase is figurative,
rewrite: "It sounded like something waiting for instructions."

**4. "a thing of X and Y" descriptor frame.** "a thing of jagged edges and
creeping shadow", "things of beauty and horror". Max 1 per chapter. Use a
concrete object with specific detail instead: "jagged black stone, edges
sticky with shadow".

**5. Cross-chapter phrase recycling.** A distinctive image or metaphor used
in an earlier chapter is spent. "The bruise-colored sky" in chapter 1 means
chapter 5 must find another sky. The pipeline tracks these; if a phrase
appears in this list, do not use it or any close variant.

**6. Aphorism capstones.** Sentences that snap shut with a grand summary
("It was the sound of something waiting to be told what to be." / "Mercy.")
as paragraph or scene enders. Max 1 per scene. Let the scene end on action
or specific detail instead of thesis statements.

**7. The judge's feedback.** If the evaluator flagged specific sentences or
patterns in a prior attempt, those exact constructions are now radioactive.
Fix them verbatim, not in spirit.

### Structural slop patterns

These are the shapes that betray machine origin. Avoid them in any voice.

**Paragraph template machine**: Don't repeat the same paragraph
structure (topic sentence -> elaboration -> example -> wrap-up).
Vary it. Sometimes the point comes last. Sometimes a paragraph is
one sentence. Sometimes three long ones in a row.

**Sentence length uniformity**: If every sentence is 15-25 words,
it reads as synthetic. Mix in fragments. And long, winding,
clause-heavy sentences that carry the reader through a thought
the way a river carries a leaf. Then a short one.

**Transition word addiction**: If consecutive paragraphs start with
"However," "Furthermore," "Additionally," "Moreover," "Nevertheless"
-- rewrite. Start with the subject. Start with action. Start with
dialogue. Start with a sense detail.

**Symmetry addiction**: Don't balance everything. Three pros, three
cons, five steps -- that's a tell. Real writing is lumpy. Some
sections are long because they need to be. Some are two lines.

**Hedge parade**: "may," "might," "could potentially," "it's possible
that" -- pick one per page, max. State things or don't.

**Em dash overload**: One or two per page is fine. Five per paragraph
is a dead giveaway. Use commas, parentheses, or two sentences instead.

**List abuse**: Prose, not bullets. If the scene calls for a list
(a merchant's inventory, a spell's components), earn it. Don't
default to bullet points because it's easy.

**Staccato fragment abuse**: No staccato emphasis fragments. Do not follow a full sentence or clause with one or more short fragments (roughly 1-4 words, lacking a main verb or a complete subject-verb pair) used to land emphasis through rhythm and white space rather than through content. This applies regardless of how many fragments are used, their part of speech, or whether they're nouns, adjectives, or clipped clauses — the tell is the shape (statement, then staccato beat(s)), not the specific words.

Banned shape, with examples spanning different lengths and word types so the pattern is clear — do not treat these as the exhaustive list, treat them as the same failure mode wearing different clothes:
*   *Single-word pairs:* "Silver. Victory." / "Restless. Hungry."
*   *Adjective contrasts:* "Warm. Safe." / "Practical. Unadorned."
*   *Three-part noun/adjective runs:* "Stronger. Tighter. More efficient."
*   *Clipped parallel clauses:* "It hurt. It was real." / "The silence stretched. Cracked. Broke."
*   *Negated fragments:* "Not reduced. Not restructured."

If a moment needs emphatic weight, build it into the rhythm of a single full sentence (varied clause length, a strong verb, a turn in the syntax) rather than trailing fragments after it. Before finalizing any sentence that ends in a period followed by a 1-4 word fragment, ask: could this be one sentence instead? If yes, rewrite it as one.

### The smell test

After writing any passage, ask:
- Read it aloud. Does it sound like a person talking?
- Is there a single surprising sentence? Human writing surprises.
- Does it say something specific? Could you swap the topic and the
  words would still work? Specificity kills slop.
- Would a reader think "AI wrote this"? If yes, rewrite.

---

## Part 2: Voice Identity (generated per novel)

Everything below is discovered during the foundation phase.
The agent proposes a voice that serves THIS story, writes exemplar
passages, and calibrates against them throughout drafting.

### Tone
<!-- Generated during foundation. Examples:
     "Mythic and weighty, like stone tablets being read aloud."
     "Warm, slightly breathless, like a traveler telling stories by firelight."
     "Spare and cold. Sentences like knife cuts." -->

### Sentence Rhythm
<!-- Generated during foundation. Not rules -- tendencies.
     "Long sentences for worldbuilding, short for violence."
     "Dialogue is clipped. Narration flows." -->

### Vocabulary Register
<!-- Generated during foundation. The word-hoard for this world.
     What does this world SOUND like? Anglo-Saxon blunt? Latinate
     baroque? Colloquial modern? A mix? -->

### POV and Tense
<!-- Generated during foundation.
     Third limited? First? Rotating? Omniscient?
     Past tense? Present? Does it shift for effect? -->

### Dialogue Conventions
<!-- Generated during foundation.
     Tags: "said" only? Action beats? No tags at all?
     How do characters sound different from each other?
     Subtext rules: do characters say what they mean? -->

### Exemplar Passages
<!-- 3-5 paragraphs that ARE the voice. Written during foundation.
     The agent calibrates every chapter against these.
     These are the tuning fork. -->

### Anti-Exemplars
<!-- 3-5 paragraphs showing what this voice is NOT.
     Not the generic anti-slop stuff above -- specific to this novel.
     "This is too flowery for our tone." "This is too modern." -->
