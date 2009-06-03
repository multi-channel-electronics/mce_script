#include "mce_header.h"

#include <stdio.h>
#include <stdlib.h>

#define MIN_READ_SIZE (44 * 4)

#define RC_SHIFT    10
#define RC_BITS     0x00003c00
#define COL_SHIFT   16
#define COL_BITS    0x000f0000

static int count_bits(int x)
{
	int n = 0;
	for (int i=0; i<sizeof(x)*8; i++) n += ((x>>i) & 1);
	return n;
}

static void v6_fill(mce_header_t *dest, int *buffer)
{
	dest->n_rows_rep = buffer[3];
	dest->n_cols_rep = N_COL;
	dest->n_rc = 0;
	dest->version = buffer[6];
	dest->header_size = 43;
	dest->footer_size = 1;

	dest->row_len = buffer[2];
	dest->n_rows_mux = buffer[9];
	dest->mux_rate = 50.e6 / (dest->row_len * dest->n_rows_mux);

	// If no RC, force all RC.
	if (count_bits(buffer[0] & RC_BITS) == 0) buffer[0] |= RC_BITS;
	for (int i=0; i<N_RC; i++) {
		int p = (buffer[0] >> (RC_SHIFT+i)) & 1;
		dest->rc_present[i] = p;
		dest->n_rc += p;
	}
	
	// Status bits override n_cols_rep default
	if (count_bits(buffer[0] & COL_BITS) != 0)
		dest->n_cols_rep = (buffer[0] & COL_BITS) >> COL_SHIFT;
}

mce_header_t *get_header(char *filename, FILE *f)
{
	fpos_t start;
	int buffer[MIN_READ_SIZE];
	if (f==NULL)
		f = fopen(filename, "rb");
	if (f==NULL) {
		fprintf(stderr, "get_header got a whole lot of NULLs.\n");
		return NULL;
	}
	
	// Minimal read
	fgetpos(f, &start);
	int n = fread(buffer, sizeof(*buffer), MIN_READ_SIZE, f);
	fsetpos(f, &start);
	if (n != MIN_READ_SIZE) {
		fprintf(stderr, "could not read header, 0 length file?\n");
		return NULL;
	}

	// Good enough.
	mce_header_t *h = calloc(1, sizeof(*h));
	
	// Determine version
	int version = buffer[6];
	switch (version) {
	case 6:
	case 7:
		v6_fill(h, buffer);
		break;
	default:
		fprintf(stderr, "unrecognized header version %i, trying anyway.\n",
			version);
		v6_fill(h, buffer);
	}
       
	return h;
}
