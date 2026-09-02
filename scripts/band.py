"""Compose the activity band (dartboard, Deadpool, three darts, thought
bubbles, the section title) on top of the freshly generated stats card and
write activity-light.svg / activity-dark.svg. Called by scripts/update.py;
can also be run on its own after editing the scene.

Sources live in assets/ (deadpool.png, dart-board.png, dart.png, Lucide
icons). The bullseye and the dart tip are located from the pixels, so
swapping the images keeps the hit on the red centre.
"""
import re, pathlib, base64, struct, zlib, math
ROOT = pathlib.Path(__file__).resolve().parent.parent
L = ROOT/'assets/lucide'
def inner(name):
    s = re.sub(r'<!--.*?-->', '', (L/f'{name}.svg').read_text(), flags=re.S)
    return re.search(r'<svg[^>]*>\s*(.*?)\s*</svg>', s, re.S).group(1).replace('\n',' ')
def png_rgba(f):
    d=pathlib.Path(f).read_bytes(); pos=8; idat=b''
    while pos<len(d):
        ln=struct.unpack('>I',d[pos:pos+4])[0]; t=d[pos+4:pos+8]; body=d[pos+8:pos+8+ln]
        if t==b'IHDR': w,h,bd,ct=struct.unpack('>IIBB',body[:10])
        if t==b'IDAT': idat+=body
        pos+=12+ln
    raw=zlib.decompress(idat); bpp=4; stride=w*bpp; rows=[]; prev=bytearray(stride); p=0
    for y in range(h):
        f=raw[p]; p+=1; line=bytearray(raw[p:p+stride]); p+=stride
        for i in range(stride):
            a=line[i-bpp] if i>=bpp else 0; b=prev[i]; c=prev[i-bpp] if i>=bpp else 0
            if f==1: line[i]=(line[i]+a)&255
            elif f==2: line[i]=(line[i]+b)&255
            elif f==3: line[i]=(line[i]+(a+b)//2)&255
            elif f==4:
                pa=abs(b-c); pb=abs(a-c); pc=abs(a+b-2*c); line[i]=(line[i]+(a if pa<=pb and pa<=pc else b if pb<=pc else c))&255
        rows.append(bytes(line)); prev=line
    return w,h,rows
def dims(f): return struct.unpack('>II', pathlib.Path(f).read_bytes()[16:24])
def b64(f): return base64.b64encode(pathlib.Path(f).read_bytes()).decode()

# ---- bullseye: centroid of red pixels near the board centre
bw,bh,brows=png_rgba(ROOT/'assets/dart-board.png')
xs=[];ys=[]
for y in range(int(bh*.35),int(bh*.65)):
    for x in range(int(bw*.4),int(bw*.75)):
        r,g,b,a=brows[y][x*4:x*4+4]
        if a>200 and r>170 and g<80 and b<80: xs.append(x); ys.append(y)
cx,cy=sum(xs)/len(xs),sum(ys)/len(ys)
for _ in range(3):
    r=bw*0.05; sel=[(x,y) for x,y in zip(xs,ys) if (x-cx)**2+(y-cy)**2<r*r]
    cx,cy=sum(x for x,_ in sel)/len(sel),sum(y for _,y in sel)/len(sel)
BULL=(cx/bw, cy/bh); print('bullseye rel',round(BULL[0],3),round(BULL[1],3),'from',len(sel),'px')
# dart tip: rightmost opaque column of the dart PNG and its vertical centre
dw_,dh_,drows=png_rgba(ROOT/'assets/dart.png')
tipx=max(x for y in range(dh_) for x in range(dw_) if drows[y][x*4+3]>60)
tipys=[y for y in range(dh_) if drows[y][tipx*4+3]>60 or drows[y][(tipx-2)*4+3]>60]
TIP_REL=(tipx/dw_, sum(tipys)/len(tipys)/dh_); print('dart tip rel',round(TIP_REL[0],3),round(TIP_REL[1],3))
# figure + dart dims
fw,fh=dims(ROOT/'assets/deadpool.png'); dw,dh=dims(ROOT/'assets/dart.png')

W=766; BH=103; CARD_H=190
TITLE=True
OUT='activity'
FIG_W=94; FIG_H=round(FIG_W*fh/fw); FIG_X=W-FIG_W; FIG_Y=BH-FIG_H   # figure bottom on the card top
BOARD_H=68; BOARD_W=round(BOARD_H*bw/bh); BOARD_X=10; BOARD_Y=BH-BOARD_H   # board bottom on the card top, like the figure
BULL_X=BOARD_X+BULL[0]*BOARD_W; BULL_Y=BOARD_Y+BULL[1]*BOARD_H
MOUTH_X=FIG_X+0.42*FIG_W; MOUTH_Y=FIG_Y+0.36*FIG_H
DART_H=7; DART_W=round(DART_H*dw/dh)
print('figure',FIG_X,FIG_Y,FIG_W,FIG_H,'board',BOARD_X,BOARD_Y,BOARD_W,BOARD_H,'bull',round(BULL_X),round(BULL_Y),'mouth',round(MOUTH_X),round(MOUTH_Y),'dart',DART_W,DART_H)

FONT='-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif'
def pop(x,y,rot,delay,body):
    return f'''<g transform="translate({x} {y}) rotate({rot})" opacity="0"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;.05;.16;.62;.74;1" dur="5.4s" begin="{delay}s" repeatCount="indefinite"/>
<g><animateTransform attributeName="transform" type="scale" values=".4;1.22;1;1;.75;.4" keyTimes="0;.12;.2;.62;.74;1" dur="5.4s" begin="{delay}s" repeatCount="indefinite" additive="sum"/>
<animateTransform attributeName="transform" type="rotate" values="-10;6;0;0;-4;-10" keyTimes="0;.12;.2;.62;.74;1" dur="5.4s" begin="{delay}s" repeatCount="indefinite" additive="sum"/>
{body}</g></g>'''
def glyph(ch,size,fill,outline,ow):
    return f'<text x="0" y="0" text-anchor="middle" dominant-baseline="central" font-family="{FONT}" font-size="{size}" font-weight="900" fill="{fill}" stroke="{outline}" stroke-width="{ow}" stroke-linejoin="round" paint-order="stroke">{ch}</text>'
def licon(name,color,px,outline,ow):
    return f'<g transform="translate({-px/2} {-px/2}) scale({px/24})"><g fill="none" stroke="{outline}" stroke-width="{2+ow*24/px}" stroke-linecap="round" stroke-linejoin="round">{inner(name)}</g><g fill="none" stroke="{color}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">{inner(name)}</g></g>'

def band(theme):
    outline='#1f2933' if theme=='light' else '#0d1117'; ow=1.25 if theme=='light' else 1.5
    blue='#3B82F6' if theme=='light' else '#79b8ff'; yel='#E0A93A' if theme=='light' else '#F2C94C'; red='#EF4444' if theme=='light' else '#ff7b72'
    headx=FIG_X+0.465*FIG_W; headtop=FIG_Y
    pops=[pop(headx-17, headtop-4, -16, 0.0, glyph('?',12.5,blue,outline,ow)),
          pop(headx+1, headtop-8, 0, 1.8, licon('lightbulb',yel,11,outline,ow)),
          pop(headx+17, headtop-4, 16, 3.6, glyph('!',12,red,outline,ow))]
    # dart: tip at local (0,0); image flipped so the tip points left
    dart=f'<image href="data:image/png;base64,{b64(ROOT/"assets/dart.png")}" x="0" y="{-DART_H/2}" width="{DART_W}" height="{DART_H}" transform="scale(-1 1) translate({-DART_W} 0)"/>'
    halo='#ffffff'
    # unflipped dart: tip at the local origin, body trailing to -x, so rotate="auto" points the tip along the flight path
    dart=f'<g filter="url(#dhalo)"><image href="data:image/png;base64,{b64(ROOT/"assets/dart.png")}" x="{-DART_W*TIP_REL[0]:.2f}" y="{-DART_H*TIP_REL[1]:.2f}" width="{DART_W}" height="{DART_H}"/></g>'
    # start fully behind the figure at chest height; a catapult arc: steep up, over the apex, landing ~10 degrees nose-down on the bullseye
    sx,sy=FIG_X+0.34*FIG_W, FIG_Y+0.46*FIG_H; ex,ey=BULL_X,BULL_Y
    T=10.0
    kt=lambda t: f'{t/T:.4f}'
    darts=[]
    # each dart: launch time, control point (its own trajectory gives its own landing angle), tip offset,
    # fall start, fall duration, and how it tips while falling (degrees, + = clockwise; the dart points left when stuck)
    # launch, control point, tip offset, fall start, fall duration, spin while falling (deg, +cw), drift x, spin easing, bubble text
    spec=[(0.8, sx-130, -30,  0, 0,  6.2, 0.9,  +95,  -4, '.35 0 .6 1', 'Yes!'),
          (2.2, ex+140, -26,  1,-1,  6.75,0.85, -92,  +5, '.4 0 .7 1',  'WOW!'),
          (3.6, sx-300,  60,  0, 1,  7.2, 1.0,  +125, -7, '.25 0 .5 1', 'Bullseye!')]
    bubbles=[]
    for i,(L,cx,cy,ox,oy,F0,FD,spin,drift,spl,text) in enumerate(spec):
        H_=L+0.5; F1=F0+FD; tx,ty=ex+ox,ey+oy
        dx,dy=tx-cx,ty-cy; n=math.hypot(dx,dy); ux,uy=dx/n,dy/n           # stuck direction (tip points this way)
        px,py=tx-ux*DART_W*0.5, ty-uy*DART_W*0.5                          # centre of mass, mid-body
        land=math.degrees(math.atan2(dy,dx)); print(f'dart{i+1}: launch {L}s, lands {abs(land)-180 if abs(land)>90 else land:+.0f} deg, falls {F0}s, bubble "{text}" at {H_}s')
        pos=f'<animateMotion path="M{sx:.1f},{sy:.1f} Q{cx:.1f},{cy:.1f} {tx:.1f},{ty:.1f}" rotate="auto" keyPoints="0;0;1;1;0;0" keyTimes="0;{kt(L)};{kt(H_)};{kt(F1+0.05)};{kt(F1+0.1)};1" calcMode="linear" dur="{T}s" repeatCount="indefinite"/>'
        op=f'<animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;{kt(L)};{kt(L+0.02)};{kt(F1)};{kt(F1+0.02)};1" dur="{T}s" repeatCount="indefinite"/>'
        # release: a short sag (2px) while the dart loosens, then free fall with gravity plus a little sideways drift
        R=0.14
        fall=f'<animateTransform attributeName="transform" type="translate" additive="sum" values="0 0;0 0;{drift*0.15:.1f} 2;{drift} {BH+34};{drift} {BH+34};0 0;0 0" keyTimes="0;{kt(F0)};{kt(F0+R)};{kt(F1)};{kt(F1+0.05)};{kt(F1+0.1)};1" calcMode="spline" keySplines="0 0 1 1;.4 0 .8 1;.5 0 1 .55;0 0 1 1;0 0 1 1;0 0 1 1" dur="{T}s" repeatCount="indefinite"/>'
        # spin about the centre of mass: a slow start during the release, then a continuous turn that never quite stops
        tipping=f'<animateTransform attributeName="transform" type="rotate" additive="sum" values="0 {px:.1f} {py:.1f};0 {px:.1f} {py:.1f};{spin*0.08:.0f} {px:.1f} {py:.1f};{spin} {px:.1f} {py:.1f};{spin} {px:.1f} {py:.1f};0 {px:.1f} {py:.1f};0 {px:.1f} {py:.1f}" keyTimes="0;{kt(F0)};{kt(F0+R)};{kt(F1)};{kt(F1+0.05)};{kt(F1+0.1)};1" calcMode="spline" keySplines="0 0 1 1;.4 0 .8 1;{spl};0 0 1 1;0 0 1 1;0 0 1 1" dur="{T}s" repeatCount="indefinite"/>'
        wob=f'<animateTransform attributeName="transform" type="rotate" values="0;0;-6;5;-3;1;0;0" keyTimes="0;{kt(H_)};{kt(H_+0.08)};{kt(H_+0.16)};{kt(H_+0.24)};{kt(H_+0.32)};{kt(H_+0.4)};1" dur="{T}s" repeatCount="indefinite"/>'
        darts.append(f'<g opacity="0">{op}<g>{fall}{tipping}<g>{pos}<g>{wob}{dart}</g></g></g></g>')
        # thought-cloud bubble: two small puffs rising from the mouth, then a scalloped cloud with the text
        ink='#1f2933'
        tw=len(text)*7.0+14; ch=20
        x1=FIG_X-10; x0=x1-tw; y0=FIG_Y+8; y1=y0+ch; ymid=(y0+y1)/2
        n=max(3,int(tw//11)); step=(tw-12)/(n-1)
        circles=[(x0+6+k*step, y0+2, 7.5) for k in range(n)]+[(x0+6+k*step, y1-2, 7.5) for k in range(n)]+[(x0+1, ymid, 9.5),(x1-1, ymid, 9.5)]
        def cloud(stroke):
            parts=[]
            for cx_,cy_,r in circles:
                parts.append(f'<circle cx="{cx_:.1f}" cy="{cy_:.1f}" r="{r}" fill="#ffffff" stroke="{ink if stroke else "none"}" stroke-width="3"/>')
            parts.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{tw:.1f}" height="{ch}" rx="6" fill="#ffffff" stroke="{ink if stroke else "none"}" stroke-width="3"/>')
            return ''.join(parts)
        ax,ay=x1-6, y1+2                      # cloud anchor (bottom-right), where the puffs lead to
        mx,my=MOUTH_X-9, MOUTH_Y-1            # just in front of the mouth
        puffs=[(mx+(ax-mx)*0.28, my+(ay-my)*0.28, 2.2, 0.05),(mx+(ax-mx)*0.62, my+(ay-my)*0.62, 3.6, 0.15)]
        def popanim(t0, origin):
            ox_,oy_=origin
            return f'<animateTransform attributeName="transform" type="scale" values="0;0;1.18;1;1;0.5;0" keyTimes="0;{kt(H_+t0)};{kt(H_+t0+0.14)};{kt(H_+t0+0.24)};{kt(H_+1.05)};{kt(H_+1.18)};1" calcMode="spline" keySplines="0 0 1 1;.2 0 .4 1;.4 0 .6 1;0 0 1 1;.4 0 1 1;0 0 1 1" dur="{T}s" repeatCount="indefinite"/>'
        def wrap(origin, t0, body):
            ox_,oy_=origin
            return f'<g transform="translate({ox_:.1f} {oy_:.1f})"><g>{popanim(t0,origin)}<g transform="translate({-ox_:.1f} {-oy_:.1f})">{body}</g></g></g>'
        puff_svg=''.join(wrap((px_,py_), t0, f'<circle cx="{px_:.1f}" cy="{py_:.1f}" r="{r}" fill="#ffffff" stroke="{ink}" stroke-width="1.5"/>') for px_,py_,r,t0 in puffs)
        cloud_svg=wrap((ax,ay), 0.25, cloud(True)+cloud(False)+f'<text x="{x0+tw/2:.1f}" y="{ymid+4.3:.1f}" text-anchor="middle" font-family="{FONT}" font-size="12" font-weight="800" fill="{ink}" letter-spacing=".3">{text}</text>')
        bub=f'<g opacity="0"><animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;{kt(H_+0.05)};{kt(H_+0.07)};{kt(H_+1.15)};{kt(H_+1.2)};1" dur="{T}s" repeatCount="indefinite"/>{puff_svg}{cloud_svg}</g>'
        bubbles.append(bub)
    flight=f'<g clip-path="url(#bandclip)">{"".join(darts)}</g>'
    title=''
    if TITLE:
        ico=(ROOT/f'emoji/{theme}/chart-line-anim.svg').read_text()
        ico_inner=re.search(r'<svg[^>]*>(.*)</svg>', ico, re.S).group(1)
        ink='#1f2933' if theme=='light' else '#e6edf3'
        title=f'<g transform="translate(0 4)"><g transform="scale(1.0909)">{ico_inner}</g><text x="32" y="17.5" font-family="{FONT}" font-size="20" font-weight="600" fill="{ink}">Activity</text></g>'
    return f'''<g id="band">{title}
<defs><clipPath id="bandclip"><rect x="0" y="0" width="{W}" height="{BH}"/></clipPath><filter id="dhalo" x="-20%" y="-60%" width="140%" height="220%"><feMorphology in="SourceAlpha" operator="dilate" radius="1.1" result="d"/><feFlood flood-color="{halo}" flood-opacity=".95"/><feComposite in2="d" operator="in" result="h"/><feGaussianBlur in="h" stdDeviation=".4" result="hb"/><feMerge><feMergeNode in="hb"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
<image href="data:image/png;base64,{b64(ROOT/"assets/dart-board.png")}" x="{BOARD_X}" y="{BOARD_Y}" width="{BOARD_W}" height="{BOARD_H}"/>
{flight}
<image href="data:image/png;base64,{b64(ROOT/"assets/deadpool.png")}" x="{FIG_X}" y="{FIG_Y}" width="{FIG_W}" height="{FIG_H}"/>
{"".join(pops)}
{"".join(bubbles)}
</g>'''

def build():
  for theme in ('light','dark'):
      card=(ROOT/f'stats-{theme}.svg').read_text()
      m=re.match(r'<svg[^>]*>', card); card_inner=card[m.end():card.rfind('</svg>')]
      svg=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {BH+CARD_H}" width="{W}" height="{BH+CARD_H}">
  {band(theme)}
  <svg x="0" y="{BH}" width="{W}" height="{CARD_H}" viewBox="0 0 {W} {CARD_H}" font-family="{FONT}">{card_inner}</svg>
  </svg>'''
      (ROOT/f'{OUT}-{theme}.svg').write_text(svg)
  print('written activity-light/dark.svg', len(svg)//1024, 'KB')

if __name__=='__main__': build()
