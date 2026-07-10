import logging

logger = logging.getLogger("autotrip")

class TranslationService:
    """
    Infrastructure service responsible for handling station name translations.
    Prioritizes official JR English names. Does NOT use general web translators.
    """
    def __init__(self):
        # In a real app, this might query an internal SQLite DB or a local JSON dictionary.
        self._official_jr_map = {
            "大阪": "Osaka",
            "京都": "Kyoto",
            "新大阪": "Shin-Osaka"
        }

    def get_english_name(self, jp_name: str) -> str:
        """Returns the official English name if available, else falls back to original."""
        if jp_name in self._official_jr_map:
            return self._official_jr_map[jp_name]
        logger.warning(f"Official translation missing for station: {jp_name}")
        return jp_name
