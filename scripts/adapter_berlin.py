"""Berlin programme discovery and separate, explicit IMPACT result monitoring."""
import re
import copy
from urllib.parse import urljoin
from adapter_common import discover, base, snippet

IMPACT='https://www.berlin.de/sen/kultur/foerderung/foerderprogramme/interkulturelle-projekte/artikel.82020.php'

def collect(client,source,now):
    rows,errors,meta=discover(client,source,now,8)
    # Category labels are not announcements. Follow only relevant official
    # programme categories, then discover their actual grant/stipend links.
    from adapter_common import content
    index=content(client.html(source['url']))
    categories={urljoin(source['url'],a.attrs.get('href','')) for a in index.find(tag='a')
        if re.search(r'Bildende Kunst|Spartenoffene Förderung|Internationaler Kulturaustausch|Kofinanzierung|Kunst im Stadtraum',a.text())}
    for url in sorted(categories)[:5]:
        if not url.startswith('https://www.berlin.de/sen/kultur/foerderung/foerderprogramme/'):continue
        try:
            category={**source,'url':url}
            added,problems,_=discover(client,category,now,4);rows.extend(added);errors.extend(problems)
        except Exception as e:errors.append({'url':url,'error':type(e).__name__+': '+str(e)[:150]})
    root=client.html(IMPACT);text=root.text()
    x=base(source,IMPACT,'IMPACT-Förderung',now)
    x['eligibility']=snippet(root,r'Künstlerinnen|Künstler\*|Voraussetzungen|Wohnsitz|Lebensmittelpunkt',700) or None
    x['cash_support']=snippet(root,r'Projektförderung|Förderhöhe|Höhe der Förderung',500) or None
    x['evidence']=snippet(root,r'Abgabe.{0,10}Bewerbungsfrist|Oktober 2026',300) or None
    # The 2026 page labels its October cutoff MEZ during daylight time;
    # retain date precision instead of silently correcting its UTC offset.
    m=re.search(r'(?:Bewerbungsfrist:|Abgabe-/ Bewerbungsfrist:)\s*(\d{1,2})\.\s*Oktober\s*(20\d{2})',text)
    if m:
        x['deadline']=f'{m[2]}-10-{int(m[1]):02d}'
        if now.date().isoformat()>x['deadline']:x['status']='closed'
    x['review_reasons']=['依官方原文保留日期；時區標示及個人資格需核對。結果公告須獨立核實。']
    rows=[r for r in rows if r['url']!=IMPACT]+[x]
    results=[]
    for a in root.find(tag='a'):
        if re.search(r'2027',a.text()) and re.search(r'Ergebnis|Juryentscheidung|geförderte Projekte|Förderentscheidung',a.text(),re.I):
            url=urljoin(IMPACT,a.attrs.get('href',''))
            if url.startswith('https://www.berlin.de/'):
                detail=client.html(url)
                if '2027' in detail.text():results.append(url)
    x['results_urls']=sorted(set(results))
    x['announcement_urls']=x['results_urls']
    meta.update(results_state='已辨識官方 2027 結果連結，請人工核對名單' if results else '待人工核實：本頁尚未辨識到明確 2027 結果連結',results_urls=results,
        scope=meta['scope']+'；另讀取 IMPACT 官方頁及明確標為 2027 結果的連結')
    return rows,errors,meta
