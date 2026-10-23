"""Cash-supported international residency; programme facts != current open call."""
import re
from adapter_common import base, snippet

def collect(client,source,now):
    root=client.html(source['url']);text=root.text()
    if 'Solitude Fellowship' not in text: raise ValueError('Solitude programme structure changed')
    amount=re.search(r'monthly fellowship of\s*€([\d,]+)',text,re.I)
    if not amount: raise ValueError('Cannot verify substantive residency funding')
    x=base(source,source['url'],'Solitude Fellowship',now,'residency')
    x['support']={'stipend':'EUR '+amount[1]+'／月','artist_fee':None,
        'production':'視預算提供計畫經費，非保證核定' if 'Project funding (depending on budget availability)' in text else None,
        'accommodation':'提供含水電暖氣的居住／工作室；個人額外費用須核對' if 'including electricity, heating, and water' in text else None,
        'studio':'提供居住／工作室' if 'furnished live/work studio' in text else None,
        'travel':'抵達及離開的一次性交通費報銷' if 'reimbursement of travel costs for arrival and departure' in text else None}
    x['eligibility']=snippet(root,r'fellowship is aimed at',650) or None
    x['relevance_tags']=[tag for tag in ('sculpture','fashion design','urban planning','interdisciplinary') if tag in text.lower()]
    x.update(currency='EUR',monthly_amount=int(amount[1].replace(',','')),funding_unit='month',payment_frequency='每月',
        amount_status='verified_text',residency_length='6 或 9 個月' if '6- or 9-month' in text else None,
        full_attendance='須全期居住 Stuttgart，並設為主要居所' if 'main residence in Stuttgart required' in text else None,
        taiwan_eligibility='全球藝術家皆可提出申請；年資、在學狀態及語言仍須個別核對' if 'from around the world' in text else None,
        evidence='官方方案已確認生活津貼；本頁未提供可核實的本期申請起訖日。',
        review_reasons=['已確認實質現金資助；本期徵件日期、費用與駐村起訖時間未核實，不能標示開放'])
    return [x],[],{'scope':'Solitude 官方方案頁；核實津貼、工作室與在場要求，不推定徵件日期'}
