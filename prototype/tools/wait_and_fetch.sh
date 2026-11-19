#!/bin/bash
# Waits for the given Kaggle kernels (slugs after your Kaggle user name; set KAGGLE_USER) and downloads each output into prototype/kaggle/results_<dir>.
#   wait_and_fetch.sh sdxl-turbo-bench:results_sdxl_turbo profile-qwen21-story-bench:results_profile_qwen21-story
mkdir -p "$(dirname "$0")/../kaggle"; cd "$(dirname "$0")/../kaggle" || exit 1
P="${KAGGLE_PY:-python}"
KU="${KAGGLE_USER:?set KAGGLE_USER to your Kaggle user name}"
for i in $(seq 1 85); do
  all=1
  for pair in "$@"; do
    s=$("$P" -m kaggle.cli kernels status $KU/${pair%%:*} 2>&1 | tail -1)
    echo "$s" | grep -qiE "complete|error|cancel" || all=0
  done
  [ $all = 1 ] && break
  sleep 40
done
for pair in "$@"; do
  slug=${pair%%:*}; dir=${pair##*:}
  "$P" -m kaggle.cli kernels output $KU/$slug -p $dir >/dev/null 2>&1
  (cd $dir && rm -rf code "=0.10" cld_ckpt art_ckpt PrismLayers flux_dev_cfg)
  echo "== $slug -> $dir ($(du -sh $dir | cut -f1))"
  find $dir -name results.json | head -1 | xargs -I{} python -c "
import json
for r in json.load(open(r'{}')): print({k: v for k, v in r.items() if k in ('case','median_s','tag','compute_s','layers','error','peak_gib')})"
done
