"""Strict IMPACT year-specific result proof, never personal selection inference."""
import datetime as dt
import re
from urllib.parse import urljoin, urlsplit
from adapter_common import content

RESULT=re.compile(r'Ergebnis|Juryentscheidung|geförderte.{0,20}Projekte|Förderentscheidung|Förderauswahl',re.I)

def result_proof(root,url,year,now):
    main=content(root)
    # Navigation years cannot establish the year of this result announcement.
    titles=[n.text() for n in root.find(tag='h1')]+[n.text() for n in main.find(tag='h2')]
    heading=next((t for t in titles if re.search(r'\bIMPACT\b',t,re.I) and RESULT.search(t) and re.search(r'\b'+str(year)+r'\b',t)),None)
    if not heading:return None
    dates=[]
    for n in main.find(tag='time'):
        if n.attrs.get('itemprop')!='datePublished' and 'published' not in n.attrs.get('class','').lower():continue
        value=n.attrs.get('datetime','')
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:T.*)?',value):dates.append(value[:10])
    for n in root.find(tag='meta'):
        if n.attrs.get('property') in ('article:published_time',) or n.attrs.get('itemprop')=='datePublished':
            dates.append(n.attrs.get('content','')[:10])
    # Berlin press announcements commonly label their release date explicitly.
    match=re.search(r'Pressemitteilung vom\s+(\d{2})\.(\d{2})\.(20\d{2})',main.text())
    if match:dates.append(f'{match[3]}-{match[2]}-{match[1]}')
    valid=set()
    for value in dates:
        try:
            day=dt.date.fromisoformat(value)
            if day<=now.date():valid.add(value)
        except ValueError:pass
    if len(valid)!=1:return None
    documents=[]
    for a in main.find(tag='a'):
        target=urljoin(url,a.attrs.get('href',''))
        if urlsplit(target).hostname=='www.berlin.de' and ('.pdf' in target.lower() or RESULT.search(a.text())):
            documents.append(target)
    return {'year':year,'title':heading,'url':url,'published_at':valid.pop(),'verified_at':now.isoformat(),
            'verified':True,'document_urls':sorted(set(documents))}

def collect_results(client,root,base,now,year=2027):
    verified=[];pending=[];errors=[]
    candidates=[]
    for a in content(root).find(tag='a'):
        title=a.text()
        if RESULT.search(title) and re.search(r'\b'+str(year)+r'\b',title):
            url=urljoin(base,a.attrs.get('href',''))
            if urlsplit(url).hostname=='www.berlin.de':candidates.append(url)
    for url in sorted(set(candidates))[:5]:
        try:
            proof=result_proof(client.html(url),url,year,now)
            if proof:verified.append(proof)
            else:pending.append(url)
        except Exception as e:errors.append({'url':url,'error':type(e).__name__+': '+str(e)[:150]})
    return verified,pending,errors
