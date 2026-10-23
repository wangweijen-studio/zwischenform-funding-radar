"""Berlin districts: bounded culture/funding discovery, no inferred open state."""
import re
from urllib.parse import urljoin,urlsplit
from adapter_common import discover

def collect(client,source,now):
    if source.get('funding_indexes') or source.get('programme_pages'):
        rows=[];errors=[]
        for url in source.get('funding_indexes',[])[:2]:
            try:
                found,problems,_=discover(client,{**source,'url':url},now,6);rows.extend(found);errors.extend(problems)
            except Exception as e:errors.append({'url':url,'error':type(e).__name__+': '+str(e)[:150]})
        from adapter_program import collect as programme
        for url in source.get('programme_pages',[])[:2]:
            try:
                found,problems,_=programme(client,{**source,'url':url},now);rows.extend(found);errors.extend(problems)
            except Exception as e:errors.append({'url':url,'error':type(e).__name__+': '+str(e)[:150]})
        rows=list({r['id']:r for r in rows}.values())
        if not rows:errors.append({'error':'本次官方補助索引未辨識到可解析公告；不代表沒有徵件，須人工核對'})
        return rows,errors,{'scope':'由區公所官方連結核對的文化補助專用入口，最多2個索引及2個指定方案頁；未完整核實不標開放','culture_indexes':source.get('funding_indexes',[])[:2],'programme_pages':source.get('programme_pages',[])[:2]}
    root=client.html(source['url']);candidates={}
    for a in root.find(tag='a'):
        title=a.text().replace('\u00ad','');u=urljoin(source['url'],a.attrs.get('href',''))
        if urlsplit(u).hostname!='www.berlin.de' or urlsplit(u).path.startswith('/kultur-und-tickets/'):continue
        if re.search(r'Kulturförderung|Kunstförderung|Fachbereich Kunst|Fachbereich Kultur|Kunst und Kultur|Kultur und Kunst|^Kultur$|Weiterbildung und Kultur',title,re.I):
            candidates[u]=title
    rows=[];errors=[]
    selected=sorted(candidates,key=lambda u:((10 if '/newsletter/' in u else 0)+(0 if 'förder' in candidates[u].lower() else 1 if re.search('Kunst und Kultur|Fachbereich Kultur|^Kultur$',candidates[u]) else 2),u))[:2]
    for url in selected:
        try:
            found,problems,_=discover(client,{**source,'url':url},now,4);rows.extend(found);errors.extend(problems)
            if not found:
                page=client.html(url)
                funding={urljoin(url,a.attrs.get('href','')) for a in page.find(tag='a') if re.search(r'Kulturförderung|Kunstförderung|Fördermöglichkeiten|^Förderung$',a.text(),re.I)}
                for funding_url in sorted(funding)[:1]:
                    more,problems,_=discover(client,{**source,'url':funding_url},now,4);rows.extend(more);errors.extend(problems)
                if not funding:
                    culture={urljoin(url,a.attrs.get('href','')) for a in page.find(tag='a') if re.search(r'Fachbereich Kultur|Kunst und Kultur|Kultur und Geschichte|Dezentrale Kulturarbeit|^Kultur$',a.text().replace('\u00ad',''))}
                    for child in sorted(culture)[:2]:
                        if child==url or '/newsletter/' in child:continue
                        more,problems,_=discover(client,{**source,'url':child},now,4);rows.extend(more);errors.extend(problems)
        except Exception as e:errors.append({'url':url,'error':type(e).__name__+': '+str(e)[:150]})
    rows=list({r['id']:r for r in rows}.values())
    if not rows:errors.append({'error':'本次未辨識可解析的區級藝術補助公告；不代表沒有徵件，仍須人工核對'})
    return rows,errors,{'scope':'區公所導覽中的藝術文化／補助入口及有界線的子索引；非全站完整爬取','culture_indexes':selected}
