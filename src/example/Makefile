CC=gcc

# -std=c99 lets us define vars anywhere...
CFLAGS=-Wall -std=c99

LIB=-lmcecmd -lconfig -lmaslog

example: example.o
	$(CC) $(CFLAGS) -o $@ $^ $(LIB) $(INC)

tidy:
	-rm *.o *~ #*

clean: tidy
	-rm example
