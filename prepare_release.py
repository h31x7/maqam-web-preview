"""Verify the public release and assemble its allowlisted assets; standard library only."""
from pathlib import Path
import hashlib,json,tempfile,zipfile,subprocess,sys
ROOT=Path(__file__).resolve().parent
m=json.loads((ROOT/'release-manifest.json').read_text(encoding='utf-8'))
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(1024*1024):h.update(b)
 return h.hexdigest()
def extract(path,allowed):
 with zipfile.ZipFile(path) as z:
  names=z.namelist()
  if len(names)!=len(set(names)) or set(names)!=set(allowed):raise ValueError('Unexpected archive contents')
  for name in names:
   if name.startswith('/') or '..' in Path(name).parts or '\\' in name:raise ValueError('Unsafe path')
  if z.testzip():raise ValueError('Corrupt archive')
  z.extractall(ROOT/'app')
p=ROOT/m['main']['name']
if digest(p)!=m['main']['sha256']:raise ValueError('Source checksum mismatch')
extract(p,m['mainFiles'])
with tempfile.TemporaryDirectory(dir=ROOT) as directory:
 combined=Path(directory)/'books.zip'
 with combined.open('wb') as dest:
  for item in m['parts']:
   p=ROOT/item['name']
   if digest(p)!=item['sha256']:raise ValueError('Book part checksum mismatch')
   with p.open('rb') as source:
    while b:=source.read(1024*1024):dest.write(b)
 if digest(combined)!=m['booksSha256']:raise ValueError('Books checksum mismatch')
 extract(combined,m['bookFiles'])
print('Verified Maqam release assembled in app/')

# The only added runtime dependency is pinned in the verified app archive.
subprocess.check_call([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-r", str(ROOT/"app"/"requirements.txt")])
