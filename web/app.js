'use strict';
const $ = id => document.getElementById(id);
let sites = [], selected = null, loading = false, rerun = false, toastTimer;
const formatNumber = new Intl.NumberFormat('pt-BR', {maximumFractionDigits: 1});
const pct = s => Number(s.total) ? `${formatNumber.format(100 * Number(s.successes) / Number(s.total))}%` : '—';
const node = (tag, cls, value) => { const el = document.createElement(tag); if (cls) el.className = cls; if (value !== undefined) el.textContent = value; return el; };
async function request(path, options = {}) {
  const response = await fetch('/api' + path, {...options, headers: {'Content-Type': 'application/json', ...options.headers}});
  if (!response.ok) { let message = `Erro HTTP ${response.status}`; try { const data = await response.json(); if (typeof data.detail === 'string') message = data.detail; } catch {} throw new Error(message); }
  return response.status === 204 ? null : response.json();
}
function toast(message) { $('toast').textContent = message; $('toast').hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').hidden = true, 4500); }
function badge(online) { const el = node('span', `status ${online === true ? 'up' : online === false ? 'down' : ''}`); el.append(node('i', `dot ${online === true ? 'green' : online === false ? 'red' : ''}`), document.createTextNode(online === true ? 'Online' : online === false ? 'Offline' : 'Pendente')); return el; }
function renderSites() {
  const online = sites.filter(s => s.online === true), offline = sites.filter(s => s.online === false);
  $('total').textContent = sites.length; $('online').textContent = online.length; $('offline').textContent = offline.length;
  $('latency').textContent = online.length ? `${Math.round(online.reduce((a,s) => a+s.latency_ms,0)/online.length)} ms` : '—';
  $('count').textContent = `${sites.length} ${sites.length === 1 ? 'serviço' : 'serviços'}`;
  $('empty').hidden = sites.length > 0;
  const body = $('sites'); body.replaceChildren();
  for (const site of sites) {
    const tr = node('tr', selected === site.id ? 'selected' : ''); tr.dataset.id = site.id; tr.tabIndex = 0;
    tr.setAttribute('aria-label', `Ver histórico de ${site.name}`);
    tr.addEventListener('click', () => { selected = site.id; renderSites(); load(); });
    tr.addEventListener('keydown', e => { if (e.target === tr && ['Enter',' '].includes(e.key)) { e.preventDefault(); tr.click(); } });
    const name = node('td'); name.append(node('div','site-name',site.name),node('span','site-url',site.url));
    const status = node('td'); status.append(badge(site.online));
    const action = node('td'); const del = node('button','delete','×'); del.title = 'Excluir monitor'; del.setAttribute('aria-label', `Excluir ${site.name}`);
    del.addEventListener('click', async e => { e.stopPropagation(); if (!confirm(`Excluir ${site.name} e seu histórico?`)) return; del.disabled = true; try { await request(`/sites/${site.id}`,{method:'DELETE'}); if (selected === site.id) selected = null; toast('Monitor excluído.'); await load(); } catch(err) { toast(err.message); del.disabled = false; } });
    action.append(del); tr.append(name,status,node('td','',pct(site)),node('td','',site.latency_ms == null ? '—' : `${site.latency_ms} ms`),action); body.append(tr);
  }
}
function drawChart(history) {
  const box = $('chart'); box.replaceChildren(); if (!history.length) { box.textContent = 'Aguardando a primeira verificação.'; return; }
  const values = [...history].reverse(); const max = Math.max(1,...values.map(x => x.latency_ms));
  const ns = 'http://www.w3.org/2000/svg', svg = document.createElementNS(ns,'svg'); svg.setAttribute('viewBox','0 0 340 136'); svg.setAttribute('role','img'); svg.setAttribute('aria-label','Gráfico de latência; pontos vermelhos indicam falhas.');
  const add = (tag, attrs, text) => { const el = document.createElementNS(ns,tag); for(const [key,val] of Object.entries(attrs)) el.setAttribute(key,val); if(text !== undefined) el.textContent=text; svg.append(el); };
  for (let i=0;i<=3;i++) { const y=12+i*34; add('line',{x1:36,x2:328,y1:y,y2:y,stroke:'#e0e6ef'}); add('text',{x:30,y:y+3,'text-anchor':'end',fill:'#8490a1','font-size':9},Math.round(max*(1-i/3))); }
  const points=values.map((v,i)=>[values.length===1?182:36+i*292/(values.length-1),114-102*v.latency_ms/max]);
  if(points.length>1) add('polyline',{points:points.map(p=>p.join(',')).join(' '),fill:'none',stroke:'#2459d8','stroke-width':2,'stroke-linejoin':'round'});
  points.forEach(([x,y],i)=>add('circle',{cx:x,cy:y,r:values.length>25?2:3,fill:values[i].online?'#2459d8':'#d34755'}));
  add('text',{x:36,y:130,fill:'#8490a1','font-size':9},'Mais antiga'); add('text',{x:328,y:130,fill:'#8490a1','font-size':9,'text-anchor':'end'},'Mais recente'); box.append(svg);
}
function renderDetail(site,history=[]) {
  $('detail-empty').hidden=!!site; $('detail-content').hidden=!site;
  $('detail-title').textContent=site ? site.name : 'Histórico do serviço'; $('detail-url').textContent=site ? site.url : 'Selecione um monitor'; if(!site)return;
  $('uptime').textContent=pct(site); $('checks').textContent=site.total; drawChart(history); const list=$('history'); list.replaceChildren();
  if(!history.length) list.append(node('p','','O worker ainda não registrou resultados.'));
  for(const item of history.slice(0,10)) { const row=node('div','history-row'); row.append(node('span','',new Date(item.checked_at).toLocaleString('pt-BR',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'})),badge(item.online),node('span','',`${item.status_code ?? '—'} · ${item.latency_ms} ms`)); if(item.error)row.append(node('small','',item.error)); list.append(row); }
}
async function load() {
  if(loading){rerun=true;return;} loading=true;
  try { sites=await request('/sites'); if(!sites.some(s=>s.id===selected)) selected=sites[0]?.id??null; renderSites(); const id=selected; const site=sites.find(s=>s.id===id); const history=site?await request(`/sites/${id}/history`):[]; if(id===selected)renderDetail(site,history); $('connection').className='live ok'; $('connection').replaceChildren(node('i'),document.createTextNode('API conectada')); }
  catch(e){$('connection').className='live error';$('connection').replaceChildren(node('i'),document.createTextNode('Conexão indisponível'));} finally{loading=false;if(rerun){rerun=false;void load();}}
}
$('new').addEventListener('click',()=>{$('add-form').reset();$('form-error').textContent='';$('modal').showModal();$('name').focus();});
for(const id of ['close','cancel']) $(id).addEventListener('click',()=>$('modal').close());
$('add-form').addEventListener('submit',async e=>{e.preventDefault();$('submit').disabled=true;$('form-error').textContent='';try{const site=await request('/sites',{method:'POST',body:JSON.stringify({name:$('name').value,url:$('url').value})});selected=site.id;$('modal').close();toast('Monitor cadastrado. Aguardando sondagem.');await load();}catch(err){$('form-error').textContent=err.message;}finally{$('submit').disabled=false;}});
$('demo').addEventListener('click',async()=>{$('demo').disabled=true;try{const result=await request('/demo',{method:'POST'});toast(result.created.length?'Monitores locais adicionados.':'Demonstração já cadastrada.');await load();}catch(err){toast(err.message);}finally{$('demo').disabled=false;}});
void load();setInterval(load,5000);
