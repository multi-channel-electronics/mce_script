#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <stdint.h>
#include <assert.h>

#define RAMP_AMP 6000

#define FILTER_GAIN 1218.

#ifndef __i32
#define __i32 int
#endif

uint32_t* extract_bitfield(uint32_t *data, int count, int bit_start, int bit_count,
			int signed_out, int in_place, uint32_t *_data_out)
{
	int i;
	uint32_t *data_out = data;
	int left_shift = 32 - bit_start - bit_count;
	int right_shift = 32 - bit_count;

	if (!in_place) {
		if (_data_out == NULL) {
			data_out = malloc(count * sizeof(uint32_t));
		} else {
			data_out = _data_out;
		}
	}
	if (data_out == NULL)
		return NULL;
	
	if (signed_out) {
		__i32 divisor = (1 << right_shift);
		for (i=0; i<count; i++)
			data_out[i] = ((__i32)(data[i] << left_shift)) / divisor;
	} else {
		for (i=0; i<count; i++)
			data_out[i] = (data[i] << left_shift) >> right_shift;
	}
	return data_out;
}

int main(int argc, char **argv)
{
	assert(sizeof(__i32)==4);

	int i;

	// Data mode 10...
	int bit_start = 7;
	int bit_count = 25;

	if (argc<4) {
		fprintf(stderr, "Usage: %s <filename> <frame_size> <first frame> <frame count>\n",
			argv[0]);
		return 1;
	}

	int frame_size = atoi(argv[2]);
	int frame_start = atoi(argv[3]);
	int frame_count = atoi(argv[4]);

	float* data_max = malloc(frame_size * sizeof(float));
	float* data_min = malloc(frame_size * sizeof(float));

	FILE *fin = fopen(argv[1], "r");
	if (fin==NULL) {
		fprintf(stderr, "Could not open file '%s'\n", argv[1]);
		return 1;
	}

	if (fseek(fin, frame_size*frame_start, SEEK_SET) != 0) {
		fprintf(stderr, "Could not seek to offset %i*%i=%i\n", 
			frame_start, frame_size, frame_start*frame_size);
		return 1;
	}
	
	uint32_t data[4096];

	float rescale = 1./128. * 8;

	int first = 1;
	int offset = 43;
	int count = 32*33;

	for (; frame_count > 0; frame_count--) {
		if ( fread(data, frame_size, 1, fin) != 1) {
			fprintf(stderr, "Failed with %i frames left!\n", frame_count);
			return 1;
		}
		// Get feedback data only
		extract_bitfield(data+offset, count, bit_start, bit_count, 1, 1, NULL);

		if (first) {
			for (i=0; i<count; i++) {
				float x = (float)(int)data[i+offset] * rescale;
				data_max[i] = x;
				data_min[i] = x;
			}
			first = 0;
		} else {
			for (i=0; i<count; i++) {
				float x = (float)(int)data[i+offset] * rescale;
				if (x > data_max[i]) data_max[i] = x;
				if (x < data_min[i]) data_min[i] = x;
			}
		}		
	}

	for (i=0; i<count; i++) {
		int x = (((data_max[i] - data_min[i])) > RAMP_AMP);
		if (x) {
			printf("Ramper? %i %i = r%02ic%02i   %lf to %lf\n",
			       x,
			       i, i / 32, i % 32, data_min[i], data_max[i]);
		}
	}

	return 0;
}
