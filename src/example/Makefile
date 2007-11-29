CC=gcc

CFLAGS=-Wall

LIB=-lmcecmd -lconfig -lmaslog

example: example.o
	$(CC) $(CFLAGS) -o $@ $^ $(LIB) $(INC)