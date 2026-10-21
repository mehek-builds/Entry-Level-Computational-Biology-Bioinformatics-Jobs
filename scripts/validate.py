"""Validate published role mirrors and known exclusions without network reads."""
import argparse,csv,io,json,re,subprocess
from pathlib import Path
from datetime import date,datetime,timedelta
ID=re.compile(r'/job/([a-f0-9-]{36})')
LINK=re.compile(r'\]\((https://trylitos\.com/job/[^)]+)\)')
def require(ok,message):
 if not ok:raise ValueError(message)
def markdown_links(text):
 return [(ID.search(u).group(1),u)for u in LINK.findall(text)]
def validate(root,baseline=None):
 root=Path(root);excluded={j['id']for j in json.loads((root/'eligibility-exclusions.json').read_text())['jobs']};files={};sets={};all_rows=None
 for p in sorted((root/'csv').glob('*.csv')):
  rows=list(csv.DictReader(io.StringIO(p.read_text())));pairs=[]
  for row in rows:
   m=ID.search(row['Link']);require(m is not None,f'{p.name}: invalid job link');pairs.append((m.group(1),row['Link']))
  ids=[i for i,u in pairs];require(len(ids)==len(set(ids)),f'{p.name}: duplicate job');require(not excluded.intersection(ids),f'{p.name}: excluded job')
  md=root/('README.md'if p.stem=='all'else f'lists/{p.stem}.md');text=md.read_text();mdpairs=markdown_links(text);mdids=[i for i,u in mdpairs]
  require(len(mdids)==len(set(mdids)),f'{md.name}: duplicate job');require(set(mdids)==set(ids),f'{md.name}: CSV membership mismatch')
  companies=len({r['Company']for r in rows});n=len(rows)
  if p.stem=='all':
   require(f'**{n} title-screened leads' in text and f'at {companies} US employers.**'in text,'README total or company count')
   snapshot=re.search(r'Snapshot (\d{2} [A-Z][a-z]{2} \d{4})',text);require(snapshot is not None,'snapshot date missing');end=datetime.strptime(snapshot[1],'%d %b %Y').date();start=(end-timedelta(days=6)).toordinal()
   recent=sum(start<=date.fromisoformat(r['Posted']).toordinal()<=end.toordinal()for r in rows if r['Posted'])
   require(f"{recent} have posting dates in the seven-day window ending {end.strftime('%d %b %Y')}."in text,'README recent count or date interval')
   require(f"{sum(bool(r['Visa signal'].strip())for r in rows)} at employers with a visa sponsorship record."in text,'README visa count');all_rows=set(ids)
  else:
   require(re.search(r'^# '+str(n)+r'\b',text)is not None,f'{md.name}: heading count')
   require(f'**{n} roles at {companies} companies.**'in text,f'{md.name}: summary counts')
   summary=(root/'README.md').read_text();require(re.search(r'\]\(lists/'+re.escape(p.stem)+r'\.md\) \| '+str(n)+r' \| '+str(companies)+r' \|',summary)is not None,f'{md.name}: README category count')
  sets[p.stem]=set(ids);files[str(p.relative_to(root))]=dict(pairs);files[str(md.relative_to(root))]=dict(mdpairs)
 require(all_rows is not None,'all CSV missing')
 require(set().union(*(v for k,v in sets.items()if k!='all'))==all_rows,'category union differs from all roles')
 require({p.stem for p in(root/'lists').glob('*.md')}==set(sets)-{'all'},'unpaired category Markdown')
 if baseline:
  for path,old in baseline.items():
   require(path in files,'published path lost')
   for jid,url in old.items():
    if jid in files[path]:require(files[path][jid]==url,f'{path}: surviving link changed')
 return {'roles':len(all_rows),'categories':len(sets)-1,'published_files':len(files),'excluded_absent':len(excluded)}
def git_baseline(root,ref):
 paths=subprocess.check_output(['git','ls-tree','-r','--name-only',ref],cwd=root,text=True).splitlines();result={}
 for path in paths:
  if path=='README.md'or path.startswith('lists/')and path.endswith('.md'):
   text=subprocess.check_output(['git','show',f'{ref}:{path}'],cwd=root,text=True);result[path]=dict(markdown_links(text))
  elif path.startswith('csv/')and path.endswith('.csv'):
   text=subprocess.check_output(['git','show',f'{ref}:{path}'],cwd=root,text=True);result[path]={ID.search(r['Link']).group(1):r['Link']for r in csv.DictReader(io.StringIO(text))}
 return result
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--base');args=parser.parse_args();root=Path(__file__).resolve().parents[1]
 print(json.dumps(validate(root,git_baseline(root,args.base)if args.base else None)))
