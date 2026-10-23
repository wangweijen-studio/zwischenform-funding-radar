"""Named official art programmes or a structurally checked latest-news index."""
import re
from urllib.parse import urljoin,urlsplit
from adapter_common import base,content,snippet,RELEVANT,CALL,EXCLUDE

def collect(client,source,now):
    root=client.html(source['url']);links={};entries=0
    for a in root.find(tag='a'):
        title=a.text();url=urljoin(source['url'],a.attrs.get('href',''))
        if urlsplit(url).hostname not in client.hosts:continue
        if source.get('news_path') and source['news_path'] in url and title:entries+=1
        known=title in source.get('program_names',[])
        if not known and not(RELEVANT.search(title) and CALL.search(title)):continue
        if EXCLUDE.search(title) or re.search(r'公立學校|學校參訪|理財|展訊|藝術獎得主|獲獎|揭曉',title):continue
        if url==source['url'] or url.lower().endswith('.pdf'):continue
        links.setdefault(url,title)
    rows=[];errors=[]
    for url,title in list(links.items())[:6]:
        try:
            page=content(client.html(url));text=page.text()
            if len(text)<80:raise ValueError('Expected official programme text missing')
            x=base(source,url,title,now)
            x['record_kind']='program'
            x['eligibility']=snippet(page,r'申請資格|申請對象|申請者|創作之個人|剛起步',450) or None
            x['cash_support']=snippet(page,r'獎助|贊助|補助|捐贈|藝術家費',450) or None
            x['evidence']=snippet(page,r'徵件|徵選|申請|認養|贊助|提名',350) or None
            x['review_reasons']=['官方藝術支持方案／公告已取得；不推定公開受理，當期申請日期、金額與資格須人工核實。提名制不等於可自行申請。']
            rows.append(x)
        except Exception as e:errors.append({'url':url,'error':type(e).__name__+': '+str(e)[:140]})
    if not rows and not entries:raise ValueError('Official programme/news index structure not recognised')
    return rows,errors,{'scope':'已知藝術支持方案，或最新一頁消息標題；提名制及活動參加不當成開放補助','news_entries_parsed':entries,'candidate_links':len(links),'programme_pages_parsed':len(rows)}
