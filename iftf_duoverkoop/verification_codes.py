"""
Three-word code generator for purchase verification.

Generates unique, memorable three-word codes for purchase identification.
Uses a curated word list to create codes like 'apple-tree-button'.
"""
import random
from typing import List, Set


# Curated word lists for generating memorable codes
# Each list contains simple, common words that are easy to spell and remember
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
    """
    Generate a unique three-word code.

    Format: adjective-noun-object (e.g., 'happy-tree-button')

    Returns:
        A hyphen-separated three-word code
    """
    adjective = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    obj = random.choice(OBJECTS)

    return f"{adjective}-{noun}-{obj}".lower()


def generate_unique_code(existing_codes: Set[str], max_attempts: int = 1000) -> str:
    """
    Generate a unique three-word code that doesn't exist in the database.

    Args:
        existing_codes: Set of already used codes
        max_attempts: Maximum number of generation attempts

    Returns:
        A unique three-word code

    Raises:
        RuntimeError: If unable to generate unique code after max_attempts
    """
    for attempt in range(max_attempts):
        code = generate_code()
        if code not in existing_codes:
            return code

    # If we exhausted all attempts, raise an error
    raise RuntimeError(
        f"Unable to generate unique code after {max_attempts} attempts. "
        "Consider expanding the word lists."
    )


def validate_code_format(code: str) -> bool:
    """
    Validate that a code follows the three-word format.

    Args:
        code: The code to validate

    Returns:
        True if code is valid format, False otherwise
    """
    if not code:
        return False

    parts = code.lower().strip().split('-')

    # Must have exactly 3 parts
    if len(parts) != 3:
        return False

    # Each part must be non-empty and alphanumeric
    for part in parts:
        if not part or not part.isalpha():
            return False

    return True


def normalize_code(code: str) -> str:
    """
    Normalize a code to standard format (lowercase, trimmed).

    Args:
        code: The code to normalize

    Returns:
        Normalized code string
    """
    return code.lower().strip()


def get_code_statistics() -> dict:
    """
    Get statistics about the code generation space.

    Returns:
        Dictionary with total possible combinations and current usage
    """
    total_combinations = len(ADJECTIVES) * len(NOUNS) * len(OBJECTS)

    # Import here to avoid circular dependency
    from iftf_duoverkoop.models import Purchase

    used_codes = Purchase.objects.exclude(verification_code__isnull=True).count()

    return {
        'total_combinations': total_combinations,
        'used_codes': used_codes,
        'remaining': total_combinations - used_codes,
        'usage_percentage': (used_codes / total_combinations * 100) if total_combinations > 0 else 0
    }

