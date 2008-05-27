#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>

typedef unsigned int mceword_t;
#define WORD_FORMAT "%11u"

#define HEADER_WORDS 43
#define FOOTER_WORDS  1
#define MAX_ROWS     64
#define MAX_COLS     64

int seek_frame(FILE *fin, int frame_index, int frame_sizew)
{
	int whence = (frame_index >= 0) ? SEEK_SET : SEEK_END;

	if ( fseek(fin, frame_sizew*frame_index*sizeof(mceword_t), whence) )
		return -1;
	
	return 0;
}

int read_words(FILE *fin, mceword_t *words, int n_words)
{
	if (fread(words, sizeof(mceword_t), n_words, fin)!=n_words)
		return -1;

	return 0;
}

int dump_words(mceword_t *words, int rows, int cols, char *format)
{
	int i, j;
	
	for (i=0; i<HEADER_WORDS; i++)
		printf(format, *(words++));

	printf("\n");

	for (i=0; i<rows; i++) {
		for (j=0; j<cols; j++)
			printf(format, *(words++));
		printf("\n");
	}

	for (i=0; i<FOOTER_WORDS; i++)
		printf(format, *(words++));

	return 0;
}

#define USAGE "Usage:\n\n    %s <rows> <columns> <filename> <index> [<format>]\n\n"

int main(int argc, char **argv)
{
	int rows, cols, fidx, frame_size;
	mceword_t frame[HEADER_WORDS + FOOTER_WORDS + MAX_ROWS*MAX_COLS];
	FILE *fin;
	char format[16] = WORD_FORMAT;

	if (argc!=5 && argc!=6) {
		fprintf(stderr, USAGE, argv[0]);
		return 1;
	}

	rows = atoi(argv[1]);
	cols = atoi(argv[2]);
	fidx = atoi(argv[4]);
	frame_size = HEADER_WORDS + FOOTER_WORDS + rows*cols;

	if (argc==6)
		strcpy(format, argv[5]);
	strcat(format, " ");

	fin = fopen(argv[3], "r");
	if (fin==NULL) {
		fprintf(stderr, "Couldn't open '%s'\n", argv[3]);
		return 1;
	}
	
	if (seek_frame(fin, fidx, frame_size) != 0) {
		fprintf(stderr, "Couldn't seek to index %i\n", fidx);
		return 1;
	}

	if (read_words(fin, frame, frame_size) != 0) {
		fprintf(stderr, "Couldn't read frame of size %i\n",
			frame_size);
		return -1;
	}

	if (dump_words(frame, rows, cols, format) != 0) {
		fprintf(stderr, "Why would you want ascii?\n");
		return -1;
	}

	return 0;
}
