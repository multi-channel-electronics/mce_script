#ifndef __MCEHEADER_H__
#define __MCEHEADER_H__

#include <stdio.h>

#define N_RC 4
#define N_ROW 41
#define N_COL 8

typedef struct {
	int version;
	int header_size;        /* in 32-bit words */
	int footer_size;        /* in 32-bit words */

	/* Structural */
	int n_rows_rep;         /* per RC */
	int n_cols_rep;         /* per RC */
	int n_rc;               /* 1-4 */
	int rc_present[N_RC];
	
	/* Timing */
	int n_rows_mux;
	int row_len;
	double mux_rate;
} mce_header_t;

/* Pass a data filename or an open file (offset will not be changed) */

mce_header_t *get_header(char *filename, FILE *f);


#endif
