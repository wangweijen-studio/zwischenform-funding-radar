"""NCAF official HTML/PDF adapter. No LLM/API; never infer missing facts.

Program rounds are canonical. News links enrich the same program/round rather
than duplicating it. Unknown, failed, stale, or conflicting evidence fails closed.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import io
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://www.ncafroc.org.tw/'
INDEX = BASE + 'founding.aspx'
NEWS = BASE + 'news.html?categoryId=002'
TAIPEI = dt.timezone(dt.timedelta(hours=8))
KEYWORDS = ('視覺藝術', '跨域', '多元藝術', '文化資產', '視聽媒體', '藝文環境',
            '海外藝遊', '共融藝術', '策展', '現象書寫', '國際文化交流')
VOID = {'img', 'br', 'hr', 'input', 'meta', 'link', 'source', 'wbr', 'area', 'base', 'embed', 'param', 'col'}


class Node:
    def __init__(self, tag='', attrs=()):
        self.tag, self.attrs, self.children = tag, dict(attrs), []

    def text(self):
        return re.sub(r'\s+', ' ', ' '.join(c.text() if isinstance(c, Node) else c for c in self.children)).strip()

    def find(self, *, tag=None, cls=None, id=None):
        found = []
        for c in self.children:
            if not isinstance(c, Node):
                continue
            if ((tag is None or c.tag == tag) and (cls is None or cls in c.attrs.get('class', '').split())
                    and (id is None or c.attrs.get('id') == id)):
                found.append(c)
            found.extend(c.find(tag=tag, cls=cls, id=id))
        return found


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs)
        self.stack[-1].children.append(n)
        if tag not in VOID:
            self.stack.append(n)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, attrs))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, text):
        if not any(n.tag in ('script', 'style') for n in self.stack):
            self.stack[-1].children.append(text)


def canonical(url):
    p = urllib.parse.urlsplit(urllib.parse.urljoin(BASE, url))
    if p.scheme != 'https' or p.hostname != 'www.ncafroc.org.tw' or p.username or p.password:
        raise ValueError('Not an allowed NCAF official HTTPS URL')
    query = urllib.parse.parse_qs(p.query)
    if p.path.endswith(('founding_detail.html', 'news_detail.html')):
        query = {k: query[k] for k in ('sid', 'id', 'categoryId') if k in query}
        if 'sid' in query:
            query = {'sid': query['sid']}
    return urllib.parse.urlunsplit(('https', 'www.ncafroc.org.tw', p.path,
                                    urllib.parse.urlencode(sorted(query.items()), doseq=True), ''))


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


class Fetcher:
    def __init__(self, cache_dir=None):
        self.cache = {}
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.requests = []

    def get(self, url):
        url = canonical(url)
        if url in self.cache:
            return self.cache[url]
        if self.cache:
            time.sleep(0.25)
        req = urllib.request.Request(urllib.parse.quote(url, safe=':/?=&%()'),
                                     headers={'User-Agent': 'ZWISCHENFORM-FundingRadar/1.0 (daily public grant research)'})
        with urllib.request.urlopen(req, timeout=25) as response:
            canonical(response.url)
            data = response.read(12_000_001)
            if len(data) > 12_000_000:
                raise ValueError('Official response too large')
            if response.status != 200:
                raise ValueError('Official source did not return HTTP 200')
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            (self.cache_dir / (digest(url) + ('.pdf' if '.pdf' in url.lower() else '.html'))).write_bytes(data)
        self.cache[url] = data
        self.requests.append({'url': url, 'sha256': hashlib.sha256(data).hexdigest()})
        return data

    def html(self, url):
        return Document(self.get(url).decode('utf-8-sig')).root


def first(nodes):
    return nodes[0] if nodes else Node()


def relevant(text):
    return [k for k in KEYWORDS if k in text]


def match_program(programs, title):
    return next((p for p in sorted(programs, key=lambda p: len(p['name']), reverse=True)
                 if p['name'].replace('補助', '') in title.replace('補助', '')), None)


def discover(root):
    programs = {}
    for card in root.find(cls='foundingCard'):
        name = first(card.find(cls='name')).text()
        anchors = card.find(tag='a')
        if name and relevant(name) and anchors:
            url = canonical(anchors[0].attrs.get('href', ''))
            if '/founding_detail.html?' in url:
                programs[url] = {'name': name, 'url': url, 'index_note': first(card.find(cls='note')).text()}
    if not programs:
        raise ValueError('NCAF program index changed or returned an empty/non-content page')
    return list(programs.values())


def date_ranges(section):
    ranges = []
    for block in section.find(cls='applyTime'):
        for part in block.find(cls='part'):
            if first(part.find(cls='label')).text() != '收件時間':
                continue
            raw = first(part.find(cls='time')).text()
            m = re.fullmatch(r'(\d{4})/(\d{1,2})/(\d{1,2})\s*[-–~～至]\s*(\d{4})/(\d{1,2})/(\d{1,2})', raw)
            if m:
                start = dt.date(*map(int, m.groups()[:3]))
                end = dt.date(*map(int, m.groups()[3:]))
                if end < start:
                    raise ValueError('NCAF application range is reversed')
                ranges.append((start, end, first(block.find(cls='period')).text(), raw))
    return list(dict.fromkeys(ranges))


def news_range(text):
    # Require an explicit Gregorian year and application context. Never use the
    # budget/ROC year from the title or dates of an information session.
    pattern = r'(?:自|於)?(20\d{2})年(\d{1,2})月(\d{1,2})日\s*(?:至|到)\s*(?:(\d{1,2})月)?(\d{1,2})日\s*(?:起|期間)?\s*(?:受理(?:線上)?申請|開放(?:線上)?申請|接受申請|受理收件|開放收件)'
    m = re.search(pattern, text)
    if not m:
        return None
    y, sm, sd, em, ed = m.groups()
    start, end = dt.date(int(y), int(sm), int(sd)), dt.date(int(y), int(em or sm), int(ed))
    return (start, end, '公告收件期', m.group(0)) if start <= end else None


def pdf_facts(fetch, section, year):
    from pypdf import PdfReader
    facts = {'rules_url': None, 'rules_year_matches': False, 'cutoff_time': None,
             'amount': None, 'eligibility': None, 'rules_sha256': None}
    links = [a for a in section.find(tag='a') if '.pdf' in a.attrs.get('href', '').lower()
             and any(k in a.text() + a.attrs.get('download', '') for k in ('基準', '辦法'))]
    if not links:
        return facts
    url = canonical(links[0].attrs['href'])
    data = fetch.get(url)
    reader = PdfReader(io.BytesIO(data))
    if len(reader.pages) > 120:
        raise ValueError('Unexpected rule PDF page count')
    text = '\n'.join(p.extract_text() or '' for p in reader.pages)
    compact = re.sub(r'\s+', '', text).replace('：', ':')
    facts.update(rules_url=url, rules_sha256=hashlib.sha256(data).hexdigest())
    # A previous-year PDF must not verify a next-year round.
    facts['rules_year_matches'] = bool(re.search(fr'{year}年補助申請基準|{year - 1911}年度[^。]{{0,50}}(?:申請|補助)', compact))
    cutoff = re.search(r'線上申請至收件截止日(\d{1,2}:\d{2})', compact)
    if cutoff:
        facts['cutoff_time'] = cutoff.group(1)
    eligibility = re.search(r'(?:壹、|一、)?(?:申請資格[:：]?)?((?:經營或從事文化藝術事業且)?具有中華民國國籍[^。]{10,200})。', compact)
    if eligibility:
        facts['eligibility'] = eligibility.group(1)
    # Dedicated category rule attachments may contain general rules and Q&A.
    # Extract only the explicitly labelled funding section, never the largest
    # currency number anywhere in the PDF.
    amount = re.search(r'補助經費[:：](.{12,480}?)(?=2\.|二、|獲補助計畫結束|$)', compact)
    if amount:
        facts['amount'] = amount.group(1).strip()[:420]
    return facts


def make_record(program, root, round_info, now, facts):
    start, end, period, raw = round_info
    facts = dict(facts)
    if not facts.get('rules_year_matches'):
        facts['amount'] = None
    rules = first(root.find(id='foundingD1'))
    application = first(root.find(id='foundingD4'))
    eligibility = next((p.text().split('申請資格：', 1)[1] for p in application.find(tag='p')
                        if '申請資格：' in p.text()), None) or facts.get('eligibility')
    restrictions = next((p.text() for p in application.find(tag='p') if '不受理申請之計畫' in p.text()), None)
    date_end = end.isoformat()
    time_value = facts.get('cutoff_time') if facts.get('rules_year_matches') else None
    deadline = date_end + 'T' + time_value + ':00+08:00' if time_value else date_end
    today = now.astimezone(TAIPEI).date()
    reasons = []
    if not eligibility:
        reasons.append('申請資格待人工核實')
    if not facts.get('amount'):
        reasons.append('補助金額／費用上限待人工核實')
    if not facts.get('rules_year_matches'):
        reasons.append('本期適用辦法年度待人工核實')
    status = ('closed' if today > end or (time_value and now >= dt.datetime.fromisoformat(deadline))
              else 'upcoming' if today < start else 'needs_review' if reasons or (today == end and not time_value) else 'open')
    record = {
        'id': 'ncaf-' + digest(program['url'] + '|' + start.isoformat() + '|' + date_end)[:20],
        'source_id': 'ncaf', 'record_kind': 'program_round', 'type': 'grant',
        'name': program['name'] + ' · ' + period, 'program_name': program['name'],
        'organizer': '國家文化藝術基金會 NCAF', 'location': '臺灣／國際（依官方計畫範圍）',
        'url': program['url'], 'official_source': True,
        'application_start': start.isoformat(), 'deadline': deadline,
        'deadline_precision': 'minute' if time_value else 'date', 'deadline_timezone': 'Asia/Taipei',
        'status': status, 'verification_status': 'needs_review' if reasons else 'verified',
        'verified_at': now.isoformat() if not reasons else None, 'last_checked_at': now.isoformat(),
        'evidence': '官方收件時間：' + raw, 'eligibility': eligibility or '待人工核實',
        'restrictions': restrictions, 'eligibility_match': '須自行確認國籍／居留身分、個人或團體及計畫限制',
        'cash_support': facts.get('amount') or '待人工核實；未推定補助額度',
        'amount_status': 'verified_text' if facts.get('amount') else 'needs_review',
        'application_fee': '待人工核實；不推定免費',
        'relevance_tags': relevant(program['name'] + ' ' + rules.text()),
        'relevance_basis': '依計畫類別／官方受理項目比對；不代表個人資格已符合',
        'review_reasons': reasons, 'rules_url': facts.get('rules_url'),
        'rules_sha256': facts.get('rules_sha256'), 'announcement_urls': [],
        'field_evidence': {
            'application_dates': {'url': program['url'], 'text': raw},
            'eligibility': {'url': program['url'], 'text': eligibility},
            'amount': {'url': facts.get('rules_url'), 'text': facts.get('amount')},
        },
    }
    return record


def demote(record, now, reason):
    record = dict(record)
    record['verification_status'] = 'needs_review'
    record['status'] = 'needs_review'
    record['review_reasons'] = list(dict.fromkeys(record.get('review_reasons', []) + [reason]))
    record['last_checked_at'] = now.isoformat()
    if record.get('deadline'):
        try:
            if dt.date.fromisoformat(record['deadline'][:10]) < now.astimezone(TAIPEI).date():
                record['status'] = 'closed'
        except ValueError:
            pass
    return record


def collect(fetch, previous, now):
    rows, errors, completed = [], [], set()
    programs = discover(fetch.html(INDEX))
    for program in programs:
        try:
            root = fetch.html(program['url'])
            if not root.find(id='foundingD1'):
                raise ValueError('Required program content sections missing')
            rounds = date_ranges(first(root.find(id='foundingD2')))
            if not rounds:
                # Keep a single candidate with no invented cycle or dates.
                rows.append({'id': 'ncaf-' + digest(program['url'])[:20], 'source_id': 'ncaf',
                             'record_kind': 'program', 'type': 'grant', 'name': program['name'],
                             'program_name': program['name'], 'url': program['url'], 'official_source': True,
                             'organizer': '國家文化藝術基金會 NCAF', 'status': 'needs_review',
                             'verification_status': 'needs_review', 'application_start': None, 'deadline': None,
                             'verified_at': None, 'last_checked_at': now.isoformat(),
                             'evidence': None, 'relevance_tags': relevant(program['name']),
                             'review_reasons': ['官方未提供可可靠解析的收件期；待人工核實'],
                             'cash_support': '待人工核實', 'eligibility': '待人工核實'})
            for info in rounds:
                facts = {}
                if info[1] >= now.astimezone(TAIPEI).date():
                    try:
                        facts = pdf_facts(fetch, first(root.find(id='foundingD1')), info[1].year)
                    except Exception as exc:
                        errors.append({'url': program['url'], 'stage': 'rules_pdf', 'error': type(exc).__name__})
                rows.append(make_record(program, root, info, now, facts))
            completed.add(program['url'])
        except Exception as exc:
            errors.append({'url': program['url'], 'stage': 'program', 'error': type(exc).__name__ + ': ' + str(exc)[:120]})
    # Discover application announcements only. A result, procurement, or event
    # registration is never treated as a call, even if it contains relevant words.
    news_count, excluded = 0, 0
    try:
        news_root = fetch.html(NEWS)
        cards = news_root.find(cls='newsCard')
        if not cards:
            raise ValueError('NCAF news markup missing')
        for card in cards:
            title = first(card.find(cls='title')).text()
            if not relevant(title) or re.search(r'名單|結果|採購|評選|詐騙', title) or not re.search(r'受理|徵件|開放收件', title):
                excluded += 1
                continue
            anchor = first(card.find(tag='a'))
            url = canonical(anchor.attrs.get('href', ''))
            article = fetch.html(url)
            section = first(article.find(cls='main-content'))
            if not section.text():
                raise ValueError('NCAF news content missing')
            news_count += 1
            # Name matching is used to associate a news item, never to verify a
            # date. Date extraction must come from an explicit year in its body.
            # Longest match prevents generic "視覺藝術" from swallowing
            # "視覺藝術策展專案" or "視覺藝術組織營運專案".
            match = match_program(programs, title)
            rng = news_range(section.text())
            mapped = [x for x in rows if match and x['url'] == match['url'] and rng
                      and x.get('application_start') == rng[0].isoformat() and (x.get('deadline') or '')[:10] == rng[1].isoformat()]
            if mapped:
                for record in mapped:
                    record['announcement_urls'].append(url)
                    record['published_at'] = first(card.find(cls='date')).text().replace('/', '-')
            else:
                undated = [x for x in rows if match and x['url'] == match['url'] and x['record_kind'] == 'program']
                if undated and not rng:
                    for record in undated:
                        record.setdefault('announcement_urls', []).append(url)
                        record['published_at'] = first(card.find(cls='date')).text().replace('/', '-')
                    continue
                # If a program has no schedule but its newer news has an explicit
                # date, use that news as evidence without trusting the index badge.
                name = match['name'] if match else title
                candidate = {'id': 'ncaf-news-' + digest(url)[:20], 'source_id': 'ncaf', 'record_kind': 'announcement',
                             'type': 'grant', 'name': name, 'program_name': name, 'url': url, 'official_source': True,
                             'organizer': '國家文化藝術基金會 NCAF', 'status': 'needs_review',
                             'verification_status': 'needs_review', 'verified_at': None, 'last_checked_at': now.isoformat(),
                             'published_at': first(card.find(cls='date')).text().replace('/', '-'),
                             'application_start': rng[0].isoformat() if rng else None,
                             'deadline': rng[1].isoformat() if rng else None, 'deadline_precision': 'date',
                             'deadline_timezone': 'Asia/Taipei', 'relevance_tags': relevant(title),
                             'evidence': rng[3] if rng else None, 'eligibility': '待人工核實：請閱讀官方辦法',
                             'cash_support': '待人工核實：請閱讀官方辦法',
                             'review_reasons': ['公告已擷取；資格、金額與本期辦法尚待人工核實']}
                if rng:
                    today = now.astimezone(TAIPEI).date()
                    candidate['status'] = 'closed' if today > rng[1] else 'upcoming' if today < rng[0] else 'needs_review'
                if match and rng:
                    candidate['id'] = 'ncaf-' + digest(match['url'] + '|' + rng[0].isoformat() + '|' + rng[1].isoformat())[:20]
                    rows = [x for x in rows if not (x['url'] == match['url'] and x['record_kind'] == 'program')]
                candidate['announcement_urls'] = [url]
                rows.append(candidate)
    except Exception as exc:
        errors.append({'url': NEWS, 'stage': 'news', 'error': type(exc).__name__ + ': ' + str(exc)[:120]})
    # Retain missing/failed previous records as review-only. Never refresh their
    # verified_at or silently present them as still open.
    ids = {r['id'] for r in rows}
    for old in previous:
        if old.get('source_id') != 'ncaf':
            rows.append(old)
        elif old.get('id') not in ids and old.get('url') not in completed:
            rows.append(demote(old, now, '本次未能重新取得此公告；待人工核實'))
    dedup = {}
    for record in rows:
        if record['id'] not in dedup:
            dedup[record['id']] = record
        else:
            first_record = dedup[record['id']]
            first_record['announcement_urls'] = sorted(set(first_record.get('announcement_urls', []) + record.get('announcement_urls', [])))
    priority = {'open': 0, 'upcoming': 1, 'needs_review': 2, 'closed': 3}
    rows = sorted(dedup.values(), key=lambda r: (priority.get(r.get('status'), 2), r.get('deadline') or '9999', r['id']))
    status = {'source_id': 'ncaf', 'checked_at': now.isoformat(), 'status': 'partial' if errors else 'success',
              'programs_discovered': len(programs), 'programs_checked': len(completed),
              'announcements_checked': news_count, 'news_excluded': excluded, 'records': len(rows),
              'open_verified': sum(r.get('status') == 'open' for r in rows), 'errors': errors,
              'requests': fetch.requests, 'news_scope': '官方補助訊息最新一頁；補助廣場全部相關類別'}
    return rows, status


def write_json(path, payload):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache-dir')
    args = parser.parse_args()
    now = dt.datetime.now(dt.timezone.utc)
    target = ROOT / 'data/opportunities.json'
    payload = json.loads(target.read_text(encoding='utf-8'))
    fetch = Fetcher(args.cache_dir)
    try:
        rows, status = collect(fetch, payload.get('opportunities', []), now)
    except Exception as exc:
        rows = [demote(x, now, 'NCAF 擷取失敗；待人工核實') if x.get('source_id') == 'ncaf' else x
                for x in payload.get('opportunities', [])]
        status = {'source_id': 'ncaf', 'status': 'failed', 'checked_at': now.isoformat(),
                  'errors': [{'stage': 'discovery', 'error': type(exc).__name__ + ': ' + str(exc)[:160]}], 'requests': fetch.requests}
    payload.update(schema_version=2, last_scan_at=now.isoformat(), opportunities=rows)
    write_json(target, payload)
    write_json(ROOT / 'data/extraction_status.json', {'generated_at': now.isoformat(), 'sources': [status]})
    print(json.dumps({k: v for k, v in status.items() if k != 'requests'}, ensure_ascii=True))
    # A failed extraction still publishes the honest review state. Tests and
    # schema validation, rather than successful HTTP alone, gate deployment.


if __name__ == '__main__':
    main()
