import sys
sys.path.append('backend')
from infrastructure.services.translation_service import TranslationService

ts = TranslationService()
print("1. Osaka Bus:", ts.get_english_name("大阪駅前（高速・連絡バス）"))
print("2. Nagoya Bus:", ts.get_english_name("名古屋駅（高速・連絡バス）"))
print("3. Airport Bus:", ts.get_english_name("空港リムジンバス"))
print("4. Shin-Osaka:", ts.get_english_name("新大阪駅"))
