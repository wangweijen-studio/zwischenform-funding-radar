"""Recognise explicit official cancellation/reopening; never infer from absence."""
import re

CANCEL=re.compile(r'(?:本次|本期|此)(?:補助)?(?:徵件|徵選|申請)(?:作業)?(?:業已|已經|已)(?:取消|撤銷)|(?:this|the|current) (?:open )?call (?:has been|is|was) (?:cancelled|canceled|withdrawn)|(?:diese|die|aktuelle) Ausschreibung (?:wurde|ist) (?:abgesagt|aufgehoben|zurückgezogen)',re.I)
REOPEN=re.compile(r'(?:本次|本期|此)(?:徵件|徵選|申請)(?:已)?(?:重新開放|恢復受理)|(?:this|the) (?:open )?call (?:has been|is|was) reopened|(?:die|diese) Ausschreibung (?:wurde|ist) wieder geöffnet',re.I)
CONDITIONAL=re.compile(r'\b(?:if|when|unless|falls|wenn|kann)\b|若|倘|可能|保留|尚未|並未|並無|未曾',re.I)

def statement(text,pattern=CANCEL):
    for sentence in re.split(r'[。.!?；;\n]',text):
        if len(sentence)>500 or CONDITIONAL.search(sentence):continue
        if pattern.search(sentence):return sentence.strip()[:220]
    return None

def mark(record,evidence,now,uncertain=False):
    result=dict(record)
    result['cancellation_evidence']=evidence
    result['cancellation_checked_at']=now.isoformat()
    result['cancellation_scope_uncertain']=uncertain
    result['status']='needs_review' if uncertain else 'cancelled'
    result['verification_status']='needs_review'
    message='官方有取消公告，但與本期的對應範圍待人工核實' if uncertain else '官方明確公告本次徵件已取消'
    result['review_reasons']=list(dict.fromkeys(result.get('review_reasons',[])+[message]))
    return result

def apply_cached(records,client,now):
    from collect_ncaf import Document
    from adapter_common import content
    cache=getattr(client,'cache',None)
    if cache is None:cache=getattr(getattr(client,'client',None),'cache',{})
    out=[]
    for record in records:
        raw=cache.get(record.get('url'))
        if not raw:out.append(record);continue
        root=content(Document(raw.decode('utf-8-sig')).root)
        evidence=statement(root.text())
        reopening=statement(root.text(),REOPEN)
        if reopening:record={**record,'reopening_evidence':reopening}
        if evidence:
            # A programme page may contain multiple NCAF rounds. Without an
            # exact round label, lower confidence instead of cancelling all.
            period=record.get('name','').split(' · ')[-1]
            uncertain=record.get('record_kind')=='program_round' and re.sub(r'\s','',period) not in re.sub(r'\s','',evidence)
            if not record.get('cancellation_evidence'):
                record=mark(record,evidence,now,uncertain)
        out.append(record)
    return out
