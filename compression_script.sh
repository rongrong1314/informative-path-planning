find iros_figures/experiments \( -name "*.log" -or -name "*.csv" -or -name "trajectory-N.SUMMARY.png" -or -name "world*.png" \) -exec cp --parents \{\} ./condensed_iros_experiments \;