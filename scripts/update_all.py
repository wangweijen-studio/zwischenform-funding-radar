"""Daily public-only update. Failed sources retain, demote and explain old rows."""
import datetime as dt
import importlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo
from collect_ncaf import Fetcher, collect, demote, write_json
from official_http import OfficialHTTP, Blocked
from validate_data import validate

ROOT=Path(__file__).resolve().parents[1]
FIELDS=('application_start','deadline','eligibility','cash_support','support','status','cofunding','results_urls')

def reconcile(previous, fresh, history, now):
    old={x['id']:x for x in previous}
    # Programme round labels, not dates, are the NCAF identity. Preserve IDs
    # from the deployed version when the official deadline changes.
    for x in fresh:
        if x['id'] not in old and x.get('source_id')=='ncaf':
            matches=[p for p in previous if p.get('url')==x.get('url') and p.get('name')==x.get('name') and p.get('record_kind')==x.get('record_kind')]
            if len(matches)==1:x['id']=matches[0]['id']
        p=old.get(x['id'])
        for field in FIELDS if p else ('new_announcement',):
            before=p.get(field) if p else None
            after=x.get(field) if p else x['name']
            if before!=after:
                history.append({'opportunity_id':x['id'],'at':now.isoformat(),'field':field,'old_value':before,'new_value':after,'url':x['url']})
    return fresh,history

def main():
    now=dt.datetime.now(dt.timezone.utc)
    load=lambda name,default:json.loads((ROOT/'data'/name).read_text(encoding='utf-8')) if (ROOT/'data'/name).exists() else default
    payload=load('opportunities.json',{'opportunities':[]});previous=payload['opportunities']
    old_status={s['source_id']:s for s in load('extraction_status.json',{'sources':[]})['sources']}
    sources=load('sources.json',[]);rows=[];statuses=[];clients={}
    for source in sources:
        sid=source['id']; prior=[x for x in previous if x.get('source_id')==sid]
        if not source.get('enabled'):
            rows.extend(prior)
            statuses.append({'source_id':sid,'status':'not_configured','checked_at':None,'last_success_at':None,'scope':source.get('scope')})
            continue
        client=None
        try:
            if sid=='ncaf':
                client=Fetcher();fresh,status=collect(client,prior,now)
            else:
                key=tuple(sorted(source['hosts']))
                client=clients.setdefault(key,OfficialHTTP(source['hosts']))
                request_start=len(client.requests)
                fresh,errors,meta=importlib.import_module(source['module']).collect(client,source,now)
                status={'source_id':sid,'status':'partial' if errors else 'success','checked_at':now.isoformat(),'errors':errors,'records':len(fresh),**meta}
                present={x['id'] for x in fresh}
                fresh.extend(demote(x,now,'本次索引未重新取得；待人工核實') for x in prior if x['id'] not in present)
                status['requests']=client.requests[request_start:]
            status['last_success_at']=now.isoformat() if status['status']=='success' else old_status.get(sid,{}).get('last_success_at')
            rows.extend(fresh)
        except Exception as e:
            rows.extend(demote(x,now,'本次來源擷取失敗；待重新核實') for x in prior)
            status={'source_id':sid,'status':'blocked' if isinstance(e,Blocked) else 'failed','checked_at':now.isoformat(),
                'last_success_at':old_status.get(sid,{}).get('last_success_at'),'errors':[{'error':type(e).__name__+': '+str(e)[:220]}],
                'requests':client.requests if client else []}
        statuses.append(status)
    # Preserve records belonging to sources not present in the current registry.
    known={s['id'] for s in sources}
    rows.extend(demote(x,now,'來源未設定，待重新核實') for x in previous if x.get('source_id') not in known)
    rows=list({r['id']:r for r in rows}.values())
    history=load('changes.json',{'changes':[]})['changes']
    rows,history=reconcile(previous,rows,history,now)
    payload.update(schema_version=3,last_scan_at=now.isoformat(),opportunities=rows)
    validate(payload,now)
    write_json(ROOT/'data/opportunities.json',payload)
    write_json(ROOT/'data/changes.json',{'changes':history})
    write_json(ROOT/'data/extraction_status.json',{'generated_at':now.isoformat(),'timezone':'Europe/Berlin','local_date':now.astimezone(ZoneInfo('Europe/Berlin')).date().isoformat(),'sources':statuses})
    print(json.dumps([{'source':s['source_id'],'status':s['status'],'records':s.get('records',0),'errors':s.get('errors',[])} for s in statuses],ensure_ascii=True))

if __name__=='__main__':main()
