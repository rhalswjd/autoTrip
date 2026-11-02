"""Conservative original-line/section capabilities, not a JR-brand heuristic.

Tokaido ownership: https://railway.jr-central.co.jp/route-map/_pdf/numbering.pdf
11501/11502/11503 are the imported station catalogue's Tokaido section IDs.
Unregistered/ambiguous corridors use Yahoo; this is not a complete operator atlas.
"""
import unicodedata


def timetable_operator(railway: str, stations=None) -> str:
    name = unicodedata.normalize('NFKC', railway)
    west_lines = ('琵琶湖線', '京都線', '神戸線', '大阪環状線', '小浜線', '山陰本線',
                  '福知山線', '大和路線', '奈良線', '和歌山線', '万葉まほろば線',
                  '阪和線', '湖西線', '北陸本線', '特急サンダーバード', '特急はるか', '大和路快速')
    west_services = ('特急こうのとり', '特急くろしお', '特急スーパーおき', '特急スーパーまつかぜ')
    if any(name.startswith('JR' + line) for line in west_lines + west_services):
        return 'jr_west'
    if stations:
        origin, target = stations
        if '東海道本線' in name and origin.id[:5] in {'11501', '11502', '11503'}:
            return 'jr_central'
        if '新幹線' in name:
            regions = {origin.prefecture, target.prefecture}
            if regions <= {'16', '17', '18'} or regions <= {'27', '28', '33', '34', '35', '40'}:
                return 'jr_west'
            if '23' in regions or '22' in regions:
                return 'jr_central'
    return 'unknown'
