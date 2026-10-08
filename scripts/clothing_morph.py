from PIL import Image,ImageDraw,ImageFont,ImageFilter
from pathlib import Path
from functools import lru_cache
import math,numpy as np,subprocess,wave,json,imageio_ffmpeg
# Configured solely from workspace/context.json and a reviewed asset specification.
O=Path.cwd();S=1.;W,H=720,1280;FPS=30;DUR=15;N=4
FONTDIR=Path('.');ims=[];padding_colors=[];logo=None;context={};spec={}
OUTPUT_SIZE=(720,1280)
BASE_DUR=15;BRAND_START=None
BRAND_DARK=(6,15,10);BRAND_CREAM=(248,243,216)
BG=(242,241,236);INK=(34,33,30);GRAY=(123,120,111);WHITE=(253,252,248)
COLORS=[(220,218,210)]*4
@lru_cache(None)
def f(n,serif=False):return ImageFont.truetype(str(FONTDIR/('SourceHanSerifCN-Regular.otf' if serif else 'NotoSansSC.ttf')),round(n*S))
def tx(im,xy,s,n,col=INK,serif=False,center=False):
 d=ImageDraw.Draw(im);x,y=xy;fo=f(n,serif)
 if center:x-=d.textlength(s,font=fo)/S/2
 d.text((round(x*S),round(y*S)),s,font=fo,fill=col)
def smooth(x):x=max(0,min(1,x));return x*x*x*(10+x*(-15+6*x))
def spring(t,w=16):
 if t<=0:return 0
 return 1-(1+w*t)*math.exp(-w*t)
def val(t,base,events,w=16):
 out=base;old=base
 for at,v in events:out+=(v-old)*spring(t-at,w);old=v
 return out
# One persistent surface; every target change adds a continuous spring response.
POSES=[(0,360,648,306,82,41,INK),(.5,360,648,452,98,49,INK),(1,360,655,586,918,28,WHITE),(4,360,655,620,916,30,WHITE),(6.5,360,655,584,918,26,WHITE),(9,360,655,614,912,28,WHITE),(11.5,360,655,628,888,32,WHITE),(13.5,360,650,436,98,49,INK)]
def pose(t):
 values=[]
 for j in range(1,6):values.append(val(t,POSES[0][j],[(p[0],p[j]) for p in POSES[1:]]))
 rgb=[round(val(t,POSES[0][6][j],[(p[0],p[6][j]) for p in POSES[1:]])) for j in range(3)]
 return (*values,tuple(rgb))
def photo(i,w,h,z=1):
 w=max(1,round(w*S));h=max(1,round(h*S));im=ims[i];r=min(w/im.width,h/im.height)*z
 p=im.resize((max(1,round(im.width*r)),max(1,round(im.height*r))),Image.Resampling.LANCZOS)
 c=Image.new('RGB',(w,h),padding_colors[i]);c.paste(p,((w-p.width)//2,(h-p.height)//2));return c
starts=[1,4,6.5,9]
labels=['LOOK 01 · 优雅日常','LOOK 02 · 从容通勤','LOOK 03 · 利落有型','LOOK 04 · 自在出街']
sub=['系带衬衫 / 半裙搭配','西装外套 / 宽松长裤','西装外套 / 长裤搭配','立领外套 / 条纹设计']
def content(mode,w,h,t):
 p=Image.new('RGBA',(max(1,round(w*S)),max(1,round(h*S))),(0,0,0,0));d=ImageDraw.Draw(p)
 if mode==0:
  tx(p,(w/2,h/2-18),'打开今日衣橱',25,WHITE,center=True)
 elif mode==1:
  tx(p,(w/2-78,h/2-14),f'{N}款穿搭' if N!=4 else '四种风格',21,WHITE,center=True)
  for i in range(min(N,8)):
   x=w/2+18+i*min(38,160/max(1,N));tx(p,(x+10,h/2-11),f'{i+1:02d}',12 if N>4 else 15,WHITE,center=True)
 elif 2<=mode<=N+1:
  i=mode-2;pad=16;ph=max(20,h-168)
  p.paste(photo(i,w-pad*2,ph,1+.012*smooth((t-starts[i])/.9)),(round(pad*S),round(pad*S)))
  tx(p,(w/2,h-144),labels[i],31,INK,True,True)
  tx(p,(w/2,h-98),sub[i],17,GRAY,center=True)
 elif mode==N+2:
  tx(p,(w/2,25),'衣橱里的四种可能' if N==4 else '找到你的日常风格',29,INK,True,True)
  gap=14;pad=20;cols=1 if N==1 else 2 if N<=6 else 3;rows=math.ceil(N/cols)
  pw=(w-pad*2-gap*(cols-1))/cols;ph=max(20,(h-162-gap*(rows-1))/rows)
  for i in range(N):
   x=pad+(i%cols)*(pw+gap);y=82+(i//cols)*(ph+gap)
   p.paste(photo(i,pw,ph),(round(x*S),round(y*S)))
   d=ImageDraw.Draw(p);d.rounded_rectangle(tuple(round(v*S) for v in (x+8,y+8,x+44,y+34)),radius=6*S,fill=WHITE)
   tx(p,(x+16,y+10),f'0{i+1}' if i<9 else str(i+1),13)
  tx(p,(w/2,h-50),'找到与你合拍的那一套',21,INK,True,True)
 elif mode==N+3:
  # Small chat mark, drawn with the same stroke as the cursor.
  bx=w/2-150;by=h/2-13
  d.rounded_rectangle(tuple(round(v*S) for v in (bx,by,bx+27,by+23)),radius=6*S,outline=WHITE,width=2)
  d.line(tuple(round(v*S) for v in (bx+6,by+23,bx+3,by+29,bx+13,by+23)),fill=WHITE,width=2)
  tx(p,(w/2+23,h/2-18),'私信咨询 · 尺码搭配',23,WHITE,center=True)
 return p
MODES=[(0,0),(.5,1),(1.03,2),(4.03,3),(6.53,4),(9.03,5),(11.55,6),(13.53,7)]
# Pointer makes the morph causality visible. Independent leading/trailing tab edges stretch slightly.
ptr=[(0,610,865),(.2,420,672),(.5,430,690),(.9,632,1090),(3.55,286,1067),(4.25,636,1113),(6.05,418,1067),(6.8,636,1113),(8.55,550,1067),(9.3,637,1113),(11.08,642,1184),(11.8,644,1130),(13.15,508,1140),(13.8,602,908)]
clicks=[.45,3.98,6.48,8.98,11.48,13.48]
def pointer(c,t):
 x=val(t,ptr[0][1],[(a,x) for a,x,y in ptr[1:]],18);y=val(t,ptr[0][2],[(a,y) for a,x,y in ptr[1:]],18)
 a=1 if t<BASE_DUR-1 else 1-smooth((t-(BASE_DUR-1))/.5)
 l=Image.new('RGBA',(W,H));d=ImageDraw.Draw(l)
 pulse=sum(math.exp(-((t-b)/.06)**2) for b in clicks);sc=1-.16*min(1,pulse)
 pts=[(0,0),(0,24),(6,18),(11,29),(16,26),(11,16),(21,16)]
 ps=[(round((x+dx*sc)*S),round((y+dy*sc)*S)) for dx,dy in pts]
 d.polygon(ps,fill=(*INK,round(255*a)),outline=(*WHITE,round(255*a)),width=round(1.5*S))
 return Image.alpha_composite(c,l)
def frame(t):
 if logo is not None and t>=BRAND_START:return fit_output(brand_frame(t),BRAND_DARK)
 c=Image.new('RGBA',(W,H),(*BG,255));
 tx(c,(45,35),'THE EVERYDAY EDIT',12,GRAY)
 tx(c,(599,35),f'{N:02d} LOOKS',11,GRAY)
 d=ImageDraw.Draw(c);d.line((round(45*S),round(69*S),round(675*S),round(69*S)),fill=(204,200,188),width=1)
 tx(c,(360,105),'日常，自有格调',38,INK,True,True)
 tx(c,(360,165),'A QUIET SENSE OF STYLE',12,GRAY,center=True)
 cx,cy,w,h,r,col=pose(t);x=cx-w/2;y=cy-h/2;wi,hi=round(w*S),round(h*S)
 # Restrained depth, same shadow attached throughout the entire morph.
 sh=Image.new('RGBA',(wi+100,hi+100));sd=ImageDraw.Draw(sh);sd.rounded_rectangle((45,40,wi+55,hi+53),radius=round(r*S),fill=(50,45,35,29));sh=sh.filter(ImageFilter.GaussianBlur(19))
 c.alpha_composite(sh,(round(x*S)-50,round(y*S)-35))
 surf=Image.new('RGBA',(wi,hi),(*col,255))
 k=max(i for i,(a,m) in enumerate(MODES) if t>=a);at,mode=MODES[k];age=t-at
 if k and age<.4:
  # Separate exit and entrance: no doubled faces or overlapping labels.
  if age<.12:
   a=1-smooth(age/.12);layer=content(MODES[k-1][1],w,h,t)
   layer=layer.filter(ImageFilter.GaussianBlur(8*(1-a)))
  else:
   a=smooth((age-.12)/.19);layer=content(mode,w,h,t)
   layer=layer.filter(ImageFilter.GaussianBlur(8*(1-a)))
  layer.putalpha(layer.getchannel('A').point(lambda v:round(v*a)))
 else:layer=content(mode,w,h,t)
 surf=Image.alpha_composite(surf,layer)
 if 1.25<t<END+.15:
  alpha=smooth((t-1.25)/.25)*(1-smooth((t-END)/.15));tl=Image.new('RGBA',(wi,hi));td=ImageDraw.Draw(tl)
  left=26;space=(w-52)/N;yy=h-51
  tab=val(t,0,[(at,i) for i,at in enumerate(starts[1:],1)],19)
  ahead=val(t,0,[(at,i) for i,at in enumerate(starts[1:],1)],23)
  xl=left+tab*space;xr=left+(ahead+1)*space-6
  td.rounded_rectangle(tuple(round(v*S) for v in (xl,yy,xr,yy+35)),radius=round(17*S),fill=(224,220,210,round(255*alpha)))
  for i in range(N):tx(tl,(left+(i+.5)*space-3,yy+5),f'LOOK {i+1:02d}' if N<=4 else f'{i+1:02d}',15,(*INK,round(255*alpha)),center=True)
  surf=Image.alpha_composite(surf,tl)
 mask=Image.new('L',(wi,hi));ImageDraw.Draw(mask).rounded_rectangle((0,0,wi-1,hi-1),radius=round(r*S),fill=255);surf.putalpha(mask)
 c.alpha_composite(surf,(round(x*S),round(y*S)))
 foot=('点击，发现适合你的风格' if t<1 else ('四种风格 · 自在切换' if N==4 else '日常穿搭 · 自在切换') if t<END else '喜欢哪一套？私信聊聊' if t<END+2 else '从通勤，到自在日常')
 tx(c,(360,1180),foot,20,GRAY,True,True)
 if 1<t<END:
  # Persistent progress line communicates a collection, not fabricated stock data.
  d=ImageDraw.Draw(c);d.line(tuple(round(v*S) for v in (308,1240,412,1240)),fill=(209,204,193),width=2)
  d.line(tuple(round(v*S) for v in (308,1240,308+104*min(1,(t-1)/(END-1)),1240)),fill=INK,width=2)
 c=pointer(c,t)
 return fit_output(c)

def fit_output(c,background=BG):
 c=c.convert('RGB')
 if c.size!=OUTPUT_SIZE:
  out=Image.new('RGB',OUTPUT_SIZE,background);out.paste(c,((out.width-c.width)//2,(out.height-c.height)//2));return out
 return c

def fade(layer,a):
 layer=layer.copy();layer.putalpha(layer.getchannel('A').point(lambda v:round(v*max(0,min(1,a)))));return layer

def brand_frame(t):
 """Retained V5 outro: same surface, source-logo contain, no generated branding."""
 u=t-BRAND_START;q=smooth((u-.16)/1.14);p0=pose(BRAND_START)
 # Wide source matches the approved 648px-wide card. Tall marks stay in frame.
 lw=min(648,460*logo.width/logo.height);lh=lw*logo.height/logo.width
 target=(360,625,lw,lh,12)
 cx,cy,w,h,r=[a+(b-a)*q for a,b in zip(p0[:5],target)]
 bgq=smooth((u-.34)/1.08);bg=tuple(round(a+(b-a)*bgq) for a,b in zip(BG,BRAND_DARK))
 c=Image.new('RGBA',(W,H),(*bg,255));chrome=Image.new('RGBA',(W,H))
 tx(chrome,(45,35),'THE EVERYDAY EDIT',12,GRAY);tx(chrome,(599,35),f'{N:02d} LOOKS',11,GRAY)
 ImageDraw.Draw(chrome).line((round(45*S),round(69*S),round(675*S),round(69*S)),fill=(204,200,188),width=1)
 tx(chrome,(360,105),'日常，自有格调',38,INK,True,True);tx(chrome,(360,165),'A QUIET SENSE OF STYLE',12,GRAY,center=True)
 tx(chrome,(360,1180),'从通勤，到自在日常',20,GRAY,True,True)
 c=Image.alpha_composite(c,fade(chrome,1-smooth(u/.6)))
 wi,hi=max(1,round(w*S)),max(1,round(h*S));x=round((cx-w/2)*S);y=round((cy-h/2)*S)
 sh=Image.new('RGBA',(wi+100,hi+100));ImageDraw.Draw(sh).rounded_rectangle((45,40,wi+55,hi+53),radius=round(r*S),fill=(50,45,35,round(29*(1-bgq))));sh=sh.filter(ImageFilter.GaussianBlur(19));c.alpha_composite(sh,(x-50,y-35))
 shell=tuple(round(a+(b-a)*q) for a,b in zip(p0[5],BRAND_DARK));surf=Image.new('RGBA',(wi,hi),(*shell,255))
 olda=1-smooth(u/.34)
 if olda>0:surf=Image.alpha_composite(surf,fade(content(N+3,w,h,t),olda))
 la=smooth((u-.44)/.65)
 if la>0:
  scale=min(wi/logo.width,hi/logo.height);size=(max(1,round(logo.width*scale)),max(1,round(logo.height*scale)))
  mark=fade(logo.resize(size,Image.Resampling.LANCZOS),la);surf.alpha_composite(mark,((wi-mark.width)//2,(hi-mark.height)//2))
 mask=Image.new('L',(wi,hi));ImageDraw.Draw(mask).rounded_rectangle((0,0,wi-1,hi-1),radius=round(r*S),fill=255);surf.putalpha(mask);c.alpha_composite(surf,(x,y))
 a=smooth((u-1.2)/.55);txt=Image.new('RGBA',(W,H));dy=10*(1-a)
 # Wide baseline retains y=826. Taller logos move the caption below the image.
 caption_y=max(826,625+lh/2+76)
 tx(txt,(360,caption_y+dy),'私信咨询 · 尺码与搭配',22,BRAND_CREAM,True,True)
 ImageDraw.Draw(txt).line((round(329*S),round((caption_y+63+dy)*S),round(391*S),round((caption_y+63+dy)*S)),fill=(*BRAND_CREAM,150),width=1)
 return Image.alpha_composite(c,fade(txt,a))

def make_audio():
 sr=48000;ts=np.arange(sr*DUR)/sr;v=np.zeros_like(ts);rng=np.random.default_rng(21)
 for i,beat in enumerate(np.arange(0,BASE_DUR,.5)):
  q=ts-beat;m=(q>=0)&(q<.3);xx=q[m];v[m]+=.12*np.sin(2*np.pi*(48*xx+1.3*(1-np.exp(-30*xx))))*np.exp(-20*xx)
  ff=[130.81,110,87.31,98][(i//4)%4];v[m]+=.045*np.sin(2*np.pi*ff*xx)*np.exp(-8*xx)
 for i,beat in enumerate(np.arange(0,BASE_DUR-.2,.25)):
  q=ts-beat;m=(q>=0)&(q<.07);xx=q[m];v[m]+=.011*rng.normal(size=len(xx))*np.exp(-60*xx)
 for i,beat in enumerate(np.arange(0,BASE_DUR,2)):
  for j,ff in enumerate([[261.63,329.63,493.88],[220,261.63,392],[174.61,261.63,329.63],[196,293.66,392]][i%4]):
   q=ts-beat-j*.025;m=(q>=0)&(q<2.5);xx=q[m];v[m]+=.037*np.sin(2*np.pi*ff*xx+.3*np.sin(2*np.pi*ff*2*xx)*np.exp(-5*xx))*(1-np.exp(-60*xx))*np.exp(-2*xx)
 for beat in clicks:
  q=ts-beat;m=(q>=0)&(q<.04);xx=q[m];v[m]+=.025*np.sin(2*np.pi*1350*xx)*np.exp(-160*xx)
 if logo is not None:
  for j,ff in enumerate([130.81,261.63,329.63,392,493.88]):
   q=ts-(BASE_DUR+.5)-j*.025;m=(q>=0)&(q<2.5);xx=q[m];v[m]+=.027*np.sin(2*np.pi*ff*xx+.25*np.sin(2*np.pi*ff*2*xx)*np.exp(-4*xx))*(1-np.exp(-55*xx))*np.exp(-1.4*xx)
 v*=np.minimum(ts/.07,1)*np.clip((DUR-ts)/(1.1 if logo is not None else .65),0,1)
 with wave.open(str(O/'tmp/music.wav'),'wb') as f1:f1.setnchannels(2);f1.setsampwidth(2);f1.setframerate(sr);f1.writeframes((np.column_stack([v,v])*32767).astype('<i2').tobytes())

CATEGORIES={'shirt-skirt':'系带衬衫 / 半裙搭配','suit-trousers':'西装外套 / 宽松长裤',
            'suit':'西装外套 / 长裤搭配','track-jacket':'立领外套 / 条纹设计','garment':'日常穿搭'}
TAGLINES=['优雅日常','从容通勤','利落有型','自在出街']

def configure(workspace, settings):
 """Asset identities are validated against the current project, never filenames."""
 global O,S,W,H,FPS,DUR,N,FONTDIR,ims,padding_colors,logo,context,spec,OUTPUT_SIZE,END,POSES,MODES,starts,labels,sub,ptr,clicks,BASE_DUR,BRAND_START
 O=Path(workspace).resolve();context=json.loads((O/'context.json').read_text('utf-8'));spec=settings
 assets={a['id']:a for a in context['assets']}
 def asset(aid, brand=False):
  a=assets.get(aid)
  if not a or a['kind']!='image' or a['role'] not in (('brand',) if brand else ('material',)):raise ValueError('只能使用当前项目的画面图片素材')
  return a
 looks=spec.get('looks',[]);N=len(looks)
 if not 1<=N<=12:raise ValueError('需1至12款服装；没有服装或需要拆片时请先确认')
 if len({look['asset_id'] for look in looks})!=N:raise ValueError('同一主图不可重复冒充不同款式')
 classified=spec.get('classification',[])
 if len({a.get('asset_id') for a in classified})!=len(classified):raise ValueError('素材分类重复')
 if {a.get('asset_id') for a in classified}!=set(assets):raise ValueError('必须逐张分类当前全部素材，包括参考图和Logo')
 roles={a['asset_id']:a.get('role') for a in classified}
 allowed_roles={'garment','detail','duplicate','logo','store','poster','other','reference'}
 if set(roles.values())-allowed_roles:raise ValueError('素材分类无效')
 if any(roles.get(l['asset_id'])!='garment' for l in looks):raise ValueError('款式主图必须分类为garment，不能使用Logo或店铺图')
 if {l['asset_id'] for l in looks}!={aid for aid,r in roles.items() if r=='garment'}:raise ValueError('不能遗漏已识别的款式主图')
 for item in classified:
  if item['role'] not in ('garment','logo') and not str(item.get('reason','')).strip():raise ValueError('未展示素材需要分类理由')
 brand_ids=[a['id'] for a in assets.values() if a['kind']=='image' and a['role']=='brand']
 logo_id=spec.get('logo_asset_id')
 if not logo_id and len(brand_ids)==1:logo_id=brand_ids[0]
 if not logo_id and len(brand_ids)>1:raise ValueError('上传了多个品牌图片，请选择片尾使用的品牌图片')
 if logo_id:
  asset(logo_id,brand=True)
  if roles.get(logo_id)!='logo':raise ValueError('品牌图片必须单独分类为logo，不得列为服装LOOK')
  if logo_id not in brand_ids:raise ValueError('片尾只能使用当前上传的品牌图片')
 spec={**settings,'logo_asset_id':logo_id}
 extra=3 if logo_id else 0
 DUR=float(spec.get('duration',max(10,3*N+3)+extra));BASE_DUR=DUR-extra
 if not math.isfinite(DUR) or not N*2.4+4.5<=BASE_DUR or DUR>300:raise ValueError('片长不足以清晰展示所有款式及品牌片尾；请确认增加时长或分组，不得省略款式')
 END=BASE_DUR-3.5;BRAND_START=BASE_DUR-.5 if logo_id else None
 fps=int(context['target']['fps']);edge=int(context['target']['short_edge'])
 FPS=fps
 if fps not in (30,60) or edge not in (720,1080):raise ValueError('遵守项目preview/final档位')
 aspect=context['aspect'];rx,ry=map(int,aspect.split(':'))
 OUTPUT_SIZE=(2*round(edge*rx/min(rx,ry)/2),2*round(edge*ry/min(rx,ry)/2))
 S=min(OUTPUT_SIZE[0]/720,OUTPUT_SIZE[1]/1280);W,H=round(720*S),round(1280*S)
 FONTDIR=Path(context['fonts']);f.cache_clear()
 from PIL import ImageOps
 ims=[];padding_colors=[]
 for look in looks:
  a=asset(look['asset_id']);image=ImageOps.exif_transpose(Image.open(a['original'])).convert('RGBA')
  if 'crop' in look:
   crop=look['crop']
   if len(crop)!=4 or any(not isinstance(v,(float,int)) or not math.isfinite(v) for v in crop) or not 0<=crop[0]<crop[2]<=1 or not 0<=crop[1]<crop[3]<=1:raise ValueError('裁切须是0至1的有效归一化边界')
   if not look.get('crop_reason'):raise ValueError('裁切需注明主体安全理由，默认不裁切')
   image=image.crop(tuple(round(v*(image.width if i%2==0 else image.height)) for i,v in enumerate(crop)))
  if min(image.size)<2:raise ValueError('裁切图片过小')
  corner=image.getpixel((0,0));padding_colors.append(corner[:3] if corner[3] else BG)
  matte=Image.new('RGBA',image.size,(*BG,255));matte.alpha_composite(image);ims.append(matte.convert('RGB'))
  if look.get('category','garment') not in CATEGORIES:raise ValueError('服装类型不确定时使用garment')
 labels=[f'LOOK {i+1:02d} · '+TAGLINES[i%4] for i in range(N)]
 sub=[CATEGORIES[l.get('category','garment')] for l in looks]
 logo=None
 if logo_id:
  aid=logo_id;a=asset(aid, brand=True)
  if roles.get(aid)!='logo':raise ValueError('Logo必须单独分类为logo')
  logo=ImageOps.exif_transpose(Image.open(a['original'])).convert('RGBA')
 base=(BASE_DUR-5)/N;starts=[1]+[1+.5+i*base for i in range(1,N)]
 widths=[586,620,584,614];heights=[918,916,918,912];radii=[28,30,26,28]
 POSES=[(0,360,648,306,82,41,INK),(.5,360,648,452,98,49,INK)]
 POSES += [(at,360,655,widths[i%4],heights[i%4],radii[i%4],WHITE) for i,at in enumerate(starts)]
 POSES += [(END,360,655,628,888,32,WHITE),(END+2,360,650,436,98,49,INK)]
 MODES=[(0,0),(.5,1)]+[(at+.03,i+2) for i,at in enumerate(starts)]+[(END+.05,N+2),(END+2.03,N+3)]
 ptr=[(0,610,865),(.2,420,672),(.5,430,690),(.9,632,1090)]
 for i,at in enumerate(starts[1:],1):
  prevw=widths[(i-1)%4];xx=360-prevw/2+26+(i+.5)*(prevw-52)/N
  ptr.extend([(at-.45,xx,1067),(at+.3,636,1113)])
 ptr += [(END-.42,642,1184),(END+.3,644,1130),(END+1.65,508,1140),(END+2.3,602,908)]
 clicks=[.45]+[at-.02 for at in starts[1:]]+[END-.02,END+1.98]
 (O/'tmp').mkdir(exist_ok=True);(O/'artifacts').mkdir(exist_ok=True)
 return {'title':'日常，自有格调','summary':f'{N}款服装，连续容器形变与编号切换；不生成颜色描述。'+('含上传品牌图片的连续形变片尾。' if logo is not None else ''),
         'duration':DUR,'chapters':[{'start':0,'title':'打开今日衣橱'}]+[{'start':at,'title':f'LOOK {i+1:02d}'} for i,at in enumerate(starts)]+[{'start':END,'title':'款式合集'},{'start':END+2,'title':'咨询'}]+([{'start':BRAND_START,'title':'品牌展示'}] if logo is not None else []),
         'used_asset_ids':[l['asset_id'] for l in looks]+([spec['logo_asset_id']] if logo is not None else []),
         'review_notes':'基于固定 clothing-morph-v1 动效；每款清晰展示至少约2秒；没有图片生成或颜色识别。'+('品牌片尾复用V5认可效果，按原图比例和透明通道展示。' if logo is not None else '未上传品牌图片，不生成品牌片尾。')}

def main():
 import argparse,os,time
 parser=argparse.ArgumentParser();parser.add_argument('--workspace',type=Path,default=Path.cwd());parser.add_argument('--spec',type=Path,default=Path('src/clothing-spec.json'));parser.add_argument('--keyframes',action='store_true');args=parser.parse_args()
 sp=args.spec if args.spec.is_absolute() else args.workspace/args.spec
 manifest=configure(args.workspace,json.loads(sp.read_text('utf-8')))
 def save(path,data):
  tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),'utf-8');tmp.replace(path)
 save(O/'tmp/manifest-draft.json',manifest)
 times=[0,.8]+[min(END-.05,at+.8) for at in starts]+[END+1,END+2.9]+([DUR-1] if logo is not None else [])
 board=Image.new('RGB',(4*270,math.ceil(len(times)/4)*480),BG)
 for i,t in enumerate(times):
  thumb=frame(t);thumb.thumbnail((270,480));board.paste(thumb,(i%4*270+(270-thumb.width)//2,i//4*480+(480-thumb.height)//2))
 board.save(O/'tmp/keyframes.jpg');frame(END+1).save(O/'artifacts/poster.jpg')
 seams=[1,starts[1] if N>1 else END,END+2]+([BRAND_START] if logo is not None else [])
 board=Image.new('RGB',(4*270,len(seams)*480),BG)
 for row,at in enumerate(seams):
  for col,dt in enumerate([-.05,.1,.3,.65]):
   thumb=frame(min(DUR-.02,at+dt));thumb.thumbnail((270,480));board.paste(thumb,(col*270,row*480))
 board.save(O/'tmp/transitions.jpg')
 if args.keyframes:return
 make_audio();out=O/'artifacts/video.next.mp4';ff=context['ffmpeg'];last=0
 command=[ff,'-y','-v','error','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s',f'{OUTPUT_SIZE[0]}x{OUTPUT_SIZE[1]}','-r',str(FPS),'-i','-']
 if spec.get('music',True):command+=['-i',str(O/'tmp/music.wav'),'-c:a','aac','-ar','48000','-b:a','192k','-af','loudnorm=I=-17:TP=-1.5:LRA=9']
 command+=['-c:v','libx264','-preset','fast','-crf','18' if FPS==60 else '20','-pix_fmt','yuv420p','-t',str(DUR),'-movflags','+faststart',str(out)]
 total=round(FPS*DUR)
 with (O/'tmp/encode.log').open('wb') as log:
  proc=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=log)
  try:
   for n in range(total):
    t=n/FPS;im=frame(t)
    if any(0<t-p[0]<.7 for p in POSES[1:]) or (logo is not None and BRAND_START<t<BRAND_START+1.8):
     for j in range(1,4):im=Image.blend(im,frame(t+j/(FPS*8)),1/(j+1))
    proc.stdin.write(im.tobytes())
    if time.monotonic()-last>=1:
     save(O/'tmp/render-progress.json',{'frame':n+1,'total_frames':total});last=time.monotonic()
   proc.stdin.close()
   if proc.wait(timeout=60):raise ValueError('编码失败，请查看tmp/encode.log')
  finally:
   if proc.poll() is None:proc.kill();proc.wait()
 out.replace(O/'artifacts/video.mp4');save(O/'tmp/render-progress.json',{'frame':total,'total_frames':total})
 print(json.dumps({'video':'artifacts/video.mp4','manifest_draft':'tmp/manifest-draft.json','notice':'由独立运行器完成校验并交付。'},ensure_ascii=False))

if __name__=='__main__':main()
