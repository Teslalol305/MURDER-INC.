"""The story's routes on the Block's nav grid, as a top-down picture (docs/unreal/PLAY.md, guide lane): level.json's grid,
the A* of FMIBoxWorld::FindPath (8 neighbours, no corner cutting, octile heuristic x 1.001) with its string pulling, the
chevrons every 1.5 m laid back from 1.2 m short of the goal, as AMIGuide lays them. A replica in Python for the document
(the game's own routes are checked by MurderInc.Guide.Routes); north is up.
Usage (repository root): python3 tools/box/fp/guide_routes_map.py [out.jpg]"""
import json, heapq, math, os, sys
from PIL import Image, ImageDraw, ImageFont
d=json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../unreal/MurderInc/Content/Data/level.json')))
n=d['nav']; g=n['grid']['cells']
rows=len(g); cols=len(g[0]); ox,oz=-46.0,-34.0; c=0.5
def blk(i,j): return i<0 or j<0 or i>=cols or j>=rows or g[j][i]=='#'
def near(x,z):
  fi,fj=(x-ox)/c,(z-oz)/c; i,j=int(fi),int(fj)
  if not blk(i,j): return i,j
  best=None
  for r in range(1,13):
    for jj in range(j-r,j+r+1):
      for ii in range(i-r,i+r+1):
        if not blk(ii,jj):
          dd=(ii+.5-fi)**2+(jj+.5-fj)**2
          if best is None or dd<best[0]: best=(dd,ii,jj)
    if best: return best[1],best[2]
D=[(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]
def astar(a,b):
  op=[(0,0,a)];gs={a:0};par={a:None};k=0
  while op:
    f,_,cur=heapq.heappop(op)
    if cur==b: break
    for q,(dx,dz) in enumerate(D):
      nb=(cur[0]+dx,cur[1]+dz)
      if blk(*nb): continue
      if q>=4 and (blk(cur[0]+dx,cur[1]) or blk(cur[0],cur[1]+dz)): continue
      ng=gs[cur]+(1 if q<4 else 2**.5)
      if ng<gs.get(nb,1e9):
        gs[nb]=ng;par[nb]=cur;ax,az=abs(nb[0]-b[0]),abs(nb[1]-b[1]);k+=1
        heapq.heappush(op,(ng+(max(ax,az)+(2**.5-1)*min(ax,az))*1.001,k,nb))
  p=[];x=b
  while x: p.append(x);x=par.get(x)
  return p[::-1]
def linefree(x0,z0,x1,z1):
  n=int(max(abs(x1-x0),abs(z1-z0))/0.05)+1
  for t in range(n+1):
    x=x0+(x1-x0)*t/n; z=z0+(z1-z0)*t/n
    if blk(int((x-ox)//c),int((z-oz)//c)): return False
  return True
def cen(cl): return (ox+(cl[0]+.5)*c, oz+(cl[1]+.5)*c)
def pull(A,B,cells):
  out=[A]; i=0; last=len(cells)-1; s=A
  while i<last:
    j=last; t=B
    while j>i+1 and not linefree(s[0],s[1],t[0],t[1]):
      j-=1; t=cen(cells[j])
    out.append(t); s=t; i=j
  return out
pts={'start':(-37.4,8.15)}
for o in d['objectives']: pts[o['id']]=(o['web']['pos']['x'],o['web']['pos']['z'])
pts['truck']=(d['extraction']['web']['pos']['x'],d['extraction']['web']['pos']['z'])
seq=['start','reel1','reel2','reel3','truck']
S=8
im=Image.new('RGB',(cols*S,rows*S),(30,30,32)); dr=ImageDraw.Draw(im)
for j in range(rows):
  for i in range(cols):
    if g[j][i]=='.': dr.rectangle([i*S,j*S,i*S+S-1,j*S+S-1],fill=(150,150,146))
def P(x,z): return ((x-ox)/c*S,(z-oz)/c*S)
cols_=[(255,170,40),(255,120,30),(240,200,60),(120,230,120)]
tot=0
for k,(fa,b) in enumerate(zip(seq,seq[1:])):
  A=pts[fa] if k==0 else (pts[fa][0]+0.8,pts[fa][1])
  ca=near(*A); cb=near(*pts[b]); cells=astar(ca,cb)
  B=cen(cb) if (int((pts[b][0]-ox)//c),int((pts[b][1]-oz)//c))!=cb else pts[b]
  A2=A if (int((A[0]-ox)//c),int((A[1]-oz)//c))==ca else cen(ca)
  path=pull(A2,B,cells)
  L=sum(math.dist(p,q) for p,q in zip(path,path[1:])); tot+=L
  dr.line([P(*p) for p in path],fill=cols_[k],width=5)
  # chevrons every 1.5 m back from the goal (stop 1.2 m short)
  cum=[0]
  for p,q in zip(path,path[1:]): cum.append(cum[-1]+math.dist(p,q))
  s=cum[-1]-1.2
  while s>1.4:
    m=max(i for i in range(len(cum)-1) if cum[i]<=s) if s>0 else 0
    m=min(m,len(path)-2); t=(s-cum[m])/max(cum[m+1]-cum[m],1e-9)
    x=path[m][0]+(path[m+1][0]-path[m][0])*t; z=path[m][1]+(path[m+1][1]-path[m][1])*t
    dx,dz=path[m+1][0]-path[m][0],path[m+1][1]-path[m][1]; l=math.hypot(dx,dz) or 1; dx/=l; dz/=l
    a=math.radians(52); tip=P(x,z)
    for sg in (-1,1):
      bx=-dx*math.cos(a)+(-dz)*sg*math.sin(a); bz=-dz*math.cos(a)+dx*sg*math.sin(a)
      dr.line([tip,P(x+bx*0.5,z+bz*0.5)],fill=(20,20,20),width=3)
    s-=1.5
  print(fa,b,round(L,1))
for name,(x,z) in pts.items():
  X,Z=P(x,z); dr.ellipse([X-10,Z-10,X+10,Z+10],fill=(30,110,255),outline=(255,255,255),width=2)
  dr.text((X+13,Z-10),{'start':'START','reel1':'REEL 1','reel2':'REEL 2','reel3':'REEL 3','truck':'IPX TRUCK'}[name],fill=(255,255,255))
print('total',round(tot,1))
im=im.resize((im.width*3//4,im.height*3//4))
out=sys.argv[1] if len(sys.argv)>1 else 'play-guide-routes.jpg'
im.save(out,quality=82); print(out, os.path.getsize(out), im.size)
