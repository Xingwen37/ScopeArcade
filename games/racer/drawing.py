"""Perspective projection, clipping and compact private line frames."""
import binascii
import math

MAX_LINES=72
SEGMENTS=[((0,8),(4,8)),((4,8),(4,4)),((4,4),(4,0)),((4,0),(0,0)),
          ((0,0),(0,4)),((0,4),(0,8)),((0,4),(4,4))]
MASKS=[0x3f,0x06,0x5b,0x4f,0x66,0x6d,0x7d,0x07,0x7f,0x6f]

def clip2(a,b):
    x,y=a;dx=b[0]-x;dy=b[1]-y;lo=0.;hi=1.
    for p,q in [(-dx,x-8),(dx,247-x),(-dy,y-10),(dy,236-y)]:
        if abs(p)<1e-12:
            if q<0:return None
        else:
            t=q/p
            if p<0:lo=max(lo,t)
            else:hi=min(hi,t)
            if lo>hi:return None
    result=tuple(round(v) for v in (x+lo*dx,y+lo*dy,x+hi*dx,y+hi*dy))
    return result if result[:2]!=result[2:] else None

def center(distance):return 3.0*math.sin(distance/110)+1.3*math.sin(distance/49)
def slope(distance):return 3/110*math.cos(distance/110)+1.3/49*math.cos(distance/49)

def project_line(game,a,b):
    # Clip in camera depth before perspective division.
    a=list(a);b=list(b)
    if a[2]<2 and b[2]<2:return None
    if a[2]<2:
        t=(2-a[2])/(b[2]-a[2]);a=[a[i]+t*(b[i]-a[i]) for i in range(3)]
    elif b[2]<2:
        t=(2-b[2])/(a[2]-b[2]);b=[b[i]+t*(a[i]-b[i]) for i in range(3)]
    def project(p):
        x,h,z=p
        curve=center(game.distance+z)-center(game.distance)-slope(game.distance)*z
        return 128+170*(x+curve-game.player)/z,146+170*(h-1.25)/z
    return clip2(project(a),project(b))

def digit(lines,value,x,y,scale=2):
    for i,(a,b) in enumerate(SEGMENTS):
        if MASKS[value]&(1<<i):lines.append((x+a[0]*scale,y+a[1]*scale,x+b[0]*scale,y+b[1]*scale))

def scene(game):
    essential=[];road=[];traffic=[]
    # Left number: score; right number: seconds remaining. Clear labels on PC.
    score=min(99,game.score);remaining=math.ceil(game.remaining) if game.mode!='attract' else 60
    for number,x in [(score,18),(remaining,209)]:
        if number>=10 or x==209:digit(essential,number//10,x,213)
        digit(essential,number%10,x+12,213)
    hood=[(69,15),(79,25),(177,25),(187,15)]
    essential.extend((*a,*b) for a,b in zip(hood,hood[1:]))
    essential.append((69,15,187,15))
    depths=[2,5,12,30,90]
    for edge in (-3.5,3.5):
        for z0,z1 in zip(depths,depths[1:]):
            line=project_line(game,(edge,0,z0),(edge,0,z1))
            if line:road.append(line)
    phase=game.distance%8
    for lane in (-1.17,1.17):
        for j in range(4):
            z=2+j*8-phase
            line=project_line(game,(lane,0,z),(lane,0,z+3.5))
            if line:road.append(line)
    # Draw the closest cars first so budget pressure cannot hide immediate hazards.
    for car in sorted([c for c in game.cars if -2<c.z<90],key=lambda c:c.z)[:3]:
        x,z=car.x,car.z
        contour=[(x-.8,.15,z),(x+.8,.15,z),(x+.8,.8,z),
                 (x+.58,1.25,z+.8),(x-.58,1.25,z+.8),(x-.8,.8,z),(x-.8,.15,z)]
        edges=list(zip(contour,contour[1:]))+[((x-.8,.8,z),(x+.8,.8,z)),
               ((x-.63,0,z),(x-.63,.22,z)),((x+.63,0,z),(x+.63,.22,z))]
        group=[q for a,b in edges if (q:=project_line(game,a,b))]
        traffic.append(group)
    if game.mode=='countdown':digit(essential,max(1,min(3,math.ceil(game.countdown))),120,158,3)
    if game.flash>0:
        essential.extend([(113,178,123,164),(133,178,143,164)])
    lines=essential+road
    for group in traffic:
        if len(lines)+len(group)<=MAX_LINES:lines.extend(group)
    # Use spare slots to subdivide the longest lines for more even brightness.
    while len(lines)<MAX_LINES:
        lengths=[max(abs(c-a),abs(d-b)) for a,b,c,d in lines]
        index=max(range(len(lines)),key=lambda i:lengths[i])
        if lengths[index]<=30:break
        a,b,c,d=lines[index];m=(round((a+c)/2),round((b+d)/2))
        lines[index:index+1]=[(a,b,*m),(*m,c,d)]
    assert 0<len(lines)<=MAX_LINES
    assert all(0<=v<=255 for line in lines for v in line)
    return lines

def packet(seq,lines):
    if not 0<len(lines)<=MAX_LINES:raise ValueError('line count')
    body=bytes([seq&255,len(lines)])+bytes(v for line in lines for v in line)
    return b'\xa5\x5a'+body+binascii.crc_hqx(body,0xffff).to_bytes(2,'big')
