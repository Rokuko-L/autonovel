You are an editor reviewing the chapter titles of a novel.
The novel seed is:
{seed}

The current chapter outline is:
{outline}

Here are the current titles in order:
{current_titles}

YOUR TASK:
Review and rewrite the chapter titles to make them catchier, wittier, and perfectly matching the tone of the seed/story. Keep the ones that are already cool, but change the boring, cliché, or repetitive ones.

CRITICAL CONSTRAINTS:
1. Output MUST be valid JSON only, mapping chapter numbers to their new titles:
   Example format:
   {{
     "1": "Title One",
     "2": "Title Two",
     ...
   }}
2. No duplicates: Every chapter title must be unique.
3. Prefix variety:
   - At most 30% of chapter titles (at most 9 out of 30) can start with the word "The".
   - At most 10% of chapter titles (at most 3 out of 30) can start with the words "In Which".
   - At most 10% of chapter titles (at most 3 out of 30) can start with the words "A" or "An".
   - Vary the starting words by using different grammatical structures:
     * Gerund phrases (e.g., "Breaking the Mirror", "Drowning the Song")
     * Prepositional phrases (e.g., "Inside the Iron Stack", "Under the Scriptorium")
     * Bare Nouns (e.g., "Obsidian Dreams", "Glass Hearts")
     * Direct Action/Verbs (e.g., "Whisper to the Dead", "Flee the Golden Court")
4. Word variety:
   - Do not repeat distinctive words (e.g., "Gambit", "Protocol", "Aftermath", "Core", "Apocalypse", character names like "Kael" or "Dara") more than twice across all titles.
   - Do not repeat long comedic phrasing formulas.
