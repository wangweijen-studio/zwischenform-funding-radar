"""Camargo: discover the current fellowship link, retain explicit closed status."""
import re
from urllib.parse import urljoin
from adapter_common import base,content

CONDITIONS='https://camargofoundation.org/en/residencies/residency-conditions'
def collect(client,source,now):
    index=content(client.html(source['url']))
    links=[a for a in index.find(tag='a') if 'Camargo Fellowship' in a.text()]
    if not links:raise ValueError('Camargo current fellowship link missing')
    conditions=client.html(CONDITIONS).text()
    if 'Residency stipends vary according to the program' not in conditions:raise ValueError('Cannot verify funded residency support')
    rows=[]
    for a in links[:2]:
        url=urljoin(source['url'],a.attrs.get('href',''));detail=content(client.html(url));text=detail.text()
        name=next((n.text() for n in detail.find(tag='h2') if 'Camargo Fellowship' in n.text()),'Camargo Fellowship')
        x=base(source,url,name,now,'residency')
        x['support']={'stipend':'依駐村方案提供津貼；本期金額與支付頻率待核實','artist_fee':None,'production':None,'travel':None,'accommodation':'提供獨立公寓；是否完全免費待核實','studio':None}
        x['rules_url']=CONDITIONS
        x['review_reasons']=['官方確認有津貼，但本期額度、資格、費用及日期須閱讀官方指南人工核實']
        x['evidence']='官方駐村條件頁確認津貼依方案而異；不推定固定金額或免費住宿。'
        if re.search(r'call for applications is now closed',text,re.I):x['status']='closed'
        rows.append(x)
    return rows,[],{'scope':'官方現有 fellowship 連結及條件頁；不從網址年份推定期別，不把補件截止當申請截止'}
