"""Retrieve public source files only; preserve URLs, dates and SHA-256 hashes."""
from pathlib import Path
import requests,hashlib,json,datetime,concurrent.futures

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'materials/sources/raw/comparator_timetables'
SOURCES={
 'chicago_2023.zip':'https://openmobilitydata-data.s3.us-west-1.amazonaws.com/public/feeds/chicago-transit-authority/165/20230503/gtfs.zip',
 'zenodo_record.json':'https://zenodo.org/api/records/14779119',
}

def fetch(item):
    name,url=item;path=OUT/name
    if path.exists():return name,dict(status='cached',bytes=path.stat().st_size,url=url,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    try:
        part=path.with_suffix(path.suffix+'.part')
        offset=part.stat().st_size if part.exists() else 0
        with requests.get(url,headers={'Range':f'bytes={offset}-'} if offset else {},stream=True,timeout=(30,60)) as r:
            r.raise_for_status()
            if offset and r.status_code==206:
                assert r.headers.get('Content-Range','').startswith(f'bytes {offset}-')
            else:offset=0
            size=offset
            with part.open('ab' if offset else 'wb') as f:
                for chunk in r.iter_content(1024*1024):
                    size+=len(chunk)
                    if size>800*1024*1024:raise ValueError('800 MiB download cap exceeded')
                    f.write(chunk)
            part.replace(path)
            result=dict(status='downloaded',url=url,final_url=r.url,bytes=size,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        last_modified=r.headers.get('Last-Modified'),content_type=r.headers.get('Content-Type'))
            print(name,size,'bytes',flush=True);return name,result
    except Exception as e:
        print(name,type(e).__name__,str(e)[:200],flush=True)
        return name,dict(status='error',url=url,error=str(e))

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        result=dict(pool.map(fetch,SOURCES.items()))
    manifest=OUT/'download_manifest.json'
    prior=json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {}
    for name,entry in result.items():
        if entry['status']!='cached' or name not in prior:prior[name]=entry
    manifest.write_text(json.dumps(prior,indent=2),encoding='utf-8')
