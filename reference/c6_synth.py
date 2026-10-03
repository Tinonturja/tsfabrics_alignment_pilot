"""Section 4 audit: v1.1 A12/E10 decomposition applied verbatim to synthetic 80x100 maps."""
import numpy as np
from scipy.ndimage import maximum_filter
H,Wd=80,100
def M3(a): return maximum_filter(a,size=3,mode='nearest')   # 3x3 max, clipped at borders (nearest == clip for max)
rng=np.random.default_rng(5)
def noise(n): return rng.gamma(4.0,1.0,(n,H,Wd)).astype(np.float64)   # positive, skewed like squared distances
val=noise(1500); b1=val.mean(0); b3=np.mean([M3(v) for v in val],0); tau_cell=np.quantile(val,0.999)
def classify(maps,te,u0,K):
    a=maps[te]; p=np.unravel_index(np.argmax(a),a.shape); ys,xs=p
    E0=a[p]-b1[p]; g=(a>tau_cell).mean()
    path=[]
    for j in range(1,K+1):
        U=int(np.floor(j*u0+0.5)); x=xs-U          # leftward motion: U(t_e+j,j)=floor(j*u0+0.5)
        if not (0<=x<=99) or te+j>=len(maps): break
        path.append((j,x))
    if g>=0.02: return 'global'
    if len(path)<3 or E0<=0: return 'ambiguous(J<3/E0<=0)'
    e=[(M3(maps[te+j])[ys,x]-b3[ys,x])/E0 for j,x in path]
    e0=[]
    for j,x in path:
        rows=[r for r in (ys+10,ys-10) if 0<=r<H]; m=M3(maps[te+j])
        e0.append(np.mean([(m[r,x]-b3[r,x]) for r in rows])/E0)
    rho,rho0=np.median(e),np.median(e0)
    if rho>=0.5 and rho-rho0>=0.25: return 'persistent-local'
    if rho<0.25: return 'transient'
    return 'ambiguous'
def blob(m,t,y,x,A,wy=1,wx=1):
    x=int(round(x))
    if 0<=x<Wd: m[t,max(0,y-wy):y+wy+1,max(0,x-wx):x+wx+1]+=A
def case(kind,u0,K,A=12.0):
    n=K+3; m=noise(n); te=0
    y=int(rng.integers(15,65)); x0=float(rng.integers(60,95))
    if kind=='pure noise': pass
    elif kind=='global strong': m+=2.5
    elif kind=='global mild (+1)': m+=1.0; blob(m,te,y,x0,A)
    elif kind=='persistent fabric-fixed': [blob(m,t,y,x0-t*u0,A) for t in range(n)]
    elif kind=='transient (1 frame)': blob(m,te,y,x0,A)
    elif kind=='camera-fixed': [blob(m,t,y,x0,A) for t in range(n)]
    elif kind=='persistent, exit-edge start (x0=20)': [blob(m,t,y,20-t*u0,A) for t in range(n)]
    elif kind=='persistent, late peak': [blob(m,t,y,x0-t*u0,A*(0.45+0.25*t)) for t in range(n)]
    elif kind=='persistent vertical line (all rows)':
        for t in range(n):
            x=int(round(x0-t*u0))
            if 0<=x<Wd: m[t,:,max(0,x-1):x+2]+=A*0.6; m[t,y,max(0,x-1):x+2]+=A*0.4
    return classify(m,te,u0,K)
kinds=['pure noise','global strong','global mild (+1)','transient (1 frame)','persistent fabric-fixed','camera-fixed',
       'persistent, exit-edge start (x0=20)','persistent, late peak','persistent vertical line (all rows)']
for fold,u0,K in [('A-G1 speed',14.0,7),('A-G4 speed',4.75,21)]:
    print(f"\n{fold}: u0={u0} cells/frame, K={K}")
    for k in kinds:
        from collections import Counter
        c=Counter(case(k,u0,K) for _ in range(60))
        print(f"  {k:40s} ", dict(c))
