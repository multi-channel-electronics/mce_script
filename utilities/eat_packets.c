#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <errno.h>
#include <stdint.h>

#include "mce_header.h"

#define BUF_SIZE (8192)

#define FRAME_SEQ_OFS 0x01
#define SYNC_DV_OFS 0x0A

#define u32 uint32_t

int checksum(u32 *data, int frame_size) {
  int sum = 0;
  int i;
  for (i=0; i<frame_size; i++) {
    sum ^= data[i];
  }
  return sum;
}


#include "sequence.h"

struct sequence_analyser seq;
struct sequence_analyser dv;

int main(int argc, char **argv) {

  long offset=0;
  int frame_size=-1;
  int max_frames = -1;
  FILE *src = stdin;
  char filename[1024];
  int check_dv = 1;
  int check_seq = 1;

  int option;
  while ( -1 != (option = getopt(argc, argv, "s:f:n:N:a:d:c:"))) {
    switch(option) {

    case 'd':
      check_dv = strtol(optarg, NULL, 0);
      break;

    case 'c':
      check_seq = strtol(optarg, NULL, 0);
      break;

    case 's':
      offset = strtol(optarg, NULL, 0);
      break;

    case 'n':
      frame_size = strtol(optarg, NULL, 0) / 4;
      break;

    case 'N':
      frame_size = strtol(optarg, NULL, 0);
      break;

    case 'a':
      max_frames = strtol(optarg, NULL, 0);
      break;

    case 'f':
      strcpy(filename, optarg);
      src = fopen(filename, "r");
      if (src==NULL) {
	fprintf(stderr, "Could not open %s\n", filename);
	return 1;
      }
      break;
    default:
      printf("Options:\n"
	     "     -s offset       in bytes\n"
             "     -n frame_size   in bytes\n"
             "     -N frame_size   in dwords\n"
	     "     -a max_frames   in frames\n"
	     "     -d [1|0]        to check the sync dv number, or not\n"
	     "     -c [1|0]        to check the CC frame counter, or not\n"
             "     -f filename     otherwise data is read from stdin\n"
	     );
    }
  }

  u32 packet[BUF_SIZE];
  int count = 0;

  int index = 0;
  int target = 0;

  mce_header_t* header = get_header(NULL, src);

  if (frame_size >= 0) {
	  printf("Forced     frame_size=%i (%i)\n", frame_size, frame_size*4);
  } else {
	  frame_size = header->header_size + header->footer_size + 
		  header->n_cols_rep * header->n_rows_rep * header->n_rc;
	  printf("Determined frame_size=%i (%i)\n", frame_size, frame_size*4);
  }

  sequence_init(&seq, 0, "frame_seq", FRAME_SEQ_OFS);
  sequence_init(&dv,  0, "sync_dv"  , SYNC_DV_OFS);

  //Seek...
  if (offset>0) {
    if (fseek(src, offset, SEEK_CUR)) {
      index = 0;
      while (!feof(src) && index < offset) {
	int target = BUF_SIZE*sizeof(*packet);
	if (offset-index < target) target = offset-index;
	int err = fread((void*)packet, 1, target, src);
	if (err<=0) {
	  printf("Couldn't seek to offset...\n");
	  break;
	}	
	index += err;
      }
    }
  }

  printf("offset     frm_idx   frame#\n");
  
  while (!feof(src) && ((max_frames < 0) || count < max_frames)) {

    index = 0;
    target = frame_size*sizeof(u32);
    while (index<target) {
      int err = fread((void*)packet + index, 1, target-index, src);
      if (err<=0) break;
      index+=err;
    }

    if (index<target) break;

    char seq_msg[1024];
    char dv_msg[1024];
    int err_chk = checksum(packet, frame_size);
    int err_seq = (check_seq ? sequence(&seq, packet, seq_msg): 0);
    int err_dv  = (check_dv ? sequence(&dv , packet, dv_msg) : 0 );

    if (err_chk || err_seq || err_dv) {
      char line[1024];
      sprintf(line, "%#010lx %8i %8i ", 
	      offset+count*frame_size*sizeof(u32), 
	      count, packet[1]);

      if (err_chk) {
	printf("%s non-zero checksum %#08x = %11i\n",
	       line, err_chk, err_chk);
      }
      if (err_seq) {
	printf( "%s %s\n", line, seq_msg);
      }
      if (err_dv) {
	printf( "%s %s\n", line, dv_msg);
      }
    }
	   
    count ++;
  }

  printf("EOF, exiting after %i frames + %i bytes\n", count, index);
  return 0;

}


