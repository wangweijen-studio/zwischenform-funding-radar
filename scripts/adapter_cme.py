"""EU Culture Moves Europe semantic HTML attributes and dated rolling timeline."""
import datetime as dt
import re
from zoneinfo import ZoneInfo
from collect_ncaf import first,digest
from adapter_common import base

MONTHS={m:i+1 for i,m in enumerate(('January','February','March','April','May','June','July','August','September','October','November','December'))}

def official_datetime(value):
    m=re.fullmatch(r'(\d{1,2}) (\w+) (20\d{2}), (\d{1,2}):(\d{2}) (CET|CEST)',value or '')
    if not m or m[2] not in MONTHS:raise ValueError('Unknown official datetime format')
    value=dt.datetime(int(m[3]),MONTHS[m[2]],int(m[1]),int(m[4]),int(m[5]),tzinfo=ZoneInfo('Europe/Berlin'))
    if value.utcoffset()!=dt.timedelta(hours=2 if m[6]=='CEST' else 1):raise ValueError('Official timezone label conflicts with calendar date')
    return value

def collect(client,source,now):
    root=client.html(source['url']);nodes=root.find(tag='eac-calls-detail')
    if len(nodes)!=1:raise ValueError('EU semantic call component missing or ambiguous')
    call=nodes[0];attr=call.attrs;text=call.text()
    if 'individual mobility' not in attr.get('reference','').lower():raise ValueError('Not the expected individual mobility call')
    start=official_datetime(attr.get('date-opening'));end=official_datetime(attr.get('date-deadline'))
    # An extension is never silently ignored, nor guessed from a news date.
    extension=attr.get('date-extended-deadline','').strip()
    if extension not in ('','/'):end=official_datetime(extension)
    windows=[]
    for item in root.find(cls='js-toggle-timeline-item'):
        year=first(item.find(cls='stripe-timeline-year')).text()
        if not re.fullmatch(r'20\d{2}',year):continue
        for a in item.find(tag='a'):
            match=re.fullmatch(r'(\d{1,2}) (\w+)',a.text())
            if match and match[2] in MONTHS:
                date=dt.date(int(year),MONTHS[match[2]],int(match[1]))
                if start.date()<=date<=end.date():windows.append(date)
    windows=sorted(set(windows));today=now.astimezone(ZoneInfo('Europe/Berlin')).date()
    next_batch=next((d for d in windows if d>=today),None)
    x=base(source,source['url'],attr.get('title') or attr['reference'],now)
    x['id']+='-'+digest(attr['reference'])[:8]
    x['record_kind']='rolling_call';x['application_start']=start.date().isoformat();x['overall_deadline']=end.isoformat()
    x['official_call_state']=attr.get('status')
    x['deadline']=next_batch.isoformat() if next_batch else end.isoformat()
    x['deadline_precision']='date' if next_batch else 'minute'
    if next_batch==end.date():x.update(deadline=end.isoformat(),deadline_precision='minute')
    x['rolling_deadlines']=[d.isoformat() for d in windows]
    money=re.search(r'€(\d+) per day of project implementation',text)
    eligible=all(v in text for v in ('legally residing in one of the Creative Europe countries','18 years of age or older','design and fashion design','letter of invitation'))
    if eligible:x['eligibility']='年滿18歲、合法居住在 Creative Europe 參與國，從事含建築、服裝設計、文學及視覺藝術等指定領域；可個人或最多五人團體申請。須自行提供合法居住證明，國籍不等於居住資格。'
    if money:x.update(cash_support='生活費 EUR '+money[1]+'／計畫執行日；另有按旅程距離計算的交通與條件式加額，總額須依官方辦法核算。',daily_amount=int(money[1]),currency='EUR',amount_status='verified_text')
    x['overseas_execution']='須在自身居住國以外的另一個 Creative Europe 參與國執行，並有國際合作夥伴／邀請函。' if 'another Creative Europe country' in text else None
    x['restrictions']='本卡截止日顯示下一批收件日期，批次未公布時分時不推定午夜；整體徵件截止 '+end.isoformat()+'。計畫須符合 learn/create/explore/connect 中兩項；重複申請及共同補助條款仍需核對。'
    x['relevance_tags']=[t for t in ('architecture','fashion design','visual arts','literature','create','explore') if t in text]
    x['evidence']='官方 date-opening='+attr.get('date-opening','')+'；date-deadline='+attr.get('date-deadline','')+'；明確年份的批次表：'+', '.join(x['rolling_deadlines'])
    x['review_reasons']=[] if eligible and money and windows and x['overseas_execution'] else ['日期、批次、金額或資格必要欄位未完整解析，待人工核實']
    if attr.get('status') in ('cancelled','canceled'):
        from official_notices import mark
        x=mark(x,'歐盟官方語意欄位 status='+attr['status'],now)
    elif now>=end or attr.get('status')=='closed':x['status']='closed'
    elif now<start:x['status']='upcoming'
    elif not x['review_reasons'] and attr.get('status')=='open' and (x['deadline_precision']=='minute' or today<next_batch):
        x.update(status='open',verification_status='verified',verified_at=now.isoformat())
    return [x],[],{'scope':'歐盟官方本期 semantic call component 與明確年度的 monthly timeline；不將月生活費／日生活費當總額'}
