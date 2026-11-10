import unittest
from unittest.mock import patch
from change_summary import summarize_changes


def page(text):
    return {'index.html': ('<h2>お知らせ</h2><p>' + text + '</p>').encode()}


class ChangeSummaryTests(unittest.TestCase):
    def test_added_sentence_is_short_and_exact(self):
        result = summarize_changes(page('診療しています。'), page('診療しています。土曜は休診です。'))
        self.assertEqual(result['items'], [{'title': 'お知らせ', 'kind': 'added', 'before': '', 'after': '土曜は休診です。'}])

    def test_replacement_and_deletion(self):
        item = summarize_changes(page('18時まで'), page('19時まで'))['items'][0]
        self.assertEqual((item['before'], item['after']), ('18時まで', '19時まで'))
        item = summarize_changes(page('18時まで'), page(''))['items'][0]
        self.assertEqual((item['before'], item['after']), ('18時まで', ''))

    def test_nonvisible_text_is_not_presented_as_content(self):
        changed = {'index.html': b'<script>alert(1)</script><p>&lt;img src=x&gt;</p>'}
        result = summarize_changes({'index.html': b'<p>old</p>'}, changed)
        self.assertEqual(result['items'][0]['after'], '<img src=x>')
        self.assertNotIn('alert', str(result))

    def test_styles_images_and_bounds(self):
        result = summarize_changes({'a.css': b'old'}, {'a.css': b'new', 'b.png': b'image'})
        self.assertEqual([item['after'] for item in result['items']], ['デザインを変更', '画像を追加'])
        result = summarize_changes({}, {str(i)+'.txt': ('長'*200).encode() for i in range(8)})
        self.assertEqual((len(result['items']), result['additional_count']), (5, 3))
        self.assertEqual(len(result['items'][0]['after']), 120)
        self.assertEqual(summarize_changes(page('same'), page('same'))['items'], [])
        self.assertEqual(summarize_changes({}, {'version.json': b'generated'})['items'], [])

    def test_changed_words_remain_visible_inside_long_paragraph(self):
        prefix, suffix = '前文。'*100, '後文。'*100
        item = summarize_changes(page(prefix+'18時まで'+suffix), page(prefix+'19時まで'+suffix))['items'][0]
        self.assertIn('18時まで', item['before'])
        self.assertIn('19時まで', item['after'])
        self.assertLessEqual(len(item['after']), 120)

    def test_large_files_and_many_blocks_do_not_enter_quadratic_diff(self):
        for data in (b'x'*131073, ('<p>text</p>'*501).encode()):
            with self.subTest(size=len(data)), patch('change_summary.SequenceMatcher', side_effect=AssertionError('unbounded diff')):
                result = summarize_changes({}, {'index.html': data})
                self.assertEqual(result['items'][0]['kind'], 'description')
