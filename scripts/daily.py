"""Explainable reading-priority scores and reproducible daily paper selection."""
import datetime as dt
import hashlib
import re

BEIJING = dt.timezone(dt.timedelta(hours=8))
VERSION = 'reading-priority-v1'


def paper_date(row):
    for field in ('published_at', 'updated_at'):
        try:
            value = dt.datetime.fromisoformat((row.get(field) or '').replace('Z', '+00:00'))
            return value.replace(tzinfo=value.tzinfo or dt.timezone.utc).astimezone(BEIJING).date()
        except ValueError:
            continue
    return None


def fingerprint(row):
    return hashlib.sha256((row['title'] + '\n' + row.get('abstract', '')).encode()).hexdigest()


def evaluate(row, today):
    text = (row['title'] + ' ' + row.get('abstract', '')).lower().replace('-', ' ')
    tags = row.get('topics', [])
    relevance = min(40, 25 * bool(tags) + 5 * len(tags) +
                    10 * bool(re.search(r'robot|manipulation|locomotion|embodied', text)))
    evidence_checks = [
        ('真实机器人实验线索', r'real world|real robot|physical robot|hardware experiment'),
        ('基准或对照实验线索', r'benchmark|baseline|compar(?:e|ison)|ablation'),
        ('定量结果线索', r'\d+(?:\.\d+)?\s*(?:%|percent|tasks|robots|environments)'),
        ('泛化评估线索', r'generaliz|unseen|out.of.distribution|cross.embodiment'),
    ]
    evidence = [label for label, pattern in evidence_checks if re.search(pattern, text)]
    method_checks = [
        ('方法描述', r'propos|introduc|framework|algorithm|architecture'),
        ('实现或数据线索', r'code|open source|dataset|github|release'),
        ('局限或分析线索', r'limitation|failure|analysis|trade.off|ablation'),
        ('任务描述', r'manipulation|grasp|navigation|locomotion|assembly|dexter'),
    ]
    methods = [label for label, pattern in method_checks if re.search(pattern, text)]
    published = paper_date(row)
    age = (today - published).days if published else None
    freshness = 0
    if age is not None and age >= 0:
        for days, points in ((3, 15), (7, 12), (14, 7), (30, 3)):
            if age <= days:
                freshness = points
                break
    components = {'主题相关性': relevance, '实验信息': len(evidence) * 6 + int(len(evidence) == 4),
                  '阅读信息量': len(methods) * 5, '时效性': freshness}
    reasons = ['覆盖 ' + '、'.join(tags)] if tags else []
    reasons += evidence + methods
    return dict(score=sum(components.values()), components=components, reasons=reasons,
                version=VERSION, evaluated_on=today.isoformat(), content_hash=fingerprint(row))


def build_edition(rows, history, stamp, config):
    today = dt.datetime.fromisoformat(stamp.replace('Z', '+00:00')).astimezone(BEIJING).date()
    options = config.get('daily_selection', {})
    window = options.get('lookback_days', 30)
    cooldown = options.get('repeat_after_days', 30)
    recent = [edition for edition in history if
              today - dt.timedelta(days=cooldown) <= dt.date.fromisoformat(edition['date']) < today]
    used = {item['id'] for edition in recent for item in edition['items']}
    candidates = []
    for row in rows:
        if row.get('kind') != '论文' or row.get('basis') != '论文摘要':
            continue
        row['rating'] = evaluate(row, today)
        published = paper_date(row)
        if (published and 0 <= (today - published).days < window and
                len(row.get('abstract', '').strip()) >= 100 and row['id'] not in used):
            candidates.append(row)
    candidates.sort(key=lambda row: (-row['rating']['score'], -paper_date(row).toordinal(), row['id']))
    by_id = {row['id']: row for row in candidates}
    previous = next((edition for edition in history if edition['date'] == today.isoformat()), None)
    selected = []
    if previous:
        for item in previous['items']:
            row = by_id.get(item['id'])
            if row and fingerprint(row) == item['content_hash']:
                selected.append(row)
    chosen = {row['id'] for row in selected}
    # Reruns preserve today's order and fill missing slots without duplicates.
    selected.extend(row for row in candidates if row['id'] not in chosen)
    selected = selected[:12]
    items = [dict(id=row['id'], content_hash=fingerprint(row),
                  reading='deep' if index < 2 else 'skim', rating=row['rating'])
             for index, row in enumerate(selected)]
    return dict(date=today.isoformat(), generated_at=stamp, items=items,
                candidate_count=len(candidates), lookback_days=window,
                repeat_after_days=cooldown, target=12, scoring_version=VERSION)


def finish_edition(data, edition):
    rows = {row['id']: row for row in data['articles']}
    for item in edition['items']:
        row = rows[item['id']]
        # Preserve a readable historical edition when source records are revised.
        item['article'] = {key: row.get(key) for key in
                           ('title', 'title_zh', 'url', 'topics', 'published_at', 'summary_zh', 'abstract', 'basis')}
    count = sum(bool(item['article'].get('summary_zh')) for item in edition['items'])
    edition['summary_count'] = count
    edition['state'] = 'complete' if len(edition['items']) == 12 and count == 12 else 'partial'
    data['daily_editions'] = sorted(
        [e for e in data.get('daily_editions', []) if e['date'] != edition['date']] + [edition],
        key=lambda e: e['date'], reverse=True)[:60]


def prioritize(rows, edition):
    order = {item['id']: index for index, item in enumerate(edition['items'])}
    return sorted(rows, key=lambda row: order.get(row['id'], len(order)))
