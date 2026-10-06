"""Three concrete, always-readable experiences with illustrative motion."""
import json
import struct
from html import escape as e
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = json.loads((ROOT / 'scripts/engineering-experience.json').read_text())
ASSETS = '/assets/engineer-experience/'


def lines(text):
    return '<br>'.join(e(line) for line in text.split('\n'))


def hero(lang):
    c = CONTENT[lang]['heroDemo']
    outputs = ''.join(f'<li><span aria-hidden="true">{i+1:02}</span>{e(item)}</li>' for i,item in enumerate(c['outputs']))
    panels = []
    for side, count in [('before', 2), ('after', 1)]:
        receipts = ''.join(f'<span class="mini-receipt receipt-{i}" aria-hidden="true"><span>✓</span>{e(c['receipt'])}</span>' for i in range(count))
        panels.append(f'''<div class="comparison-side comparison-{side}"><div class="comparison-label">{e(c[side])}<strong>{e(c['countBefore' if side == 'before' else 'countAfter'])}</strong></div><span class="mock-submit" aria-hidden="true">{e(c['submit'])}<span class="click-ring"></span></span><div class="mini-receipts">{receipts}</div><p class="comparison-result">{e(c['duplicate' if side == 'before' else 'protected'])}</p></div>''')
    return f'''<aside class="mission" aria-labelledby="hero-demo-title" data-hero-demo>
      <div class="mission-bar"><b>SIMY</b><span class="preview-label">{e(c['preview'])}</span></div>
      <div class="mission-body"><p class="hero-request"><span aria-hidden="true">↳</span>{e(c['request'])}</p>
      <h2 id="hero-demo-title">{e(c['title'])}</h2><div class="hero-comparison">{''.join(panels)}</div>
      <button type="button" class="hero-replay" data-hero-replay hidden><span aria-hidden="true">↻</span>{e(c['replay'])}</button>
      <p class="hero-process-label">{e(c['label'])}</p><ol class="hero-process">{outputs}</ol><p class="hero-demo-note">{e(c['note'])}</p></div></aside>'''


def experience(lang):
    c = CONTENT[lang]
    sections = []
    for s in c['scenes']:
        frames = []
        steps = []
        for i, f in enumerate(s['frames']):
            raw = (ROOT / 'site' / ASSETS.lstrip('/') / f['image']).read_bytes()
            width, height = struct.unpack('>II', raw[16:24])
            steps.append(f'<button type="button" data-step="{i}" aria-pressed="{str(i == 0).lower()}" aria-controls="demo-{s["id"]}-{i}"><span class="step-number">{i+1:02}</span>{e(f["label"])}<span class="step-track" aria-hidden="true"></span></button>')
            frames.append(f'''<div class="demo-frame" id="demo-{s['id']}-{i}" data-frame="{i}"{' hidden' if i else ''}>
              <div class="screen-window" data-focus="{f['focus']}"><img src="{ASSETS+f['image']}" width="{width}" height="{height}" alt="{e(f['alt'])}" loading="lazy" decoding="async"></div>
              <div class="demo-caption" data-tone="{f['tone']}"><span class="activity-indicator" aria-hidden="true">{'✓' if f['tone'] == 'done' else '?' if f['tone'] == 'decision' else ''}</span><div><h3>{e(f['title'])}</h3><p>{e(f['body'])}</p></div></div>
              <a class="capture-zoom" href="{ASSETS+f['image']}" target="_blank" rel="noopener">{e(c['zoom'])} ↗</a>
            </div>''')
        captions = ''.join(f'<li><strong>{e(f["label"])}</strong> {e(f["title"])} — {e(f["body"])} <a href="{ASSETS+f["image"]}" target="_blank" rel="noopener">{e(c["zoom"])}</a></li>' for f in s['frames'])
        sections.append(f'''<section class="experience-story" id="scene-{s['id']}" aria-labelledby="title-{s['id']}"><div class="frame">
          <div class="story-heading"><span class="story-number">{s['number']}</span><div><p class="eyebrow">{e(s['label'])}</p><h2 id="title-{s['id']}">{lines(s['title'])}</h2></div></div>
          <div class="story-layout"><div class="story-copy"><p class="story-description">{e(s['body'])}</p><div class="request-card"><span class="label">{e(s.get('requestLabel', c['requestLabel']))}</span><p>{e(s['request'])}</p></div><div class="result-card"><span class="label">{e(c['resultLabel'])}</span><p>{e(s['result'])}</p></div><button class="text-button" type="button" data-share="{s['id']}" data-enhancement hidden>{e(c['share'])} ↗</button>
          <p data-share-status role="status"></p><div class="share-fallback" hidden><label for="share-{s['id']}">{e(c['shareLabel'])}</label><input id="share-{s['id']}" readonly type="text"></div></div>
          <div class="animated-capture" data-demo="{s['id']}" data-playing="false"><div class="demo-toolbar"><span>{e(c['animationNote'])}</span><button type="button" class="motion-control" data-motion data-enhancement hidden>{e(c['play'])}</button></div><div class="demo-steps" role="group" aria-label="{e(c['stepLabel'])}" data-enhancement hidden>{''.join(steps)}</div><div class="demo-stage">{''.join(frames)}</div><p class="capture-note">{e(s['note'])}</p><details class="demo-transcript"><summary>{'動きの内容を文章で読む' if lang == 'ja' else 'Read the animation as text'}</summary><ol>{captions}</ol></details></div></div>
        </div></section>''')
    data = json.dumps({k:c[k] for k in ['copied','copyFailed','play','pause','next']}, ensure_ascii=False).replace('<', '\\u003c')
    return f'''<div id="experience" class="experience-stories">{''.join(sections)}</div>
      <script type="application/json" id="experience-data">{data}</script>'''
