TARGET=mem_test
#TARGET=mem_test_varied
include ../shared/Makefile.shared

$(TARGET): $(TARGET).o
	$(CC) $(TARGET).o -lm $(SNIPER_LDFLAGS) -o $(TARGET)

run_$(TARGET):
	../../run-sniper -v -n 1 -c ../../disaggr_config/local_memory_cache.cfg --roi -- ./mem_test
#	../../run-sniper -v -n 1 -c ../../disaggr_config/local_memory_cache.cfg -s stop-by-icount:5000000 --roi -- ./mem_test
#	../../run-sniper -v -n 1 -c ../../disaggr_config/local_memory_cache.cfg --roi -- ./mem_test_varied

CLEAN_EXTRA=viz
