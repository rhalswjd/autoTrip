"""Small public-format station/train HTML fixtures with synthetic source IDs."""

STATION_PAGE = '''<div class="route-name01">新大阪駅</div>
<div class="select-date"><span>2026年10月31日(土)</span></div>
<div class="minute-item"><a href="/train-timetable/100?date=20261031">
<div class="departure-time">06:34</div><div class="train-info">
<div class="train-name"><span></span><span>特急サンダーバード1号（全車指定席）</span></div>
<div class="destination">敦賀行</div><div class="platform-no">のりば[4]</div>
</div></a></div>'''

TRAIN_PAGE = '''<table class="train-details-tbl"><tbody class="train-details">
<tr><th>列車番号</th><td>4001M</td></tr><tr><th>列車名</th><td>サンダーバード1号</td></tr>
</tbody><tbody class="time-details">
<tr><td>新大阪</td><td><div>06:33<span>着</span></div><div>06:34<span>発</span></div></td><td>4</td></tr>
<tr><td>途中</td><td>レ</td><td></td></tr>
<tr><td>敦賀</td><td><div>07:54<span>着</span></div></td><td>31</td></tr>
</tbody></table>'''
