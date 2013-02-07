#include <stdlib.h>
#include <stdio.h>
#include <errno.h>
#include <stdint.h>

int main(int argc, char **argv)
{
	if (argc<4) {
		fprintf(stderr, "Usage: %s <filename> <frame_size> <first frame> <frame count>\n",
			argv[0]);
		return 1;
	}

	int frame_size = atoi(argv[2]);
	int frame_start = atoi(argv[3]);
	int frame_count = atoi(argv[4]);

	FILE *fin = fopen(argv[1], "r");
	if (fin==NULL) {
		fprintf(stderr, "COuld not open file '%s'\n", argv[1]);
		return 1;
	}

	if (fseek(fin, frame_size*frame_start, SEEK_SET) != 0) {
		fprintf(stderr, "Could not seek to offset %i*%i=%i\n", 
			frame_start, frame_size, frame_start*frame_size);
		return 1;
	}
	
	uint32_t data[4096];
	for (; frame_count > 0; frame_count--) {
		if ( fread(data, frame_size, 1, fin) != 1) {
			fprintf(stderr, "Failed with %i frames left!\n", frame_count);
			return 1;
		}
		fwrite(data, frame_size, 1, stdout);
	}

	return 0;
}
