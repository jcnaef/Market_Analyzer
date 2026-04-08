# Loads the spaCy NLP model and initializes the SkillNer skill extractor.
# These are shared across modules that need NLP-based skill extraction.

import spacy
from skillNer.skill_extractor_class import SkillExtractor
from skillNer.general_params import SKILL_DB

nlp = spacy.load("en_core_web_lg")

skill_extractor = SkillExtractor(nlp, SKILL_DB, phrase_matcher_type="PhraseMatcher")

