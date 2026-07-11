from backend.infrastructure.services.translation_service import TranslationService

ts = TranslationService()

trains = [
    "ＪＲ東海道・山陽本線",
    "ＪＲ湖西線",
    "大阪メトロ御堂筋線",
    "阪急京都本線",
    "近鉄奈良線",
    "ＪＲ特急くろしお15号",
    "ＪＲ新快速",
    "OsakaMetro御堂筋線",
    "東京メトロ銀座線"
]

for t in trains:
    print(f"{t} -> {ts.translate_train(t)}")
