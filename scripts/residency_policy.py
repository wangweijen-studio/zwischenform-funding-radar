"""Evidence-separated funding and location profile. No airfare price guessing."""
import re

COMPONENTS=('stipend','artist_fee','accommodation','studio','production','airfare','visa','other_transport')

def blank(source,now,region):
    def unknown():return {'status':'needs_review','text':'官方未明確核實','url':source['url'],'verified_at':None}
    return {'version':1,'region':region,'country_code':source.get('country_code'),
        'checked_at':now.isoformat(),'components':{k:unknown() for k in COMPONENTS},
        'eligibility':{k:unknown() for k in ('nationality','residence','departure')},
        'airfare':{'coverage':'unknown','mode':'unknown','origin_rule':'unknown','berlin_eligible':False,
            'cap':None,'currency':None,'conditions':'柏林／德國出發、來回範圍與報銷額度待主辦確認',
            'possible_shortfall':'待確認；沒有即時柏林來回票價證據，不估算差額','url':source['url'],'verified_at':None},
        'funding_level':'partial','full_cost_coverage_verified':False,
        'other_eligibility':'年齡、年資、語言、在學狀態、實際在場及入境文件仍須人工核對'}

def proof(text,url,now,status='confirmed',**extra):
    return {'status':status,'text':text,'url':url,'verified_at':now.isoformat(),**extra}

def apply_rules(policy,text,rules,url,now):
    for key,pattern,description in rules:
        if re.search(pattern,text,re.I):policy['components'][key]=proof(description,url,now)
    return policy

def legacy_policy(record,client,now,source):
    """Only upgrade details whose official page was actually fetched this run."""
    from collect_ncaf import Document
    from adapter_common import content
    p=blank(source,now,'europe');raw=client.cache.get(record['url'])
    if not raw:return p
    text=content(Document(raw.decode('utf-8-sig')).root).text()
    if source['id']=='solitude':
        apply_rules(p,text,[
            ('stipend',r'monthly fellowship of\s*€1,300','每月 EUR 1,300 生活津貼'),
            ('accommodation',r'furnished live/work studio.{0,100}including electricity, heating, and water','提供居住／工作室，含水電暖氣'),
            ('studio',r'furnished live/work studio','提供帶家具的居住／工作室'),
            ('other_transport',r'reimbursement of travel costs for arrival and departure','抵達與離開的交通費可一次性報銷；上限及核准方式待確認'),
        ],record['url'],now)
        if re.search(r'Project funding \(depending on budget availability\)',text,re.I):
            p['components']['production']=proof('視主辦預算另行提供，非保證核定',record['url'],now,'needs_review')
        # A substantive Who-can-apply rule is stronger than an International label,
        # but it still does not expressly settle nationality/residence restrictions.
        if 'from around the world' in text:
            for key in ('nationality','residence'):
                p['eligibility'][key]=proof('申請對象條款面向世界各地從業者；未逐項列明臺灣國籍／柏林居住條件，須按最終辦法確認',record['url'],now,'needs_review')
    else:
        # Camargo's general "stipends vary" wording does not prove current-round
        # support. Keep the source candidate, but never recommend it as funded.
        rules=record.get('rules_url');body=client.cache.get(rules)
        if body and b'Residency stipends vary' in body:
            p['components']['stipend']=proof('一般條件提及津貼，但本期支持尚未核實',rules,now,'needs_review')
    return p
