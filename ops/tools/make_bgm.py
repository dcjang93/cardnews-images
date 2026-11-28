# 소재 분위기에 맞춘 배경음악을 코드로 직접 합성한다 (저작권 걱정 없는 원본, 매번 seed로 조금씩 다름).
# 사용법: python3 make_bgm.py <mood> <길이초> <출력.wav> [seed]
# mood: calm(잔잔·정리/절약) | bright(경쾌·혜택/환급/지원금) | urgent(긴장·마감/소멸/사기주의) | warm(따뜻·부모님/건강/가족)
import sys, numpy as np, wave
mood=sys.argv[1]; dur=float(sys.argv[2]); out=sys.argv[3]; seed=int(sys.argv[4]) if len(sys.argv)>4 else 7
sr=44100; N=int(sr*dur); mix=np.zeros((N,2)); rng=np.random.default_rng(seed)
P={
 "calm":  dict(bpm=84, ch=[[48,55,64,71],[45,52,60,67],[41,48,57,64],[43,50,59,65]], arp=True, kick=(0,2), hat=0.025, pad=0.06, bass="long", keys=0.09, dec=0.45),
 "bright":dict(bpm=104,ch=[[48,55,64,67],[43,50,59,62],[45,52,60,64],[41,48,57,60]], arp=True, kick=(0,1,2,3), hat=0.035, pad=0.04, bass="eighth", keys=0.10, dec=0.25),
 "urgent":dict(bpm=96, ch=[[45,52,60,64],[41,48,57,60],[48,55,60,64],[43,50,55,59]], arp=False, kick=(0,2), hat=0.03, pad=0.07, bass="pulse", keys=0.07, dec=0.3),
 "warm":  dict(bpm=72, ch=[[48,55,64,67],[41,48,57,64],[45,52,60,64],[43,50,59,62]], arp=True, kick=(), hat=0.0, pad=0.07, bass="long", keys=0.11, dec=0.8),
}[mood]
beat=60/P["bpm"]; bar=beat*4
def f(n): return 440*2**((n-69)/12)
def env(n,a,r): t=np.arange(n)/sr; return np.minimum(1,t/a)*np.exp(-t/r)
def keys(freq,n):
    t=np.arange(n)/sr
    return np.sin(2*np.pi*freq*t)+0.35*np.sin(2*np.pi*2*freq*t)*np.exp(-t*3)+0.1*np.sin(2*np.pi*3*freq*t)*np.exp(-t*6)
def add(x,start,pan=0.5,g=1.0):
    s=int(start*sr)
    if s>=N: return
    e=min(N,s+len(x)); mix[s:e,0]+=x[:e-s]*g*(1-pan); mix[s:e,1]+=x[:e-s]*g*pan
t0=0; k=0
while t0<dur:
    ch=P["ch"][k%4]; n=int(bar*sr*1.6)
    for note in ch[1:]:
        t=np.arange(n)/sr; pad=np.sin(2*np.pi*f(note)*t+0.3*np.sin(2*np.pi*0.3*t))*np.minimum(1,t/0.8)*np.exp(-t/3)
        add(pad,t0,0.3+0.4*rng.random(),P["pad"])
    b=f(ch[0]-12)
    if P["bass"]=="long":
        m=int(bar*sr); add(np.sin(2*np.pi*b*np.arange(m)/sr)*env(m,0.02,1.2),t0,0.5,0.22)
    else:
        m=int(beat/2*sr)
        for j in range(8):
            g=0.2 if P["bass"]=="eighth" else (0.24 if j%2==0 else 0.14)
            add(np.sin(2*np.pi*b*np.arange(m)/sr)*env(m,0.005,0.12),t0+j*beat/2,0.5,g)
    if P["arp"]:
        a=[ch[1]+12,ch[2]+12,ch[3]+12,ch[2]+12,ch[1]+24,ch[3]+12,ch[2]+12,ch[3]+12]
        mid=a[1:7]; rng.shuffle(mid); a[1:7]=mid
        for j,nn in enumerate(a):
            m=int(beat*2*sr); add(keys(f(nn),m)*env(m,0.005,P["dec"]),t0+j*beat/2,0.35 if j%2 else 0.65,P["keys"])
    else:  # urgent: 같은 음을 반복하는 긴장감 있는 리듬
        for j in range(8):
            m=int(beat*sr); add(keys(f(ch[3]+12),m)*env(m,0.003,0.12),t0+j*beat/2,0.6,P["keys"]*(1.2 if j in (0,3,6) else 0.7))
    for j in range(4):
        m=int(0.25*sr); tt=np.arange(m)/sr
        if j in P["kick"]: add(np.sin(2*np.pi*(55+60*np.exp(-tt*30))*tt)*np.exp(-tt*12),t0+j*beat,0.5,0.25)
        if P["hat"]:
            hn=int(0.06*sr); hh=rng.standard_normal(hn)*np.exp(-np.arange(hn)/sr*60); hh=np.diff(hh,prepend=0)
            add(hh,t0+j*beat+beat/2,0.6,P["hat"])
    t0+=bar; k+=1
fi=int(0.8*sr); fo=int(1.5*sr)
mix[:fi]*=np.linspace(0,1,fi)[:,None]; mix[-fo:]*=np.linspace(1,0,fo)[:,None]
mix=mix/np.abs(mix).max()*0.5
with wave.open(out,'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes((mix*32767).astype('<i2').tobytes())
print(out)
