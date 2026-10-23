(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory();else root.RadarCore=factory();})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const KEY='funding-radar-private-v2',LEGACY='funding-radar-records';
const PERSONAL=['','interested','applied','skipped'];
const FIELDS=['name','category','project','submittedDate','expectedResultDate','amount','currency','confirmedAmount','progress','url','contact','notes','nextAction','preparationDate','invitationDate','budgetDate','portfolioDate','submissionTarget','costKey','residencyStart','residencyEnd','cofunding','cofundingEvidence'];
const CHECKS=['臺灣國籍','德國居留／柏林工作場域','個人藝術家','須非營利組織','戶籍／居住證明','海外執行','合作機構／邀請函','年齡／學歷／年資','語言文件'];
const RESULTS=['等待公告','需要補件','通過','未通過','撤回'];
const uid=()=>globalThis.crypto?.randomUUID?.()||Date.now().toString(36)+Math.random().toString(36).slice(2);
const empty=()=>({format:'funding-radar-private',version:2,applications:{},calendar:[],budgets:[],migrated:false});
const text=(v,max=10000)=>typeof v==='string'?v.slice(0,max):v==null?'':String(v).slice(0,max);
const safeId=id=>typeof id==='string'&&id.length>0&&id.length<=200&&!['__proto__','constructor','prototype'].includes(id);
const clone=v=>JSON.parse(JSON.stringify(v));
const dateOK=v=>typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&!Number.isNaN(Date.parse(v+'T00:00:00Z'))&&new Date(v+'T00:00:00Z').toISOString().slice(0,10)===v;
function normalize(raw){
 if(!raw||!safeId(raw.id))throw Error('紀錄缺少有效 ID');
 const fields=Object.fromEntries(FIELDS.map(k=>[k,text(raw.fields?.[k]??(k==='name'?raw.name:''))]));
 const a={id:raw.id,personal:PERSONAL.includes(raw.personal)?raw.personal:'',submitted:raw.submitted===true||raw.personal==='applied',result:RESULTS.includes(raw.result)?raw.result:'等待公告',manual:raw.manual===true,fields,documents:[],tasks:[],eligibility:{},history:[],snapshot:{}};
 if(['通過','未通過','需要補件','撤回'].includes(a.result))a.submitted=true;
 if(['通過','未通過','需要補件'].includes(a.result)&&a.personal!=='skipped')a.personal='applied';
 for(const key of ['documents','tasks'])for(const item of Array.isArray(raw[key])?raw[key].slice(0,200):[]){if(item&&text(item.title))a[key].push({id:safeId(item.id)?item.id:uid(),title:text(item.title,500),done:item.done===true,due:dateOK(item.due)?item.due:'',notes:text(item.notes),url:text(item.url,2000)});}
 for(const k of CHECKS){const x=raw.eligibility?.[k];if(x)a.eligibility[k]={status:['符合','可能符合','不符合','待確認'].includes(x.status)?x.status:'待確認',basis:text(x.basis),url:text(x.url,2000)};}
 for(const h of Array.isArray(raw.history)?raw.history.slice(-200):[])if(h&&h.at)a.history.push({at:text(h.at),from:text(h.from),to:text(h.to),event:text(h.event)});
 const publicKeys=['id','name','organizer','type','url','deadline','deadline_timezone','deadline_precision','application_start','location','country','city','status','verification_status','verified_at','source_id','eligibility','cash_support','rules_url','residency_start','residency_end','support','relevance_tags','review_reasons','cofunding'];
 for(const k of publicKeys)if(raw.snapshot?.[k]!=null)a.snapshot[k]=clone(raw.snapshot[k]);
 if(raw.legacyRecord)a.legacyRecord=clone(raw.legacyRecord);return a;
}
function migrateLegacy(rows){return (Array.isArray(rows)?rows:[]).filter(r=>r&&safeId(r.id)).map(r=>{
 const applied=['已送件','等待結果','獲選','未獲選'].includes(r.status);
 const a=normalize({id:r.id,manual:true,personal:applied?'applied':r.status==='不申請'?'skipped':'interested',submitted:applied,result:r.status==='獲選'?'通過':r.status==='未獲選'?'未通過':'等待公告',fields:{name:r.name,category:r.category,project:r.project,progress:r.status,url:r.url,notes:r.notes}});
 if(r.deadline)a.snapshot={id:r.id,name:r.name,organizer:r.org||'',deadline:r.deadline,deadline_precision:'date',url:r.url,type:'grant'};
 a.legacyRecord=clone(r);return a;
});}
function read(storage){const state=empty();let raw=storage.getItem(KEY);if(raw){const p=JSON.parse(raw);if(p.version!==2||p.format!=='funding-radar-private')throw Error('私人資料格式不符，已停止寫入以保留原資料');for(const a of Object.values(p.applications||{})){const n=normalize(a);state.applications[n.id]=n;if(a.legacyRecord)state.applications[n.id].legacyRecord=a.legacyRecord;}state.calendar=normalizeCalendar(p.calendar);state.budgets=normalizeBudgets(p.budgets);state.migrated=p.migrated===true;}
 if(!state.migrated){const legacy=JSON.parse(storage.getItem(LEGACY)||'[]');for(const a of migrateLegacy(legacy))if(!state.applications[a.id])state.applications[a.id]=a;state.migrated=true;}return state;}
function write(storage,state){storage.setItem(KEY,JSON.stringify(state));}
function normalizeCalendar(rows){return (Array.isArray(rows)?rows:[]).filter(x=>x&&dateOK(x.start)&&dateOK(x.end)&&x.start<=x.end).slice(0,200).map(x=>({id:safeId(x.id)?x.id:uid(),name:text(x.name,200),start:x.start,end:x.end}));}
function normalizeBudgets(rows){return (Array.isArray(rows)?rows:[]).filter(x=>x&&Number.isFinite(Number(x.target))&&Number(x.target)>=0).slice(0,100).map(x=>({id:safeId(x.id)?x.id:uid(),project:text(x.project,200),currency:text(x.currency,12),target:Number(x.target)}));}
function select(state,id,target,snapshot={},confirmed=false,now=new Date().toISOString()){
 if(!safeId(id)||!PERSONAL.includes(target))throw Error('無效狀態');
 const old=state.applications[id]||normalize({id,snapshot}),next=old.personal===target?'':target;
 if(old.personal==='applied'&&next!=='applied'&&!confirmed)return {confirmation:true,message:'此項已有送件紀錄。確定變更個人狀態？送件歷史與審查結果會保留。'};
 if(['通過','未通過'].includes(old.result)&&next==='interested')return {blocked:true,message:'已公布審查結果，不能改回待申請。可保留或略過，送件歷史不變。'};
 const a=clone(old);a.personal=next;if(next==='applied')a.submitted=true;a.snapshot={...a.snapshot,...clone(snapshot)};if(!a.fields.name)a.fields.name=snapshot.name||'';
 a.history.push({at:now,from:old.personal,to:next,event:'personal_status'});state.applications[id]=a;return {application:a};
}
function today(zone='Europe/Berlin',now=Date.now()){try{return new Intl.DateTimeFormat('sv-SE',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(now));}catch{return new Date(now).toISOString().slice(0,10);}}
function days(date,zone='Europe/Berlin',now=Date.now()){if(!dateOK((date||'').slice(0,10)))return null;return Math.ceil((Date.parse(date.slice(0,10)+'T00:00:00Z')-Date.parse(today(zone,now)+'T00:00:00Z'))/86400000);}
function hasSubstantiveSupport(s={}){s=s&&typeof s==='object'?s:{};const unresolved=/待|未確認|unknown|不提供|沒有|自費|無(?:生活|津貼|藝術家費|製作|交通)|not provided|no (?:stipend|artist fee|production)|not available/i;const cash=['stipend','artist_fee','production','travel'].some(k=>![undefined,null,false,0,'','unknown','待確認','無'].includes(s[k])&&!unresolved.test(String(s[k])));const kind=['accommodation','studio'].some(k=>s[k]===true||(/免費|kostenlos|\bfree\b/i.test(s[k]||'')&&!unresolved.test(String(s[k]))&&!/非免費|不免費|not free|nicht kostenlos/i.test(String(s[k]))));return cash||kind;}
function publicState(x,now=Date.now()){
 const day=today(x.deadline_timezone||'UTC',now),end=x.deadline;
 if(x.status==='cancelled')return 'cancelled';
 if(x.status==='closed'||(end&&(x.deadline_precision==='date'?day>end:Number.isFinite(Date.parse(end))&&Date.parse(end)<=now)))return 'closed';
 if(x.application_start&&day<x.application_start)return 'upcoming';
 const verified=Date.parse(x.verified_at),fresh=Number.isFinite(verified)&&verified<=now&&now-verified<=7*86400000;
 const validEnd=x.deadline_precision==='date'?dateOK(end)&&day<end:/T.*(?:Z|[+-]\d{2}:\d{2})$/.test(end||'')&&Date.parse(end)>now;
 const cash=x.type!=='residency'||hasSubstantiveSupport(x.support);
 if(x.status==='open'&&x.verification_status==='verified'&&x.official_source===true&&fresh&&validEnd&&dateOK(x.application_start)&&day>=x.application_start&&x.evidence&&cash)return 'open';
 return 'needs_review';
}
function fit(x){const t=[x.name,x.eligibility,...(x.relevance_tags||[])].join(' ').toLowerCase(),groups={Research:/研究|調查|城市|建築|research|urban|architec/,Production:/創作|製作|雕塑|服裝|跨域|多元藝術|production|sculpt|textile|interdisciplin/,Exhibition:/展覽|策展|視覺藝術|exhibit|curat|visual|bildend/,Publication:/出版|藝評|書寫|publish|publication|writing/,Workshop:/工作坊|共融|參與|workshop|participat|soziokultur/,Travel:/國際交流|藝遊|駐村|出國|residen|travel|exchange/};const matched=Object.keys(groups).filter(k=>groups[k].test(t));return {level:matched.length>=2?'高':matched.length===1?'中':'待確認',matched,explanation:matched.length?'官方主題文字涉及 '+matched.join('、')+'，可對應 IMPOSED 的相關工作。這是主題適配推論；國籍、居留、海外執行及邀請文件仍須按官方辦法核對。':'目前官方文字不足以判斷與 IMPOSED 的關係；主題與個人資格皆待確認。'};}
function filter(rows,state,f={},now=Date.now()){
 return rows.filter(x=>{const p=state.applications[x.id]?.personal||'',s=publicState(x,now),relevance=fit(x),blob=[x.name,x.organizer,x.location,x.country,x.city,x.eligibility,...(x.relevance_tags||[])].join(' ').toLowerCase();
 if(f.personal&&f.personal!=='all'&&p!==f.personal)return false;if((!f.personal||f.personal==='all')&&p==='skipped')return false;
 if(f.status==='active'||!f.status){if(['closed','cancelled'].includes(s))return false;}else if(f.status!=='all'&&s!==f.status)return false;
 if(f.q&&!blob.includes(f.q.toLowerCase()))return false;
 if(f.country&&!([x.country,x.location,x.source_id==='ncaf'?'臺灣':''].join(' ').toLowerCase().includes(f.country.toLowerCase())))return false;
 if(f.city&&!([x.city,x.location].join(' ').toLowerCase().includes(f.city.toLowerCase())))return false;
 if(f.deadline&&(!x.deadline||x.deadline.slice(0,10)>f.deadline))return false;
 if(f.amount&&(!Number.isFinite(x.funding_amount)||x.funding_amount<Number(f.amount)))return false;
 if(f.currency&&x.currency!==f.currency)return false;
 if(f.verification&&x.verification_status!==f.verification)return false;
 if(f.fit&&relevance.level!==f.fit)return false;
 if(f.eligibility&&!(x.eligibility||'').toLowerCase().includes(f.eligibility.toLowerCase()))return false;
 return true;
 }).sort((a,b)=>(a.deadline||'9999').localeCompare(b.deadline||'9999'));
}
function fingerprint(a){return [a.fields?.name||a.name||'',a.fields?.category||a.category||''].map(s=>s.normalize('NFKC').replace(/\s+/g,'').toLowerCase()).join('|');}
function previewImport(input,state){if(!input||input.format!=='funding-radar-private'||![1,2].includes(input.version))throw Error('請選擇 Funding Radar 私人 JSON 備份');const raw=Array.isArray(input.applications)?input.applications:Object.values(input.applications||{});if(raw.length>2000)throw Error('匯入紀錄過多');const rows=raw.map(normalize),ids=new Set(Object.keys(state.applications)),fps=new Set(Object.values(state.applications).map(fingerprint)),added=[],duplicates=[];for(const a of rows){if(ids.has(a.id)||fps.has(fingerprint(a)))duplicates.push(a);else{ids.add(a.id);fps.add(fingerprint(a));added.push(a);}}return {added,duplicates,calendar:normalizeCalendar(input.calendar),budgets:normalizeBudgets(input.budgets)};}
function mergeImport(state,preview){for(const a of preview.added)if(!state.applications[a.id])state.applications[a.id]=clone(a);for(const k of ['calendar','budgets']){const ids=new Set(state[k].map(x=>x.id));for(const x of preview[k])if(!ids.has(x.id)){state[k].push(clone(x));ids.add(x.id);}}return state;}
function funding(state){const buckets={};for(const a of Object.values(state.applications)){const f=a.fields,key=[f.project||'未指定計畫',f.currency||'未指定幣別'].join('|');const b=buckets[key]||(buckets[key]={project:f.project||'未指定計畫',currency:f.currency||'未指定幣別',requested:0,pending:0,confirmed:0,unknown:0,confirmedUnknown:0,costKeys:[]});if(a.personal==='skipped'||a.result==='撤回')continue;const amount=f.amount===''?null:Number(f.amount);if(Number.isFinite(amount)&&amount>=0){b.requested+=amount;if(a.submitted&&['等待公告','需要補件'].includes(a.result))b.pending+=amount;}else b.unknown++;if(a.result==='通過'&&f.confirmedAmount!==''&&Number.isFinite(Number(f.confirmedAmount)))b.confirmed+=Math.max(0,Number(f.confirmedAmount));else if(a.result==='通過')b.confirmedUnknown++;if(f.costKey)b.costKeys.push(f.costKey);}
 for(const t of state.budgets){const key=t.project+'|'+t.currency;const b=buckets[key]||(buckets[key]={project:t.project,currency:t.currency,requested:0,pending:0,confirmed:0,unknown:0,confirmedUnknown:0,costKeys:[]});b.target=t.target;b.gap=Math.max(0,t.target-b.confirmed);}
 return Object.values(buckets).map(b=>({...b,duplicateCosts:b.costKeys.filter((x,i)=>b.costKeys.indexOf(x)!==i)}));}
function conflicts(x,calendar){const start=x.residency_start||x.fields?.residencyStart,end=x.residency_end||x.fields?.residencyEnd;if(!dateOK(start)||!dateOK(end))return null;return calendar.filter(c=>start<=c.end&&end>=c.start);}
function summary(state,rows,sources=[],now=Date.now()){const apps=Object.values(state.applications);return {sources:sources.filter(s=>s.enabled===true).length,interested:apps.filter(a=>a.personal==='interested').length,applied:apps.filter(a=>a.personal==='applied').length,upcoming:rows.filter(x=>publicState(x,now)==='open'&&days(x.deadline,x.deadline_timezone,now)>=0&&days(x.deadline,x.deadline_timezone,now)<=30&&state.applications[x.id]?.personal!=='skipped').length};}
return {KEY,LEGACY,FIELDS,CHECKS,RESULTS,uid,empty,normalize,read,write,select,today,days,publicState,hasSubstantiveSupport,fit,filter,previewImport,mergeImport,funding,conflicts,summary,clone,dateOK};
});
