"""Small, identified, rate-limited robots-aware official-source client."""
import hashlib
import time
from urllib.parse import urlsplit, urlunsplit, quote, urljoin
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
from urllib.robotparser import RobotFileParser

AGENT = 'ZWISCHENFORM-FundingRadar/2.0 (+https://github.com/wangweijen-studio/zwischenform-funding-radar)'

class Blocked(RuntimeError):
    pass

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

class OfficialHTTP:
    def __init__(self, hosts):
        self.hosts = set(hosts)
        self.cache, self.robots, self.last, self.requests = {}, {}, {}, []
        self.opener = build_opener(NoRedirect)

    def allowed_url(self, url):
        p = urlsplit(url)
        if p.scheme != 'https' or p.hostname not in self.hosts or p.username or p.password or p.port not in (None,443):
            raise Blocked('URL outside official HTTPS allowlist')
        return p

    def redirect_target(self,url,target):
        target=urljoin(url,target)
        p=urlsplit(target)
        # Some official sites emit legacy HTTP redirects, including robots.
        # Request only the secure equivalent on the same allowlisted host;
        # never downgrade transport, broaden hosts or bypass robots rules.
        if p.scheme=='http' and p.hostname in self.hosts and p.port is None:
            target=urlunsplit(p._replace(scheme='https'))
        self.allowed_url(target)
        return target

    def raw(self, url, delay=1, robots=False, depth=0):
        p = self.allowed_url(url)
        time.sleep(max(0, delay - (time.monotonic()-self.last.get(p.hostname,0))))
        self.last[p.hostname] = time.monotonic()
        try:
            with self.opener.open(Request(quote(url,safe=':/?=&%()'),headers={'User-Agent':AGENT}),timeout=25) as r:
                data=r.read(12_000_001)
                if len(data)>12_000_000: raise ValueError('Response exceeds size limit')
                return data
        except HTTPError as e:
            if robots and e.code in (301,302,303,307,308) and depth<5:
                target=self.redirect_target(url,e.headers.get('Location',''))
                return self.raw(target,delay,robots=True,depth=depth+1)
            raise

    def policy(self, url):
        p=self.allowed_url(url)
        if p.hostname not in self.robots:
            robots='https://'+p.hostname+'/robots.txt'
            try:
                body=self.raw(robots,robots=True).decode('utf-8-sig')
                if body.lstrip().startswith('<'):raise Blocked('robots returned HTML; policy cannot be verified')
                lines=body.splitlines()
            except HTTPError as e:
                if e.code not in (404,410): raise Blocked('robots unavailable: HTTP '+str(e.code))
                lines=['User-agent: *','Allow: /']
            parser=RobotFileParser(robots); parser.parse(lines); self.robots[p.hostname]=parser
        return self.robots[p.hostname]

    def get(self, url, depth=0):
        p=self.allowed_url(url)
        if url in self.cache: return self.cache[url]
        parser=self.policy(url)
        if not parser.can_fetch(AGENT,url): raise Blocked('robots.txt disallows automated access')
        delay=max(1,parser.crawl_delay(AGENT) or parser.crawl_delay('*') or 0)
        try:data=self.raw(url,delay)
        except HTTPError as e:
            if e.code not in (301,302,303,307,308) or depth>=5:raise
            target=self.redirect_target(url,e.headers.get('Location',''))
            # Every redirect destination is checked against official hosts and
            # its own robots policy before the request is sent.
            self.allowed_url(target)
            data=self.get(target,depth+1)
        self.cache[url]=data
        self.requests.append({'url':url,'sha256':hashlib.sha256(data).hexdigest()})
        return data

    def html(self,url):
        from collect_ncaf import Document
        return Document(self.get(url).decode('utf-8-sig')).root
