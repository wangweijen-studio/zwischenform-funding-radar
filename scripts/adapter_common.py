"""Conservative shared parsing; discovery never means a verified open call."""
import datetime as dt
import hashlib
import re
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode
from collect_ncaf import first

RELEVANT=re.compile(r'藝術|藝文|跨域|出版|展覽|服裝|設計|交流|視覺|工作坊|kunst|kultur|art\b|artist|design|residen|fellowship|publication|workshop|spatial',re.I)
CALL=re.compile(r'補助|徵件|申請|受理|徵選|förder|fonds|zuschuss|projektmittel|stipend|ausschreib|bewerb|application|open.call|fellowship',re.I)
EXCLUDE=re.compile(r'決標|採購|徵才|職缺|新聞澄清|結果|核定名單|獲選名單|補助名單|得獎|stellenausschreibung|geschäftsführung|förderergebnisse|juryentscheidung',re.I)

def canonical(url):
    p=urlsplit(url)
    if p.scheme=='http':p=p._replace(scheme='https')
    query=urlencode(sorted((k,v) for k,v in parse_qsl(p.query) if not k.lower().startswith(('utm_','fbclid'))))
    return urlunsplit((p.scheme,p.netloc,p.path,query,''))

def content(root):
    for nodes in (root.find(id='layout-grid__area--maincontent'),root.find(tag='main'),root.find(id='content')):
        if nodes:return first(nodes)
    return root

def snippet(root, pattern, limit=500):
    pattern=re.compile(pattern,re.I)
    candidates=[n.text() for n in content(root).find() if n.tag in ('p','li') and pattern.search(n.text()) and 10<len(n.text())<2000]
    return next(iter(candidates),'')[:limit]

def base(source,url,name,now,kind='grant'):
    return {'id':source['id']+'-'+hashlib.sha256(canonical(url).encode()).hexdigest()[:20],
        'source_id':source['id'],'name':name,'organizer':source['name'],'type':kind,
        'url':canonical(url),'official_source':True,'country':source.get('country'),
        'city':source.get('city'),'status':'needs_review','verification_status':'needs_review',
        'verified_at':None,'last_checked_at':now.isoformat(),'application_start':None,'deadline':None,
        'deadline_precision':'date','deadline_timezone':source.get('timezone','UTC'),
        'eligibility':None,'cash_support':None,'review_reasons':['已取得官方內容；本期日期、資助與個人資格仍須人工核實']}

def discover(client,source,now,limit=8):
    root=client.html(source['url']); links={}
    for a in root.find(tag='a'):
        title=a.text(); url=canonical(urljoin(source['url'],a.attrs.get('href','')))
        if title in ('Weitere Informationen','Read more','更多','閱讀更多','詳細資訊','more') or not title:
            title=a.attrs.get('aria-label') or a.attrs.get('title') or title
        context=source['id'].startswith('ba-') or source['id']=='berlin-kultur'
        if not ((RELEVANT.search(title) or context) and CALL.search(title)) or EXCLUDE.search(title): continue
        if urlsplit(url).hostname not in client.hosts or url==canonical(source['url']) or '.pdf' in url.lower(): continue
        prefix=urlsplit(source['url']).path
        prefixes=source.get('link_prefixes',[prefix])
        if (prefix.endswith('/') or source.get('link_prefixes')) and not any(urlsplit(url).path.startswith(p) for p in prefixes):continue
        if any(part in url.lower() for part in ('login','datenschutz','impressum')): continue
        links.setdefault(url,title)
    rows=[]; errors=[]
    for url,title in list(links.items())[:limit]:
        try:
            detail=content(client.html(url)); name=first(detail.find(tag='h1')).text() or title
            if name in ('最新消息','各項補助資訊','新聞與公告','News','Latest news'):name=title
            if not ((RELEVANT.search(name+' '+title) or context) and CALL.search(name+' '+title)): continue
            if re.search(r'residen|駐村',name+' '+title,re.I):continue  # dedicated funded-residency adapters only
            x=base(source,url,name,now)
            x['eligibility']=snippet(detail,r'申請資格|申請對象|antragsberechtigt|voraussetzung|who can apply|eligible') or None
            x['cash_support']=snippet(detail,r'補助上限|最高補助|補助額度|förderhöhe|maximal.{0,30}(euro|€)|grant.{0,20}amount') or None
            # No general-purpose deadline regex: meetings, project periods and
            # historical rounds must not become application windows.
            x['evidence']=snippet(detail,r'截止|受理|bewerbungsfrist|antragsfrist|deadline|ausschreibung') or None
            rows.append(x)
        except Exception as e: errors.append({'url':url,'error':type(e).__name__+': '+str(e)[:150]})
    return rows,errors,{'links_discovered':len(links),'detail_pages_checked':len(rows),'scope':'最新索引頁，最多 '+str(limit)+' 個相關官方細節頁；未核實欄位不推測'}
