#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <string.h>

#include "runfile.h"

#define MAX_BLOCKS 100 
#define LINE 1024

//char errstr[][4] = {"ERR", "OK ", "COM", "CLO"};

enum {
	IDLE = 0,
	LIST_BLOCKS,
	LIST_KEYS,
	GET_BLOCK,
	GET_TAG
};

struct {
	int operation;
	int verbosity;

	char block_name[LINE];
	char key_name[LINE];
	char runfile_name[LINE];

} options = {IDLE, 0, "", "", ""};


int load_options(int argc, char **argv)
{
	int option;
	while ( (option = getopt(argc, argv, "f:k:b:v")) >=0) {
		switch(option) {

		case 'f':
			strcpy(options.runfile_name, optarg);
			break;

		case 'k':
			strcpy(options.key_name, optarg);
			break;

		case 'b':
			strcpy(options.block_name, optarg);
			break;

		case 'v':
			options.verbosity = 1;
			break;

		default:
			printf("Unimplemented option '-%c'!\n", option);
		}
	}
	return 0;
}

int usage(char *prog)
{
	printf("Usage:\n"
	       "              %s [ -v ] [ -f runfile [ -b 'block_name' "
	       "[ -k 'key_name' ] ] ]\n\n", prog);
	return 0;
}


int list_blocks(FILE *fin)
{
	int err;
	rf_block_t block[MAX_BLOCKS];

	fseek(fin, 0, SEEK_SET);
	err = store_blocks(fin, block, MAX_BLOCKS);
	if (err < 0) return -err;
	int i;
	for ( i=0; i<err; i++) {
		printf("%s %i\n", block[i].name, block[i].count);
	}
	return 0;
}

int list_tags(FILE *fin)
{
	int err;
	rf_block_t block;
	rf_key_t key;
	key.parent = NULL;

	err = find_block(fin, &block, options.block_name);
	if (err < 0) return -err;
	int i;
	for (i=0; i<block.count; i++) {
		err = block_key( &key, &block, i, &key);
		printf("%s\n", key.name);
	}
	return 0;
}

int lookup(FILE *fin)
{
	int err;
	rf_block_t block;
	rf_key_t key;

	err = find_block(fin, &block, options.block_name);
	if (err != 0) return -err;

	err = find_key( &key, &block, options.key_name);
	if (err != 0) return -err;

	printf("%s\n", key.data);
	return 0;
}

int main(int argc, char **argv)
{
	FILE *fin = stdin;

	load_options(argc, argv);

	if (*options.runfile_name != 0) {
		fin = fopen(options.runfile_name, "r");
		if (fin==NULL) {
			fprintf(stderr, "Could not open file '%s'\n",
				options.runfile_name);
			return 1;
		}

		options.operation = LIST_BLOCKS;
		if (*options.block_name != 0) {
			options.operation = LIST_KEYS;
			if (*options.key_name != 0) {
				options.operation = GET_TAG;
			}
		}
	}

	rf_verbose = options.verbosity;

	switch (options.operation) {

	case LIST_BLOCKS:
		return list_blocks(fin);

	case LIST_KEYS:
		return list_tags(fin);

	case GET_TAG:
		return lookup(fin);

	}

	usage(argv[0]);
	return 1;
}
