import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sync', ROOT / 'scripts/sync_games.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


class CatalogTests(unittest.TestCase):
    def test_live_drift_is_rejected_even_if_metadata_matches(self):
        source = b'<title>Game</title><meta name="description" content="Learn"><body>v1</body>'
        with self.assertRaisesRegex(ValueError, 'Live HTML differs'):
            sync.verify_content(source, source.replace(b'v1', b'v2'))

    def test_title_drift_and_missing_description_are_rejected(self):
        source = b'<title>Game</title><meta name="description" content="Learn">'
        with self.assertRaisesRegex(ValueError, 'title/description differs'):
            sync.verify_content(source, source.replace(b'Game', b'Changed'))
        with self.assertRaises(ValueError):
            sync.Metadata('<title>Game</title>')

    def test_pending_or_stale_pages_deployment_is_rejected(self):
        project = json.loads((ROOT / 'catalog/projects.json').read_text())[0]
        for status, conclusion, sha in [('in_progress', None, 'current'), ('completed', 'failure', 'current'), ('completed', 'success', 'old')]:
            responses = [{'default_branch': 'main'}, {'sha': 'current'}, {'workflow_runs': [{
                'head_branch': 'main', 'name': 'Deploy to GitHub Pages', 'path': '.github/workflows/pages.yml',
                'status': status, 'conclusion': conclusion, 'head_sha': sha, 'created_at': '2026-09-15T00:00:00Z'}]}]
            with patch.object(sync, 'api', side_effect=responses):
                with self.assertRaisesRegex(ValueError, 'unsuccessful, pending, or behind'):
                    sync.collect(project)

    def test_render_escapes_metadata_and_rejects_unsafe_url(self):
        catalog = json.loads((ROOT / 'catalog/games.json').read_text())
        catalog['games'][0]['title'] = '<script>alert("x")</script>'
        output = sync.render(catalog)
        self.assertIn('&lt;script&gt;', output)
        self.assertNotIn('<script>alert', output)
        catalog['games'][0]['url'] = 'javascript:alert(1)'
        with self.assertRaisesRegex(ValueError, 'Invalid catalog URL'):
            sync.render(catalog)

    def test_committed_page_matches_verified_catalog(self):
        catalog = json.loads((ROOT / 'catalog/games.json').read_text())
        self.assertEqual(sync.render(catalog), (ROOT / 'index.html').read_text())
        self.assertEqual(len(catalog['games']), len({g['url'] for g in catalog['games']}))


if __name__ == '__main__':
    unittest.main()
