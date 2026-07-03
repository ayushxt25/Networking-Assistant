"""
Topic Generator Service
------------------------
Generates natural-sounding conversation starters using GPT-2 Small.

Unlike the event analyzer (which makes a classification judgment call),
this service produces original generated text. We use prompt engineering --
constructing a structured natural-language prompt that interpolates the
event's themes and the user's interests -- to nudge GPT-2 toward producing
short, first-person conversation openers rather than arbitrary text.

set_seed(42) fixes the random seed used by the underlying generation
sampler. This means that, given the same prompt, the model will produce the
same output across repeated runs. That's valuable for debugging and for
writing deterministic-ish tests, even though GPT-2 Small's output quality
is naturally a bit rough compared to larger models.
"""

import logging
import re
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

_generator = None
_generator_load_attempted = False


def _has_local_model_cache(model_name: str) -> bool:
    cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
    model_dir = cache_dir / f"models--{model_name.replace('/', '--')}"
    snapshots_dir = model_dir / "snapshots"
    return snapshots_dir.exists() and any(snapshots_dir.iterdir())


def _build_prompt(
    themes: List[str],
    interests: List[str],
    relationship_context: Optional[str] = None,
) -> str:
    theme_text = ", ".join(themes) if themes else "general topics"
    interest_text = ", ".join(interests) if interests else "meeting new people"
    context_block = (
        f"Relevant relationship context:\n{relationship_context}\n"
        if relationship_context
        else ""
    )

    return (
        f"I'm attending an event focused on {theme_text}. "
        f"I'm personally interested in {interest_text}. "
        f"{context_block}"
        f"Here are some conversation starters I could use:\n"
        f"1."
    )


def _clean_line(line: str) -> str:
    """Strip leading numbering/bullets and surrounding whitespace from a line."""
    cleaned = line.strip()
    for prefix in ("1.", "2.", "3.", "-", "*", "â€¢"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
    return cleaned


def _normalize_topic_token(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip(" .,:;!?")).strip()


def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    result = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _is_low_quality_suggestion(suggestion: str) -> bool:
    text = suggestion.strip()
    if not text:
        return True
    if text.count("|") >= 2:
        return True
    if len(text) < 18:
        return True

    words = re.findall(r"[A-Za-z']+", text)
    if len(words) < 4:
        return True

    alpha_ratio = sum(char.isalpha() or char.isspace() for char in text) / max(len(text), 1)
    if alpha_ratio < 0.72:
        return True

    lowercase_words = [word.lower() for word in words]
    unique_words = set(lowercase_words)
    if len(unique_words) <= 2 and len(lowercase_words) >= 4:
        return True
    if any(lowercase_words.count(word) >= 3 for word in unique_words):
        return True

    useful_markers = ("?", "how ", "what ", "which ", "why ", "where ", "when ", "tell me", "i noticed")
    if not any(marker in text.lower() for marker in useful_markers):
        return True

    return False


def _get_generator():
    global _generator, _generator_load_attempted

    if _generator is not None:
        return _generator
    if _generator_load_attempted:
        return None

    _generator_load_attempted = True

    if not _has_local_model_cache("gpt2"):
        logger.info("Transformer model cache not found; using fallback topic generation.")
        return None

    try:
        from transformers import pipeline, set_seed

        set_seed(42)
        _generator = pipeline("text-generation", model="gpt2")
    except Exception as exc:
        logger.warning("Falling back to template-based topic generation: %s", exc)
        _generator = None

    return _generator


def _generate_topics_fallback(
    themes: List[str],
    interests: List[str],
    relationship_context: Optional[str] = None,
) -> List[str]:
    primary_theme = _normalize_topic_token(themes[0]) if themes else "this event"
    secondary_theme = _normalize_topic_token(themes[1]) if len(themes) > 1 else primary_theme
    primary_interest = _normalize_topic_token(interests[0]) if interests else "your work"
    secondary_interest = _normalize_topic_token(interests[1]) if len(interests) > 1 else primary_interest
    context_hint = (
        " I want to keep the conversation relevant to the relationships and priorities I'm already tracking."
        if relationship_context
        else ""
    )

    starters = [
        f"I noticed this event focuses on {primary_theme}. What trends are you watching most closely there?{context_hint}",
        f"What inspired your work in {primary_interest}?",
        f"How do you see {secondary_interest} changing over the next year?",
    ]

    if secondary_theme and secondary_theme != primary_theme:
        starters.append(
            f"How does {secondary_theme} show up in the conversations you're having most often right now?"
        )

    cleaned = [_normalize_topic_token(item) for item in starters if item.strip()]
    return _dedupe_preserve_order(cleaned)[:3]


def finalize_topic_suggestions(
    suggestions: List[str],
    themes: List[str],
    interests: List[str],
    relationship_context: Optional[str] = None,
) -> List[str]:
    cleaned = [_clean_line(item) for item in suggestions]
    cleaned = [item for item in cleaned if item and not _is_low_quality_suggestion(item)]
    cleaned = _dedupe_preserve_order(cleaned)
    if cleaned:
        return cleaned[:3]
    return _generate_topics_fallback(themes, interests, relationship_context)


def generate_topics(
    themes: List[str],
    interests: List[str],
    relationship_context: Optional[str] = None,
) -> List[str]:
    """
    Generate up to 3 conversation starter suggestions.

    Args:
        themes: Themes extracted from the event description (see event_analyzer).
        interests: The user's stated interests.

    Returns:
        A list of up to 3 non-empty conversation starter strings.
    """
    prompt = _build_prompt(themes, interests, relationship_context)

    generator = _get_generator()
    if generator is None:
        return _generate_topics_fallback(themes, interests, relationship_context)

    try:
        output = generator(
            prompt,
            max_new_tokens=80,
            num_return_sequences=1,
            truncation=True,
            pad_token_id=50256,
        )
    except Exception as exc:
        logger.warning("Topic generation failed; using fallback suggestions: %s", exc)
        return _generate_topics_fallback(themes, interests, relationship_context)

    generated_text = output[0]["generated_text"]
    continuation = generated_text[len(prompt):]
    lines = continuation.split("\n")
    return finalize_topic_suggestions(lines, themes, interests, relationship_context)
