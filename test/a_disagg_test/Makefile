TARGET=mem_test
include ../shared/Makefile.shared

$(TARGET): $(TARGET).o
	$(CC) $(TARGET).o -lm $(SNIPER_LDFLAGS) -o $(TARGET)

run_$(TARGET):
	../../run-sniper -v -n 1 -c nandita_cache.cfg -c usercustom.cfg --roi -- ./mem_test

CLEAN_EXTRA=viz
