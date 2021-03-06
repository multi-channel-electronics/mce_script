/* (C) 2013, 2014, 2015, 2018 D. V. Wiebe
 *
 *************************************************************************
 *
 * defile-mas is free software; you can redistribute it and/or modify it
 * under the terms of the GNU General Public License as published by the
 * Free Software Foundation; either version 2 of the License, or (at your
 * option) any later version.
 *
 * defile-mas is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public
 * License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with defile-mas; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
 */
#ifdef HAVE_CONFIG_H
#include "config.h"
#endif

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <errno.h>
#include <ctype.h>
#include <libgen.h>

#include <defile.h>

#define MAS_CHUNK_SIZE 50000 /* frames per file chunk */

/* the only runfile version we're willing to deal with */
#define MAS_RF_VERSION 2

#define EOF_CHECK_TIME 10 /* check every tenth of a second */

/* frame status word bits */
#define MAS_FSW_LAST_FRM 0x00000001 /* bit 0 */
#define MAS_FSW_STOP_BIT 0x00000002 /* bit 1 */
#define MAS_FSW_FREE_RUN 0x00000004 /* bit 2 */
#define MAS_FSW_SYNC_ERR 0x00000008 /* bit 3 */
#define MAS_FSW_ACTV_CLK 0x00000010 /* bit 4 */
/* bit 5 (0x0020) is only used in v3 firmware */
/* bits 6-8 (0x0040-0x0100) unused */
#define MAS_FSW_FIBR_LEV 0x00000200 /* bit 9 */
#define MAS_FSW_RC1_HERE 0x00000400 /* bit 10 */
#define MAS_FSW_RC2_HERE 0x00000800 /* bit 11 */
#define MAS_FSW_RC3_HERE 0x00001000 /* bit 12 */
#define MAS_FSW_RC4_HERE 0x00002000 /* bit 13 */
/* bits 14-15 (0x0004000-0x0008000) unused */
#define MAS_FSW_COL_MASK 0x000F0000 /* bits 16-19 */
#define MAS_FSW_COL_OFFSET 16
#define MAS_FSW_TIME_ERR 0x00100000 /* bit 20 */

#define MAS_FSW_NCOL(x) (((x) & MAS_FSW_COL_MASK) >> MAS_FSW_COL_OFFSET)
#define MAS_FSW_NRC(x) \
  (((x & MAS_FSW_RC1_HERE) ? 1 : 0) + \
  ((x & MAS_FSW_RC2_HERE) ? 1 : 0) + \
  ((x & MAS_FSW_RC3_HERE) ? 1 : 0) + \
  ((x & MAS_FSW_RC4_HERE) ? 1 : 0))

#define HEADER_LEN 43
/* this is 43 32-bit words */
struct frame_header {
  /* twelve words that get stored: */
  uint32_t status, frame_count, row_len, nrow_reported, data_rate, arz_count;
  uint32_t hdr_vers, ramp_val, ramp_adr, nrow, sync, run_id, user_word;
  uint32_t errno1, t_ac_fpga, t_bc1_fpga, t_bc2_fpga, t_bc3_fpga;
  uint32_t t_rc1_fpga, t_rc2_fpga, t_rc3_fpga, t_rc4_fpga, t_cc_fpga;
  uint32_t errno2, t_ac_card, t_bc1_card, t_bc2_card, t_bc3_card;
  uint32_t t_rc1_card, t_rc2_card, t_rc3_card, t_rc4_card, t_cc_card;
  uint32_t errno3;
  uint32_t reserved[7]; /* Formerly for PSUC readout */
  uint32_t errno4;
  uint32_t box_temp;
};

#define NHEADER_FIELDS 14
static struct header_field {
  const char *name;
  int offset;
} header_field_data[NHEADER_FIELDS] = {
  { "status", 0 },
  { "frame_ctr", 1 },
  { "row_len", 2 },
  { "num_rows_reported", 3 },
  { "data_rate", 4 },
  { "address0_ctr", 5 },
  { "header_version", 6 },
  { "ramp_value", 7 },
  { "ramp_addr", 8 },
  { "num_rows", 9 },
  { "sync_box_num", 10 },
  { "runfile_id", 11 },
  { "userfield", 12 },
  { "box_temp", 42 }
};

/* derived field bits */

#define NDATA_MODES 13
/* types */
#define DERIV_RAW      1
#define DERIV_SCALE    2
#define DERIV_BIT      3
#define DERIV_BITSCALE 4
/* field types */
#define RW_FIELD(n) { n, DERIV_RAW, 0, 0, 0, 0 }
#define SC_FIELD(n,s) { n, DERIV_SCALE, 0, 0, 0, s }
#define BT_FIELD(n,b,x,z) { n, DERIV_BIT, b, x, z, 0 }
#define BS_FIELD(n,b,x,s,z) { n, DERIV_BITSCALE, b, x, z, s }
#define NO_FIELD { NULL, 0, 0, 0, 0, 0 }
static const struct {
  const char *name;
  int type, bitnum, numbits, sign;
  double scale;
} derived[NDATA_MODES][2] = {
  /*  0 */ { RW_FIELD("error"), NO_FIELD },
  /*  1 */ { SC_FIELD("fb", 1./4096), NO_FIELD },
  /*  2 */ { RW_FIELD("filt"), NO_FIELD },
  /*  3 */ { RW_FIELD("raw"), NO_FIELD },
  /*  4 */ { BT_FIELD("error", 0, 14, 1), BT_FIELD("fb", 14, 18, 1) },
  /*  5 */ { BT_FIELD("fj", 0, 8, 1), BS_FIELD("fb", 8, 24, 1./1024, 1) },
  /*  6 */ { NO_FIELD, NO_FIELD },
  /*  7 */ { NO_FIELD, NO_FIELD },
  /*  8 */ { NO_FIELD, NO_FIELD },
  /*  9 */ { BT_FIELD("fj", 0, 8, 1), BS_FIELD("filt", 8, 24, 2., 1) },
  /* 10 */ { BT_FIELD("fj", 0, 7, 1), BS_FIELD("filt", 7, 25, 8., 1) },
  /* 11 */ { BT_FIELD("col", 0, 3, 0), BT_FIELD("row", 3, 7, 0) },
  /* 12 */ { RW_FIELD("raw"), NO_FIELD }
};

struct runfile_tag {
  char *name;
  int nspec;
  char **spec;
  int ndata;
  char **data;
};

struct runfile_block {
  char *name;
  int ntag;
  struct runfile_tag *tag;
};

struct runfile {
  int nblock;
  struct runfile_block *block;
};

/* yay for globals */
static int not_symlink;
static int sequence;
static int fdind = -1;
static struct df_fdef fdef;
static int mas_rcs[4];
static long long mas_offset;
static struct runfile_block *mas_rf_header;
static int mas_fd = -1;
static char *mas_fr;
static struct runfile rf = { 0, NULL };
static char *mas_flatfile = NULL;
static char *mas_pathname = NULL;
static struct {
  int rf_vers;
  const char *mas_vers;
  const char *array_id;
  int rc[4];
  const char *filename;
  int64_t framecount;
  int64_t ctime;
  const char *hostname;
} frameacq;

static struct {
  int nrow;
  int ncol;
  int data_mode;

  /* derived parameters */
  double rate;
} mas_rf_data;

/* public strings; see defile-input(7) */
#define DEFILE_MAS_COPYRIGHT "Copyright (C) 2013, 2014, 2015, 2018 D. V. Wiebe"
#define DEFILE_MAS_CONTACT \
  "For contact information, see https://e-mode.phas.ubc.ca/mcewiki/"
#define DEFILE_MAS_DESCRIPTION "MCE-MAS flat-file data"

/* the probe function: return non-zero if we think "name" is a MAS file */
static int mas_probe(const char *name)
{
  int i;
  char *run_file;
  char *full_name = df_shell_expand(name);
  size_t full_name_len;

  if (full_name == NULL)
    return 0;

  /* try opening the data file */
  mas_fd = open(full_name, O_RDONLY);

  if (mas_fd < 0) {
    free(full_name);
    return 0;
  }
  close(mas_fd);

  /* now, look for a run file */
  full_name_len = strlen(full_name);
  run_file = malloc(full_name_len + sizeof(".run") + 1);
  if (run_file == NULL) {
    free(full_name);
    return 0;
  }

  sprintf(run_file, "%s.run", full_name);
  free(full_name);

  /* try opening it */
  mas_fd = open(run_file, O_RDONLY);
  if (mas_fd >= 0) {
    /* successful open */
    free(run_file);
    close(mas_fd);
    return 1;
  }

  /* Opening the runfile didn't work. */

  /* Is it a sequenced file? Check last
   * three characters of name for digits */
  for (i = 0; i < 3; ++i)
    if (run_file[full_name_len - i - 1] < '0'
        || run_file[full_name_len - i - 1] > '9')
    {
      /* Non-digit found */
      free(run_file);
      return 0;
    }

  /* also check for a '.' */
  if (run_file[full_name_len - 4] != '.') {
    free(run_file);
    return 0;
  }
  
  /* Replace the final ### with run, including
   * trailing NUL */
  memcpy(run_file + full_name_len - 3, "run", 4);

  /* Now try opening that one */
  /* try opening it */
  mas_fd = open(run_file, O_RDONLY);
  free(run_file);

  if (mas_fd >= 0) {
    /* successful open */
    close(mas_fd);
    return 1;
  }

  /* Still failed */
  return 0;
}

static void mas_close_flatfile(int clear_metadata)
{
  int i, j;

  if (mas_fd >= 0)
    close(mas_fd);

  if (clear_metadata) {
    for (i = 0; i < rf.nblock; ++i) {
      for (j = 0; j < rf.block[i].ntag; ++j) {
        free(rf.block[i].tag[j].name);
        if (rf.block[i].tag[j].spec) {
          free(rf.block[i].tag[j].spec[0]);
          free(rf.block[i].tag[j].spec);
        }
        if (rf.block[i].tag[j].data) {
          free(rf.block[i].tag[j].data[0]);
          free(rf.block[i].tag[j].data);
        }
      }
      free(rf.block[i].tag);
      free(rf.block[i].name);
    }
    free(rf.block);
    rf.block = NULL;
    rf.nblock = 0;
  }
}

static int mas_clean(void)
{
  mas_close_flatfile(1);

  free(mas_fr);
  free(mas_pathname);
  free(mas_flatfile);

  return 0;
}

/* find a runfile block */
static struct runfile_block *runfile_find_block(const char *name)
{
  int i;

  for (i = 0; i < rf.nblock; ++i)
    if (strcmp(rf.block[i].name, name) == 0)
      return rf.block + i;

  return NULL;
}

/* make a tag + spec string (for error reporting) */
static char runfile_tag_spec_buffer[1024];
static char *runfile_tag_and_spec(const char *name, int nspec,
    const char **spec)
{
  int i;
  strcpy(runfile_tag_spec_buffer, name);

  for (i = 0; i < nspec; ++i) {
    strcat(runfile_tag_spec_buffer, " ");
    strcat(runfile_tag_spec_buffer, spec[i]);
  }

  return runfile_tag_spec_buffer;
}
  
/* find a runfile tag with specifiers in a block */
static struct runfile_tag *runfile_find_tag(struct runfile_block *block,
    const char *name, int nspec, const char **spec)
{
  int i, j;

  for (i = 0; i < block->ntag; ++i) {
    if ((strcmp(block->tag[i].name, name) == 0)
        && (nspec == block->tag[i].nspec))
    {
      for (j = 0; j < nspec; ++j)
        if (strcmp(block->tag[i].spec[j], spec[j]))
          break;

      if (j == nspec) /* success */
        return block->tag + i;
    }
  }

  return NULL;
}

/* convert a runfile item into an array of longs  */
static int runfile_long_arr(long **out, struct runfile_block *block,
    const char *name, int nspec, const char **spec)
{
  int i;
  long *a = NULL;
  char *endptr;
  struct runfile_tag *tag = runfile_find_tag(block, name, nspec, spec);

  if (tag == NULL) {
    *out = NULL;
    return -1;
  }

  if (tag->ndata == 0) {
    *out = NULL;
    return 0;
  }

  a = malloc(sizeof(long) * tag->ndata);
  if (a == NULL) {
    df_printf(DF_PRN_ERR, "Out of memory.\n");
    df_exit(1, 1);
  }

  for (i = 0; i < tag->ndata; ++i) {
    a[i] = strtol(tag->data[i], &endptr, 10);
    if (*endptr) {
      df_printf(DF_PRN_ERR, "Couldn't interpret element %i of tag \"%s\" in "
          "%s block as integer.\n", i, runfile_tag_and_spec(name, nspec,
            spec), block->name);
      df_exit(1, 1);
    }
  }

  *out = a;
  return tag->ndata;
}

/* convert a runfile item into string */
static const char *runfile_string(struct runfile_block *block, const char *name,
    int nspec, const char **spec)
{
  struct runfile_tag *tag = runfile_find_tag(block, name, nspec, spec);

  if (tag == NULL)
    return NULL;

  if (tag->ndata == 0) {
    df_printf(DF_PRN_ERR, "missing data for tag \"%s\" in %s block.\n",
        runfile_tag_and_spec(name, nspec, spec), block->name);
    df_exit(1, 1);
  } else if (tag->ndata > 1) {
    df_printf(DF_PRN_ERR,
        "Array found where scalar expected as tag \"%s\" in %s block.\n",
        runfile_tag_and_spec(name, nspec, spec), block->name);
    df_exit(1, 1);
  }

  return tag->data[0];
}

/* convert a runfile item into a int64_t */
static int64_t runfile_int64(struct runfile_block *block, const char *name,
    int nspec, const char **spec, int64_t dft)
{
  int64_t v;
  char *endptr;
  struct runfile_tag *tag = runfile_find_tag(block, name, nspec, spec);

  if (tag == NULL)
    return dft;

  if (tag->ndata == 0) {
    df_printf(DF_PRN_ERR, "missing data for tag \"%s\" in %s block.\n",
        runfile_tag_and_spec(name, nspec, spec), block->name);
    df_exit(1, 1);
  } else if (tag->ndata > 1) {
    df_printf(DF_PRN_ERR,
        "Array found where scalar expected as tag \"%s\" in %s block.\n",
        runfile_tag_and_spec(name, nspec, spec), block->name);
    df_exit(1, 1);
  }

  v = (int64_t)strtoll(tag->data[0], &endptr, 10);
  if (*endptr) {
    df_printf(DF_PRN_ERR,
        "Couldn't interpret tag \"%s\" in %s block as integer.\n",
        runfile_tag_and_spec(name, nspec, spec), block->name);
    df_exit(1, 1);
  }

  return v;
}

/* convert a runfile item into a long */
static long runfile_long(struct runfile_block *block, const char *name,
    int nspec, const char **spec, long dft)
{
  long v;
  char *endptr;
  struct runfile_tag *tag = runfile_find_tag(block, name, nspec, spec);

  if (tag == NULL)
    return dft;

  if (tag->ndata == 0) {
    df_printf(DF_PRN_ERR, "missing data for tag \"%s\" in %s block.\n",
        runfile_tag_and_spec(name, nspec, spec), block->name);
    df_exit(1, 1);
  } else if (tag->ndata > 1) {
    df_printf(DF_PRN_ERR,
        "Array found where scalar expected as tag \"%s\" in %s block.\n",
        runfile_tag_and_spec(name, nspec, spec), block->name);
    df_exit(1, 1);
  }

  v = strtol(tag->data[0], &endptr, 10);

  if (*endptr) {
    df_printf(DF_PRN_ERR,
        "Couldn't interpret tag \"%s\" in %s block as integer (%s).\n",
        runfile_tag_and_spec(name, nspec, spec), block->name);
    df_exit(1, 1);
  }

  return v;
}

static long runfile_rca_param_long(const char *param)
{
  int i, used = -1, different = 0;
  long v = 0;
  char rc[] = "rc0";
  const char *spec[] = { rc, param };
  
  for (i = 0; i < 4; ++i)
    if (mas_rcs[i]) {
      rc[2] = '1' + i;
      long l = runfile_long(mas_rf_header, "RB", 2, spec, -1);
      if (l == -1) {
        df_printf(DF_PRN_WARN, "missing parameter \"%s\" on %s.\n", param, rc);
      } else if (used == -1) {
        used = i;
        v = l;
      } else if (l != v)
        different = 1;
    }

  if (used == -1) {
    df_printf(DF_PRN_ERR, "missing parameter \"%s\" on rca.\n", param);
    df_exit(1, 1);
  } else if (different) {
    df_printf(DF_PRN_WARN, "parameter \"%s\" varies between RCs.  "
        "Using value reported by rc%i.\n", param, used + 1);
  }

  return v;
}

static long runfile_param_long(const char *card, const char *param, long dft)
{
  const char *spec[] = { card, param };
  return runfile_long(mas_rf_header, "RB", 2, spec, dft);
}

/* break a string into multiple NUL-separated parts */
static int runfile_wordify(char *in, char ***out)
{
  int n = 1;
  char **list;
  void *tmp;
  int w = 0;

  if (in == NULL || *in == 0) {
    *out = NULL;
    return 0;
  }

  list = (char**)malloc(sizeof(char*));
  if (list == NULL)
    return -1;

  /* skip leading whitespace */
  for (; *in && (*in == ' ' || *in == '\t'); ++in);

  list[0] = strdup(in);
  if (list[0] == NULL)
    return -1;

  for (in = list[0]; *in; ++in) {
    if (*in == ' ' || *in == '\t') {
      if (!w) {
        *in = 0;
        w = 1;
      }
    } else {
      if (w == 1) {
        /* add another thing */
        tmp = realloc(list, sizeof(char*) * (n + 1));
        if (tmp == NULL) {
          free(list);
          return -1;
        }
        list = (char**)tmp;
        list[n++] = in;
        w = 0;
      }
    }
  }

  *out = list;
  return n;
}

/* Tokenise a runfile line.  A valid line is one of:
 *
 * <BLOCK_NAME>
 * </BLOCK_NAME>
 * <TAG SPEC...> DATA...
 *
 * where words are space or tab separated.  We'll further assume they can't
 * contain < or >, although that's not stated.  We make three strings in the 
 * supplied buffer: a tag, a spec list, and the data.  Leading whitespace has
 * already been removed, and tag points to the first character after the '<'
 *
 * Returns non-zero on failure.
 */
static int runfile_toke(char *tag, char **spec, char **data, int lineno)
{
  char *ptr;

  /* strip newlne */
  for (ptr = tag; *ptr; ++ptr)
    if (*ptr == '\n' || *ptr == '\r') {
      *ptr = '\0';
      break;
    }

  /* find the '>' */
  for (ptr = tag; *ptr && *ptr != '>'; ++ptr)
    if (*ptr == '<') {
      df_printf(DF_PRN_ERR, "Unexpected '<' on line %i of runfile.\n", lineno);
      return 1;
    }

  /* not found */
  if (*ptr == 0) {
    df_printf(DF_PRN_ERR, "missing > on line %i of runfile.\n", lineno);
    return 1;
  }
  *ptr = 0;
  *data = ptr + 1;

  /* find the end of the tag */
  for (ptr = tag; *ptr && *ptr != ' ' && *ptr != '\t'; ++ptr);

  if (*ptr) {
    /* one or more specifier exist */
    *ptr = 0;
    *spec = ptr + 1;
  } else {
    /* no specifiers */
    *spec = NULL;
  }

  return 0;
}

/* load and store the runfile -- returns NULL on error; the parsed runfile
 * data on success */
static int runfile_read(const char *base)
{
  FILE *stream;
  size_t len = strlen(base);
  char *runfile = malloc(len + sizeof(".run"));
  char buffer[1024];
  struct runfile_block *block = NULL;
  struct runfile_tag *tag = NULL;
  char *name, *spec, *data;
  void *ptr;
  int i, lineno = 0;

  if (runfile == NULL)
    return 1;

  sprintf(runfile, "%s.run", base);

  sequence = -1;
  mas_offset = 0;
  stream = fopen(runfile, "rt");
  if (stream == NULL) {
    if (errno == ENOENT) { /* not found -- maybe its a sequenced file? */
      /* look for a three digit extension with a preceding '.' */
      if (len > 4 && isdigit(runfile[len - 1]) && isdigit(runfile[len - 2]) &&
          isdigit(runfile[len - 3]) && runfile[len - 4] == '.') {
        /* let's assume it's a sequenced file and try again */
        sequence = runfile[len - 1] - '0' + 10 * (runfile[len - 2] - '0')
          + 100 * (runfile[len - 3] - '0');
        mas_offset = sequence * MAS_CHUNK_SIZE;
        strcpy(runfile + len - 3, "run");
        stream = fopen(runfile, "rt");
      }
    }
    if (stream == NULL) {
      df_printf(DF_PRN_ERR, "Unable to open runfile: %s: %s\n", runfile,
          strerror(errno));
      free(runfile);
      return 1;
    }
  }
  free(runfile);

  while (!feof(stream)) {
    if (fgets(buffer, 1024, stream)) {
      lineno++;

      /* strip leading whitespace */
      for (name = buffer; *name && (*name == ' ' || *name == '\t'); ++name);

      /* comment */
      if (*name == '#' || *name == 0 || *name == '\r' || *name == '\n')
        continue;

      /* syntax error */
      if (*(name++) != '<') {
        df_printf(DF_PRN_ERR,
            "Expected '<' at the start of line %i of runfile.\n", lineno);
        goto RUNFILE_FAILED;
      }

      /* tokenise */
      if (runfile_toke(name, &spec, &data, lineno))
        goto RUNFILE_FAILED;

      if (block == NULL) { /* this needs to be a block designator */
        if (*name == '/') {
          df_printf(DF_PRN_ERR,
              "Spurious block termination </%s> on line %i of runfile.\n",
              name, lineno);
          goto RUNFILE_FAILED;
        } else if (spec) {
          df_printf(DF_PRN_ERR,
              "Block initialiser carries specifiers on line %i of runfile.\n",
              name, lineno);
          goto RUNFILE_FAILED;
        } else if (*data) {
          df_printf(DF_PRN_ERR,
              "Block initialiser carries data on line %i of runfile.\n",
              lineno);
          goto RUNFILE_FAILED;
        }

        /* look for duplicate */
        for (i = 0; i < rf.nblock; ++i)
          if (strcmp(rf.block[i].name, name) == 0) {
            df_printf(DF_PRN_ERR, "Duplicate block %s on line %i of runfile.\n",
                name, lineno);
            goto RUNFILE_FAILED;
          }

        /* add a new block record */
        ptr =
          realloc(rf.block, sizeof(struct runfile_block) * (rf.nblock + 1));
        if (ptr == NULL) {
          df_printf(DF_PRN_ERR, "Out of memory.\n");
          goto RUNFILE_FAILED;
        }
        rf.block = ptr;
        block = rf.block + rf.nblock;

        block->name = strdup(name);
        block->ntag = 0;
        block->tag = NULL;
        rf.nblock++;
        if (block->name == NULL) {
          df_printf(DF_PRN_ERR, "Out of memory.\n");
          goto RUNFILE_FAILED;
        }
      } else if (*name == '/') { /* a block terminator */
        if (strcmp(name + 1, block->name)) {
          df_printf(DF_PRN_ERR,
              "Block %s ended by %s on line %i of runfile.\n", block->name,
              name, lineno);
          goto RUNFILE_FAILED;
        } else if (spec) {
          df_printf(DF_PRN_ERR,
              "Block initialiser carries specifiers on line %i of runfile.\n",
              name, lineno);
          goto RUNFILE_FAILED;
        } else if (*data) {
          df_printf(DF_PRN_ERR,
              "Block terminator carries data on line %i of runfile.\n",
              lineno);
          goto RUNFILE_FAILED;
        }
        block = NULL;
      } else { /* a tag */
        char **specs;
        char **datas;
        int ndata, nspec;
        if ((nspec = runfile_wordify(spec, &specs)) < 0)
          goto RUNFILE_FAILED;
        if ((ndata = runfile_wordify(data, &datas)) < 0)
          goto RUNFILE_FAILED;

        /* look for a duplicate */
        if (runfile_find_tag(block, name, nspec, (const char **)specs)) {
          df_printf(DF_PRN_ERR, "Duplicate tag/specifier group %s/%s in "
              "block on line %i of runfile.\n", name, spec, lineno);
          goto RUNFILE_FAILED;
        }

        /* add a new tag */
        ptr =
          realloc(block->tag, sizeof(struct runfile_tag) * (block->ntag + 1));
        if (ptr == NULL) {
          df_printf(DF_PRN_ERR, "Out of memory.\n");
          goto RUNFILE_FAILED;
        }
        block->tag = ptr;
        tag = block->tag + block->ntag;
        tag->name = strdup(name);
        tag->nspec = nspec;
        tag->spec = specs;
        tag->ndata = ndata;
        tag->data = datas;
        block->ntag++;
      }
    }
  }

  if (block) {
    df_printf(DF_PRN_ERR, "Unterminated block %s at end of runfile.\n",
        block->name);
    goto RUNFILE_FAILED;
  }

  fclose(stream);
  return 0;

RUNFILE_FAILED:
  fclose(stream);
  return 1;
}

static int load_frameacq(void)
{
  int i, nrc;
  long *rcs;
  struct runfile_block *fa_block = runfile_find_block("FRAMEACQ");

  if (!fa_block) {
    df_printf(DF_PRN_ERR, "Required block FRAMEACQ missing from runfile.\n");
    return 1;
  }

  /* populate the frameacq struct */
  frameacq.rf_vers = runfile_long(fa_block, "RUNFILE_VERSION", 0, NULL, -1);
  if (frameacq.rf_vers != MAS_RF_VERSION) {
    df_printf(DF_PRN_ERR, "Unsupported RUNFILE_VERSION %i\n", frameacq.rf_vers);
    return 1;
  }

  frameacq.mas_vers = runfile_string(fa_block, "MAS_VERSION", 0, NULL);
  frameacq.array_id = runfile_string(fa_block, "ARRAY_ID", 0, NULL);

  nrc = runfile_long_arr(&rcs, fa_block, "RC", 0, NULL);
  for (i = 0; i < nrc; ++i) {
    if (rcs[i] < 1 || rcs[i] > 4) {
      df_printf(DF_PRN_ERR, "Bad RC: %i in FRAMEACQ\n", rcs[i]);
      return 1;
    }
    frameacq.rc[rcs[i] - 1] = 1;
  }
  free(rcs);

  frameacq.filename = runfile_string(fa_block, "DATA_FILENAME", 0, NULL);
  frameacq.framecount = runfile_int64(fa_block, "DATA_FRAMECOUNT", 0, NULL, -1);
  frameacq.ctime = runfile_int64(fa_block, "CTIME", 0, NULL, -1);
  frameacq.hostname = runfile_string(fa_block, "HOSTNAME", 0, NULL);

  return 0;
}

static void load_frameheader(struct frame_header *fh, int follow)
{
  ssize_t n;
  size_t left = sizeof(*fh);

  while (left > 0) {
    n = read(mas_fd, fh, sizeof(*fh));
    if (n < 0) {
      df_perror(DF_PRN_ERR, "read");
      df_exit(1, 1);
    }
    left -= n;
    if (left > 0 && !follow) {
      df_printf(DF_PRN_ERR, "data file too short");
      df_exit(1, 1);
    }
    if (left > 0)
      usleep(10000);
  }
}

/* return non-zero if we support this supplied data mode */
#define DATA_MODE_RAW 12
static const int mas_data_mode_supported(int data_mode)
{
  return (data_mode == 0 || data_mode == 1 || data_mode == 2 || data_mode == 4
      || data_mode == 5 || data_mode == 10 || data_mode == 11
      || data_mode == 12);
}

/* add a field specification with error handling */
static void mas_add_spec(const char *spec, int frag)
{
  if (df_add_spec(spec, frag) < 0)
    df_exit(1, 1);
}

/* add a string, with string trucation checking */
static void mas_add_string(const char *name, const char *value, int frag)
{
  char spec[4096];
  spec[4094] = '\0';
  snprintf(spec, 4094, "%s STRING \"%s\"", name, value);
  /* terminate truncated strings */
  if (spec[4094]) {
    spec[4094] = '"';
    spec[4095] = 0;
  }
  mas_add_spec(spec, frag);
}

/* store the runfile data in the dirfile metadata (similar to 'mce_status -d')
 */
static void write_rf_header(void)
{
  char spec[4096];
  struct {
    const char *id, *name;
    int wrote;
  } cards[] = {
    { "psc", "power supply card",    0 },
    { "cc",  "clock card",           0 },
    { "rc1", "readout card",         0 },
    { "rc2", "readout card",         0 },
    { "rc3", "readout card",         0 },
    { "rc4", "readout card",         0 },
    { "bc1", "bias card",            0 },
    { "bc2", "bias card",            0 },
    { "bc3", "bias card",            0 },
    { "bac", "biasing address card", 0 },
    { "ac",  "address card",         0 },
    { "rcs", "readout-all-go",       0 },
    { "sys", "system",               0 },
    { "rca", "readout-all",          0 },
    { "sq2", "sq2 mapping",          0 },
    { "sq1", "sq1 mapping",          0 },
    { "sa",  "sa mapping",           0 },
    { "tes", "tes mapping",          0 },
    { "heater", "heater mapping",    0 },
    { "dummy", "dummy mapping",      0 },
    { NULL, NULL, 0}
  };

  int c, i, j;

  int rf_frag = df_add_fragment("format.runfile", 0, 0, 0, NULL, NULL);
  if (rf_frag < 0)
    df_exit(1, 1);

  /* write frameacq stuff, if present */
  if (frameacq.rf_vers == MAS_RF_VERSION) {
    sprintf(spec, "frameacq_rf_vers CONST UINT16 %i", frameacq.rf_vers);
    mas_add_spec(spec, rf_frag);

    mas_add_string("frameacq_mas_vers", frameacq.mas_vers, rf_frag);
    mas_add_string("frameacq_array_id", frameacq.array_id, rf_frag);

    sprintf(spec, "frameacq_rc CARRAY UINT8 %i %i %i %i", frameacq.rc[0],
        frameacq.rc[1], frameacq.rc[2], frameacq.rc[3]);
    mas_add_spec(spec, rf_frag);

    sprintf(spec, "frameacq_framecount CONST INT64 %lli",
        (long long)frameacq.framecount);
    mas_add_spec(spec, rf_frag);

    sprintf(spec, "frameacq_ctime CONST INT64 %lli", (long long)frameacq.ctime);
    mas_add_spec(spec, rf_frag);

    mas_add_string("frameacq_hostname", frameacq.hostname, rf_frag);

    /* doubly fake time:
     * - frameacq_ctime doesn't actually indicate when the acquisition started.
     *   Whatever created the runfile can put anything in there.  Typically it's
     *   some arbitrary point in time before the acqusition was requested.
     *   
     *   So, expect an arbitrary offset.
     *
     * - acq_seconds adjusts neither for frames dropped by MAS nor for ARZs
     *   dropped by the CC
     */
    mas_add_spec("frameacq_time LINCOM acq_seconds 1 frameacq_ctime", rf_frag);
  }

  for (i = 0; i < mas_rf_header->ntag; ++i) {
    if (mas_rf_header->tag[i].nspec != 2)
      continue;
    if (mas_rf_header->tag[i].ndata == 0)
      continue;

    /* make sure we've added a card pseudo item */
    for (c = 0; cards[c].id; ++c) {
      if (strcmp(cards[c].id, mas_rf_header->tag[i].spec[0]) == 0) {
        if (cards[c].wrote == 0) {
          sprintf(spec, "%s STRING \"%s\"", cards[c].id, cards[c].name);
          mas_add_spec(spec, rf_frag);
          cards[c].wrote = 1;
        }
        break;
      }
    }

    /* add the parameter */
    if (mas_rf_header->tag[i].ndata == 1) {
      char *endptr;
      long v = strtol(mas_rf_header->tag[i].data[0], &endptr, 10);

      if (*endptr) {
        if (strcmp(mas_rf_header->tag[i].data[0], "ERROR") == 0) {
          df_printf(DF_PRN_WARN, "'ERROR' found where integer expected for "
              "\"%s %s\".  Dropped.\n", mas_rf_header->tag[i].spec[0],
              mas_rf_header->tag[i].spec[1]);
          continue;
        } else {
          df_printf(DF_PRN_ERR, "Couldn't interpret parameter \"%s\" of "
              "%s as integer.\n", mas_rf_header->tag[i].spec[1],
              mas_rf_header->tag[i].spec[0]);
          df_exit(1, 1);
        }
      }
      sprintf(spec, "%s/%s CONST INT32 %li", mas_rf_header->tag[i].spec[0],
          mas_rf_header->tag[i].spec[1], v);
    } else {
      size_t pos = sprintf(spec, "%s/%s CARRAY INT32",
          mas_rf_header->tag[i].spec[0], mas_rf_header->tag[i].spec[1]);
      for (j = 0; j < mas_rf_header->tag[i].ndata; ++j) {
        char *endptr;
        long v = strtol(mas_rf_header->tag[i].data[j], &endptr, 10);

        if (*endptr) {
          if (strcmp(mas_rf_header->tag[i].data[j], "ERROR") == 0) {
            df_printf(DF_PRN_WARN, "'ERROR' found where integer expected for "
                "element %i of \"%s %s\".  Replaced with 0.\n",
                mas_rf_header->tag[i].spec[0], mas_rf_header->tag[i].spec[1]);
            v = 0;
          } else {
            df_printf(DF_PRN_ERR, "Couldn't interpret element %i of parameter "
                "\"%s\" of %s as integer.\n", j, mas_rf_header->tag[i].spec[1],
                mas_rf_header->tag[i].spec[0]);
            df_exit(1, 1);
          }
        }
        pos += sprintf(spec + pos, " %li", v);
      }
    }
    mas_add_spec(spec, rf_frag);
  }
}

/* given the base pointer to the data buffer and the current amount of stuff
 * in it; returns non-zero on EOF */
static int read_datafile(char *data, size_t *size)
{
  size_t len = fdef.framesize - *size;
  ssize_t n;

  /* data is always the base pointer, so increment */
  data += *size;

  /* read more */
  while (len > 0) {
    n = read(mas_fd, data, len);
    if (n < 0) {
      df_perror(DF_PRN_ERR, "read");
      df_exit(1, 1);
    }
    if (n == 0) {/* eof */
      return 1;
    }
    *size += n;
    len -= n;
    data += n;
  }

  return 0;
}

/* try to find another chunk.  If it finds one, updates global mas_flatfile
 * and returns non-zero */
static int mas_find_next_chunk()
{
  char *new_flatfile;
  struct stat stat_buf;
  size_t len;

  /* not a file sequenced flatfile */
  if (sequence == -1)
    return 0;

  /* sanity check */
  len = strlen(mas_flatfile);
  if (len < 3)
    return 0;

  /* The sequence number is always three zero-padded decimal digits at the end
   * of mas_flatfile */
  new_flatfile = strdup(mas_flatfile);
  if (new_flatfile == NULL) {
    df_printf(DF_PRN_ERR, "out of memory");
    df_exit(1, 1);
  }

  sprintf(new_flatfile + len - 3, "%03i", sequence + 1);

  /* check for the file */
  if (stat(new_flatfile, &stat_buf) < 0) {
    free(new_flatfile);
    return 0;
  }

  /* it's there */
  sequence++;
  free(mas_flatfile);
  mas_flatfile = new_flatfile;
  return 1;
}

/* check whether (global) mas_pathname is a symlink;  if it is, reutrn the
 * canonical name in (global) mas_flatfile, otherwise just copy mas_pathname to
 * mas_flatfile; returns whether the symlink changed */
static int mas_check_symlink(int retry)
{
  int changed;
  struct stat stat_buf;
  char *target = NULL;
  ssize_t n;

  /* we've already checked */
  if (not_symlink)
    return 0;

  if (lstat(mas_pathname, &stat_buf) < 0) {
    df_printf(DF_PRN_ERR, "unable to stat %s: %s", mas_pathname,
        strerror(errno));
    df_exit(1, 1);
  }

  /* not a link -- do nothing.  Weird stuff will happen if someone changes
   * mas_pathname from a symlink to a real file (or vice-versa) while defile's
   * running.
   */
  if (!S_ISLNK(stat_buf.st_mode)) {
    not_symlink = 1;
    return 0;
  }

  target = malloc(stat_buf.st_size + 1);
  if (target == NULL) {
    df_printf(DF_PRN_ERR, "out of memory");
    df_exit(1, 1);
  }

  n = readlink(mas_pathname, target, stat_buf.st_size + 1);
  if (n < 0) {
    df_perror(DF_PRN_ERR, "readlink");
    df_exit(1, 1);
  } else if (n > stat_buf.st_size) {
    /* symlink changed between stat() and readlink(); try again (once) */
    free(target);
    if (!retry)
      return mas_check_symlink(1);
    else {
      df_printf(DF_PRN_ERR, "unable to read unstable symlink: %s\n",
          mas_pathname);
      df_exit(1, 1);
    }
  }
  target[stat_buf.st_size] = 0; /* readlink doesn't guarantee NUL-termination */

  /* handle relative paths */
  if (target[0] != '/') {
    char *ptr, *c, *dir;
    c = strdup(mas_pathname); /* dirname may modify its input */
    if (c == NULL) {
      df_printf(DF_PRN_ERR, "Out of memory");
      free(target);
      df_exit(1, 1);
    }

    dir = dirname(c);
    ptr = malloc(strlen(target) + strlen(dir) + 2);
    if (ptr == NULL) {
      df_printf(DF_PRN_ERR, "Out of memory");
      free(c);
      free(target);
      df_exit(1, 1);
    }

    sprintf(ptr, "%s/%s", dir, ptr);
    free(c);
    free(target);
    target = ptr;
  }

  /* re-stat to ensure kosheritude */
  if (stat(target, &stat_buf)) {
    df_printf(DF_PRN_ERR, "unable to stat %s: %s", target, strerror(errno));
    free(target);
    df_exit(1, 1);
  }

  /* changed? */
  changed = (strcmp(target, mas_flatfile)) ? 1 : 0;

  if (changed) {
    free(mas_flatfile);
    mas_flatfile = target;
  }

  return changed;
}

static void mas_metadata(void)
{
  int i, j;
  struct df_fdef_field *field;
  struct df_fdef_field *f;

  /* store the runfile data in a new fragment */
  write_rf_header();

  /* field data */
  field = malloc(sizeof(struct df_fdef_field) *
      (mas_rf_data.nrow * mas_rf_data.ncol + NHEADER_FIELDS + 1));

  /* make the framedef */
  fdef.framesize = (mas_rf_data.nrow * mas_rf_data.ncol + HEADER_LEN + 1)
    * sizeof(uint32_t);
  fdef.n_fields = mas_rf_data.nrow * mas_rf_data.ncol + NHEADER_FIELDS + 1;
  fdef.field = field;

  /* Add header fields */
  for (i = 0; i < NHEADER_FIELDS; ++i) {
    f = field + i;
    f->name = (char*)header_field_data[i].name;
    f->spf = 1;
    f->type = GD_UINT32;
    f->offset = header_field_data[i].offset * sizeof(uint32_t);
    f->cadence = 0;
  }

  /* Add data fields */
  for (i = 0; i < mas_rf_data.ncol; ++i)
    for (j = 0; j < mas_rf_data.nrow; ++j) {
      f = field + j * mas_rf_data.ncol + i + NHEADER_FIELDS;
      f->name = malloc(sizeof("tesdatar##c##"));
      sprintf(f->name, "tesdatar%02ic%02i", j, i);
      f->spf = 1;
      f->type = GD_UINT32;
      f->offset = sizeof(uint32_t) * (j * mas_rf_data.ncol + i + HEADER_LEN);
      f->cadence = 0;
    }

  /* Add the checksum */
  f = field + mas_rf_data.nrow * mas_rf_data.ncol + NHEADER_FIELDS;
  f->name = "checksum";
  f->spf = 1;
  f->type = GD_UINT32;
  f->offset = sizeof(uint32_t) * (mas_rf_data.nrow * mas_rf_data.ncol
      + HEADER_LEN);
  f->cadence = 0;

  /* Register framedef */
  fdind = df_add_framedef(&fdef, 1, 0);

  /* add data_mode derived fields */
  char spec[4096];
  int d;
  for (d = 0; d < 2; ++d) {
    for (i = 0; i < mas_rf_data.ncol; ++i)
      for (j = 0; j < mas_rf_data.nrow; ++j) {
        switch (derived[mas_rf_data.data_mode][d].type) {
          case DERIV_RAW:
            /* use an /ALIAS? */
            sprintf(spec, "%s_r%02ic%02i LINCOM tesdatar%02ic%02i 1 0",
                derived[mas_rf_data.data_mode][d].name, j, i, j, i);
            mas_add_spec(spec, 0);
            break;
          case DERIV_SCALE:
            sprintf(spec, "%s_r%02ic%02i LINCOM tesdatar%02ic%02i %lg 0",
                derived[mas_rf_data.data_mode][d].name, j, i, j, i,
                derived[mas_rf_data.data_mode][d].scale);
            mas_add_spec(spec, 0);
            break;
          case DERIV_BIT:
            sprintf(spec, "%s_r%02ic%02i %sBIT tesdatar%02ic%02i %i %i",
                derived[mas_rf_data.data_mode][d].name, j, i,
                derived[mas_rf_data.data_mode][d].sign ? "S" : "", j, i,
                derived[mas_rf_data.data_mode][d].bitnum,
                derived[mas_rf_data.data_mode][d].numbits);
            mas_add_spec(spec, 0);
            break;
          case DERIV_BITSCALE:
            sprintf(spec, "INTER_%s_r%02ic%02i %sBIT tesdatar%02ic%02i %i %i",
                derived[mas_rf_data.data_mode][d].name, j, i,
                derived[mas_rf_data.data_mode][d].sign ? "S" : "", j, i,
                derived[mas_rf_data.data_mode][d].bitnum,
                derived[mas_rf_data.data_mode][d].numbits);
            mas_add_spec(spec, 0);
            sprintf(spec, "%s_r%02ic%02i LINCOM INTER_%s_r%02ic%02i %lg 0",
                derived[mas_rf_data.data_mode][d].name, j, i,
                derived[mas_rf_data.data_mode][d].name, j, i,
                derived[mas_rf_data.data_mode][d].scale);
            mas_add_spec(spec, 0);
            break;
          default:
            /* skip */
            break;
        }
      }
  }

  /* add convenience fields */
  sprintf(spec, "frame_rate CONST FLOAT64 %.16g", mas_rf_data.rate);
  mas_add_spec(spec, 0);

  /* this just divides the frame number by the frame rate.  More accurate
   * timing can be obtained by using the address0_ctr found in the frame header.
   * The downside to that is how quickly it wraps around.  */
  sprintf(spec, "acq_seconds LINCOM INDEX %.16g 0", 1. / mas_rf_data.rate);
  mas_add_spec(spec, 0);
}

/* returns nframes; on error exits with error code ret (1 for the first
 * flatfile; zero when cycling, so that the previous conversion is kept) */
static long long mas_load_flatfile(struct frame_header *fh, int new_acq,
    int follow, int ret)
{
  struct stat stat_buf;

  if (new_acq) {
    /* read and parse the runfile */
    if (runfile_read(mas_flatfile))
      df_exit(ret, 1);

    /* load the frameacq data from the runfile */
    if (load_frameacq())
      df_exit(ret, 1);

    /* runfile header */
    mas_rf_header = runfile_find_block("HEADER");
    if (mas_rf_header == NULL) {
      df_printf(DF_PRN_ERR, "missing required HEADER block in runfile.\n");
      df_exit(ret, 1);
    }

    /* check CC fw_rev */
    uint32_t cc_fw_rev = runfile_param_long("cc", "fw_rev", 0);
    if (cc_fw_rev < 0x5000000) {
      df_printf(DF_PRN_ERR, "Unsupported clock card firmware revision: 0x%X\n",
          cc_fw_rev);
      df_exit(ret, 1);
    }
  }

  /* open the data file */
  mas_fd = open(mas_flatfile, O_RDONLY);
  if (mas_fd < 0) {
    df_perror(DF_PRN_ERR, "open");
    df_exit(ret, 1);
  }

  df_printf(DF_PRN_INFO, "Reading %s\n", mas_flatfile);

  /* load the header of the first frame */
  load_frameheader(fh, follow);

  /* verify header version */
  if (fh->hdr_vers < 6) {
    df_printf(DF_PRN_ERR, "Unsupported frame header version: %u\n",
        fh->hdr_vers);
    df_exit(ret, 1);
  }

  /* calculate some useful things */
  int num_rc_present = MAS_FSW_NRC(fh->status);
  int ncol = MAS_FSW_NCOL(fh->status);
  mas_rcs[0] = (fh->status & MAS_FSW_RC1_HERE);
  mas_rcs[1] = (fh->status & MAS_FSW_RC2_HERE);
  mas_rcs[2] = (fh->status & MAS_FSW_RC3_HERE);
  mas_rcs[3] = (fh->status & MAS_FSW_RC4_HERE);

  int words_per_rc = ncol * fh->nrow_reported;
  int framesize = sizeof(*fh) /* header size */
    + words_per_rc * sizeof(uint32_t) * num_rc_present /* frame data */
    + sizeof(uint32_t); /* checksum */

  /* in follow mode, nframes can't be reliably calculated */
  long long nframes = 0;
  if (!follow) {
    if (stat(mas_flatfile, &stat_buf))
      df_perror(DF_PRN_WARN, "stat");
    else
      nframes = stat_buf.st_size / framesize;

    if (new_acq && sequence > 0)
      nframes += sequence * MAS_CHUNK_SIZE;
  }

  /* figure out the packing */
  mas_rf_data.ncol = runfile_rca_param_long("num_cols_reported");
  mas_rf_data.nrow = runfile_rca_param_long("num_rows_reported");
  int data_rate = runfile_param_long("cc", "data_rate", -1);
  if (data_rate <= 0) {
    df_printf(DF_PRN_ERR, "Bad cc parameter \"data_rate\"");
    df_exit(ret, 1);
  }
  mas_rf_data.data_mode = runfile_rca_param_long("data_mode");
  if (!mas_data_mode_supported(mas_rf_data.data_mode)) {
    df_printf(DF_PRN_ERR, "Unsupported data mode: %i\n", mas_rf_data.data_mode);
    df_exit(ret, 1);
  }

  mas_rf_data.rate = 50e6;
  if (mas_rf_data.data_mode == DATA_MODE_RAW) { /* the easy case */
    if (follow) {
      df_printf(DF_PRN_ERR,
          "RAW mode (data_mode 12) data can't be read in follow mode");
      df_exit(ret, 1);
    }
    mas_rf_data.nrow = 32;
    mas_rf_data.ncol = 8;
  } else { /* rectangle mode data */
    int cc_count = mas_rf_data.nrow * mas_rf_data.ncol;
    int rc_count = words_per_rc;

    /* sanity checks */
    if (cc_count % rc_count != 0)
      df_printf(DF_PRN_WARN, "imperfect RC->CC frame packing (%i->%i)\n",
          rc_count, cc_count);
    if (cc_count != rc_count && rc_count * data_rate != cc_count)
      df_printf(DF_PRN_WARN, "uneven RC->CC frame packing\n");

    /* frequency */
    long num_rows = runfile_param_long("cc", "num_rows", 0);
    long row_len = runfile_param_long("cc", "row_len", 0);
    mas_rf_data.rate = mas_rf_data.rate / (num_rows * row_len * data_rate);

    mas_rf_data.ncol *= num_rc_present;
  }

  return nframes;
}

/* the module entry point: this function runs as a separate thread (the input
 * thread) */
static int mas_entry(const struct df_config *config)
{
  long long skip, nframes;
  struct frame_header fh;
  size_t size = 0;
  int follow, eof, eof_count, last_pass, new_file;
  int have_fh = 1;

  /* cleanup function */
  df_on_abort(mas_clean);

  /* are we in follow mode? */
  follow = df_mode() & DF_MODE_FOLLOW;

  /* get the input plugin name and handle symlinkery */
  mas_pathname = strdup(df_input_name(1));
  if (mas_pathname == NULL) {
    df_printf(DF_PRN_ERR, "Out of memory");
    df_exit(1, 1);
  }

  mas_flatfile = strdup(mas_pathname);
  if (mas_flatfile == NULL) {
    df_printf(DF_PRN_ERR, "Out of memory");
    df_exit(1, 1);
  }
  mas_check_symlink(0);

  /* open and verify the input */
  nframes = mas_load_flatfile(&fh, 1, follow, 1);

  if (sequence != -1) { /* hide chunk number */
    size = strlen(mas_flatfile) - 4;
    mas_flatfile[size] = 0;
  }

  /* finally, we can spin up defile */
  if (df_init(nframes, mas_rf_data.rate, mas_flatfile))
    df_exit(1, 1);

  if (sequence != -1) /* restore chunk number */
    mas_flatfile[size] = '.';

  /* create the metadata */
  mas_metadata();

  /* deal with a skip */
  skip = df_get_offset();

  if (skip > mas_offset) { /* time to skip stuff */
    /* figure out if we need a new chunk */
    if (sequence != -1) {
      int new_sequence = skip / MAS_CHUNK_SIZE;
      if (sequence != new_sequence) {
        sequence = new_sequence;
        sprintf(mas_flatfile + strlen(mas_flatfile) - 3, "%03i", sequence);

        /* close old chunk; open new */
        mas_close_flatfile(0);

        nframes = mas_load_flatfile(&fh, 0, follow, 0);

        /* update total input length */
        df_update_length(nframes, 0);
      }

      /* adjust skip within this chunk */
      skip %= MAS_CHUNK_SIZE;
    }

    if (skip > 0) {  
      /* need to advance in this file and invalidate the frame header */
      if (lseek(mas_fd, skip * fdef.framesize, SEEK_SET) < 0) {
        df_perror(DF_PRN_ERR, "open");
        df_exit(1, 1);
      }
      have_fh = 0;
    }
  } else if (mas_offset > 0) {
    /* inform defile of the starting frame */
    df_set_offset(mas_offset);
  }

  /* OK Go */
  if (df_ready("checksum"))
    df_exit(1, 1);

  mas_fr = malloc(fdef.framesize);

  /* file loop */
  for (;;) {
    /* copy the header to the first frame of data */
    last_pass = 0;
    eof_count = 0;
    new_file = 0;
    if (have_fh) {
      size = sizeof(fh);
      memcpy(mas_fr, &fh, size);
    } else
      size = 0;

    /* chunk loop */
    for (;;) {
      for (eof = read_datafile(mas_fr, &size); !eof;
          eof = read_datafile(mas_fr, &size))
      {
        eof_count = 0;
        df_push_frame(fdind, 1, mas_fr, 1);
        size = 0; /* reset frame buffer */
      }

      df_check_abort();

      /* check for a change in file or symlink */
      if (eof_count++ > EOF_CHECK_TIME) {
        if (!last_pass) { /* haven't already checked */
          new_file = 0;

          if (mas_find_next_chunk())
            new_file = 1;

          /* Symlink checking only occurs in follow mode */
          if (follow && mas_check_symlink(0))
            new_file = 2;

          if (new_file) {
            /* We found a new chunk, so MAS must have stopped writing to the old
             * one.  So: we should only have to attempt reading it one more time
             * to get all the data out of it. */
            last_pass = 1; 
          } else if (!follow) {
            /* in follow mode, we continue to wait for more data, either in this
             * chunk or the next.  In non-follow mode, we're done */
            goto DONE;
          }
        } else {
          /* new flatfile */
          mas_close_flatfile(new_file == 2 ? 1 : 0); 

          /* open and verify the new input */
          long long nframes = mas_load_flatfile(&fh, new_file == 2 ? 1 : 0,
              follow, 0);
          have_fh = 1;

          if (new_file == 1) {
            /* increment nframes in non-follow mode */
            df_update_length(nframes, 1);
          } else {
            /* cycle the output on new symlink */

            if (sequence != -1) /* hide chunk number */
              mas_flatfile[strlen(mas_flatfile) - 4] = 0;

            if (df_reinit(nframes, mas_rf_data.rate, mas_flatfile,
                  DF_REINIT_SAVE))
            {
              df_exit(1, 1);
            }

            if (sequence != -1) /* restore chunk number */
              mas_flatfile[strlen(mas_flatfile) - 4] = '.';

            /* create the metadata */
            mas_metadata();

            /* and go again */
            if (df_ready("checksum"))
              df_exit(1, 1);
          }

          /* back to the top of the file loop */
          break;
        }
      }
      usleep(10000);
    }
  }

DONE:
  mas_clean();
  return 0;
}

/* The plugin framework; this is the only exported symbol.  It provides all
 * necessary information about this plugin to defile */
const struct df_input_framework mas_framework = {
  .licence = DF_LICENCE_GPL,
  .contact = DEFILE_MAS_CONTACT,
  .copyright = DEFILE_MAS_COPYRIGHT,
  .description = DEFILE_MAS_DESCRIPTION,
  .name = "mas",
  .version = PACKAGE_VERSION,
  .preamble = NULL,
  .postamble = NULL,
  .opts = NULL,
  .probe = mas_probe,
  .entry = mas_entry
};
