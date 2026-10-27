from pathlib import Path
from dataclasses import replace
import json
from brickbuilder.ldraw import dumps,from_model,read_source,PartLibrary
from brickbuilder.model import Model,PartInstance
from brickbuilder.rendering import render_bundle
from brickbuilder.rendering.config import load_config,View
import argparse
p=argparse.ArgumentParser();p.add_argument('--release',type=Path,required=True);p.add_argument('--library',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=Path(__file__).resolve().parents[3];out=a.output;out.mkdir(parents=True,exist_ok=True)
r=json.loads((a.release/'instructions/instructions.json').read_text())
keys=sorted({(q['native']['part'],q['native']['colour']) for s in r['steps'] for q in s['inventory']})
parts=[];views=[];mapping=[]
for n,(part,colour) in enumerate(keys):
 name=f'part_{n:03d}';parts.append(PartInstance(name,part+'.dat',colour,group=name))
 views.append(View(name,(-0.7,-1,-1.3),groups=(name,)))
 mapping.append(dict(part=part,colour=colour,image=name+'.png',approximate=part=='7798'))
(out/'parts.ldr').write_text(dumps(from_model(Model(tuple(parts)),title='Native-colour part thumbnails; isolated view per identity')))
config,_=load_config(root/'projects/solar_orbiter/instructions_v15/render_config.json')
config=replace(config,views=tuple(views),width=400,height=320,padding=0.18,supersampling=2)
render_bundle(read_source(out/'parts.ldr'),PartLibrary((a.library,),missing=json.loads((root/'projects/solar_orbiter/geometry_exceptions.json').read_text())),config,a.library/'LDConfig.ldr',out/'renders')
(out/'mapping.json').write_text(json.dumps(mapping,indent=2))
print('Rendered',len(keys),'native part/colour thumbnails.')
