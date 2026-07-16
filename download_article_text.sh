#!/bin/bash

#SBATCH -p general
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --mem=32g
#SBATCH -t 3-00:00:00
#SBATCH --mail-type=all
#SBATCH --job-name=download_text

module purge
module load anaconda

export PYTHONWARNINGS="ignore"
source config.sh

conda activate $MAIN_CONDA_ENV_PATH

python3.12 download_article_text_first_pass.py "cyankiwi/gemma-4-12B-it-AWQ-INT4"