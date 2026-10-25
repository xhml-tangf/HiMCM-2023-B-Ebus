"""Render every manuscript page and check automatic layout invariants."""
from pathlib import Path
import fitz,json,re,subprocess,shutil
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
PDF=ROOT/'paper/claude_plan/charging_ahead_claude_plan.pdf'
OUT=ROOT/'tmp/claude_pdf';OUT.mkdir(exist_ok=True,parents=True)
doc=fitz.open(PDF);plan=json.loads((ROOT/'results/claude_plan/manuscript_page_plan.json').read_text())
errors=[];normalize=lambda s:re.sub(r'\s+',' ',s).strip().casefold()
if len(doc)!=len(plan):errors.append(f'{len(doc)} actual pages vs {len(plan)} planned')
for n,page in enumerate(doc):
    text=normalize(page.get_text())
    if n<len(plan) and normalize(plan[n]['title']) not in text:errors.append(f'page {n+1}: expected title missing')
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines',[]):
            for span in line['spans']:
                x0,y0,x1,y1=span['bbox']
                if x0<50 or x1>560 or y0<8 or y1>835:errors.append(f'page {n+1}: text outside safe margins {span["text"][:40]}')
                if '\ufffd' in span['text'] or '\u25a0' in span['text']:errors.append(f'page {n+1}: replacement glyph')
if shutil.which('pdftoppm') is None:errors.append('Poppler pdftoppm unavailable')
else:
    for old in OUT.glob('page-*.png'):old.unlink()
    subprocess.run(['pdftoppm','-png','-r','110',str(PDF),str(OUT/'page')],check=True)
for start in range(0,len(doc),8):
    sheet=Image.new('RGB',(4*340,2*465),'#cbd5da');draw=ImageDraw.Draw(sheet)
    for k in range(start,min(start+8,len(doc))):
        with Image.open(OUT/f'page-{k+1:02d}.png') as page:
            page.thumbnail((330,435));x=((k-start)%4)*340+5;y=((k-start)//4)*465+22
            sheet.paste(page,(x,y));draw.text((x,y-18),f'Page {k+1}',fill='black')
    sheet.save(OUT/f'contact_{start//8+1}.jpg',quality=90)
result=dict(actual_pages=len(doc),solution_pages=len(doc)-1,planned_pages=len(plan),within_25_solution_pages=len(doc)-1<=25,
            automatic_layout_pass=not errors,errors=errors,visual_review_status='pending human-visible image inspection')
(ROOT/'results/claude_plan/pdf_quality.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
