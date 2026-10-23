"""Package only explicitly allowed public website assets."""
from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1]
out=root/'_site'
out.mkdir(exist_ok=True)
shutil.copyfile(root/'index.html',out/'index.html')
shutil.copyfile(root/'residencies.html',out/'residencies.html')
(out/'data').mkdir(exist_ok=True)
for name in ('opportunities.json','scan_status.json','sources.json'):
    shutil.copyfile(root/'data'/name,out/'data'/name)
(out/'.nojekyll').touch()
