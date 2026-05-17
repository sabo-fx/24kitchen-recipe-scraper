from pypdf import PdfReader
r = PdfReader('tmp/empanada-test.pdf')
n = len(r.pages)
print('total pages:', n)
for i, p in enumerate(r.pages, 1):
    t = p.extract_text() or ''
    expected = f'Page {i} of {n}'
    print(f'page {i}: {expected!r} -> ' + ('FOUND' if expected in t else 'MISSING'))
    print('---tail---')
    print(t[-300:])
    print('---end---')
