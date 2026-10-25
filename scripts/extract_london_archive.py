"""Seek an openly published ZIP using HTTP Range; never fetch the entire 19 GB."""
import io,zipfile,json,requests,time,argparse,hashlib,datetime
from pathlib import Path
OUT=Path(__file__).resolve().parents[1]/'materials/sources/raw/comparator_timetables'

class HTTPFile(io.RawIOBase):
    def __init__(self,url,size):self.url=url;self.size=size;self.pos=0
    def seekable(self):return True
    def readable(self):return True
    def tell(self):return self.pos
    def seek(self,offset,whence=0):
        self.pos=offset if whence==0 else self.pos+offset if whence==1 else self.size+offset
        return self.pos
    def read(self,n=-1):
        if n<0:n=self.size-self.pos
        n=min(n,self.size-self.pos)
        if n<=0:return b''
        if n>600*1024*1024:raise ValueError('range exceeds safety cap')
        start=self.pos;end=start+n-1
        for attempt in range(3):
            try:
                with requests.get(self.url,headers={'Range':f'bytes={start}-{end}'},stream=True,timeout=(20,60)) as r:
                    if r.status_code!=206:raise ValueError(f'Range unsupported {r.status_code}')
                    # A cache must not supply a previous range in response to a new request.
                    if not r.headers.get('Content-Range','').startswith(f'bytes {start}-{end}/'):
                        raise ValueError(f'Unexpected range {r.headers.get("Content-Range")}')
                    data=b''.join(r.iter_content(1024*1024))
                if len(data)!=n:raise ValueError('short range')
                self.pos+=n;return data
            except (requests.RequestException,ValueError):
                if attempt==2:raise
                time.sleep(1)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--member');a=p.parse_args()
    rec=json.loads((OUT/'zenodo_record.json').read_text())['files'][0]
    with zipfile.ZipFile(HTTPFile(rec['links']['self'],rec['size'])) as z:
        listing=[dict(name=x.filename,bytes=x.file_size,compressed=x.compress_size,offset=x.header_offset) for x in z.infolist()]
        (OUT/'london_archive_directory.json').write_text(json.dumps(listing,indent=2))
        print(json.dumps(listing[:5],indent=2),len(listing),'members',flush=True)
        if a.member:
            target=OUT/'london_2023.zip'
            with z.open(a.member) as src,target.with_suffix('.part').open('wb') as dst:
                while data:=src.read(1024*1024):dst.write(data)
            target.with_suffix('.part').replace(target)
            (OUT/'london_2023_provenance.json').write_text(json.dumps(dict(
                archive_url=rec['links']['self'],archive_published_md5=rec['checksum'],
                archive_member=a.member,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),indent=2))
            print('extracted',target.stat().st_size,flush=True)
