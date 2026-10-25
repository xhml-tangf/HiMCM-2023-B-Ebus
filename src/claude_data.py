"""Existing evidence adapter; keeps observed trips separate from travel assumptions."""
from pathlib import Path
from datetime import date
import hashlib
import numpy as np
import pandas as pd
from .audit_gtfs_baseline import active_services, haversine_km
from .claude_evsp import Instance

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'data/processed/vancouver_gtfs_trip_manifest_classified_2023.csv'


def load_data():
    frame=pd.read_csv(MANIFEST,dtype={'trip_id':str,'service_id':str,'route_short_name':str,
                                    'route_key':str,'first_stop_id':str,'last_stop_id':str},low_memory=False)
    daily=pd.read_csv(ROOT/'data/processed/vancouver_gtfs_daily_service_2023.csv')
    raw=ROOT/'materials/sources/raw/vancouver_gtfs_2023'
    cal=pd.read_csv(raw/'calendar.txt',dtype=str,keep_default_na=False)
    exc=pd.read_csv(raw/'calendar_dates.txt',dtype=str,keep_default_na=False)
    stops=pd.read_csv(raw/'stops.txt',dtype=str).set_index('stop_id')
    # Same evidence-labeled trolley proxy as the archived source audit.
    electric_proxy=frame.proxy_class.isin(['cap47','cap70'])
    frame=frame[~electric_proxy].copy()
    ids=sorted(set(frame.first_stop_id)|set(frame.last_stop_id))
    nodes=[dict(stop_id=i,name=stops.loc[i,'stop_name'],lat=float(stops.loc[i,'stop_lat']),
                lon=float(stops.loc[i,'stop_lon'])) for i in ids]
    mapping={i:k for k,i in enumerate(ids)}
    frame['o']=frame.first_stop_id.map(mapping);frame['dst']=frame.last_stop_id.map(mapping)
    return frame,daily,cal,exc,nodes


def day_frame(frame,cal,exc,day):
    return frame[frame.service_id.isin(active_services(cal,exc,date.fromisoformat(str(day))))].sort_values(['start_seconds','end_seconds','trip_id']).reset_index(drop=True)


def instance(frame,nodes,R=270.,T=60.,road_factor=1.35,speed_kmh=30.,distance_bound='upper'):
    lat=np.array([n['lat'] for n in nodes]);lon=np.array([n['lon'] for n in nodes])
    w=haversine_km(lat[:,None],lon[:,None],lat[None,:],lon[None,:])*road_factor
    tau=w*60/speed_kmh
    trips=[(int(r.o),int(r.dst),float(r.start_seconds)/60,float(r.end_seconds)/60,
            float(getattr(r,'distance_km_'+distance_bound))) for r in frame.itertuples()]
    return Instance(R,T,tau,w,trips,frame.trip_id.tolist(),nodes)


def source_manifest():
    paths=[MANIFEST,ROOT/'data/processed/vancouver_gtfs_daily_service_2023.csv',
           ROOT/'materials/sources/raw/vancouver_gtfs_2023/calendar.txt',ROOT/'materials/sources/raw/vancouver_gtfs_2023/calendar_dates.txt',
           ROOT/'materials/sources/raw/vancouver_gtfs_2023/stops.txt',
           ROOT/'materials/research/claude_plan/spec_original.md',ROOT/'materials/research/claude_plan/solver_reference_original.py']
    return {str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
