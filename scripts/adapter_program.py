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
    x['eligibility']=snippet(root,r'antragsberechtigt|antragsteller|eligible|who can apply|Einzelkünstler',650) or None
    x['cash_support']=snippet(root,r'Förderhöhe|Stipendium.{0,50}(Euro|€)|grant.{0,50}(EUR|€)|Mindestantragssumme',450) or None
    x['evidence']=snippet(root,r'Antragsfrist|Antragsschluss|deadline|Bewerbungsschluss',350) or None
    date=re.search(r'(?:Antragsfrist|Bewerbungsschluss)[^.!?]{0,35}?(\d{1,2})\.(\d{1,2})\.(20\d{2})',text)
    if date:
        end=dt.date(int(date[3]),int(date[2]),int(date[1]));x['deadline']=end.isoformat()
        if now.date()>end:x['status']='closed'
    x['cofunding']=snippet(root,r'zeitgleich.{0,80}(Stipendium|Residency)|andere Bundesmittel|nicht.{0,30}kombinier',450) or None
    if x['cofunding']:x['cofunding_url']=source['url']
    return [x],[],{'scope':'官方單一方案文字；本期完整申請日期未經專用解析器驗證，一律待人工核實'}
