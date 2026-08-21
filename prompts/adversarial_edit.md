You are editing a fantasy novel chapter. Your job: identify exactly
what to cut or rewrite to make this chapter tighter, sharper, more alive.

THE CHAPTER ({word_count} words):
{chapter_text}

DISCLOSURE CEILING (everything established on the page through prior chapters):
{canon_context}

YOUR TASK:
1. Find 10-20 specific passages that should be CUT or REWRITTEN.
   For each, quote the EXACT text (minimum 10 words of the quote so
   it's unambiguous), explain why it's weak, and classify it.

2. Classify each cut as one of:
   - FAT: adds nothing, could be removed with no loss
   - REDUNDANT: restates what a previous sentence/scene already showed
   - OVER-EXPLAIN: narrator explaining what the scene already demonstrated
    - GENERIC: could appear in any novel, not specific to this world/character.
      Includes aphorism formulas ("X is the language of Y"), authority framings
      ("At its core, what matters is..."), and generic capstone sentences
      ("The future looked bright.")
    - TELL: names an emotion or state instead of showing it
    - STACCATO: manufactured punchlines — 2 or more consecutive fragments of 3 words or fewer used for dramatic/emphatic effect (e.g., "Silver. Victory.")
   - STRUCTURAL: paragraph/section that disrupts pacing or rhythm
   - UNGROUNDED: uses a name, title, term, or concept without it having been
     established in the disclosure ceiling above. Example: a character is addressed
     as "the Saint" but no prior chapter has explained what a Saint is.

3. For REWRITE candidates (not cuts), provide a specific revision.

4. Estimate how many words could be cut total without losing anything
   the chapter needs.

Respond with JSON:
{{
  "cuts": [
    {{
      "quote": "exact text from the chapter (10+ words)",
      "type": "FAT|REDUNDANT|OVER-EXPLAIN|GENERIC|TELL|STRUCTURAL",
      "reason": "why this should go",
      "action": "CUT or REWRITE",
      "rewrite": "replacement text if action is REWRITE, null if CUT"
    }}
  ],
  "total_cuttable_words": N,
  "tightest_passage": "quote the best 2-3 sentences in the chapter -- the ones you'd never touch",
  "loosest_passage": "quote the worst 2-3 sentences -- the ones that most need work",
  "overall_fat_percentage": N,
  "one_sentence_verdict": "what this chapter does well and what drags it down, in one sentence"
}}

IMPORTANT: After you finish your first pass, do a second read.
Ask yourself: "Does any sentence here still feel like an LLM wrote it?"
If yes, flag those too. Trust the instinct — if it sounds clean, generic,
or too perfectly balanced, it's probably AI-slop.
