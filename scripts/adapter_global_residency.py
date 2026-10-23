"""Bounded official programme adapters, with explicit support and Berlin gating."""
import io,re
from urllib.parse import urljoin
from adapter_common import base,content
from residency_policy import blank,proof,apply_rules

def collect(client,source,now):
    key=source['residency_adapter'];url=source['url']
    if key=='gas':
        from pypdf import PdfReader
        text=' '.join(page.extract_text() or '' for page in PdfReader(io.BytesIO(client.get(url))).pages)
    else:
        root=client.html(url)
        text=content(root).text() or root.text()
    x=base(source,url,source['programme_name'],now,'residency');p=blank(source,now,source['geographic_region'])
    x['residency_policy']=p
    rules=[]
    if key=='sam':
        if not re.search(r'fully funded programme.{0,150}SAM Residencies',text,re.I):raise ValueError('SAM funded programme scope missing')
        rules=[('stipend',r'Monthly stipend of SGD\$1,500','每月 SGD 1,500 生活津貼'),
            ('accommodation',r'Housing allowance for foreign residents','外國駐村者有住宿津貼；額度與是否足額待確認'),
            ('studio',r'A studio space OR co-working space','提供工作室或共享工作空間'),
            ('airfare',r'1 x return airfare on economy class','提供一張來回經濟艙機票；柏林出發規則未明')]
        if re.search(r'1 x return airfare on economy class',text,re.I):p['airfare'].update(coverage='round_trip_full',mode='unspecified',verified_at=now.isoformat())
        if re.search(r'open to those based in Singapore or internationally',text,re.I):p['eligibility']['residence']=proof('明文接受居住於新加坡或海外的申請者；柏林屬海外居住範圍',url,now,'eligible')
        p['other_eligibility']='官網另要求年滿 21 歲及駐村活動；國籍、柏林出發與本期徵件仍須核對。EX-SITU 組織方案另有亞洲條件，不能套用藝術家方案。'
    elif key=='esplanade':
        if not re.search(r'fully.funded residency',text,re.I):raise ValueError('Esplanade funded residency scope missing')
        rules=[('stipend',r'stipend of S\$2,000 per month','每月 SGD 2,000 津貼，最少一個月、最多三個月'),
            ('production',r'up to S\$1,000 for research materials','研究材料最多 SGD 1,000，須核准'),
            ('accommodation',r'Accommodation and international airfare to and from Singapore, if from abroad','海外駐村者提供住宿'),
            ('studio',r'Shared.working space for all residents','提供共享工作空間；專用工作室視需要'),
            ('airfare',r'Accommodation and international airfare to and from Singapore, if from abroad','海外駐村者提供新加坡來回國際機票；具體柏林出發與購票方式未載明')]
        if re.search(r'international airfare to and from Singapore, if from abroad',text,re.I):p['airfare'].update(coverage='round_trip_full',verified_at=now.isoformat())
        if re.search(r'application.{0,100}permits.{0,70}Esplanade',text,re.I):p['components']['visa']=proof('由主辦處理駐留許可申請；不等於簽證費已全額承擔',url,now,'needs_review')
        if re.search(r'28 April 2025 and closes on 22 June 2025',text):x.update(application_start='2025-04-28',deadline='2025-06-22T23:59:00+08:00',deadline_precision='datetime',status='closed',funding_year='2026')
    elif key=='headlands':
        if not re.search(r'Residencies of four to ten weeks include studio space, chef.prepared meals, housing, travel and living expenses',text,re.I):raise ValueError('Headlands AIR provisions missing')
        # Scope this to AIR; separate awards have different nationality/region limits.
        rules=[('stipend',r'housing, travel and living expenses','AIR 提供生活費，現行額度待確認'),('accommodation',r'fully sponsored residencies.{0,400}housing','AIR 提供受資助住宿'),('studio',r'Residencies of four to ten weeks include studio space','AIR 提供工作室'),('other_transport',r'housing, travel and living expenses','AIR 提供旅費，但本期來回機票與柏林起點未核實')]
        if '2027 Artist in Residence applications are now closed' in text:x.update(status='closed',funding_year='2027')
        p['other_eligibility']='僅核對一般 AIR；額外獎項的美國／加拿大居住或其他限制不代表所有 AIR 申請者都符合。'
    elif key=='bemis':
        rules=[('stipend',r'US.based artists.in.residence receive a \$1,250 USD monthly stipend','每月 USD 1,250 僅明確用於美國居住藝術家；柏林居住者須另查支付條款'),('accommodation',r'private kitchen and bathroom','提供居住／工作室與廚衛設施'),('studio',r'live/work studio','提供居住／工作室')]
        # Cash terms explicitly differentiate US-based artists. Do not give them
        # to a Berlin resident, nor count an airfare reimbursement example as full.
        if re.search(r'J.1 visa',text,re.I):p['other_eligibility']='國際藝術家的支付受簽證條件限制；不能把美國居住者津貼套用到柏林申請者。'
        if re.search(r'\$750 USD travel stipend',text,re.I):p['airfare'].update(coverage='partial',cap=750,currency='USD',conditions='官網 USD 750 旅費條款屬美國居住藝術家；柏林居住者適用性、來回範圍與簽證支付限制待確認',verified_at=now.isoformat())
        if '2027 and 2028, residencies will be paused' in text:x['status']='closed'
    elif key=='bundanon':
        if not re.search(r'providing residencies free of charge',text,re.I):raise ValueError('Bundanon free residency proof missing')
        rules=[('accommodation',r'most artists are provided with a private room','提供免費駐村住宿；部分團體房型須共住'),('studio',r'Artists in Residence Complex','免費駐村方案有工作空間，實際配置須核對')]
        if re.search(r'expenses, including travel, food, toiletries, and materials',text,re.I):
            p['airfare'].update(coverage='none',conditions='主辦明文要求藝術家自行負擔交通、餐食、日用品及材料；沒有柏林往返機票資助',verified_at=now.isoformat())
            p['components']['airfare']=proof('旅費自付，非來回機票資助',url,now,'not_provided')
        if re.search(r'from Australia and overseas',text,re.I):p['eligibility']['residence']=proof('明文接受澳洲及海外申請者；柏林屬海外範圍',url,now,'eligible')
        p['other_eligibility']='AUD 250 可退還保證金；取消或損壞可能不退。五年內曾駐村者不符再次申請條件；家屬不能同住。'
        applyurl='https://www.bundanon.com.au/residencies/apply/'
        detail=content(client.html(applyurl)).text()
        if '2027 program have now closed' in detail:x.update(status='closed',funding_year='2027')
    elif key=='gas':
        if 'G.A.S. Fellowship Award 2025' not in text:raise ValueError('GAS exact award/year missing')
        flat=re.sub(r'\s+','',text)
        rules=[('stipend',r'£1,000 Stipend','2025 年方案提供 GBP 1,000 津貼'),('artist_fee',r'£1,000 Honorarium','2025 年方案提供 GBP 1,000 藝術家費'),('accommodation',r'private bedroom with ensuite','提供私人套房住宿'),('studio',r'shared studio/event space','提供共享工作／活動空間'),('other_transport',r'airport transfers','提供機場接送')]
        if '£1,750TravelAllowance' in flat:
            p['airfare'].update(coverage='partial',mode='allowance',cap=1750,currency='GBP',verified_at=now.isoformat(),conditions='GBP 1,750 共同涵蓋機票／交通、簽證、旅遊醫藥及保險；不是單獨來回機票保證，也未核實柏林起點')
            p['components']['airfare']=proof('GBP 1,750 共用旅費預算，不能視為足額柏林來回機票',url,now)
            p['components']['visa']=proof('簽證支出與旅費共用 GBP 1,750 額度，不另外加計',url,now)
        if 'AnationalofANDcurrentlyresidinginoneofthe54Africancountries' in flat:
            for key2 in ('nationality','residence'):p['eligibility'][key2]=proof('本期要求非洲 54 國之一國籍且居住當地；不符合臺灣國籍／柏林居住情境',url,now,'ineligible')
        x.update(status='closed',funding_year='2025')
    elif key=='arcus':
        if 'Program Provisions' not in text:raise ValueError('ARCUS funded programme provisions missing')
        rules=[('stipend',r'production fee, living expense','受資助 Artist-in-Residence 方案有生活費；官網 2024 數字不能當作本期額度'),('production',r'production fee, living expense','受資助方案提供製作費，現期額度待確認'),('accommodation',r'A private studio, accommodation, transportation','受資助方案提供住宿'),('studio',r'A private studio, accommodation','受資助方案提供私人工作室'),('other_transport',r'accommodation, transportation, production fee','受資助方案有交通支持；來回機票、上限與柏林出發未核實')]
        p['other_eligibility']='本筆是受資助 Artist-in-Residence，不能套用目前另行開放且自費的 ARCUS Research。'
    elif key=='tokas':
        # Do not substitute third-party claims when official access is blocked.
        if not re.search(r'International Creator Residency Program 2027',text):raise ValueError('TOKAS exact programme/year missing')
        rules=[('stipend',r'living expenses','本期提供生活津貼，金額待官方指南核實'),('production',r'fee for creative work/project','提供創作／計畫費，金額待指南核實'),('accommodation',r'living space \(single room\)','提供單人住宿'),('studio',r'studio','提供工作空間，費用條件待指南核對')]
        if re.search(r'closed',text,re.I):x.update(status='closed',funding_year='2027')
    else:raise ValueError('Unknown dedicated residency adapter')
    apply_rules(p,text,rules,url,now)
    # The Berlin scenario cannot inherit US-specific cash terms.
    if key=='bemis':
        p['components']['stipend']['status']='needs_review'
        # Workspace access alone does not establish rent-free support for an
        # international artist under this particular visa/payment scheme.
        for component in ('accommodation','studio'):
            if not re.search(r'(?:free|no.cost).{0,50}(?:studio|accommodation)|(?:studio|accommodation).{0,50}(?:free|no.cost)',text,re.I):
                p['components'][component]['status']='needs_review'
    known=[v for k,v in p['components'].items() if k in ('stipend','artist_fee','production','accommodation','studio') and v['status']=='confirmed']
    if not known:return [],[],{'scope':'已讀取官方方案；尚未證實柏林申請者可取得實質支持，因此不收錄於有資助清單。','excluded_unverified':1}
    x['support']={k:p['components'][k]['text'] if p['components'][k]['status']=='confirmed' else None for k in ('stipend','artist_fee','production','accommodation','studio')}
    x['support']['travel']=None
    x['eligibility']='；'.join(p['eligibility'][k]['text'] for k in ('nationality','residence','departure'))
    x['evidence']='已逐項讀取官方方案支持；柏林出發機票與臺灣國籍不能由 International 標籤推定。'
    x['review_reasons']=['資助條款與徵件開放分別核實；未完整核實的本期日期、國籍、柏林出發及費用不得推定']
    x['relevance_tags']=['research','interdisciplinary','production']
    return [x],[],{'scope':'專用官方駐村條款核對；全球地域不設限制；分開查資助、國籍、居住與柏林出發。'}
