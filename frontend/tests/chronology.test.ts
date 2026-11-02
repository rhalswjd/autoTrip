import { test } from 'node:test';
import assert from 'node:assert/strict';
import { compatibleDeparture, selectExactDeparture } from '../src/utils/chronology.ts';
import type { DepartureInfo } from '../src/api/types.ts';
const exact=(day:string,time:string,arrival:string)=>({id:day+time,operating_date:day,time,arrival_time:arrival}) as DepartureInfo;
for(const [arrival,day,time,expected] of [
 ['2026-11-01T07:57:00+09:00','2026-11-01','08:10',true],
 ['2026-11-01T07:57:00+09:00','2026-11-01','00:03',false],
 ['2026-11-01T23:55:00+09:00','2026-11-02','00:10',true],
 ['2026-11-01T23:55:00+09:00','2026-11-01','23:40',false],
] as const) test(`${arrival} → ${day} ${time}`,()=>assert.equal(compatibleDeparture(exact(day,time,'00:30'),arrival,0),expected));
test('changing earlier ride clears every dependent exact selection',()=>{
 const changed=selectExactDeparture({0:exact('2026-11-01','06:00','07:00'),1:exact('2026-11-01','08:20','09:00'),2:exact('2026-11-01','10:00','11:00')},0,exact('2026-11-01','08:00','09:00'));
 assert.deepEqual(Object.keys(changed),['0']);
});
