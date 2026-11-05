"""Illustrative FP deal-health review, adapted from cited Salesforce guidance."""

from financial_planner_locale import translator

def section(lang):
    t = translator(lang)
    # Red = an explicit concern; amber = missing or stale information, not a lost deal.
    checks = [
        ('need', 'green', ('確認済み', 'Confirmed'), ('相談したいニーズ', 'Client needs'),
         ('住宅と教育費を、一緒に考えたい。', 'Wants to plan for housing and education together.'),
         ('面談メモ 12:40「住宅購入と教育費を一緒に考えたい」', 'Meeting note 12:40: “I want to plan for a home and education together.”'),
         ('どちらを先に準備すると、安心につながりますか？', 'Which goal would you like to prepare for first?')),
        ('budget', 'red', ('赤信号', 'Red flag'), ('予算・月額負担', 'Budget & monthly commitment'),
         ('これ以上の負担は難しい、という発言。', 'The client says a higher monthly commitment would be difficult.'),
         ('面談メモ 18:20「毎月の負担を増やすのは難しいです」', 'Meeting note 18:20: “It would be difficult to increase our monthly commitments.”'),
         ('今の暮らしを保つために、毎月いくらを残したいですか？', 'How much would you like to keep available each month for your daily life?')),
        ('decision', 'red', ('赤信号', 'Red flag'), ('意思決定者・ご家族の合意', 'Decision-makers & family agreement'),
         ('一緒に決める配偶者が、まだ納得していない。', 'The partner who shares the decision is not yet comfortable.'),
         ('面談メモ 22:10「妻とは一緒に決めますが、まだ納得していません」', 'Meeting note 22:10: “My wife and I decide together, but she isn’t comfortable yet.”'),
         ('奥さまは、どの点を気にされていますか？', 'What is your partner most concerned about?')),
        ('timing', 'amber', ('要確認', 'To confirm'), ('時期・判断条件', 'Timing & decision criteria'),
         ('購入時期と、比較して決める基準が未確認。', 'The target date and comparison criteria have not been confirmed.'),
         ('面談記録：住宅購入の時期・比較条件の記載なし', 'Meeting record: no entry for the home purchase date or comparison criteria.'),
         ('いつ頃までに、何が分かれば判断できそうですか？', 'By when would you like to decide, and what would you need to know?')),
        ('engagement', 'amber', ('要確認', 'To confirm'), ('連絡・商談の停滞', 'Engagement & stalled progress'),
         ('前回の面談後、追加のやりとりが記録されていない。', 'No further conversation is recorded after the last meeting.'),
         ('活動履歴：前回面談以降の連絡記録なし。実施状況は要確認', 'Activity history: no contact logged since the last meeting. Actual contact needs checking.'),
         ('その後のご状況に変化はありますか？', 'Has anything changed since we last spoke?')),
        ('next-step', 'amber', ('要確認', 'To confirm'), ('次の行動・担当・期限', 'Next action, owner & due date'),
         ('「また連絡する」のまま、担当と日付が未設定。', '“Follow up later” has no assigned owner or date.'),
         ('次回アクション欄：担当者・期限の登録なし', 'Next-action record: no owner or due date entered.'),
         ('どなたに、いつ頃、どの方法でご連絡しましょうか？', 'Who should we contact, when, and by which method?')),
    ]
    checks.sort(key=lambda c: {"red": 0, "amber": 1, "green": 2}[c[1]])
    cards = []
    for key, tone, state, title, observation, source, question in checks:
        cards.append(f'''<article class="risk-card" data-risk="{key}" data-state="{tone}">
          <div class="risk-card-heading"><h4>{t(*title)}</h4><span class="badge {tone}">{t(*state)}</span></div>
          <p class="risk-observation">{t(*observation)}</p>
          <details class="risk-evidence"{' open' if tone == 'red' else ''}><summary>{t('根拠と、次に聞く問い','Evidence and a question to ask')}</summary>
            <dl><dt>{t('根拠の例','Example evidence')}</dt><dd>{t(*source)}</dd><dt>{t('次に聞く問い','Next question')}</dt><dd>{t(*question)}</dd></dl>
          </details></article>''')
    counts = {tone: sum(c[1] == tone for c in checks) for tone in ('red','amber','green')}
    badges = ''.join(f'<span class="badge {tone}">{t(*label)} {counts[tone]}</span>' for tone, label in [('red',('赤信号','Red flags')),('amber',('要確認','To confirm')),('green',('確認済み','Confirmed'))])
    return f'''<section class="fp-story risk-story" id="red-flags"><div class="fp-frame">
      <div class="story-top"><span class="story-number">02</span><div><p class="eyebrow">{t('営業の赤信号を把握','SPOT SALES RED FLAGS')}</p>
        <h2>{t('見逃していた赤信号を、<br>次に聞く問いへ。','Turn warning signs<br>into your next good question.')}</h2></div></div>
      <div class="story-intro"><p>{t('Salesforceの商談管理の考え方をベースに、FPの相談を6つの観点で確認。面談で表れた懸念や、確認が抜けていることを整理し、提案前に立ち止まるポイントを示します。','Drawing on Salesforce’s approach to opportunity management, review an FP consultation through six adapted checks. Bring client concerns and missing information into view before moving to a proposal.')}</p>
        <div class="request"><small>{t('たとえば、こんな依頼','TRY A REQUEST LIKE THIS')}</small><p>{t('「この面談の赤信号は？ 根拠と、次に聞くこと、誰がいつ動くかをまとめて」','“What are the red flags in this consultation? Show the evidence, what to ask next, and who should act by when.”')}</p></div></div>
      <div class="app-screen risk-screen"><div class="app-bar"><b><img src="/favicon-32.png" width="22" height="22" alt=""> SIMY</b><span>{t('商談の確認','Consultation review')}</span><span class="badge">{t('画面イメージ','Illustrative UI')}</span></div>
        <div class="risk-body"><div class="risk-overview"><div><p class="ui-kicker">{t('佐藤さま / 意向確認中','SATO FAMILY / UNDERSTANDING NEEDS')}</p><h3>{t('今は、提案よりも確認を。','Clarify first. Then prepare the proposal.')}</h3></div><div class="risk-counts">{badges}</div></div>
        <p class="risk-legend">{t('赤信号＝発言から懸念を把握。要確認＝情報が未確認・更新待ち。どちらも失注の断定ではありません。','Red flag: a concern expressed by the client. To confirm: missing or outdated information. Neither means the opportunity is lost.')}</p>
        <div class="risk-grid">{''.join(cards)}</div>
        <div class="risk-followup"><div><p class="ui-kicker">{t('次の行動案 / 担当FPの確認待ち','PROPOSED NEXT ACTION / ADVISOR REVIEW NEEDED')}</p><h4>{t('月々の負担と、ご家族の意向を確認する。','Clarify monthly commitments and each partner’s priorities.')}</h4><p>{t('担当：担当FP　／　実施候補：次回面談の前日まで。連絡先・日程はお客さまと合意してから確定。','Owner: assigned FP. Proposed timing: by the day before the next meeting. Confirm the contact and timing with the client before scheduling.')}</p></div><a class="text-link" href="#roleplay">{t('この問いをiOSで練習する','Practice these questions on iOS')} ↓</a></div>
        <p class="risk-gate">{t('提案に進む前に：月額負担・ご家族の合意・比較条件を担当FPが再確認。必要に応じて先輩や上司へ相談します。','Before progressing: the FP rechecks affordability, family agreement and comparison criteria, and consults a colleague or manager when needed.')}</p>
      </div></div><p class="visual-caption">{t('架空のお客さま・説明用の画面です。営業担当者の確認を支援する例であり、成約確率や適合性を自動判定するものではありません。','Fictional client and illustrative screen. This example supports an advisor’s review; it does not automatically determine close probability or suitability.')}</p>
      <details class="risk-method"><summary>{t('評価の考え方と参考資料','Assessment approach and references')}</summary><p>{t('ニーズ・予算・意思決定者・時期は、Salesforceが紹介するBANTの観点をFP向けに言い換えています。連絡の停滞と次の行動は、商談の進行状況を確認する考え方を加えたものです。6項目と表示例はFP相談向けの構成です。','Needs, budget, decision-makers and timing adapt the BANT dimensions described by Salesforce. Engagement and next actions add a review of progress. The six checks and examples are tailored here to FP consultations.')}</p><ul>
        <li><a href="https://trailhead.salesforce.com/{"ja/" if lang == "ja" else ""}content/learn/modules/opportunity-management/manage-opportunities-to-close-deals">Salesforce Trailhead — {t('商談管理と赤信号','Opportunity management and warning signs')}</a></li>
        <li><a href="https://trailhead.salesforce.com/content/learn/modules/lead-qualification-quick-look/get-to-know-lead-qualification">Salesforce Trailhead — {t('見込み客評価（BANT等）','Lead qualification, including BANT')}</a></li>
        <li><a href="https://www.salesforce.com/sales/pipeline/management/">Salesforce — {t('商談の停滞と次の行動','Pipeline progress and next steps')}</a></li>
      </ul></details></div></section>'''
