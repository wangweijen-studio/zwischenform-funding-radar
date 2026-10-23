"""Official single-program facts; unfamiliar date formats fail closed."""
import re
import datetime as dt
from adapter_common import base,content,snippet,RELEVANT,CALL
from collect_ncaf import first
def collect(client,source,now):
    root=content(client.html(source['url']));text=root.text()
    name=first(root.find(tag='h1')).text() or source['name']
    if len(text)<200 or not (RELEVANT.search(text) and CALL.search(text)):raise ValueError('Expected official programme content missing')
    x=base(source,source['url'],name,now)
    x['eligibility']=snippet(root,r'antragsberechtigt|antragsteller|eligible|who can apply|Einzelkünstler|Voraussetzung|Wer kann',650) or None
    x['cash_support']=snippet(root,r'Förderhöhe|Stipendium.{0,50}(Euro|€)|grant.{0,50}(EUR|€)|Mindestantragssumme|(?:bis zu|maximal|max\.).{0,35}(?:Euro|€)|Fördersumme',450) or None
    x['evidence']=snippet(root,r'Antragsfrist|Antragsschluss|deadline|Bewerbungsschluss',350) or None
    dates={dt.date(int(m[3]),int(m[2]),int(m[1])) for m in re.finditer(r'(?:Antragsfrist|Bewerbungsschluss|Bewerbungsfrist|Abgabefrist)[^.!?]{0,100}?(\d{1,2})\.(\d{1,2})\.(20\d{2})',text)}
    months={m:i+1 for i,m in enumerate(('Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember'))}
    for m in re.finditer(r'(?:Antragsfrist|Bewerbungsschluss|Bewerbungsfrist|Abgabefrist|Projektideen bis zum)[^.!?]{0,100}?(\d{1,2})\.\s*('+ '|'.join(months)+r')\s*(20\d{2})',text):
        dates.add(dt.date(int(m[3]),months[m[2]],int(m[1])))
    if len(dates)==1:
        end=next(iter(dates));x['deadline']=end.isoformat()
        if now.date()>end:x['status']='closed'
    elif dates and all(now.date()>end for end in dates):
        x['status']='closed'
        x['review_reasons'].append('此官方頁面列出的多項明確申請截止日均已過期；未將不同項目的日期合併成單一截止日')
    x['cofunding']=snippet(root,r'zeitgleich.{0,80}(Stipendium|Residency)|andere Bundesmittel|nicht.{0,30}kombinier',450) or None
    if x['cofunding']:x['cofunding_url']=source['url']
    return [x],[],{'scope':'官方單一方案文字；本期完整申請日期未經專用解析器驗證，一律待人工核實'}
