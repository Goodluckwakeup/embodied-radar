const $ = id => document.getElementById(id);
const {dayKey, filterAndSort} = window.RadarFilters;
let records = [], limit = 40;
function fmt(value) { const d=new Date(value); return value&&!isNaN(d)?new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',dateStyle:'medium',timeStyle:'short'}).format(d):'未提供'; }
function el(tag,text,cls) { const e=document.createElement(tag);if(text!=null)e.textContent=text;if(cls)e.className=cls;return e; }
function link(text,url) { const a=el('a',text);try{const u=new URL(url);if(!['http:','https:'].includes(u.protocol))return el('span',text);a.href=u.href;a.target='_blank';a.rel='noopener noreferrer';}catch{return el('span',text);}return a; }
function settings() {return {query:$('query').value,topic:$('topic').value,kind:$('kind').value,source:$('source').value,timeField:$('time-field').value,period:$('period').value,from:$('period').value==='custom'?$('from').value:'',to:$('period').value==='custom'?$('to').value:'',sort:$('sort').value,order:$('order').value,onlyChinese:$('only-chinese').checked};}
function render() {
  const o=settings();$('custom-dates').hidden=o.period!=='custom';
  const invalid=o.period==='custom'&&o.from&&o.to&&o.from>o.to;
  const rows=invalid?[]:filterAndSort(records,o);
  $('filter-help').textContent=invalid?'开始日期不能晚于结束日期。':'按'+$('time-field').selectedOptions[0].textContent+'筛选，日期均为北京时间。首次入库的文章可能有相同发现时间；缺失日期的记录在限定日期时不显示。';
  $('filter-help').className=invalid?'error':'small';
  $('count').textContent=rows.length+' / '+records.length+' 条记录';$('list').replaceChildren();
  for(const r of rows.slice(0,limit)){
    const card=el('article'),meta=el('div',null,'meta');for(const tag of r.topics||[])meta.append(el('span',tag,'tag'));
    meta.append(el('span',r.kind+' · '+r.source));const title=el('h3',null,'title');title.append(link(r.title_zh||r.title,r.url));card.append(meta,title);
    if(r.title_zh)card.append(el('p',r.title,'small'));if(r.authors?.length)card.append(el('p',r.authors.join(' · '),'small'));
    if(r.summary_zh)card.append(el('p','中文摘要','summary-label'),el('p',r.summary_zh,'abstract'));
    else{card.append(el('p',r.basis==='搜索片段（待核验）'?'搜索线索，待核验原文':'中文摘要待生成 · 下面为来源原文摘录','small'));const excerpt=r.abstract||'来源未提供摘要，请查看原文。';card.append(el('p',excerpt.slice(0,480)+(excerpt.length>480?'…':''),'abstract'));}
    if(r.abstract&&(r.summary_zh||r.abstract.length>480)){const original=el('details',null,'original');original.append(el('summary','查看来源原文摘录'),el('p',r.abstract,'abstract'));card.append(original);}
    card.append(el('p','依据：'+r.basis+' · 发表：'+fmt(r.published_at)+' · 更新：'+fmt(r.updated_at)+' · 发现：'+fmt(r.first_seen_at),'small'));
    const links=el('div',null,'links');for(const [i,url]of(r.links||[r.url]).entries())links.append(link(i===0?'查看原始来源 ↗':'关联来源 '+(i+1)+' ↗',url));card.append(links);$('list').append(card);
  }
  if(!rows.length)$('list').append(el('p',invalid?'请调整日期范围。':records.length?'没有符合条件的文章。可以点击“清空筛选”，或扩大日期范围。':'还没有采集记录，请在 GitHub Actions 运行每日更新任务。','empty'));
  $('more').hidden=rows.length<=limit;
}
function populate(id,values,label,known=[]){
  const select=$(id);select.replaceChildren();const counts=new Map();for(const value of values)if(value)counts.set(value,(counts.get(value)||0)+1);
  const all=el('option',label+'（'+values.length+'）');all.value='';select.append(all);
  for(const name of [...new Set([...known,...counts.keys()])]){const n=counts.get(name)||0,option=el('option',name+'（'+n+(n?'':'，暂无内容')+'）');option.value=name;option.disabled=n===0;select.append(option);}
}
$('query').addEventListener('input',()=>{limit=40;render();});
for(const id of ['topic','kind','source','time-field','period','from','to','sort','order','only-chinese'])$(id).addEventListener('change',()=>{limit=40;render();});
$('reset').addEventListener('click',()=>{for(const id of ['query','topic','kind','source','period','from','to'])$(id).value='';$('time-field').value='published_at';$('sort').value='updated';$('order').value='desc';$('only-chinese').checked=false;limit=40;render();});
$('more').addEventListener('click',()=>{limit+=40;render();});
fetch('data.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('HTTP '+r.status);return r.json();}).then(data=>{
  records=Array.isArray(data.articles)?data.articles:[];
  populate('kind',records.map(r=>r.kind),'全部类型',['论文','企业','高校','待核验']);populate('source',records.map(r=>r.source),'全部来源');
  $('total').textContent=records.length;$('today').textContent=records.filter(r=>dayKey(r.first_seen_at)===dayKey(Date.now())).length;
  const channels=(data.sources||[]).filter(s=>s.source!=='中文摘要');$('checked').textContent=channels.filter(s=>s.state==='ok').length+'/'+channels.length;
  const n=records.filter(r=>r.summary_zh).length,s=(data.sources||[]).find(s=>s.source==='中文摘要');
  $('summary-coverage').textContent='中文摘要 '+n+' / '+records.length+' 篇。';
  $('summary-help').textContent=n===records.length&&n?'已有摘要会优先展示，原始摘录可展开查看。':'其余摘要需要通过 GitHub Actions 补齐。'+(s?.detail||'')+'。已生成的摘要会缓存。';
  $('updated').textContent='最近尝试：'+fmt(data.last_attempt_at)+' · 采集状态：'+(({ok:'完成',partial:'部分完成／部分功能未启用',error:'失败',not_run:'尚未运行'})[data.state]||data.state)+' · 最近全渠道成功：'+fmt(data.last_complete_at);
  for(const s of data.sources||[])$('sources').append(el('li',s.source+'：'+({ok:'成功',partial:'部分完成',error:'失败',skipped:'未启用'})[s.state]+(s.count!=null?' · '+s.count+' 条':'')+(s.detail?' · '+s.detail:''),s.state));
  $('domains').textContent=data.candidate_domains?.join('、')||'暂无。搜索发现的域名需要核验后再加入固定订阅源。';render();
}).catch(error=>{$('count').textContent='加载失败';$('list').replaceChildren(el('p','数据加载失败（'+error.message+'）。请刷新页面重试。','error'));});
