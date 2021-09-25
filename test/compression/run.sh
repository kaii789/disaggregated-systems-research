# cd ../../;
# make -j 8;
# cd test/compression;
../../run-sniper -v -n 1 -c ../../disaggr_config/local_memory_cache.cfg -c ../../disaggr_config/l3cache.cfg -c ./config.cfg -- ../../benchmarks/crono/apps/sssp/sssp_pthread ../../benchmarks/crono/inputs/bcsstk25.mtx 4;

# callgrind_annotate --auto=yes --include=../../common/performance_model > 4KB_w_src.out