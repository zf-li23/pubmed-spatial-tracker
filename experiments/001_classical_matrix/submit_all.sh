#!/bin/bash
# Submit all 12 dataset × feature combinations as parallel Slurm jobs.
# Each job runs 7 models on a single dataset+feature pair.
# Uses separate output files to avoid race conditions.
# After all complete, run: cat results/classical_matrix_*.csv | sort -u > results/classical_matrix.csv

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SBATCH_OPTS="--ntasks=1 --cpus-per-task=8"

for ds in ohsumed pml pgb; do
  for feat in tfidf biobert lda meta; do
    suffix="${ds}_${feat}"
    job_name="pmt-001-${suffix}"
    outfile="${SCRIPT_DIR}/slurm_${suffix}_%j.log"
    
    sbatch \
      --job-name="${job_name}" \
      --output="${outfile}" \
      ${SBATCH_OPTS} \
      --time=12:00:00 \
      --wrap="
source \$HOME/miniconda3/etc/profile.d/conda.sh
conda activate pubmed-tracker
cd ${SCRIPT_DIR}
python -u classical_matrix.py --datasets ${ds} --features ${feat} --out-suffix ${suffix}
"
  done
done

echo "All 12 jobs submitted. Use 'squeue -u \$USER' to monitor."
echo "After completion, merge results with:"
echo "  cat results/classical_matrix_*.csv | sort -u > results/classical_matrix.csv"
