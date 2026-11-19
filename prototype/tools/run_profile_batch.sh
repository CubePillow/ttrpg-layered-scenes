#!/bin/bash
# Waits for profile bench sessions, downloads their outputs (dropping big model folders), optionally pushes the next two.
#   run_profile_batch.sh "wait1 wait2" "push1 push2"
# Example: run_profile_batch.sh "sam2 reveallayer" "cld artplus"   (then waits for the second pair as well)
mkdir -p "$(dirname "$0")/../kaggle"
K="$(cd "$(dirname "$0")/../kaggle" && pwd)"
P="${KAGGLE_PY:-python}"
KU="${KAGGLE_USER:?set KAGGLE_USER to your Kaggle user name}"
cd "$K" || exit 1

wait_for() {
  for i in $(seq 1 85); do
    all=1
    for n in "$@"; do
      s=$("$P" -m kaggle.cli kernels status $KU/profile-$n-bench 2>&1 | tail -1)
      echo "$s" | grep -qiE "complete|error|cancel" || all=0
    done
    [ $all = 1 ] && return
    sleep 40
  done
}

fetch() {
  for n in "$@"; do
    "$P" -m kaggle.cli kernels output $KU/profile-$n-bench -p results_profile_$n >/dev/null 2>&1
    (cd results_profile_$n && rm -rf code cld_ckpt cld_tvae art_ckpt art_tvae PrismLayers CLD RevealLayer flux_dev_cfg vit32 "=0.10" reveal_req)
    echo "== $n: $(du -sh results_profile_$n | cut -f1)"
    find results_profile_$n -name results.json | head -1 | xargs -I{} python -c "
import json
for r in json.load(open(r'{}')):
    print(r['tag'], r['path'], 'compute', r.get('compute_s'), 'runs', r.get('all_runs_s'), 'layers', r.get('layers'), 'diff', r.get('recomposite_diff'), str(r.get('error',''))[:160])"
    grep -ahoE "PROFILE LOADED[^\"]{0,40}|BENCH DONE[^\"]{0,40}|Error[^\"]{0,200}" results_profile_$n/*.log | head -4
  done
}

wait_for $1
fetch $1
if [ -n "$2" ]; then
  for n in $2; do
    (cd upload_profile_${n}_bench && "$P" -m kaggle.cli kernels push -p . 2>&1 | tail -1)
  done
  wait_for $2
  fetch $2
fi
