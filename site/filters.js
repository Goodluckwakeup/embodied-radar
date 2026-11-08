(function(root) {
  'use strict';
  const formatter = new Intl.DateTimeFormat('en-US', {timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'});
  function timestamp(value) { const n=value?Date.parse(value):NaN; return Number.isFinite(n)?n:null; }
  function dayKey(value) {
    const n=typeof value==='number'?value:timestamp(value);
    if(n==null||!Number.isFinite(n)) return '';
    const p=Object.fromEntries(formatter.formatToParts(new Date(n)).map(x=>[x.type,x.value]));
    return `${p.year}-${p.month}-${p.day}`;
  }
  function addDays(day,n) { const d=new Date(day+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+n);return d.toISOString().slice(0,10); }
  function filterAndSort(records,o={},clock=Date.now()) {
    const field=['published_at','updated_at','first_seen_at'].includes(o.timeField)?o.timeField:'published_at';
    const today=dayKey(clock),period=Number(o.period)||0;
    const from=period?addDays(today,1-period):(o.from||''),to=period?today:(o.to||'');
    const query=(o.query||'').trim().toLowerCase();
    const rows=records.filter(r=>{
      if(o.topic&&!(r.topics||[]).includes(o.topic))return false;
      if(o.kind&&r.kind!==o.kind)return false;
      if(o.source&&r.source!==o.source)return false;
      if(o.onlyChinese&&!r.summary_zh)return false;
      if(query&&![r.title,r.title_zh,r.abstract,r.summary_zh,r.source,...(r.authors||[])].join(' ').toLowerCase().includes(query))return false;
      const day=dayKey(r[field]);
      return !(from||to)||!!day&&(!from||day>=from)&&(!to||day<=to);
    });
    const sortField={published:'published_at',updated:'updated_at',discovery:'first_seen_at'}[o.sort]||'updated_at';
    const direction=o.order==='asc'?1:-1;
    rows.sort((a,b)=>{
      const x=timestamp(a[sortField]),y=timestamp(b[sortField]);
      if(x==null||y==null)return x==null&&y==null?String(a.id).localeCompare(String(b.id)):x==null?1:-1;
      return direction*(x-y)||(timestamp(b.updated_at)||0)-(timestamp(a.updated_at)||0)||
        (timestamp(b.published_at)||0)-(timestamp(a.published_at)||0)||String(a.title).localeCompare(String(b.title))||String(a.id).localeCompare(String(b.id));
    });
    return rows;
  }
  const api={timestamp,dayKey,filterAndSort};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.RadarFilters=api;
})(typeof window!=='undefined'?window:globalThis);
