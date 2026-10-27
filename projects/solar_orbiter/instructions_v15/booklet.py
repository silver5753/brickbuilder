"""Compact presentation of the unchanged verified release; requires reportlab/Pillow."""
from pathlib import Path
import argparse,base64,html,json,io
from PIL import Image,ImageChops
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
p=argparse.ArgumentParser();p.add_argument('--release',type=Path,required=True);p.add_argument('--thumbnails',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
r=json.loads((a.release/'instructions/instructions.json').read_text())['steps'];a.output.mkdir(parents=True,exist_ok=True)
mapping={(x['part'],x['colour']):x for x in json.loads((a.thumbnails/'mapping.json').read_text())}
unresolved={i for x in json.loads((a.release/'connections.json').read_text())['nominal']['assemblies'] for i in x['unreachable_instance_ids']}
for name,file in [('Regular','DejaVuSans.ttf'),('Bold','DejaVuSans-Bold.ttf')]:pdfmetrics.registerFont(TTFont(name,'/usr/share/fonts/truetype/dejavu/'+file))
W,H=595.28,841.89;ink='#172638';muted='#526273'
c=canvas.Canvas(str(a.output/'Solar-Orbiter-v15-Building-Instructions.pdf'),pagesize=(W,H));c.setTitle('Solar Orbiter v15 — visual building instructions')
cache={}
def asset(path,small=False):
 key=(str(path),small)
 if key not in cache:
  im=Image.open(path).convert('RGB');im=im.crop((0,42 if small else 52,im.width,im.height-(32 if small else 42)))
  bg=Image.new('RGB',im.size,(242,241,237));diff=ImageChops.difference(im,bg).convert('L').point(lambda x:255 if x>15 else 0);box=diff.getbbox()
  if box:im=im.crop((max(0,box[0]-8),max(0,box[1]-8),min(im.width,box[2]+8),min(im.height,box[3]+8)))
  # Only replace exact renderer background; preserve all part colours and shading.
  im.putdata([(255,255,255) if x==(242,241,237) else x for x in im.getdata()])
  b=io.BytesIO();im.save(b,format='PNG');cache[key]=(im,'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode())
 return cache[key]
def pic(path,x,y,w,h,small=False):
 im,_=asset(path,small);scale=min(w/im.width,h/im.height);ww,hh=im.width*scale,im.height*scale;c.drawImage(ImageReader(im),x+(w-ww)/2,y+(h-hh)/2,ww,hh)
def para(text,x,top,w,size=9,bold=False):
 s=ParagraphStyle('s',fontName='Bold' if bold else 'Regular',fontSize=size,leading=size*1.3,textColor=HexColor(ink));q=Paragraph(html.escape(text),s);_,h=q.wrap(w,1000);q.drawOn(c,x,top-h);return h
page=1
pages=[]
def footer():
 c.setStrokeColor(HexColor('#dde2e6'));c.line(28,32,W-28,32);c.setFillColor(HexColor(muted));c.setFont('Regular',7);c.drawString(28,20,'SOLAR ORBITER V15  •  DRAFT / PHYSICAL BUILD UNTESTED');c.drawRightString(W-28,20,str(page))
def end(body):
 global page
 footer();c.showPage();pages.append('<section class="page">'+body+f'<footer>Solar Orbiter v15 · Draft / physical build untested <span>{page}</span></footer></section>');page+=1
def img(path,small=False,cls=''):
 return '<img class="'+cls+'" src="'+asset(path,small)[1]+'">'
para('SOLAR ORBITER',32,790,530,30,True);para('Visual building instructions',32,743,530,19);para('121 steps  /  966 parts  /  2 steps per page',32,708,530,11)
pic(a.release/'render/hero.png',28,300,539,370)
intro='Pick parts by the small pictures in their real colours. In the assembly diagrams, gold shows new parts and grey shows earlier parts. Overview checkpoints appear at least every six steps and after major additions.'
limits='Trial-build draft: 18 of 966 parts have unresolved connection paths. Part 7798 is shown with an approximate shape (*). Physical assembly, access and strength remain untested.'
para(intro,32,265,530,11);para(limits,32,173,530,10)
end('<h1>SOLAR ORBITER</h1><h2>Visual building instructions</h2><p>121 steps · 966 parts · 2 steps per page</p>'+img(a.release/'render/hero.png',cls='hero')+'<p>'+intro+'</p><p>'+limits+'</p>')
para('Read the pictures',32,793,530,25,True)
notes=['The parts tray shows only the pieces added in that step. Pictures use native LDraw colours; quantities are prominent and part numbers are secondary references. Pictures are not to scale.', 'The large diagram focuses on the current assembly. Surrounding parts may be hidden to expose a joint; they have not been removed. At checkpoints, the small overview locates the assembly in the whole model.', 'The diagrams show final positions, not an exploded insertion path. Follow the notes for support and preassembly. Keep wings and the science boom supported; do not force connections.', 'An asterisk marks the approximate 7798 thumbnail. Optional solar stickers are not illustrated. Record trial-build problems against the step number in the supplied feedback form.']
y=743
for t in notes:y-=para(t,32,y,530,11)+18
starts=['Front frame rails','Front cradle cross rails','Roof mounts: left','Left equipment: upper front backing','Close the underside','HIS mounting standoffs','Left wing yoke','Boom left inner rail and splice']
labels=['Body frame','Cradle and display stand','Concealed mounts and axles','Side equipment','Covers and rear panel','Instruments and heat shield','Wings and solar panels','Science boom, dish and antennas']
y-=10;para('Guide map',32,y,530,16,True);y-=33;index=[]
for title,label in zip(starts,labels):
 n=next(i+1 for i,s in enumerate(r) if s['title']==title);line=f'{n:03d}   {label}';para(line,32,y,530,11);y-=25;index.append(line)
end('<h1>Read the pictures</h1>'+''.join('<p>'+t+'</p>' for t in notes)+'<h2>Guide map</h2>'+''.join('<p class="index">'+t+'</p>' for t in index))
checkpoints=[];last=0
for n in range(1,len(r)+1):
 if n-last>=6 or n in {6,16,30,48,59,73,91,109,116,118,121}:checkpoints.append(n);last=n
for base in range(0,len(r),2):
 bodies=[]
 for slot,row in enumerate(r[base:base+2]):
  n=base+slot+1;bottom=439 if slot==0 else 51;top=bottom+356
  c.bookmarkPage(row['id']);c.addOutlineEntry(f'{n:03d} {row["title"]}',row['id'],0)
  para(str(n),28,top,72,24,True);para(row['title'],105,top-3,462,12,True)
  c.setFillColor(HexColor('#f1f4f6'));c.roundRect(28,top-101,539,63,5,fill=1,stroke=0)
  tray=[];cell=539/max(6,len(row['inventory']))
  for k,q in enumerate(row['inventory']):
   part,colour=q['native']['part'],q['native']['colour'];m=mapping[(part,colour)];path=a.thumbnails/'renders'/m['image'];x=28+k*cell;label=part+('*' if m['approximate'] else '')
   pic(path,x+7,top-82,55,39,True);para(str(q['quantity'])+'×',x+63,top-52,25,10,True);para(label,x+7,top-86,76,7)
   tray.append('<div class="piece">'+img(path,True)+f'<b>{q["quantity"]}×</b><small>{label}</small></div>')
  detail=a.release/'instructions'/row['id']/'views/detail.png';overview=a.release/'instructions'/row['id']/'views/overview.png'
  if n in checkpoints:
   pic(detail,28,bottom+64,365,181);pic(overview,402,bottom+79,165,151);para('MODEL CHECKPOINT',402,bottom+69,165,7,True)
  else:pic(detail,28,bottom+64,539,181)
  note=row['callouts'][0]['text']
  if unresolved.intersection(row['added_ids']):note+=' Check: unresolved connection path in this step.'
  height=para(note,28,bottom+53,539,8.5);assert height<=53,(n,height)
  bodies.append(f'<article><header><strong>{n}</strong><h2>{html.escape(row["title"])}</h2></header><div class="tray">'+''.join(tray)+'</div><div class="diagrams">'+img(detail,cls='detail')+('<div class="overview">'+img(overview)+'<small>MODEL CHECKPOINT</small></div>' if n in checkpoints else '')+'</div><p class="note">'+html.escape(note)+'</p></article>')
 if base==120:
  pic(a.release/'render/hero.png',80,110,435,240);para('Completed model — support the wings and boom',32,390,530,14,True);bodies.append('<article><h2>Completed model</h2>'+img(a.release/'render/hero.png',cls='hero')+'</article>')
 c.setStrokeColor(HexColor('#dde2e6'));c.line(28,427,567,427);end(''.join(bodies))
c.save()
css='''@page{size:A4;margin:0}*{box-sizing:border-box}body{margin:0;background:#e5e7eb;color:#172638;font:11pt Arial,sans-serif}.page{width:210mm;height:297mm;padding:16mm 10mm 18mm;margin:12px auto;background:white;position:relative;break-after:page}h1{font-size:28pt}h2{font-size:16pt}p{line-height:1.4}.index{margin:7px 0}footer{position:absolute;bottom:7mm;left:10mm;right:10mm;font-size:7pt;border-top:1px solid #ddd;padding-top:3mm}footer span{float:right}.hero{width:100%;height:125mm;object-fit:contain}article{height:133mm;padding:0 0 5mm}article+article{border-top:1px solid #ddd;padding-top:5mm}header{display:flex;align-items:center;gap:6mm;height:13mm}header strong{font-size:25pt}header h2{font-size:12pt}.tray{height:23mm;display:flex;background:#f1f4f6;border-radius:4px;padding:2mm}.piece{width:16.66%;position:relative;padding-right:6mm}.piece img{width:100%;height:14mm;object-fit:contain}.piece b{position:absolute;right:1mm;top:4mm;font-size:10pt}.piece small{display:block;font-size:7pt}.diagrams{height:70mm;display:flex;gap:3mm;padding-top:3mm}.detail{width:100%;min-width:0;object-fit:contain}.diagrams:has(.overview) .detail{width:68%}.overview{width:32%;display:flex;flex-direction:column;justify-content:center}.overview img{width:100%;height:57mm;object-fit:contain}.overview small{font-size:7pt;text-align:center}.note{font-size:8.5pt;margin:2mm 0}article .hero{height:100mm}@media print{body{background:white}.page{margin:0}}'''
(a.output/'Solar-Orbiter-v15-Building-Instructions.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Solar Orbiter visual building instructions</title><style>'+css+'</style>'+''.join(pages)+'</html>')
(a.output/'presentation-record.json').write_text(json.dumps({'steps':len(r),'parts':sum(len(x['added_ids']) for x in r),'pages':len(pages),'checkpoints':checkpoints,'unique_native_part_colours':len(mapping),'approximate_thumbnail_parts':['7798'],'source_release':'solar-orbiter-instructions-v15','inspiration':'https://www.lego.com/cdn/product-assets/product.bi.core.pdf/6327401.pdf (ISS 21321, PDF page 90); visual layout only, no artwork reused'},indent=2))
print(f'Created {len(pages)} pages, {len(checkpoints)} checkpoints, {len(mapping)} thumbnail identities.')
