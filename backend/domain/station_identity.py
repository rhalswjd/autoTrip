"""Geographic name equivalence, never removal of a meaningful station qualifier."""
import re
import unicodedata

_JA = '北海道 青森県 岩手県 宮城県 秋田県 山形県 福島県 茨城県 栃木県 群馬県 埼玉県 千葉県 東京都 神奈川県 新潟県 富山県 石川県 福井県 山梨県 長野県 岐阜県 静岡県 愛知県 三重県 滋賀県 京都府 大阪府 兵庫県 奈良県 和歌山県 鳥取県 島根県 岡山県 広島県 山口県 徳島県 香川県 愛媛県 高知県 福岡県 佐賀県 長崎県 熊本県 大分県 宮崎県 鹿児島県 沖縄県'.split()
_EN = 'Hokkaido Aomori Iwate Miyagi Akita Yamagata Fukushima Ibaraki Tochigi Gunma Saitama Chiba Tokyo Kanagawa Niigata Toyama Ishikawa Fukui Yamanashi Nagano Gifu Shizuoka Aichi Mie Shiga Kyoto Osaka Hyogo Nara Wakayama Tottori Shimane Okayama Hiroshima Yamaguchi Tokushima Kagawa Ehime Kochi Fukuoka Saga Nagasaki Kumamoto Oita Miyazaki Kagoshima Okinawa'.split()


def prefecture_full(value: str) -> str:
    value = str(value or '')
    if value.isdigit() and 1 <= int(value) <= 47:
        return _JA[int(value) - 1]
    return next((name for name in _JA if value == name or value == name[:-1]), '')


def prefecture_label(value: str) -> str:
    full = prefecture_full(value)
    return _EN[_JA.index(full)] if full else value


def qualified_station_name(value: str) -> str:
    value = unicodedata.normalize('NFKC', value or '').strip()
    def region(match):
        full = prefecture_full(match[1])
        return '(' + (full or match[1]) + ')'
    return re.sub(r'\(([^()]+)\)$', region, value)


def station_base_name(value: str) -> str:
    value = qualified_station_name(value)
    match = re.search(r'\(([^()]+)\)$', value)
    return value[:match.start()] if match and prefecture_full(match[1]) else value


def station_comparison_name(value: str) -> str:
    """Comparison only: two spelling variants, never kana deletion or fuzzy matching.

    NFKC handles width/punctuation; it does not fold small ヶ/ヵ. Geographic
    qualifiers remain part of the result. Stored/display/provider names are untouched.
    """
    return qualified_station_name(value).translate(str.maketrans({'ヶ': 'ケ', 'ヵ': 'カ'}))


def station_orthography_matches(expected: str, actual: str) -> bool:
    """Exact spelling equivalence with optional geographic disambiguation.

    Two explicit regions must agree. Operator/entity qualifiers are never removed.
    """
    expected, actual = station_comparison_name(expected), station_comparison_name(actual)
    if expected == actual:
        return True
    left, right = station_base_name(expected), station_base_name(actual)
    if left != expected and right != actual:
        return False
    return left == right


def station_name_prefecture(value: str) -> str:
    match = re.search(r'\(([^()]+)\)$', qualified_station_name(value))
    return prefecture_full(match[1]) if match else ''
