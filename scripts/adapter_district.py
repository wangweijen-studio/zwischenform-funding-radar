"""Berlin districts: bounded culture/funding discovery, no inferred open state."""
import re
from urllib.parse import urljoin,urlsplit
from adapter_common import discover

def collect(client,source,now):
    root=client.html(source['url']);candidates={}
    for a in root.find(tag='a'):
        title=a.text();u=urljoin(source['url'],a.attrs.get('href',''))
        if urlsplit(u).hostname!='www.berlin.de' or urlsplit(u).path.startswith('/kultur-und-tickets/'):continue
        if re.search(r'Kulturförderung|Kunstförderung|Fachbereich Kunst|Fachbereich Kultur|Kunst und Kultur|Kultur und Kunst|^Kultur$|Weiterbildung und Kultur',title,re.I):
            candidates[u]=title
    rows=[];errors=[]
    selected=sorted(candidates,key=lambda u:(0 if 'förder' in candidates[u].lower() else 1 if re.search('Kunst und Kultur|^Kultur$',candidates[u]) else 2,u))[:2]
    for url in selected:
        try:
            found,problems,_=discover(client,{**source,'url':url},now,4);rows.extend(found);errors.extend(problems)
            if not found:
                page=client.html(url)
                funding={urljoin(url,a.attrs.get('href','')) for a in page.find(tag='a') if re.search(r'Kulturförderung|Kunstförderung|Fördermöglichkeiten|^Förderung$',a.text(),re.I)}
                for funding_url in sorted(funding)[:1]:
                    more,problems,_=discover(client,{**source,'url':funding_url},now,4);rows.extend(more);errors.extend(problems)
        except Exception as e:errors.append({'url':url,'error':type(e).__name__+': '+str(e)[:150]})
    if not rows:errors.append({'error':'本次未辨識可解析的區級藝術補助公告；不代表沒有徵件，仍須人工核對'})
    return rows,errors,{'scope':'區公所導覽中的藝術文化／補助入口，最多2個入口各4篇；非全站完整爬取','culture_indexes':list(candidates)[:2]}
