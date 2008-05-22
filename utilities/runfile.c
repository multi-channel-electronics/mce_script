#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "runfile.h"

int rf_verbose = 0;

enum {
       RF_ERR=-1,
       RF_COM=0,
       RF_CLO=1,
       RF_OK=2,
};

/* utilities */

#define WHITE   " \t\n"
#define COMMENT "#"
#define LEFTB   '<'
#define RIGHTB  '>'

static char* eat_whitespace(char *start)
{
	while (index(WHITE, *start)!=NULL) start++;
	return start;
}

/* Removes leading and trailing whitespace from s, compresses any
 * intermediate whitespace into a single space. */

static void convert_whitespace(char *s)
{
	char *dest = s;
	int first_word = 1;

	while (*s!=0) {
		while ( *s!= 0 && index(WHITE, *s)!=NULL ) s++;
		
		if (*s != 0 && !first_word)
			*dest++ = ' ';

		first_word = 0;

		while ( *s!=0 && index(WHITE, *s)==NULL )
			*dest++ = *s++;
	}

	*dest = 0;
	
}


//static
int remove_tag(char *s, char **tag, char **data)
{
	int i;

	*tag = NULL;
	*data = NULL;

	convert_whitespace(s);

	//Check comment
	if (*s==0) return RF_COM;
	if (index(COMMENT, *s)!=NULL)
		return RF_COM;

	//Check key
	if (*s!=LEFTB)
		return RF_ERR;

	//Discover right bracket

	*tag = s;
	while (*(++s) != RIGHTB) {
		if (s==0) {
			*tag = NULL;
			return RF_ERR;
		}
	}
	
	// [tag,s] is <...>
	for (i=0; i < (s-*tag-1); i++)
		(*tag)[i] = (*tag)[i+1];
	(*tag)[i] = 0;

	*data = ++s;

	convert_whitespace(*tag);
	convert_whitespace(*data);

	if (**tag == '/') {
		(*tag) ++;
		return RF_CLO;
	}

	return RF_OK;
}

static int strip_brackets(char *s, const char *bset)
{
	int i;

	if (s[0]!=bset[0] || s[strlen(s)-1]!=bset[1])
		return -1;

	for (i=1; i<strlen(s)-2; i++)
		s[i-1] = s[i];
	*s = 0;
	return 0;
}


static int block_store(FILE *fin, rf_block_t *block, const char *b_tag)
{
	int line_count = 1;
	char line[RF_LINE];
	char *tag, *data;

	block->fstart = ftell(fin);
	block->fin = fin;
	block->count = 0;
	strcpy(block->name, b_tag);

	while (fgets(line, RF_LINE, fin)!=NULL) {
		switch(remove_tag(line, &tag, &data)) {
		case RF_COM:
			break;

		case RF_ERR:
			if (rf_verbose)
				fprintf(stderr, "Runfile format error!\n");
			return -RF_FILE_BAD;
			
		case RF_CLO:
			if (strcmp(tag, block->name)!=0) {
				if (rf_verbose)
					fprintf(stderr,
					"Bad closure of block %s with tag %s\n",
					block->name, tag);
				return -RF_BLOCK_BAD_CLOSURE;
			}
			return 0;

		case RF_OK:
			block->count++;
			break;
		}
		line_count++;
		block->fend = ftell(fin);
	}
	if (rf_verbose)
		fprintf(stderr, "Block %s doesn't end\n", block->name);
	return -RF_BLOCK_NO_CLOSURE;
}



int traverse_blocks(FILE *fin, rf_block_t *block,
		    int store_all, int target, int max, const char *name)
{
	int  block_count = 0;
	int  line_count = 1;
	char line[RF_LINE];
	char *tag, *data;
	int  err = 0;

	while (fgets(line, RF_LINE, fin)!=NULL) {

		switch(remove_tag(line, &tag, &data)) {

		case RF_COM:
			break;

		case RF_ERR:
			if (rf_verbose)
				fprintf(stderr, "Runfile format error!\n");
			return -RF_FILE_BAD;
			break;
			
		case RF_CLO:
			if (rf_verbose)
				fprintf(stderr,
					"Unexpected closure '%s' at relative "
					"line %i\n", tag, line_count);
			return -RF_BLOCK_BAD_CLOSURE;
			break;

		case RF_OK:
		    
			if (store_all && (block_count++ >= max) ) {
				if (rf_verbose)
					fprintf(stderr, "Block count exceeded\n");
				return -RF_TOO_MANY_BLOCKS;
			}

			if ( (err=block_store(fin, block, tag)) ) {
				return err;
			}

			if (store_all)
				block++;
			else if (name != NULL && strcmp(name, block->name)==0)
				return 0;
			else if (name == NULL && block_count++ == target)
				return 0;

			break;
		}

	}

	if (store_all)
		return block_count;

	if (rf_verbose)
		fprintf(stderr, "Block not found\n");
	return -RF_BLOCK_NOT_FOUND;

}

int store_blocks(FILE *fin, rf_block_t *block, int max_blocks)
{
	return traverse_blocks(fin, block, 1, 0, max_blocks, NULL);
}

int seek_block(FILE *fin, rf_block_t *block, int index)
{
	return traverse_blocks(fin, block, 0, index, 0, NULL);
}


int find_block(FILE *fin, rf_block_t *block, const char *name)
{
	return traverse_blocks(fin, block, 0, 0, 0, name);
}


int block_key( rf_key_t *key, rf_block_t *block, int index,
	       const rf_key_t *last_key)
{
	int  line_count = 0;
	char line[RF_LINE];
	char *tag, *data;

	if (index < 0 || index >= block->count)
		return -RF_KEY_NOT_FOUND;

	if (block->fin == NULL)
		return -RF_BLOCK_UNINITIALIZED;

	memset(key, 0, sizeof(*key));

	if (last_key != NULL && last_key->parent == block) {
		fseek(block->fin, last_key->fend, SEEK_SET);
		line_count = last_key->index + 1;
	} else {
		fseek(block->fin, block->fstart, SEEK_SET);
	}


	while (fgets(line, RF_LINE, block->fin)!=NULL) {

		switch(remove_tag(line, &tag, &data)) {

		case RF_COM:
			continue;

		case RF_ERR:
			if (rf_verbose)
				fprintf(stderr, "Runfile format error!\n");
			return -RF_FILE_BAD;
			
		case RF_CLO:
			if (rf_verbose)
				fprintf(stderr,
					"Unexpected closure '%s' at relative "
					"line %i\n", tag, line_count);
			return -RF_BLOCK_UNINITIALIZED;

		case RF_OK:
			if (line_count++==index) {
				strcpy(key->name, tag);
				strcpy(key->data, data);
				key->parent = block;
				key->index = index;
				key->fend = ftell(block->fin);
				return 0;
			}
			break;
		}
	}
	if (rf_verbose)
		fprintf(stderr,
			"End of file reached without complete block.\n");

	return -RF_BLOCK_NOT_FOUND;
}



int find_key(rf_key_t *key, rf_block_t *block, const char *name)
{
	int  line_count = 0;
	char line[RF_LINE];
	char *tag, *data;
	int index = 0;

	if (name==NULL)
		return -RF_ARGS_BAD;

	if (block->fin == NULL)
		return -RF_BLOCK_UNINITIALIZED;

	memset(key, 0, sizeof(*key));

	fseek(block->fin, block->fstart, SEEK_SET);

	while (fgets(line, RF_LINE, block->fin)!=NULL) {

		switch(remove_tag(line, &tag, &data)) {

		case RF_COM:
			continue;

		case RF_ERR:
			if (rf_verbose)
				fprintf(stderr, "Runfile format error!\n");
			return -RF_FILE_BAD;
			
		case RF_CLO:
			if (strcmp(block->name, tag)==0) {
				if (rf_verbose)
					fprintf(stderr,
						"Key '%s' not found.\n", name);
				return -RF_KEY_NOT_FOUND;
			}

			if (rf_verbose)
				fprintf(stderr,
					"Unexpected closure '%s' at relative "
					"line %i\n", tag, line_count);
			return -RF_BLOCK_BAD_CLOSURE;

		case RF_OK:
			if (strcmp(name, tag)==0) {
				strcpy(key->name, tag);
				strcpy(key->data, data);
				key->parent = block;
				key->index = index;
				key->fend = ftell(block->fin);
				return 0;
			}
			index++;
			break;
		}
	}
	if (rf_verbose)
		fprintf(stderr,
			"End of file reached without complete block.\n");

	return -RF_BLOCK_NO_CLOSURE;
}
