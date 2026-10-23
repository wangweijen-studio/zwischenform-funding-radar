"""MOC main-site subsidy announcements; never access robots-blocked grants portal."""
import re
import hashlib
from urllib.parse import urljoin,urlsplit
from adapter_common import base,content,RELEVANT,CALL,EXCLUDE
def collect(client,source,now):
    root=content(client.html(source['url']));rows=[]
    for a in root.find(tag='a'):
        title=a.text();url=urljoin(source['url'],a.attrs.get('href',''))
        if urlsplit(url).hostname!='grants.moc.gov.tw' or not RELEVANT.search(title) or not CALL.search(title) or EXCLUDE.search(title):continue
        name=re.split(r'自(?:即日|\d{2,4}年)|[，,](?:即日|於)',title)[0].rstrip('，,')
        x=base(source,url,name,now)
        x['id']='moc-'+hashlib.sha256(name.encode()).hexdigest()[:20]
        x['announcement_urls']=[source['url']]
        x['evidence']=title
        x['review_reasons']=['僅取得文化部主站公告標題；完整辦法位於禁止自動讀取的補助入口，須人工核實日期、金額及資格']
        m=re.search(r'至(?:民國)?(\d{3})年(\d{1,2})月(\d{1,2})日',title)
        if m:
            import datetime as dt
            end=dt.date(int(m[1])+1911,int(m[2]),int(m[3]));x['deadline']=end.isoformat()
            if now.astimezone(dt.timezone(dt.timedelta(hours=8))).date()>end:x['status']='closed'
        rows.append(x)
    if not rows:raise ValueError('MOC index yielded no expected announcements; selector must be reviewed')
    return list({r['id']:r for r in rows}.values()),[{'url':'https://grants.moc.gov.tw/robots.txt','error':'完整辦法入口 Disallow: /；僅擷取允許讀取的主站公告標題，不視為已核實徵件'}],{'scope':'文化部主站補助最新索引標題；未自動讀取被禁止的完整辦法入口'}
