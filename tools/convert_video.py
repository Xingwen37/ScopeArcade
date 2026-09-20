"""Offline asset preparation only. OpenCV/NumPy are not player dependencies."""
import argparse
import json
import math
from pathlib import Path
import sys
import time
import zipfile

def vectorize(frame,budget=72):
    import cv2
    height,width=frame.shape[:2]
    scale=min(1,320/max(width,height));w=max(2,round(width*scale));h=max(2,round(height*scale))
    small=cv2.resize(frame,(w,h),interpolation=cv2.INTER_LINEAR)
    gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY) if small.ndim==3 else small
    gray=cv2.medianBlur(gray,3)
    _,binary=cv2.threshold(gray,127,255,cv2.THRESH_BINARY)
    contours,_=cv2.findContours(binary,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
    candidates=[]
    for contour in contours:
        area=abs(cv2.contourArea(contour));x,y,cw,ch=cv2.boundingRect(contour)
        if area<max(4,w*h*.00015):continue
        if x<=1 and y<=1 and cw>=w-2 and ch>=h-2 and area>w*h*.90:continue
        candidates.append((area,contour))
    candidates=sorted(candidates,key=lambda item:item[0],reverse=True)[:12]
    fit=min(240/w,240/h);ox=(256-w*fit)/2;oy=(256-h*fit)/2
    def xy(point):return (max(0,min(255,round(ox+int(point[0])*fit))),max(0,min(255,round(255-oy-int(point[1])*fit))))
    def simplify(epsilon):
        lines=[]
        for _,contour in candidates:
            polygon=cv2.approxPolyDP(contour,epsilon,True).reshape(-1,2)
            points=[]
            for point in polygon:
                p=xy(point)
                if not points or p!=points[-1]:points.append(p)
            if len(points)==2:lines.append((*points[0],*points[1]))
            elif len(points)>2:lines.extend((*a,*b) for a,b in zip(points,points[1:]+points[:1]) if a!=b)
        return lines
    lines=simplify(.25)
    if len(lines)>budget:
        lo=.25;hi=max(w,h)/2;best=[]
        for _ in range(14):
            mid=(lo+hi)/2;candidate=simplify(mid)
            if len(candidate)<=budget:hi=mid;best=candidate
            else:lo=mid
        lines=best
    if not lines:
        if float(binary.mean())>250:
            a=xy((0,0));b=xy((w-1,h-1));lines=[(a[0],a[1],b[0],a[1]),(b[0],a[1],b[0],b[1]),(b[0],b[1],a[0],b[1]),(a[0],b[1],a[0],a[1])]
        else:lines=[(0,0,0,0)] # Existing firmware requires >=1 line; park outside content.
    while len(lines)<budget:
        lengths=[max(abs(c-a),abs(d-b)) for a,b,c,d in lines]
        index=max(range(len(lines)),key=lambda i:lengths[i])
        if lengths[index]<=28:break
        a,b,c,d=lines[index];mid=(round((a+c)/2),round((b+d)/2));lines[index:index+1]=[(a,b,*mid),(*mid,c,d)]
    assert 1<=len(lines)<=budget
    return lines

def convert(source,destination,fps=30,progress=None,cancel=None):
    import cv2
    cv2.setNumThreads(1)
    source=Path(source);destination=Path(destination)
    if not source.is_file():raise ValueError('找不到源视频')
    if not 1<=fps<=30:raise ValueError('转换帧率必须在1～30之间')
    capture=cv2.VideoCapture(str(source))
    if not capture.isOpened():raise ValueError('视频无法解码')
    frames=bytearray();count=0;index=0;last_progress=0
    try:
        input_fps=capture.get(cv2.CAP_PROP_FPS);total=capture.get(cv2.CAP_PROP_FRAME_COUNT)
        width=capture.get(cv2.CAP_PROP_FRAME_WIDTH);height=capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        if not math.isfinite(input_fps) or input_fps<=0:raise ValueError('视频帧率无效')
        output_fps=min(float(fps),input_fps)
        if total>0 and total/input_fps>600:raise ValueError('视频最多10分钟')
        while capture.grab():
            if cancel and cancel.is_set():raise RuntimeError('转换已取消')
            timestamp=index/input_fps
            if timestamp>=600:raise ValueError('视频超过10分钟')
            if timestamp+1e-8>=count/output_fps:
                ok,frame=capture.retrieve()
                if not ok:raise ValueError('视频帧解码失败')
                lines=vectorize(frame);frames.append(len(lines));frames.extend(v for line in lines for v in line);count+=1
            index+=1
            if progress and time.monotonic()-last_progress>.5:
                progress(index,total,count);last_progress=time.monotonic()
    finally:capture.release()
    if count==0:raise ValueError('视频没有可用画面')
    metadata={'version':1,'fps':output_fps,'frame_count':count,'source_name':source.name,
              'source_width':width,'source_height':height,'source_fps':input_fps,'line_budget':72,'audio':False}
    destination.parent.mkdir(parents=True,exist_ok=True);temporary=destination.with_suffix(destination.suffix+'.tmp')
    try:
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
            for name,data in [('metadata.json',json.dumps(metadata,ensure_ascii=False).encode('utf-8')),('frames.bin',bytes(frames))]:
                info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                archive.writestr(info,data)
        temporary.replace(destination)
    finally:
        if temporary.exists():temporary.unlink()
    return metadata

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);parser.add_argument('destination',type=Path);parser.add_argument('--fps',type=int,default=30);args=parser.parse_args()
    def progress(done,total,frames):print(f'{done/total*100:.1f}% — {frames} vector frames' if total else f'{frames} frames',flush=True)
    print(json.dumps(convert(args.source,args.destination,args.fps,progress),ensure_ascii=False),flush=True)
