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
    for prefix in ("1.", "2.", "3.", "-", "*", "•"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
    return cleaned


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
    theme_text = ", ".join(themes) if themes else "the event"
    interest_text = ", ".join(interests) if interests else "meeting new people"
    context_hint = ""
    if relationship_context:
        context_hint = " Based on your existing relationship context, where relevant."

    return [
        f"What drew you to {theme_text}?{context_hint}",
        f"How does {interest_text} connect with your work right now?",
        f"What is one idea from {theme_text} you think more people should be discussing?",
    ]


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

    output = generator(
        prompt,
        max_length=80,
        num_return_sequences=1,
        truncation=True,
        pad_token_id=50256,  # GPT-2's eos_token_id, silences a padding warning
    )

    generated_text = output[0]["generated_text"]

    # Drop the prompt itself, keep only what GPT-2 added after it.
    continuation = generated_text[len(prompt):]

    lines = continuation.split("\n")
    suggestions = [_clean_line(line) for line in lines]
    suggestions = [s for s in suggestions if s]  # drop empties from cleanup

    return suggestions[:3]
