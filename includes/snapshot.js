// Which bronze partitions a run reads. Bronze tables require a partition filter.
function filter(column = "snapshot_date") {
  const d = dataform.projectConfig.vars.snapshot_date;
  return d ? `${column} = DATE '${d}'` : `${column} IS NOT NULL`;
}

module.exports = { filter };
