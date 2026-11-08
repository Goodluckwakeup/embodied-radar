const $ = id => document.getElementById(id);
let records = [], limit = 40;
const zhDay = value => new Intl.DateTimeFormat('en-CA', {timeZone:'Asia/Shanghai', year:'numeric', month:'2-digit', day:'2-digit'}).format(new Date(value));
function fmt(value) { const d = new Date(value); return value && !isNaN(d) ? new Intl.DateTimeFormat('zh-CN',{timeZone:'Asia/Shanghai',dateStyle:'medium',timeStyle:'short'}).format(d) : '未提供'; }
function el(tag, text, cls) { const e = document.createElement(tag); if(text != null) e.textContent = text; if(cls) e.className = cls; return e; }
function link(text, url) { const a = el('a', text); try { const u = new URL(url); if(!['http:','https:'].includes(u.protocol)) return el('span',text); a.href=u.href; a.target='_blank'; a.rel='noopener noreferrer'; } catch {return el('span',text);} return a; }
function render() {
  const query=$('query').value.toLowerCase(), topic=$('topic').value, kind=$('kind').value, period=Number($('period').value), sort=$('sort').value;
  const today=zhDay(Date.now());
  const rows=records.filter(r => (!topic||r.topics.includes(topic)) && (!kind||r.kind===kind) &&
    (!query||[r.title,r.abstract,r.summary_zh,r.source,...r.authors].join(' ').toLowerCase().includes(query)) &&
    (!period||(period===1 ? zhDay(r.first_seen_at)===today : Date.now()-new Date(r.first_seen_at)<=period*86400000)));
  const field={discovery:'first_seen_at',published:'published_at',updated:'updated_at'}[sort];
  rows.sort((a,b)=>(Date.parse(b[field])||0)-(Date.parse(a[field])||0));
  $('count').textContent=`${rows.length} 条记录`;
  $('list').replaceChildren();
  for(const r of rows.slice(0,limit)) {
    const card=el('article'), meta=el('div',null,'meta');
    for(const tag of r.topics) meta.append(el('span',tag,'tag'));
    meta.append(el('span',`${r.kind} · ${r.source}`));
    const title=el('h3',null,'title'); title.append(link(r.title,r.url));
    card.append(meta,title);
    if(r.authors.length) card.append(el('p',r.authors.join(' · '),'small'));
    card.append(el('p',r.summary_zh||r.abstract||'来源未提供摘要，请查看原文。','abstract'));
    card.append(el('p',`${r.summary_zh?'AI 中文摘要 · ':''}依据：${r.basis}`,'small'));
    card.append(el('p',`发表：${fmt(r.published_at)}　更新：${fmt(r.updated_at)}　首次发现：${fmt(r.first_seen_at)}`,'small'));
    const links=el('div',null,'links');
    for(const [i,url] of (r.links||[r.url]).entries()) links.append(link(i===0?'查看原始来源 ↗':`关联来源 ${i+1} ↗`,url));
    card.append(links); $('list').append(card);
  }
  if(!rows.length) $('list').append(el('p',records.length?'没有符合筛选条件的记录。':'还没有采集记录。请先在 GitHub Actions 手动运行每日更新任务；下方状态会显示各个来源的运行结果。','empty'));
  $('more').hidden=rows.length<=limit;
}
for(const id of ['query','topic','kind','period','sort']) $(id).addEventListener('input',()=>{limit=40;render();});
$('more').addEventListener('click',()=>{limit+=40;render();});
fetch('data.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error(`HTTP ${r.status}`);return r.json();}).then(data=>{
  records=data.articles;
  $('total').textContent=records.length;
  $('today').textContent=records.filter(r=>zhDay(r.first_seen_at)===zhDay(Date.now())).length;
  const channels=data.sources.filter(s=>s.source!=='中文摘要');
  $('checked').textContent=`${channels.filter(s=>s.state==='ok').length}/${channels.length}`;
  $('updated').textContent=`最近尝试：${fmt(data.last_attempt_at)} · 采集状态：${({ok:'完成',partial:'部分完成／部分功能未启用',error:'失败',not_run:'尚未运行'})[data.state]||data.state} · 最近全渠道成功：${fmt(data.last_complete_at)}`;
  for(const s of data.sources) $('sources').append(el('li',`${s.source}：${({ok:'成功',partial:'部分完成',error:'失败',skipped:'未启用'})[s.state]}${s.count!=null?' · '+s.count+' 条':''}${s.detail?' · '+s.detail:''}`,s.state));
  $('domains').textContent=data.candidate_domains?.join('、')||'暂无。搜索发现的域名需要人工核验后再加入固定订阅源。';
  render();
}).catch(error=>{$('count').textContent='加载失败';$('list').replaceChildren(el('p',`数据加载失败（${error.message}）。请通过网站地址访问，或使用教程中的本地 HTTP 服务。`,'error'));});
