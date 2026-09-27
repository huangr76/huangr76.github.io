#!/usr/bin/env python3
"""Read-only source verification; render a self-contained, API-free game catalog."""
import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse, quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


class Metadata(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.title = ''
        self.description = ''
        self.feed(text)
        self.title = ' '.join(self.title.split())
        self.description = ' '.join(self.description.split())
        if not self.title or not self.description:
            raise ValueError('HTML must contain a title and meta description')

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'title':
            self.in_title = True
        if tag == 'meta' and attrs.get('name', '').lower() == 'description':
            self.description = attrs.get('content', '')

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


def fetch(url):
    headers = {'User-Agent': 'history-classroom-catalog', 'Accept': '*/*'}
    # Never send a GitHub credential to Pages or raw-content hosts.
    if urlparse(url).hostname == 'api.github.com' and os.environ.get('GITHUB_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    with urlopen(Request(url, headers=headers), timeout=60) as response:
        data = response.read(40 * 1024 * 1024 + 1)
        if len(data) > 40 * 1024 * 1024:
            raise ValueError('Source exceeds 40 MiB: ' + url)
        return data, response.url


def api(path):
    return json.loads(fetch('https://api.github.com/repos/' + path)[0])


def validate_project(project):
    if not re.fullmatch(r'huangr76/[A-Za-z0-9_.-]+', project['repo']):
        raise ValueError('Expected a huangr76 repository')
    if project['theme'] not in ('forest', 'ochre', 'wine'):
        raise ValueError('Unknown card theme')
    if project['art'] not in ('gate', 'manor', 'crown'):
        raise ValueError('Unknown illustration')


def verify_content(source, live):
    source_meta = Metadata(source.decode('utf-8-sig'))
    live_meta = Metadata(live.decode('utf-8-sig'))
    if (source_meta.title, source_meta.description) != (live_meta.title, live_meta.description):
        raise ValueError('Live title/description differs from deployed source')
    if source != live:
        raise ValueError('Live HTML differs from deployed source; inspect deployment before updating')
    return live_meta


def collect(project):
    validate_project(project)
    repo = project['repo']
    meta = api(repo)
    branch = meta['default_branch']
    head = api(repo + '/commits/' + quote(branch, safe=''))['sha']
    runs = api(repo + '/actions/runs?per_page=100')['workflow_runs']
    pages_runs = [r for r in runs if r['head_branch'] == branch and
                  ('pages' in r['name'].lower() or 'pages' in r['path'].lower())]
    if not pages_runs:
        raise ValueError('No Pages workflow found for ' + repo)
    run = max(pages_runs, key=lambda r: r['created_at'])
    if run['status'] != 'completed' or run['conclusion'] != 'success' or run['head_sha'] != head:
        raise ValueError('Latest Pages deployment is unsuccessful, pending, or behind ' + repo)
    # A successful deployment status supplies the published URL; do not infer it from the repo name.
    deployments = api(repo + '/deployments?environment=github-pages&per_page=100')
    deployment = next((d for d in deployments if d['sha'] == head), None)
    if not deployment:
        raise ValueError('No matching github-pages deployment for ' + repo)
    statuses = api(repo + '/deployments/' + str(deployment['id']) + '/statuses')
    if not statuses or statuses[0]['state'] != 'success':
        raise ValueError('Latest deployment status is not successful for ' + repo)
    url = statuses[0].get('environment_url')
    parsed = urlparse(url or '')
    if parsed.scheme != 'https' or parsed.netloc != 'huangr76.github.io':
        raise ValueError('Review unexpected Pages host before publishing: ' + str(url))
    expected_path = '/' + repo.split('/')[1] + '/'
    if parsed.path.rstrip('/') + '/' != expected_path or parsed.query or parsed.fragment:
        raise ValueError('Unexpected Pages path: ' + url)
    url = 'https://huangr76.github.io' + expected_path
    source_url = f'https://raw.githubusercontent.com/{repo}/{head}/index.html'
    source, _ = fetch(source_url)
    live, final_url = fetch(url)
    if final_url != url:
        raise ValueError('Review redirected Pages URL: ' + final_url)
    content = verify_content(source, live)
    return dict(project, title=content.title, description=content.description, url=url,
                source_url=source_url, source_sha=head,
                html_sha256=hashlib.sha256(live).hexdigest(),
                deployment_url=run['html_url'], deployed_at=run['updated_at'],
                deployment_status_url=deployment['statuses_url'])


def render(catalog):
    cards = []
    esc = html.escape
    projects = json.loads((ROOT / 'catalog/projects.json').read_text())
    if len(catalog['games']) != len(projects):
        raise ValueError('Catalog and project list differ; run sync_games.py')
    for i, (g, project) in enumerate(zip(catalog['games'], projects), 1):
        validate_project(g)
        if any(g[k] != v for k, v in project.items()):
            raise ValueError('Catalog configuration is stale; run sync_games.py')
        if not re.fullmatch(r'https://huangr76\.github\.io/[A-Za-z0-9_.-]+/', g['url']):
            raise ValueError('Invalid catalog URL')
        cards.append(f'''<article class="game-card {g['theme']}" aria-labelledby="game-{i}">
  <div class="card-art" aria-hidden="true"><span class="card-number">{i:02d}</span><svg viewBox="0 0 320 170"><use href="assets/hub/illustrations.svg#{g['art']}"></use></svg><span class="art-caption">{esc(g['label'])}</span></div>
  <div class="card-body"><p class="topic">{esc(g['topic'])}</p><h3 id="game-{i}">{esc(g['title'])}</h3>
  <p class="description">{esc(g['description'])}</p><p class="project-id">项目：{esc(g['repo'].split('/')[1])}</p>
  <div class="card-actions"><a class="play-link" href="{esc(g['url'])}" aria-label="开始体验：{esc(g['title'])}（{esc(g['label'])}）">开始体验 <span aria-hidden="true">↗</span></a><button class="copy-link" type="button" data-copy="{esc(g['url'])}" aria-label="复制{esc(g['label'])}链接" hidden>复制链接</button></div></div>
</article>''')
    duplicates = len({g['title'] for g in catalog['games']}) != len(catalog['games'])
    note = '<p class="catalog-note"><span aria-hidden="true">↳</span> 庄园篇的两个项目当前标题与简介相同，已按入口一、入口二区分。请按老师指定的入口进入。</p>' if duplicates else ''
    template = (ROOT / 'templates/index.html').read_text()
    return template.replace('{{CARDS}}', '\n'.join(cards)).replace('{{COUNT}}', str(len(cards))).replace('{{DUPLICATE_NOTE}}', note)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', action='store_true', help='Render from the verified local catalog, without network')
    parser.add_argument('--check', action='store_true', help='Check that committed HTML matches catalog and template')
    args = parser.parse_args()
    catalog_path = ROOT / 'catalog/games.json'
    if args.build or args.check:
        catalog = json.loads(catalog_path.read_text())
    else:
        projects = json.loads((ROOT / 'catalog/projects.json').read_text())
        if len({p['repo'] for p in projects}) != len(projects):
            raise ValueError('Duplicate repository in project list')
        games = []
        for project in projects:
            print('Verifying ' + project['repo'], flush=True)
            games.append(collect(project))
        catalog = {'verified_at': datetime.now(timezone.utc).isoformat(), 'games': games}
    output = render(catalog)
    if args.check:
        if (ROOT / 'index.html').read_text() != output:
            raise ValueError('Generated index.html is stale; run python3 scripts/sync_games.py --build')
        print('Generated HTML matches verified catalog.')
    else:
        # No writes occur until every project has passed verification and rendering.
        if not args.build:
            catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
        (ROOT / 'index.html').write_text(output)
        print('Built ' + str(len(catalog['games'])) + ' cards.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('Catalog update aborted: ' + str(error), file=sys.stderr)
        sys.exit(1)
