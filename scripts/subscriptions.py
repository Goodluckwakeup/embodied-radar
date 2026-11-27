"""Bounded subscriptions to verified official publication indexes."""
import datetime as dt
from html.parser import HTMLParser
import re
import urllib.parse
import xml.etree.ElementTree as ET

ATOM = '{http://www.w3.org/2005/Atom}'


class PaperLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        if tag != 'a':
            return
        url = dict(attrs).get('href', '')
        parsed = urllib.parse.urlsplit(url)
        if parsed.hostname not in ('arxiv.org', 'www.arxiv.org'):
            return
        match = re.match(r'^/(?:abs|pdf)/(\d{4}\.\d{4,5})(?:v\d+)?(?:\.pdf)?/?$', parsed.path)
        if match:
            self.ids.add(match[1])


def official_papers(spec, cutoff, fetch, make_article):
    parser = PaperLinks()
    parser.feed(fetch(spec['url']).decode('utf-8', errors='replace'))
    if not parser.ids:
        raise ValueError('官方索引没有可识别的论文链接')
    # arXiv IDs sort chronologically. Actual dates are verified below.
    ids = sorted(parser.ids, reverse=True)[:60]
    result = []
    for start in range(0, len(ids), 30):
        query = urllib.parse.urlencode({'id_list': ','.join(ids[start:start+30]), 'max_results': 30})
        root = ET.fromstring(fetch('https://export.arxiv.org/api/query?' + query))
        if root.find(ATOM+'error') is not None:
            raise ValueError('arXiv 返回错误')
        for entry in root.findall(ATOM+'entry'):
            url = entry.findtext(ATOM+'id', '')
            if '/api/errors' in url:
                raise ValueError('arXiv 查询失败')
            published = entry.findtext(ATOM+'published')
            updated = entry.findtext(ATOM+'updated')
            stamp = dt.datetime.fromisoformat((updated or published or '').replace('Z', '+00:00'))
            if stamp < cutoff:
                continue
            row = make_article(entry.findtext(ATOM+'title', ''), url,
                               entry.findtext(ATOM+'summary', ''), 'arXiv', '论文', published, updated,
                               [author.findtext(ATOM+'name', '') for author in entry.findall(ATOM+'author')], '论文摘要')
            if row:
                row['official_sources'] = [spec['name']]
                result.append(row)
    return result
