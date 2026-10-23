"""Fonds Soziokultur: parse the explicit dated round, never annual recurrence."""
import datetime as dt
import re
from zoneinfo import ZoneInfo
from adapter_common import base, snippet

MONTHS={'Jan':1,'Feb':2,'Mär':3,'Apr':4,'Mai':5,'Jun':6,'Jul':7,'Aug':8,'Sep':9,'Okt':10,'Nov':11,'Dez':12}

def collect(client,source,now):
    root=client.html(source['url']); text=root.text()
    if 'Allgemeine Projektförderung' not in text: raise ValueError('Fonds programme structure changed')
    x=base(source,source['url'],'Allgemeine Projektförderung',now)
    window=re.search(r'Nächstmögliche Antragstellung:\s*(\d{1,2})\.\s*(\w{3})\s*[-–]\s*(\d{1,2})\.\s*(\w{3})\s+(20\d{2})',text)
    money=re.search(r'mind(?:estens|\.)\s*([\d.]+)\s*Euro\s*(?:und\s*)?max(?:imal|\.)\s*([\d.]+)\s*Euro',text)
    x['eligibility']='須以德國團體／至少三名德國居民組成的倡議等名義申請；個人藝術家及居住海外申請者不可單獨申請。' if 'Einzelpersonen' in text and 'mindestens drei natürliche Personen mit Wohnsitz in Deutschland' in text else None
    x['cofunding']=snippet(root,r'Projekte mit einer bewilligten Kofinanzierung',500) or None
    x['cofunding_url']=source['url'] if x['cofunding'] else None
    x['restrictions']='須具參與式社會文化內容；純製作／展覽而無參與式構想不適用。' if 'Ausstellungen ohne Partizipation' in text else None
    x['overseas_execution']='不可僅於德國以外執行' if 'Projekte, die nur im Ausland stattfinden' in text else None
    if money:
        x.update(funding_min=int(money[1].replace('.','')),funding_amount=int(money[2].replace('.','')),currency='EUR',amount_status='verified_text')
        x['cash_support']=f"申請範圍 EUR {x['funding_min']:,}–{x['funding_amount']:,}；不是保證核定金額。"+('至多總預算 80%。' if '80 %' in text or '80 Prozent' in text else '')
    if window:
        year=int(window[5]); start=dt.date(year,MONTHS[window[2]],int(window[1])); end=dt.date(year,MONTHS[window[4]],int(window[3]))
        x['id']+='-'+str(year)+'-'+str(start.month)
        x['application_start']=start.isoformat();x['deadline']=end.isoformat();x['evidence']=window[0]
        if '23.59 Uhr' in text:
            x.update(deadline=dt.datetime.combine(end,dt.time(23,59),ZoneInfo('Europe/Berlin')).isoformat(),deadline_precision='minute')
        local=now.astimezone(ZoneInfo('Europe/Berlin'))
        if local.date()>end: x['status']='closed'
        elif local.date()<start: x['status']='upcoming'
        elif money and x['eligibility'] and x['restrictions'] and x['deadline_precision']=='minute':
            x.update(status='open',verification_status='verified',verified_at=now.isoformat(),review_reasons=[])
        if x['status']=='open' and now>=dt.datetime.fromisoformat(x['deadline']): x['status']='closed'
    return [x],[],{'scope':'一般計畫補助單一官方辦法頁；團體資格與 BKM 共同補助限制已列示'}
