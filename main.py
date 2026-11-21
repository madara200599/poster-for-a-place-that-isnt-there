import zlib, struct, os

W, H = 800, 1000

# pixel buffer RGB
buf = bytearray(W * H * 3)

def set_px(x, y, r, g, b):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i] = r; buf[i+1] = g; buf[i+2] = b

def fill_rect(x0, y0, x1, y1, col):
    r,g,b = col
    x0 = max(0,x0); x1 = min(W,x1); y0 = max(0,y0); y1 = min(H,y1)
    row = bytes((r,g,b)) * (x1-x0)
    for y in range(y0,y1):
        i = (y*W+x0)*3
        buf[i:i+len(row)] = row

def fill_circle(cx, cy, rad, col):
    r,g,b = col
    for y in range(cy-rad, cy+rad+1):
        if y<0 or y>=H: continue
        dy=y-cy; dx=int((rad*rad-dy*dy)**0.5)
        fill_rect(cx-dx, y, cx+dx+1, y+1, col)

def lerp(a,b,t): return int(a+(b-a)*t)

# --- SKY gradient: richer multi-stop bands, deep indigo -> violet -> teal -> amber -> warm orange ---
import math
SKY_STOPS=[(0.0,(10,16,62)),(0.18,(28,32,96)),(0.34,(58,64,132)),(0.48,(32,110,140)),(0.62,(86,168,158)),(0.78,(238,150,80)),(0.90,(255,178,92)),(1.0,(255,200,110))]
def sky_color(t):
    for i in range(len(SKY_STOPS)-1):
        t0,c0=SKY_STOPS[i]; t1,c1=SKY_STOPS[i+1]
        if t0<=t<=t1:
            tt=(t-t0)/max(1e-9,(t1-t0))
            # gentle banding / dithering to enrich gradient
            return (lerp(c0[0],c1[0],tt), lerp(c0[1],c1[1],tt), lerp(c0[2],c1[2],tt))
    return SKY_STOPS[-1][1]
for y in range(H):
    if y < 650:
        t = y/650
        col=sky_color(t)
        # subtle horizontal band glow
        band=int(6*math.sin(y*0.045))
        col=(max(0,min(255,col[0]+band)), max(0,min(255,col[1]+band//2)), max(0,min(255,col[2]+band)))
    else:
        t=(y-650)/350
        col=(lerp(20,8,t), lerp(95,38,t), lerp(110,62,t))
    row = bytes(col)*W
    i=y*W*3
    buf[i:i+len(row)]=row

# stars in upper sky — denser deterministic field, fading toward horizon
stars=[(60,60),(140,120),(680,80),(720,180),(90,220),(620,140),(200,70),(540,60),(760,300),(40,340)]
# deterministic pseudo-random extra stars (LCG, no imports needed)
_seed=1234567
def _rand():
    global _seed
    _seed=(_seed*1103515245+12345)&0x7fffffff
    return _seed
for _ in range(140):
    sx=_rand()%780+10; sy=_rand()%380+18
    stars.append((sx,sy))
for idx,(sx,sy) in enumerate(stars):
    fade=max(0.25, 1.0 - sy/420.0)  # dimmer lower down
    bright=int(150+105*fade) if idx%3 else 255
    col_star=(bright,bright,max(180,int(bright*0.92)))
    sz=2 if idx%4 else 4
    if sy<420:
        fill_rect(sx,sy,sx+sz,sy+sz,col_star)
        if idx%5==0:
            fill_rect(sx-2,sy+1,sx+sz+2,sy+2,col_star)

# sun / glowing moon-sun
fill_circle(400,420,118,(255,214,110))
fill_circle(400,420,96,(255,236,160))
# sun reflection glow band on sea handled later

# --- soft clouds for depth (layered translucent-look ellipses, drawn as overlapping circles) ---
def cloud(cx, cy, scale, col):
    for (dx, dy, r) in [(-38,-2,22),(0,-10,30),(38,-2,24),( -14,6,20),(18,6,22)]:
        fill_circle(cx+int(dx*scale), cy+int(dy*scale), max(4,int(r*scale)), col)
cloud(150,250,1.0,(214,196,205))
cloud(155,252,0.85,(232,214,214))
cloud(650,290,1.15,(206,188,200))
cloud(655,292,0.9,(228,208,210))
cloud(560,150,0.7,(198,182,198))
cloud(90,390,0.65,(226,200,196))

# --- small bird silhouettes (simple chevron wings) for depth ---
def bird(bx, by, s, col=(22,26,48)):
    for k in range(s):
        set_px(bx-s*2+k, by-k, *col); set_px(bx-s*2+k+1, by-k, *col)
        set_px(bx+k, by-k, *col); set_px(bx+k+1, by-k, *col)
    fill_rect(bx-1,by-s,by and bx+2 or bx+2,by-s+2,col) if False else fill_rect(bx-1,by-s+1,bx+2,by-s+3,col)
for (bx,by,bs) in [(250,180,7),(285,165,5),(520,200,6),(555,185,4),(180,300,5),(610,340,6),(470,140,4)]:
    bird(bx,by,bs)

# distant mountains (purple)
def mountain(base_y, peaks, col):
    # peaks: list of (x, top_y)
    for x in range(W):
        # interpolate height
        # find segment
        top=base_y
        for i in range(len(peaks)-1):
            x0,y0=peaks[i]; x1,y1=peaks[i+1]
            if x0<=x<=x1:
                tt=(x-x0)/max(1,(x1-x0)); top=int(y0+(y1-y0)*tt); break
        else:
            if x<peaks[0][0]: top=peaks[0][1]
            elif x>peaks[-1][0]: top=peaks[-1][1]
        if top<base_y:
            for y in range(top, base_y):
                set_px(x,y,*col)

mountain(660, [(0,560),(140,430),(280,540),(400,400),(540,530),(660,440),(800,560)], (86,62,118))
mountain(680, [(0,600),(180,500),(360,610),(520,480),(680,590),(800,520)], (44,38,78))

# sea sparkles
for yy in range(700,960,28):
    for xx in range(30,770,67):
        offset=(yy//28*23)%50
        x=(xx+offset)%760+10
        length=18+((xx*yy)%20)
        fill_rect(x,yy,x+length,yy+3,(110,220,205))

# island silhouette
for y in range(640,730):
    t=(y-640)/90
    half=int(260*(1-t*0.15))
    # actually island widens downward
    half=int(140+180*t)
    fill_rect(400-half,y,400+half,y+1,(18,22,38))
# beach glow edge
fill_rect(180,642,620,648,(255,190,110))

# LANDMARK: crystal lighthouse spire in centre
# base
fill_rect(365,520,435,660,(16,18,34))
# tapering tower
for y in range(340,540):
    t=(y-340)/200
    half=int(14+22*t)
    fill_rect(400-half,y,400+half,y+1,(20,24,46))
# crystal top - diamond
for dy in range(70):
    half=int(28*(1-abs(dy-35)/35))
    y=270+dy
    col=(140,240,225) if dy<35 else (90,200,210)
    fill_rect(400-half,y,400+half,y+1,col)
fill_circle(400,305,16,(255,255,220))
# light beams
for i in range(90):
    # left beam triangle-ish
    y=300+i//3
    fill_rect(400-28-i*3, y, 400-20-i*2, y+2, (255,240,170))
    fill_rect(400+20+i*2, y, 400+28+i*3, y+2, (255,240,170))
# windows glowing
for wy in (400,450,500):
    fill_rect(392,wy,408,wy+16,(255,210,90))
# palm silhouettes sides
def palm(x,y):
    fill_rect(x,y-70,x+8,y,(14,20,30))
    for ang in range(5):
        for l in range(42):
            px=x+4+int(l*math.cos(-2.4+ang*0.55))
            py=y-70+int(l*math.sin(-2.4+ang*0.55))-l//6
            fill_rect(px,py,px+4,py+3,(14,20,30))
palm(215,660); palm(575,660)

# reflection of sun/spire on water
for y in range(730,940):
    wob=int(6*math.sin(y*0.08))
    fill_rect(385+wob,y,415+wob,y+2,(255,200,100))
    if y%14<7:
        fill_rect(360+wob,y,440+wob,y+2,(90,210,195))

# border frame
fill_rect(0,0,W,14,(255,244,214)); fill_rect(0,H-14,W,H,(255,244,214))
fill_rect(0,0,14,H,(255,244,214)); fill_rect(W-14,0,W,H,(255,244,214))
fill_rect(14,14,W-14,18,(18,32,64)); fill_rect(14,H-18,W-14,H-14,(18,32,64))
fill_rect(14,14,18,H-14,(18,32,64)); fill_rect(W-18,14,W-14,H-14,(18,32,64))

# --- BITMAP FONT 5x7 ---
FONT={
'A':["01110","10001","10001","11111","10001","10001","10001"],
'E':["11111","10000","10000","11110","10000","10000","11111"],
'L':["10000","10000","10000","10000","10000","10000","11111"],
'M':["10001","11011","10101","10101","10001","10001","10001"],
'O':["01110","10001","10001","10001","10001","10001","01110"],
'R':["11110","10001","10001","11110","10100","10010","10001"],
'V':["10001","10001","10001","10001","10001","01010","00100"],
}

def draw_text(text, cx, y_top, scale, col, shadow=None):
    total_w=len(text)*5*scale+(len(text)-1)*scale
    x_start=cx-total_w//2
    for idx,ch in enumerate(text):
        glyph=FONT[ch]
        gx=x_start+idx*6*scale
        for row_i,row in enumerate(glyph):
            for col_i,bit in enumerate(row):
                if bit=='1':
                    bx=gx+col_i*scale; by=y_top+row_i*scale
                    if shadow:
                        fill_rect(bx+4,by+5,bx+scale,by+scale,shadow)
                    fill_rect(bx,by,bx+scale,by+scale,col)

# Place name BIG at top
draw_text("VELMORA", 400, 52, 17, (255,252,235), shadow=(20,30,70))
# thin gold rule under name
fill_rect(150,190,650,196,(255,210,110))
fill_rect(150,202,650,205,(255,252,235))

# write PNG manually
def chunk(typ, data):
    c=struct.pack(">I",len(data))+typ+data
    c+=struct.pack(">I", zlib.crc32(typ+data)&0xffffffff)
    return c

raw=b""
stride=W*3
for y in range(H):
    raw+=b"\x00"+bytes(buf[y*stride:(y+1)*stride])
png=b"\x89PNG\r\n\x1a\n"
png+=chunk(b"IHDR", struct.pack(">IIBBBBB",W,H,8,2,0,0,0))
png+=chunk(b"IDAT", zlib.compress(raw,9))
png+=chunk(b"IEND", b"")

out=os.environ.get("OUTPUT_PATH","/output/entry.png")
try:
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
except Exception:
    pass
# fallback if /output not writable in local test
try:
    with open(out,"wb") as f: f.write(png)
except OSError:
    out="/tmp/entry.png"
    with open(out,"wb") as f: f.write(png)
print(f"Wrote {out} {len(png)} bytes {W}x{H}")
