from dataclasses import dataclass, field
from typing import Optional

@dataclass
class EvalDim:
    key: str
    weight: float
    criteria: str

@dataclass
class FoundationEval:
    overall_calibration: str
    dimensions: list[EvalDim]

@dataclass
class ChapterEval:
    overall_calibration: str
    dimensions: list[EvalDim]

@dataclass
class ReaderMods:
    earned_ending_hint: str = ""
    extra_questions: dict = field(default_factory=dict)

@dataclass
class ReaderPanelEval:
    genre_reader_identity: str
    prompt_modifications: Optional[ReaderMods] = None

@dataclass
class EvalConfig:
    foundation: FoundationEval
    chapter: ChapterEval
    reader_panel: ReaderPanelEval

@dataclass
class Identity:
    seed_system: str
    world_system: str
    character_system: str
    outline_system: str
    chapter_system: str
    revision_system: str
    canon_system: str
    evaluator_system: str

@dataclass
class WorldGen:
    description: str
    sections: list[str]

@dataclass
class CharGen:
    description: str
    focus_areas: list[str]

@dataclass
class OutlineGen:
    description: str
    estimated_chapters: int
    estimated_words: int
    notes: list[str]

@dataclass
class GenConfig:
    world: WorldGen
    character: CharGen
    outline: OutlineGen
    seed_generate_prompt: str
    seed_riff_prompt: str
    gen_world_prompt: str
    gen_characters_prompt: str
    gen_outline_prompt: str
    gen_outline_part2_prompt: str
    gen_canon_prompt: str
    draft_chapter_instructions: str
    anti_pattern_rules: str
    canon_categories: list[str]
    arc_summary_premise: str

@dataclass
class Framework:
    lore_priorities: str
    stability_trap_applies: bool = True
    character_framework: str
    plot_framework: str
    disclosure_framework: str = ""

@dataclass
class GenreConfig:
    genre_name: str
    user_directives: str = ""
    identity: Identity
    generation: GenConfig
    evaluation: EvalConfig
    framework: Framework
