#ifndef __RUNFILE_H__
#define __RUNFILE_H__

#include <stdio.h>


/* Error codes - keep static between version if possible */

#define RF_SUCCESS                     0
#define RF_ARGS_BAD                    1
#define RF_FILE_BAD                    2 
#define RF_FILE_ERROR                  3
#define RF_TOO_MANY_BLOCKS             4
#define RF_KEY_NOT_FOUND              10
#define RF_BLOCK_UNINITIALIZED        20
#define RF_BLOCK_NOT_FOUND            21
#define RF_BLOCK_BAD_CLOSURE          22
#define RF_BLOCK_NO_CLOSURE           23

extern int rf_verbose;

#define RF_NAME 256
#define RF_DATA 1024
#define RF_LINE 1300

typedef struct {

	char name[RF_NAME];
	
	FILE *fin;
	long fstart;
	long fend;

	int  count;

} rf_block_t;

typedef struct {

	char name[RF_NAME];
	char data[RF_DATA];

	rf_block_t *parent;
	int fend;
	int index;

} rf_key_t;


int remove_tag(char *s, char **tag, char **data);

int store_blocks(FILE *fin, rf_block_t *block, int max_blocks);

int block_key( rf_key_t *key, rf_block_t *block, int idx,
	       const rf_key_t *last_key);

int find_block(FILE *fin, rf_block_t *block, const char *name);

int find_key(rf_key_t *key, rf_block_t *block, const char *name);


#endif /* __RUNFILE_H__ */
