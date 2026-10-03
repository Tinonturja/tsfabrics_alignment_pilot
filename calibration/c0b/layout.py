"""Real pilot pass layout (frozen CSV) -> concatenated timeline for metric audits. Audit only."""
import numpy as np, pandas as pd
import os as _os
_CSV=_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), *(['..']*(2 if 'calibration' in _os.path.abspath(__file__) else 1)), 'data','frozen','tsfabrics_pilot_passes_and_candidate_tracks.csv')
P=pd.read_csv(_CSV)  # repo-relative path (the only change from the frozen copy, 2026-10-03)
SC={'A-G1':[('T1_S148_I108_1',3262,-113),('T1_S148_I108_2',4804,-118),('T1_S174_I108_1',617,-127),('T1_S174_I111_1',18630,-116),('T1_S177_I108_1',16431,-118)],
    'A-G4':[('T1_S478_I118_1',3247,-39),('T1_S478_I118_2',3204,-39),('T1_S555_I117_1',18465,-38)]}
SEP=4
def build(fold, cap_grace=True):
    """returns dict: n (timeline length), isnormal (N_f mask), passes list of (lo,hi,track,s,e), scen_id, k per frame"""
    segs=[];off=0;passes=[];isn=[];scen=[];kk=[];frame=[]
    for si,(sc,N,dx) in enumerate(SC[fold]):
        k=int(np.floor(800/abs(dx)+0.5)); k=min(25,max(3,k))
        m=np.ones(N,bool)
        g=P[P.scenario==sc].sort_values('pass_start')
        rows=list(g.itertuples())
        for j,r in enumerate(rows):
            s,e=r.pass_start,r.pass_end
            nxt=rows[j+1].pass_start if j+1<len(rows) else N+1
            end=min(e+k-1,nxt-1,N) if cap_grace else e
            m[s-1:end]=False
            passes.append((off+s-1,off+end-1,r.candidate_track_id,off+s-1,off+e-1,sc,k))
        isn+=list(m); scen+=[si]*N; kk+=[k]*N; frame+=list(range(1,N+1)); off+=N
        isn+=[False]*SEP; scen+=[-1]*SEP; kk+=[k]*SEP; frame+=[0]*SEP; off+=SEP
    return dict(n=off,isn=np.array(isn),passes=passes,scen=np.array(scen),k=np.array(kk),frame=np.array(frame))
