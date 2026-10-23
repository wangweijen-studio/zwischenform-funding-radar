"""Regional official grant index; all generic discoveries require manual review."""
from adapter_common import discover
def collect(client,source,now):
    rows,errors,meta=discover(client,source,now,8)
    if not rows:errors.append({'error':'索引未辨識到可解析的相關公告；不代表沒有徵件，需人工檢查來源與解析器'})
    return rows,errors,meta
