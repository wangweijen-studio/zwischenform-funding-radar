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
    from official_results import collect_results
    results,pending,problems=collect_results(client,root,IMPACT,now,2027)
    errors.extend(problems)
    x['results_announcements']=results
    x['results_urls']=[v['url'] for v in results]
    x['results_pending_urls']=pending
    x['announcement_urls']=x['results_urls']
    # Extract a programme year only from an explicit programme/year phrase.
    from adapter_common import content
    body=content(root).text()
    year=re.search(r'(?:IMPACT.{0,35}(?:für|Förderjahr)|Förderjahr|Förderung für das Jahr|Haushaltsmittel für das Jahr)\s*(20\d{2})',body,re.I)
    if year:x['funding_year']=year[1]
    eligibility=re.search(r'Voraussetzungen\s+(.+?)\s+Umfang der Förderung',body)
    if eligibility:x['eligibility']=eligibility[1];x['restrictions']=eligibility[1]
    description=re.search(r'Zweck / Ziele der Förderung\s+(.+?)\s+Voraussetzungen',body)
    if description:x['description']=description[1]
    support=re.search(r'Umfang der Förderung\s+(.+?)\s+Zeitraum der Ausschreibung',body)
    if support:x['cash_support']='官方方案整體預算（不是個別申請金額）：'+support[1]
    meta.update(results_state='2027 結果已公布；個人結果仍須自行確認' if results else '待人工核實：尚未核實 2027 正式結果與公布日期',
        results_urls=x['results_urls'],results_announcements=results,results_pending_urls=pending,
        scope=meta['scope']+'；結果必須同時核實 IMPACT、2027、正式結果標題及公布日期')
    return rows,errors,meta
