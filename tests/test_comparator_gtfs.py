import zipfile,json,os,shutil
from pathlib import Path
import pandas as pd
from scripts import prepare_comparator_gtfs as adapter


def test_london_geography_calendar_frequency_and_absolute_clock(monkeypatch):
    workspace=Path(__file__).resolve().parents[1]
    tmp_path=workspace/'tmp'/f'comparator-test-{os.getpid()}'
    assert (workspace/'tmp').resolve() in tmp_path.resolve().parents
    shutil.rmtree(tmp_path,ignore_errors=True);tmp_path.mkdir(parents=True)
    monkeypatch.setattr(adapter,'ROOT',tmp_path);source=tmp_path/'source.zip'
    files={
      'agency.txt':'agency_id,agency_name\na,Example\n',
      'routes.txt':'route_id,route_type,route_short_name,agency_id\nb,3,B,a\nr,1,R,a\n',
      'trips.txt':'trip_id,route_id,service_id\nnight,b,s\noutside,b,s\nfrequency,b,s\nexact,b,s\nrail,r,s\ninvalid,b,s\n',
      'calendar.txt':'service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\ns,1,1,1,1,1,0,0,20230612,20230618\n',
      'calendar_dates.txt':'service_id,date,exception_type\ns,20230612,2\ns,20230617,1\n',
      'stops.txt':'stop_id,stop_name,stop_lat,stop_lon\n490a,London,51.5,-0.1\nother,Outside,51.6,-0.1\n',
      'frequencies.txt':'trip_id,start_time,end_time,headway_secs,exact_times\nfrequency,08:00:00,09:00:00,600,0\nexact,25:00:00,25:30:00,600,1\n',
      'stop_times.txt':'trip_id,arrival_time,departure_time,stop_id,stop_sequence\n'
        'night,25:00:00,25:00:00,other,3\nnight,23:55:00,23:55:00,other,1\nnight,24:20:00,24:20:00,490a,2\n'
        'outside,08:00:00,08:00:00,other,1\noutside,09:00:00,09:00:00,other,2\n'
        'frequency,08:00:00,08:00:00,490a,1\nfrequency,08:20:00,08:20:00,other,2\n'
        'exact,08:00:00,08:00:00,490a,1\nexact,08:20:00,08:20:00,other,2\n'
        'rail,08:00:00,08:00:00,490a,1\nrail,08:20:00,08:20:00,other,2\n'
        'invalid,08:00:00,08:00:00,490a,1\ninvalid,08:00:00,08:00:00,other,2\n',
    }
    with zipfile.ZipFile(source,'w') as z:
        for name,text in files.items():z.writestr(name,text)
    try:
        adapter.prepare('london',source,'2023-06-12')
        out=tmp_path/'data/processed/london_claude_gtfs'
        manifest=json.loads((out/'manifest.json').read_text())
        f=pd.read_csv(out/'trips.csv.gz')
        assert f.trip_id.tolist()==['night','exact#F90000','exact#F90600','exact#F91200']
        assert f.start_seconds.iloc[0]==86100 and f.end_seconds.iloc[0]==90000
        assert f.distance_km_lower.iloc[0]>22 and f.distance_km_upper.iloc[0]>29
        assert manifest['rejected_nonpositive_duration']==1
        assert manifest['frequency_templates_excluded_in_scope']==1
        assert manifest['exact_frequency_templates_expanded']==1
        assert manifest['exact_frequency_trips_generated']==3
        assert f.end_seconds.tolist()[1:]==[91200,91800,92400]
        st=pd.read_csv(out/'stop_times.csv.gz')
        assert st[st.trip_id=='exact#F91200'].arrival_time.tolist()==['25:20:00','25:40:00']
        assert [d['trips'] for d in manifest['daily']]==[0,4,4,4,4,4,0]
    finally:
        shutil.rmtree(tmp_path,ignore_errors=True)
