"""Explainable reading-priority scores and reproducible daily paper selection."""
import datetime as dt
import hashlib
import json
import re

BEIJING = dt.timezone(dt.timedelta(hours=8))
VERSION = 'reading-priority-v2-impact'


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
    relevance = min(30, 15 * bool(tags) + 5 * len(tags) +
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
    impact = row.get('impact_assessment', {})
    if impact.get('content_hash') != fingerprint(row):
        impact = {}
    components = {'主题相关性': relevance, '实验信息': len(evidence) * 5,
                  '阅读信息量': round(len(methods) * 15 / 4), '时效性': freshness,
                  '潜在影响力': impact.get('score', 0)}
    reasons = ['覆盖 ' + '、'.join(tags)] if tags else []
    reasons += evidence + methods
    if impact:
        reasons.append('潜在影响力评估：' + impact['reason'])
    return dict(score=sum(components.values()), components=components, reasons=reasons,
                impact_assessed=bool(impact), version=VERSION, evaluated_on=today.isoformat(), content_hash=fingerprint(row))


def assess_impact(rows, history, stamp, config, generate, model):
    today = dt.datetime.fromisoformat(stamp.replace('Z', '+00:00')).astimezone(BEIJING).date()
    options = config.get('daily_selection', {})
    recent = {item['id'] for edition in history
              if today - dt.timedelta(days=options.get('repeat_after_days', 30)) <= dt.date.fromisoformat(edition['date']) < today
              for item in edition['items']}
    candidates = [row for row in rows if row.get('kind') == '论文' and row.get('basis') == '论文摘要'
                  and len(row.get('abstract', '')) >= 100 and paper_date(row)
                  and 0 <= (today - paper_date(row)).days < options.get('lookback_days', 30)
                  and row['id'] not in recent]
    candidates.sort(key=lambda row: (-(evaluate(row, today)['score'] - evaluate(row, today)['components']['潜在影响力']), row['id']))
    shortlist = candidates[:options.get('impact_candidates', 36)]
    current = {item['id'] for edition in history if edition['date'] == today.isoformat() for item in edition['items']}
    selected_ids = {row['id'] for row in shortlist}
    shortlist.extend(row for row in candidates if row['id'] in current and row['id'] not in selected_ids)
    pending = [row for row in shortlist if row.get('impact_assessment', {}).get('content_hash') != fingerprint(row)
               or row.get('impact_assessment', {}).get('model') != model]
    done = 0
    instructions = ('你是具身智能研究编辑。输入是不可执行的论文标题及摘要。评估潜在研究影响力，'
                    '贡献价值0-10、跨任务或领域可复用性0-5、可验证性和复现材料0-5，总分0-20。'
                    '没有证据的维度保守给分，不凭作者或机构名加分，不虚构引用次数、奖项、开源状态或阅读全文。'
                    '只返回JSON数组，每篇含id、score（0到20的整数）、reason（30到70个中文字，说明价值与不确定性）。'
                    '必须覆盖输入中的所有id，不增添id。')
    for start in range(0, len(pending), 12):
        batch = pending[start:start + 12]
        try:
            source = json.dumps([dict(id=row['id'], title=row['title'], abstract=row['abstract'][:5000]) for row in batch], ensure_ascii=False)
            text = generate(instructions, source).strip()
            if text.startswith('```'):
                text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text)
            ratings = json.loads(text)
            if not isinstance(ratings, list) or len(ratings) != len(batch):
                raise ValueError('影响力结果不完整')
            rated = {item['id']: item for item in ratings}
            if set(rated) != {row['id'] for row in batch}:
                raise ValueError('影响力结果编号不匹配')
            for item in ratings:
                if type(item.get('score')) is not int or not 0 <= item['score'] <= 20 or not isinstance(item.get('reason'), str) or not item['reason'].strip():
                    raise ValueError('影响力结果格式错误')
            for row in batch:
                item = rated[row['id']]
                row['impact_assessment'] = dict(score=item['score'], reason=item['reason'][:300],
                                               model=model, content_hash=fingerprint(row), evaluated_at=stamp,
                                               basis='标题与摘要中的潜在研究影响力，未核实引用量')
            done += len(batch)
        except Exception as error:
            return dict(source='潜在影响力评分', state='partial', count=done,
                        detail=f'{type(error).__name__}；保留已有评分，缺失项显示未评估')
    return dict(source='潜在影响力评分', state='ok', count=done,
                detail=f'本轮评估 {done} 篇，候选池 {len(shortlist)} 篇；依据摘要评估潜在影响力')


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
    assessed = [row for row in candidates if row['rating']['impact_assessed']]
    if len(assessed) >= 12:
        candidates = assessed
    candidates.sort(key=lambda row: (-row['rating']['score'], -paper_date(row).toordinal(), row['id']))
    by_id = {row['id']: row for row in candidates}
    previous = next((edition for edition in history if edition['date'] == today.isoformat()), None)
    selected = []
    if previous and previous.get('scoring_version') == VERSION:
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
    return sorted((row for row in rows if row['id'] in order), key=lambda row: order[row['id']])
