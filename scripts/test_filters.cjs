const {test}=require('node:test');
const assert=require('node:assert/strict');
const {dayKey,filterAndSort}=require('../site/filters.js');
const clock=Date.parse('2026-11-08T16:30:00Z'); // 北京时间 11 月 9 日
const rows=[
 {id:'a',title:'A',kind:'论文',source:'arXiv',topics:['VLA'],published_at:'2026-11-02T16:01:00Z',updated_at:'2026-11-08T00:00:00Z',first_seen_at:'2026-11-08',summary_zh:'中文'},
 {id:'b',title:'B',kind:'企业',source:'lab',topics:['WAM'],published_at:'2026-11-02T15:59:00Z',updated_at:'2026-11-08T01:00:00Z',first_seen_at:'2026-11-08'},
 {id:'c',title:'C',kind:'高校',source:'lab',topics:['VLA'],published_at:'2026-11-08T16:00:00Z',updated_at:'2026-11-08T02:00:00Z',first_seen_at:'2026-11-08'},
 {id:'d',title:'D',kind:'论文',source:'arXiv',topics:['VTLA'],published_at:null,updated_at:null,first_seen_at:'2026-11-08'}
];
test('Beijing date boundary and seven inclusive calendar days',()=>{
 assert.equal(dayKey(clock),'2026-11-09');
 assert.deepEqual(filterAndSort(rows,{period:'7',sort:'published'},clock).map(r=>r.id),['c','a']);
 assert.deepEqual(filterAndSort(rows,{period:'1'},clock).map(r=>r.id),['c']);
});
test('time basis is independent from sort and discovery timestamps',()=>{
 assert.equal(filterAndSort(rows,{period:'1',timeField:'first_seen_at'},clock).length,0);
 assert.deepEqual(filterAndSort(rows,{from:'2026-11-03',to:'2026-11-03'},clock).map(r=>r.id),['a']);
});
test('ascending and descending put unknown dates last',()=>{
 assert.deepEqual(filterAndSort(rows,{sort:'updated',order:'asc'}).map(r=>r.id),['a','b','c','d']);
 assert.deepEqual(filterAndSort(rows,{sort:'updated',order:'desc'}).map(r=>r.id),['c','b','a','d']);
});
test('kind, source, topic and Chinese filters combine without mutating input',()=>{
 assert.deepEqual(filterAndSort(rows,{kind:'论文',source:'arXiv',topic:'VLA',onlyChinese:true}).map(r=>r.id),['a']);
 assert.deepEqual(rows.map(r=>r.id),['a','b','c','d']);
});
