"""
core/verification_codes.py – Three-word code generator for purchase verification.

Generates unique, memorable three-word codes for purchase identification.
Uses a curated word list to create codes like 'apple-tree-button'.
"""
import random
from typing import List, Set


ADJECTIVES: List[str] = [
    'happy', 'bright', 'quick', 'calm', 'bold', 'wise', 'fair', 'kind',
    'swift', 'smart', 'brave', 'clear', 'cool', 'warm', 'soft', 'hard',
    'green', 'blue', 'red', 'gold', 'silver', 'purple', 'orange', 'yellow',
    'great', 'grand', 'noble', 'proud', 'sweet', 'fresh', 'pure', 'clean',
    'sharp', 'bright', 'dark', 'light', 'heavy', 'quiet', 'loud', 'smooth',
    'rough', 'gentle', 'wild', 'tame', 'free', 'safe', 'strong', 'mighty'
]

NOUNS: List[str] = [
    'apple', 'tree', 'house', 'book', 'chair', 'table', 'river', 'mountain',
    'ocean', 'forest', 'garden', 'flower', 'bridge', 'castle', 'tower', 'gate',
    'path', 'stone', 'cloud', 'star', 'moon', 'sun', 'wind', 'rain',
    'snow', 'fire', 'water', 'earth', 'sky', 'bird', 'fish', 'horse',
    'lion', 'tiger', 'eagle', 'wolf', 'bear', 'deer', 'rabbit', 'fox',
    'piano', 'guitar', 'drum', 'flute', 'violin', 'harp', 'bell', 'crown'
]

OBJECTS: List[str] = [
    'button', 'window', 'door', 'key', 'lock', 'wheel', 'lamp', 'clock',
    'mirror', 'brush', 'pencil', 'paper', 'coin', 'ring', 'box', 'cup',
    'plate', 'bowl', 'knife', 'fork', 'spoon', 'bottle', 'glass', 'jar',
    'basket', 'bucket', 'barrel', 'chest', 'bag', 'rope', 'chain', 'hook',
    'nail', 'hammer', 'saw', 'axe', 'shield', 'sword', 'arrow', 'bow',
    'flag', 'banner', 'scroll', 'map', 'compass', 'anchor', 'sail', 'mast'
]


def generate_code() -> str:
    """Generate a random three-word code (adjective-noun-object)."""
    return f"{random.choice(ADJECTIVES)}-{random.choice(NOUNS)}-{random.choice(OBJECTS)}".lower()


def generate_unique_code(existing_codes: Set[str], max_attempts: int = 1000) -> str:
    """
    Generate a code that is not already in *existing_codes*.

    Raises RuntimeError after max_attempts if the space is exhausted.
    """
    for _ in range(max_attempts):
        code = generate_code()
        if code not in existing_codes:
            return code
    raise RuntimeError(
        f"Unable to generate a unique code after {max_attempts} attempts. "
        "Consider expanding the word lists."
    )


def validate_code_format(code: str) -> bool:
    """Return True if *code* matches the adjective-noun-object format."""
    if not code:
        return False
    parts = code.lower().strip().split('-')
    return len(parts) == 3 and all(p and p.isalpha() for p in parts)


def normalize_code(code: str) -> str:
    """Normalise a code to lowercase, stripped form."""
    return code.lower().strip()


def get_code_statistics() -> dict:
    """Return total possible combinations and current usage statistics."""
    from iftf_duoverkoop.src.core.models import Purchase  # avoid circular import at module level

    total = len(ADJECTIVES) * len(NOUNS) * len(OBJECTS)
    used = Purchase.objects.exclude(verification_code__isnull=True).count()
    return {
        'total_combinations': total,
        'used_codes': used,
        'remaining': total - used,
        'usage_percentage': (used / total * 100) if total else 0,
    }

