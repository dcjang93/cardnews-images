import subprocess, sys
from pathlib import Path
from PIL import Image
# 사용법: python3 make_reel.py <카드폴더> [출력파일]
d=Path(sys.argv[1]); out=sys.argv[2] if len(sys.argv)>2 else str(d/'reel.mp4')
cards=sorted(d.glob('card_*.jpg')); n=len(cards)
for i,c in enumerate(cards,1):
    f=Image.new('RGB',(1080,1920),(15,39,66)); f.paste(Image.open(c),(0,285)); f.save(d/f'reel_{i:02d}.png')
durs=[3.2]+[2.8]*(n-3)+[3.6,3.2] if n>=3 else [3.2]*n; T=0.35
inp=[]
for i,t in enumerate(durs,1): inp+=['-loop','1','-t',str(t),'-i',str(d/f'reel_{i:02d}.png')]
inp+=['-f','lavfi','-t',str(sum(durs)),'-i','anullsrc=channel_layout=stereo:sample_rate=44100']
fc=[];prev='[0:v]';off=0
for i in range(1,n):
    off+=durs[i-1]-T; fc.append(f'{prev}[{i}:v]xfade=transition=slideleft:duration={T}:offset={off:.2f}[v{i}]'); prev=f'[v{i}]'
fc.append(f'{prev}format=yuv420p,fps=30[vout]')
subprocess.run(['ffmpeg','-y','-loglevel','error']+inp+['-filter_complex',';'.join(fc),'-map','[vout]','-map',f'{n}:a','-c:v','libx264','-preset','veryfast','-crf','20','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',out],check=True)
print(out)
