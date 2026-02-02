import logging
from typing import Set

logger = logging.getLogger(__name__)


class HeuristicInflector:
    """
    A simple rule-based inflector for Russian names/nouns.
    It is not perfect but covers common cases to improve dictionary matching.
    """

    @staticmethod
    def get_variations(word: str) -> Set[str]:
        """
        Generate potential case variations for a given Russian word (name).
        Returns a set containing the original word and its inflected forms.
        """
        if not word:
            return set()

        word = word.strip()
        variations = {word}

        # Simple heuristic based on endings
        # We assume the input is in Nominative case (Именительный падеж)

        # Case 1: Ends with a consonant (Masculine usually, e.g., Ян, Иван)
        # Excludes 'й' which is treated separately
        # Checks if last char is a Russian consonant
        if word[-1].lower() in "бвгджзклмнпрстфхцчшщ":
            base = word
            variations.update(
                [
                    base + "а",  # Genitive (Яна)
                    base + "у",  # Dative (Яну)
                    base + "ом",  # Instrumental (Яном)
                    base + "е",  # Prepositional (Яне)
                    # Accusative for animate nouns matches Genitive (Яна)
                ]
            )

        # Case 2: Ends with 'й' (Masculine, e.g., Дмитрий, Андрей)
        elif word.endswith("й") or word.endswith("Й"):
            base = word[:-1]
            variations.update(
                [
                    base + "я",  # Genitive (Дмитрия)
                    base + "ю",  # Dative (Дмитрию)
                    base + "ем",  # Instrumental (Дмитрием)
                    base + "е",  # Prepositional (archaic/poetic but sometimes used)
                    base + "и",  # Prepositional standard (Дмитрии)
                ]
            )

        # Case 3: Ends with 'а' (Fem/Masc, e.g., Анна, Никита)
        elif word.endswith("а") or word.endswith("А"):
            base = word[:-1]
            variations.update(
                [
                    base + "ы",  # Genitive (Анны)
                    base + "е",  # Dative, Prepositional (Анне)
                    base + "у",  # Accusative (Анну)
                    base + "ой",  # Instrumental (Анной)
                ]
            )

        # Case 4: Ends with 'я' (Fem/Masc, e.g., Мария, Илья)
        elif word.endswith("я") or word.endswith("Я"):
            base = word[:-1]
            # Special case for names ending in -ия (Мария) -> Gen/Dat/Prep is -ии
            if len(word) > 2 and word[-2].lower() == "и":
                variations.update(
                    [
                        base + "и",  # Genitive, Dative, Prepositional (Марии)
                        base + "ю",  # Accusative (Марию)
                        base + "ей",  # Instrumental (Марией)
                    ]
                )
            else:
                # Standard -я (Илья, Таня)
                variations.update(
                    [
                        base + "и",  # Genitive (Ильи)
                        base + "е",  # Dative, Prepositional (Илье)
                        base + "ю",  # Accusative (Илью)
                        base + "ей",  # Instrumental (Ильей)
                        base + "ёй",  # Instrumental variation
                    ]
                )

        # Case 5: Ends with 'ь' (Can be Masc like Игорь or Fem like Любовь)
        elif word.endswith("ь") or word.endswith("Ь"):
            base = word[:-1]
            # If Masculine (Игорь): Игоря, Игорю, Игорем, Игоре
            # If Feminine (Любовь): Любови, Любовью

            # Let's add masculine forms as they are common for names
            variations.update(
                [
                    base + "я",  # Genitive
                    base + "ю",  # Dative
                    base + "ем",  # Instrumental
                    base + "е",  # Prepositional
                ]
            )
            # Add feminine forms just in case
            variations.update(
                [
                    base + "и",  # Gen/Dat/Prep for Fem
                    word + "ю",  # Instrumental Fem (Любовь -> Любовью)
                ]
            )

        return variations
