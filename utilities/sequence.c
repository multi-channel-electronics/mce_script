#include <stdio.h>
#include <stdlib.h>

#include <math.h>
#include <string.h>
#include <fcntl.h>

#include <unistd.h>

#include "sequence.h"

int sequence_init(struct sequence_analyser *seq, u32 start,
		  const char *name, int offset)
{
	seq->start = start;
	seq->index = start;
	seq->offset = offset;
	seq->anomaly = 0;
	if (name==NULL) {
		strcpy(seq->name, "field");
	} else {
		strcpy(seq->name, name);
	}
	return 0;
}

int sequence(struct sequence_analyser *seq, u32 *data, char *msg)
{
	int x = data[seq->offset];
	
	if (x != seq->index) {
		sprintf(msg, "surprise %s %i, after sequence [%i,%i)",
			seq->name, x, seq->start, seq->index);
		seq->anomaly++;
		seq->start = x;
		seq->index = x+1;
		return -1;
	}

	*msg=0;
	seq->index++;
	return 0;
}

