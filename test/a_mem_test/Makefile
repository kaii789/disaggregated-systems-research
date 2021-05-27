TARGET=simple_mem_test
include ../shared/Makefile.shared

$(TARGET): $(TARGET).o
	$(CC) $(TARGET).o -lm $(SNIPER_LDFLAGS) -o $(TARGET)

run_$(TARGET):
	../../run-sniper -v -n 1 -c gainestown -c usercustom.cfg --roi --viz -- ./simple_mem_test

CLEAN_EXTRA=viz
