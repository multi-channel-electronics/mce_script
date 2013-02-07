/* #include <stdio.h> */
/* #include <stdlib.h> */
#include <stdint.h>

/* #include <math.h> */
/* #include <string.h> */
/* #include <fcntl.h> */

/* #include <unistd.h> */
/* #include <sys/ioctl.h> */

#ifndef u32
#define u32 uint32_t
#endif

struct sequence_analyser {

	int start;
	int index;
	int anomaly;
	int offset;

	int frame_flag;
	int sequence_flag;

	char name[32];

#define FLAG_ORDER 0x0001
	
};

int sequence_init(struct sequence_analyser *seq, u32 start,
		  const char *name, int offset);

int sequence(struct sequence_analyser *seq, u32 *data, char *msg);

