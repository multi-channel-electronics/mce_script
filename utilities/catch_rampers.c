#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <linux/types.h>

#define RAMP_AMP 6000

#define FILTER_GAIN 1218.
int main(int argc, char **argv)
{
	int i;

	if (argc<4) {
		fprintf(stderr, "Usage: %s <filename> <frame_size> <first frame> <frame count>\n",
			argv[0]);
		return 1;
	}

	int frame_size = atoi(argv[2]);
	int frame_start = atoi(argv[3]);
	int frame_count = atoi(argv[4]);

	double* data_max = malloc(frame_size * sizeof(double));
	double* data_min = malloc(frame_size * sizeof(double));
	int* flips = malloc(frame_size * sizeof(int));
	__u32 *last_state = malloc(frame_size * sizeof(__u32));
	__u32 flip_mask = 0x40000000;

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
	
	__u32 data[4096];
	
	__u32 mode_mask = 0xffffff80;
	__u32 mode_sign = 0x80000000;
	double rescale = 1./128. * 8;

	int first = 1;
	int offset = 43;
	int count = 32*33;
	double gain = FILTER_GAIN / 2;

	for (; frame_count > 0; frame_count--) {
		if ( fread(data, frame_size, 1, fin) != 1) {
			fprintf(stderr, "Failed with %i frames left!\n", frame_count);
			return 1;
		}
		if (first) {
			for (i=0; i<count; i++) {
				__u32 d = (data[i+offset]) & mode_mask;
/* 				if (d & mode_sign) d |= 0xff000000; */
				double x = (*((int*)&d)) /gain * rescale;
//				printf("%i %u %lf\n", i, d, x);
				
				data_max[i] = x;
				data_min[i] = x;
				last_state[i] = data[i+offset] & flip_mask;
			}
			first = 0;
		} else {
			for (i=0; i<count; i++) {
				int me = (i == 4*32 + 4);
				__u32 d = (data[i+offset]) & mode_mask;
/* 				if (d & mode_sign) d |= 0xff000000; */
/* 				double x = (int)d; */
				double x = (*((int*)&d)) / gain * rescale;

/* 				if (me) printf("%ui\n", d); */
				if (x > data_max[i]) data_max[i] = x;
				if (x < data_min[i]) data_min[i] = x;
				if ((d & flip_mask) != last_state[i]) {
					flips[i]++;
					last_state[i] = d & flip_mask;
				}
				

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
		x = flips[i];
		if (x > 1000) {
			printf("Flipper? %i %i = r%02ic%02i   %lf to %lf\n",
			       x,
			       i, i / 32, i % 32, data_min[i], data_max[i]);
		}
	}

	return 0;
}
