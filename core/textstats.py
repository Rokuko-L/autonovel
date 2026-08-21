"""Text statistics: context windows and repetition detection."""

import re
import itertools


def tail_context(text: str, max_words: int = 600) -> str:
    """Return the tail of text (~max_words), starting at a sentence boundary.

    Prevents cutting a previous chapter's ending mid-sentence, which would
    hand the writer a dangling fragment to continue from.
    """
    import re
    words = text.split()
    if len(words) <= max_words:
        return text
    tail = ' '.join(words[-max_words:])
    # Start after the first sentence boundary in the tail so we don't begin mid-sentence
    m = re.search(r'[.!?]["\')\]]?\s+\S', tail)
    if m:
        tail = tail[m.end() - 1:].lstrip()
    return tail

def head_context(text: str, max_words: int = 300) -> str:
    """Return the head of text (~max_words), ending at a sentence boundary."""
    import re
    words = text.split()
    if len(words) <= max_words:
        return text
    head = ' '.join(words[:max_words])
    last = max(head.rfind('.'), head.rfind('!'), head.rfind('?'))
    if last > len(head) * 0.6:
        head = head[:last + 1]
    else:
        head += " […]"
    return head

def shingled_jaccard(a: str, b: str, n: int = 4) -> float:
    """Token n-gram Jaccard similarity between two strings."""
    a_tokens = a.lower().split()
    b_tokens = b.lower().split()
    if len(a_tokens) < n or len(b_tokens) < n:
        return 0.0
    shingles_a = set(zip(*[a_tokens[i:] for i in range(n)]))
    shingles_b = set(zip(*[b_tokens[i:] for i in range(n)]))
    if not shingles_a or not shingles_b:
        return 0.0
    return len(shingles_a & shingles_b) / len(shingles_a | shingles_b)

def detect_repeated_paragraphs(
    text: str,
    min_words: int = 12,
    jaccard_threshold: float = 0.55,
    ngram: int = 4,
) -> tuple[list[tuple[int, int, float]], list[str]]:
    """Find near-duplicate paragraph pairs in text.

    Splits on double-newlines, filters out short paragraphs and `---`
    separators. Returns (pairs, paragraphs) where each pair is
    (idx_a, idx_b, similarity) and paragraphs is the filtered list
    (indices correspond).
    """
    raw = [p.strip() for p in text.strip().split('\n\n') if p.strip()]
    expanded = [p for p in raw if not p.startswith('---')]
    filtered = [(i, p) for i, p in enumerate(expanded) if len(p.split()) >= min_words]
    pairs: list[tuple[int, int, float]] = []
    for (i, p1), (j, p2) in itertools.combinations(filtered, 2):
        sim = shingled_jaccard(p1, p2, n=ngram)
        if sim >= jaccard_threshold:
            pairs.append((i, j, sim))
    return pairs, expanded

def chain_flagged_pairs(
    pairs: list[tuple[int, int, float]],
    max_gap: int = 3,
    max_offset: int = 30,
) -> list[list[tuple[int, int, float]]]:
    """Cluster pairs whose (j-i) distance is similar and positions are near.

    Two pairs (i1,j1) and (i2,j2) chain if |(j1-i1) - (j2-i2)| <= max_gap
    AND |i2 - i1| <= max_offset. This groups structurally repeated templates
    (same offset recurring at different absolute positions) while keeping
    isolated refrains separate.
    """
    if not pairs:
        return []
    parent = list(range(len(pairs)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    for a in range(len(pairs)):
        i1, j1, _ = pairs[a]
        d1 = j1 - i1
        for b in range(a + 1, len(pairs)):
            i2, j2, _ = pairs[b]
            d2 = j2 - i2
            if abs(d1 - d2) <= max_gap and abs(i2 - i1) <= max_offset:
                union(a, b)

    from collections import defaultdict
    clusters: dict[int, list[tuple[int, int, float]]] = defaultdict(list)
    for idx, p in enumerate(pairs):
        clusters[find(idx)].append(p)
    return list(clusters.values())

def check_structural_repetition(
    text: str,
    min_words: int = 12,
    jaccard_threshold: float = 0.55,
    high_sim_threshold: float = 0.85,
    ngram: int = 4,
    max_gap: int = 3,
    max_offset: int = 30,
) -> tuple[bool, list[str], dict]:
    """Run full repetition check and return (regen, feedback_lines, sidecar).

    Decision logic:
    - A chained cluster is structural if it has >=3 high-sim pairs
      (the reaction-rules for-loop pattern).
    - Additionally, any unchained pair with sim >= high_sim_threshold
      is structural (short duplicated block like a repeated letter).
    """
    pairs, paras = detect_repeated_paragraphs(
        text, min_words, jaccard_threshold, ngram
    )
    clusters = chain_flagged_pairs(pairs, max_gap, max_offset)

    feedback: list[str] = []
    sidecar_clusters: list[dict] = []

    for cluster in clusters:
        indices = sorted(set(p[0] for p in cluster) | set(p[1] for p in cluster))
        n_pairs = len(cluster)
        n_paras = len(indices)
        sims = [s for _, _, s in cluster]
        high_sim = sum(1 for s in sims if s >= high_sim_threshold)

        # Rep pick: paragraph that appears in the most pairs
        counts: dict[int, int] = {}
        for i, j, _ in cluster:
            counts[i] = counts.get(i, 0) + 1
            counts[j] = counts.get(j, 0) + 1
        rep_idx = max(counts, key=lambda k: counts[k])
        rep_text = paras[rep_idx][:200] if rep_idx < len(paras) else ""

        is_structural = high_sim >= 3

        entry = {
            "n_paras": n_paras,
            "n_pairs": n_pairs,
            "high_sim": high_sim,
            "min_sim": round(min(sims), 3),
            "offsets": sorted(set(j - i for i, j, _ in cluster)),
            "indices": indices,
            "representative": rep_text[:120],
            "is_structural": is_structural,
        }
        sidecar_clusters.append(entry)

        if is_structural:
            feedback.append(
                f"The following passage (or something nearly identical to it) "
                f"appeared in {n_paras} different places:\n"
                f'  "{rep_text}..."\n'
                f"This repeated block appeared {n_pairs} times. "
                f"Each occurrence should be a distinct moment — vary the "
                f"content or cut the repetition entirely. Do not reuse the same "
                f"scene-setting beats (checking the quest log, looking at the "
                f"calendar, etc.) as a template for multiple list items.\n"
            )

    # Individual high-sim pairs within non-structural clusters
    # (catches isolated duplicates like a repeated letter quotation
    # that don't form a structural for-loop pattern)
    flagged_individual_pairs: list[dict] = []
    seen_paras: set[int] = set()
    for cluster in clusters:
        i0, j0, _ = cluster[0]
        is_struct = sum(1 for _, _, s in cluster if s >= high_sim_threshold) >= 3
        if is_struct:
            continue
        for i, j, sim in cluster:
            if sim >= high_sim_threshold:
                if i not in seen_paras:
                    seen_paras.add(i)
                    rep_text = paras[i][:200] if i < len(paras) else ""
                    feedback.append(
                        f"The following passage appeared near-verbatim in 2 places:\n"
                        f'  "{rep_text}..."\n'
                    )
                    flagged_individual_pairs.append({
                        "idx_a": i, "idx_b": j, "sim": round(sim, 3),
                        "representative": rep_text[:120],
                    })

    sidecar = {
        "regen_requested": len(feedback) > 0,
        "total_pairs": len(pairs),
        "total_clusters": len(clusters),
        "clusters": sidecar_clusters,
        "flagged_individual_pairs": flagged_individual_pairs,
    }

    return len(feedback) > 0, feedback, sidecar
