import hashlib,json,struct,time,urllib.request,urllib.error,zlib
from pathlib import Path
root=Path(__file__).resolve().parent
record=json.loads((root/'zenodo-record.json').read_text())
entry=next(f for f in record['files'] if f['key']=='basin_timeseries_v1p2_metForcing_obsFlow.zip')
url=entry['links']['self']
size=entry['size']
requests=json.loads((root/'archive-requests.json').read_text())
def get(name,url,limit,span=None):
    if len(requests)>=8 or sum(x.get('body_bytes',0) for x in requests)+limit>4*1024**2:raise ValueError('request budget')
    item={'name':name,'url':url,'max_body_bytes':limit,'range':span,'status':'intent'}
    requests.append(item)
    (root/'archive-requests.json').write_text(json.dumps(requests,indent=2)+'\n')
    headers={'User-Agent':'Autoengineering-source-metadata-review/0.2','Accept-Encoding':'identity'}
    if span:headers['Range']=f'bytes={span[0]}-{span[1]}'
    start=time.monotonic()
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=40) as response:
            item.update(http_status=response.status,final_url=response.url,etag=response.headers.get('ETag'),content_range=response.headers.get('Content-Range'))
            if span and (response.status!=206 or response.headers.get('Content-Range')!=f'bytes {span[0]}-{span[1]}/{size}'):raise ValueError('server did not honor exact range')
            data=response.read(limit+1)
            if len(data)>limit or (span and len(data)!=span[1]-span[0]+1):raise ValueError('response bound')
            with (root/name).open('xb') as f:f.write(data)
            item.update(status='complete',body_bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
        return data
    except Exception as error:
        item.update(status='failed',error_type=type(error).__name__)
        if isinstance(error,urllib.error.HTTPError):item['http_status']=error.code
        raise
    finally:
        item.update(elapsed_seconds=time.monotonic()-start,total_network_bytes=None,total_http_exchanges=None)
        (root/'archive-requests.json').write_text(json.dumps(requests,indent=2)+'\n')
        print(json.dumps(item),flush=True)
central=(root/'archive-directory.bin').read_bytes()
count=17728
files=[]
position=0
while position<len(central):
    values=struct.unpack('<4s6H3I5H2I',central[position:position+46])
    if values[0]!=b'PK\x01\x02':raise ValueError('directory entry')
    name_len,extra_len,comment_len=values[10:13]
    name=central[position+46:position+46+name_len].decode('utf-8' if values[3]&2048 else 'cp437')
    files.append({'name':name,'compressed_bytes':values[8],'uncompressed_bytes':values[9],'compression':values[4],'crc32':values[7],'local_header_offset':values[16]})
    position+=46+name_len+extra_len+comment_len
if position!=len(central) or len(files)!=count:raise ValueError('directory count')

selected=[f for f in files if f['name'].startswith('basin_dataset_public_v1p2/readme')]
start=min(f['local_header_offset'] for f in selected)
last=max(f['local_header_offset'] for f in selected)
stop=min(f['local_header_offset'] for f in files if f['local_header_offset']>last)
if stop-start>16384 or any(f not in selected for f in files if start<=f['local_header_offset']<stop):raise ValueError('non-documentation member in range')
data=get('archive-readme-block.bin',url,stop-start,(start,stop-1))
checks=[]
for f in selected:
    offset=f['local_header_offset']-start
    header=struct.unpack('<4s5H3I2H',data[offset:offset+30])
    if header[0]!=b'PK\x03\x04' or header[2]&1 or header[3]!=8:raise ValueError('readme header')
    n,e=header[9:11]
    name=data[offset+30:offset+30+n].decode('utf-8')
    if name!=f['name']:raise ValueError('readme path differs')
    payload=data[offset+30+n+e:offset+30+n+e+f['compressed_bytes']]
    decoder=zlib.decompressobj(-15)
    value=decoder.decompress(payload,16385)
    if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail or len(value)!=f['uncompressed_bytes'] or len(value)>16384 or zlib.crc32(value)!=f['crc32']:raise ValueError('readme integrity')
    filename=Path(name).name
    with (root/filename).open('xb') as output:output.write(value)
    checks.append({'path':filename,'archive_member':name,'size_bytes':len(value),'sha256':hashlib.sha256(value).hexdigest(),'crc32_verified':True})
(root/'readme-extraction.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps({'readme_members':len(checks),'time_series_members_opened':0}),flush=True)
