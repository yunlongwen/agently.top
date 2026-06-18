# Archive 分支

本分支由采集流程自动写入,存放 `output/` 的镜像归档数据。

- 目录结构:`archive/<source_id>/<YYYY-MM-DD>/<batch>.json` + `archive/latest.json`
- 生成频率:跟随采集调度(默认每天 3 次)
- 请勿手动编辑;数据由 `archive_sync.py` 维护
