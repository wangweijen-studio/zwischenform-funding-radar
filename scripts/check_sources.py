"""Check availability of official source homepages. This is NOT grant extraction."""
import json, datetime, pathlib, urllib.request
root=pathlib.Path(__file__).resolve().parents[1]
sources=json.loads((root/'data/sources.json').read_text(encoding='utf-8'))
results=[]
for source in sources:
    entry={**source,'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'unknown'}
    try:
        req=urllib.request.Request(source['url'],headers={'User-Agent':'FundingRadar/0.1 (source availability monitor)'})
        with urllib.request.urlopen(req,timeout=15) as resp:
            entry['status']='reachable' if 200<=resp.status<400 else 'http_error'
            entry['http_status']=resp.status
    except Exception as exc:
        entry['status']='check_failed'
        entry['error']=str(exc)[:160]
    results.append(entry)
(root/'data/scan_status.json').write_text(json.dumps({'generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'note':'Reachability checks only; NOT verified grant opportunities or updated deadlines.','sources':results},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

