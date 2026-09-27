"""Run in CI after installing Playwright; screenshots are uploaded as artifacts."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results'
OUT.mkdir(exist_ok=True)
server = ThreadingHTTPServer(('127.0.0.1', 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT)))
Thread(target=server.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{server.server_port}/'

try:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        errors = []
        for width in [320, 390, 768, 1280, 1440]:
            context = browser.new_context(viewport={'width': width, 'height': 900}, device_scale_factor=1)
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(url, wait_until='networkidle')
            page.screenshot(path=str(OUT / f'home-{width}.png'), full_page=True)
            assert page.locator('.game-card').count() == 3
            overflow = page.evaluate('''() => Array.from(document.querySelectorAll('body *'))
                .filter(el => {const r = el.getBoundingClientRect(); return r.width && (r.right > innerWidth || r.left < 0);})
                .map(el => ({tag: el.tagName, class: el.className, right: el.getBoundingClientRect().right}))''')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Overflow at {width}: {overflow}'
            for link in page.locator('.play-link').all():
                assert link.is_visible() and link.bounding_box()['height'] >= 44
            boxes = [card.bounding_box() for card in page.locator('.game-card').all()]
            if width <= 760:
                assert boxes[1]['y'] >= boxes[0]['y'] + boxes[0]['height']
            else:
                assert len({round(box['y']) for box in boxes}) == 1
            page.get_by_role('button', name='分享入口').click()
            assert page.locator('#share-dialog').is_visible()
            assert page.locator('.qr-code').evaluate('(image) => image.complete && image.naturalWidth > 0')
            if width == 390:
                page.screenshot(path=str(OUT / 'share-mobile.png'))
            page.keyboard.press('Escape')
            assert not page.locator('#share-dialog').is_visible()
            assert page.locator('.share-trigger').evaluate('(el) => el === document.activeElement')
            context.close()

        # Clipboard denial must offer a usable manual copy field.
        context = browser.new_context()
        context.add_init_script("Object.defineProperty(navigator, 'clipboard', {value: {writeText: () => Promise.reject(new Error('denied'))}})")
        page = context.new_page()
        page.goto(url)
        page.get_by_role('button', name='复制庄园篇 · 入口一链接').click()
        assert page.locator('#copy-dialog').is_visible()
        assert page.locator('#manual-url').input_value() == 'https://huangr76.github.io/chuzhongshiji-siqi/'
        page.keyboard.press('Escape')
        context.close()

        context = browser.new_context(permissions=['clipboard-read', 'clipboard-write'])
        page = context.new_page()
        page.goto(url)
        page.get_by_role('button', name='复制庄园篇 · 入口二链接').click()
        page.get_by_text('链接已复制，可以发给学生。', exact=True).wait_for()
        assert page.evaluate('navigator.clipboard.readText()') == 'https://huangr76.github.io/siqi-manor-escape/'
        context.close()

        # All three game links remain usable if JavaScript is unavailable.
        context = browser.new_context(java_script_enabled=False)
        page = context.new_page()
        page.goto(url)
        assert all(link.is_visible() for link in page.locator('.play-link').all())
        assert page.locator('.play-link').count() == 3
        assert not page.locator('.share-trigger').is_visible()
        context.close()
        assert not errors, errors
        browser.close()
        print('Five viewports, sharing, clipboard success/fallback, and no-JS navigation passed.')
finally:
    server.shutdown()
