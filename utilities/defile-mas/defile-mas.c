/* (C) 2013 D. V. Wiebe
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

#include <defile.h>

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
  uint32_t status, frame_count, row_len, nrow_reported, data_rate, arz_count;
  uint32_t vers, ramp_val, ramp_adr, nrow, sync, run_id, user_word;
  uint32_t header[30]; /* other stuff */
};

#define NHEADER_FIELDS 13
static const char *header_field[NHEADER_FIELDS] = {
  "status", "frame_ctr", "row_len", "num_rows_reported", "data_rate",
  "address0_ctr", "header_version", "ramp_value", "ramp_addr", "num_rows",
  "sync_box_num", "runfile_id", "userfield"
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
static int fdind = -1;
static struct df_fdef fdef;
static int mas_rcs[4];
static struct runfile_block *mas_rf_header;
static int mas_fd = -1;
static struct runfile rf = { 0, NULL };
static struct {
  long rf_vers;
  const char *mas_vers;
  const char *array_id;
  int rc[4];
  const char *filename;
  int64_t framecount;
  int64_t ctime;
  const char *hostname;
} frameacq;

/* public strings; see defile-input(7) */
#define DEFILE_MAS_COPYRIGHT "Copyright (C) 2013 D. V. Wiebe"
#define DEFILE_MAS_CONTACT \
  "For contact information, see http://cmbr.phas.ubc.ca/mcewiki/"
#define DEFILE_MAS_DESCRIPTION "MCE-MAS flat-file data"

/* the probe function: return non-zero if we think "name" is a MAS file */
static int mas_probe(const char *name)
{
  struct stat stat_buf;
  char *run_file;
  char *full_name = df_shell_expand(name);

  if (full_name == NULL)
    return 0;

  /* make sure it's a file */
  if (stat(full_name, &stat_buf)) {
    free(full_name);
    return 0;
  }

  if (!S_ISREG(stat_buf.st_mode)) {
    free(full_name);
    return 0;
  }

  /* look for a run file */
  run_file = malloc(strlen(full_name) + sizeof(".run") + 1);
  if (run_file == NULL) {
    free(full_name);
    return 0;
  }

  sprintf(run_file, "%s.run", full_name);

  /* make sure it's a file */
  if (stat(run_file, &stat_buf)) {
    free(full_name);
    free(run_file);
    return 0;
  }

  if (!S_ISREG(stat_buf.st_mode)) {
    free(full_name);
    free(run_file);
    return 0;
  }
  free(run_file);

  /* try opening it */
  mas_fd = open(full_name, O_RDONLY);
  free(full_name);

  if (mas_fd < 0)
    return 0;

  close(mas_fd);
  return 1;
}

static int mas_clean(void)
{
  int i, j;

  if (mas_fd >= 0)
    close(mas_fd);

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
  }
  free(rf.block);

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
    df_exit(1,1);
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
  char *runfile = malloc(strlen(base) + sizeof(".run"));
  char buffer[1024];
  struct runfile_block *block = NULL;
  struct runfile_tag *tag = NULL;
  char *name, *spec, *data;
  void *ptr;
  int i, lineno = 0;

  if (runfile == NULL)
    return 1;

  sprintf(runfile, "%s.run", base);

  stream = fopen(runfile, "rt");
  if (stream == NULL) {
    df_printf(DF_PRN_ERR, "Unable to open runfile: %s\n", runfile);
    free(runfile);
    return 1;
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
  if (frameacq.rf_vers != 2) {
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
static int mas_data_mode_supported(int data_mode)
{
  return (data_mode == 0 || data_mode == 1 || data_mode == 2 || data_mode == 4
      || data_mode == 5 || data_mode == 10 || data_mode == 11
      || data_mode == 12);
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
          df_add_spec(spec, rf_frag);
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
        df_printf(DF_PRN_ERR, "Couldn't interpret parameter \"%s\" of "
            "%s as integer.\n", mas_rf_header->tag[i].spec[0],
            mas_rf_header->tag[i].spec[0]);
        df_exit(1, 1);
      }
      sprintf(spec, "%s/%s CONST INT32 %li", mas_rf_header->tag[i].spec[0],
          mas_rf_header->tag[i].spec[1], v);
    } else {
      size_t pos = sprintf(spec, "%s/%s CARRAY INT32",
          mas_rf_header->tag[i].spec[0], mas_rf_header->tag[i].spec[1]);
      for (j = 0; j < mas_rf_header->tag[i].ndata; ++j) {
        char *endptr;
        long v = strtol(mas_rf_header->tag[i].data[0], &endptr, 10);

        if (*endptr) {
          df_printf(DF_PRN_ERR, "Couldn't interpret element %i of parameter "
              "\"%s\" of %s as integer.\n", j, mas_rf_header->tag[i].spec[0],
              mas_rf_header->tag[i].spec[0]);
          df_exit(1, 1);
        }
        pos += sprintf(spec + pos, " %li", v);
      }
    }
    df_add_spec(spec, rf_frag);
  }
}

/* returns non-zero on EOF */
static int read_datafile(const struct frame_header *fh, char *data)
{
  size_t len = fdef.framesize;
  ssize_t n;

  /* already read the header */
  if (fh) {
    len -= sizeof(uint32_t) * HEADER_LEN;
    memcpy(data, fh, sizeof(*fh));
    data += sizeof(*fh);
  }

  /* read more */
  while (len > 0) {
    n = read(mas_fd, data, len);
    if (n < 0) {
      df_perror(DF_PRN_ERR, "read");
      df_exit(1,1);
    }
    if (n == 0) {/* eof */
      return 1;
    }
    len -= n;
    data += n;
  }

  return 0;
}

/* the module entry point: this function runs as a separate thread (the input
 * thread) */
static int mas_entry(const struct df_config *config)
{
  int i, j;
  int follow;
  struct frame_header fh;
  struct stat stat_buf;

  /* get the input plugin name */
  const char *name = df_input_name(1);

  /* are we in follow mode? */
  follow = df_mode() & DF_MODE_FOLLOW;

  /* cleanup function */
  df_on_abort(mas_clean);

  /* read and parse the runfile */
  if (runfile_read(name))
    df_exit(1, 1);

  /* load the frameacq data from the runfile */
  if (load_frameacq())
    df_exit(1, 1);

  /* runfile header */
  mas_rf_header = runfile_find_block("HEADER");
  if (mas_rf_header == NULL) {
    df_printf(DF_PRN_ERR, "missing required HEADER block in runfile.\n");
    df_exit(1, 1);
  }

  /* check CC fw_rev */
  uint32_t cc_fw_rev = runfile_param_long("cc", "fw_rev", 0);
  if (cc_fw_rev < 0x5000000) {
    df_printf(DF_PRN_ERR, "Unsupported clock card firmware revision: 0x%X\n",
        cc_fw_rev);
    df_exit(1, 1);
  }

  /* open the data file */
  mas_fd = open(name, O_RDONLY);
  if (mas_fd < 0) {
    df_perror(DF_PRN_ERR, "open");
    df_exit(1, 1);
  }

  /* load the header of the first frame */
  load_frameheader(&fh, follow);

  /* verify header version */
  if (fh.vers < 6) {
    df_printf(DF_PRN_ERR, "Unsupported frame header version: %u\n", fh.vers);
    df_exit(1,1);
  }

  /* calculate some useful things */
  int num_rc_present = MAS_FSW_NRC(fh.status);
  int ncol = MAS_FSW_NCOL(fh.status);
  mas_rcs[0] = (fh.status & MAS_FSW_RC1_HERE);
  mas_rcs[1] = (fh.status & MAS_FSW_RC2_HERE);
  mas_rcs[2] = (fh.status & MAS_FSW_RC3_HERE);
  mas_rcs[3] = (fh.status & MAS_FSW_RC4_HERE);

  int words_per_rc = ncol * fh.nrow_reported;
  int framesize = sizeof(fh) /* header size */
    + words_per_rc * sizeof(uint32_t) * num_rc_present /* frame data */
    + sizeof(uint32_t); /* checksum */

  /* in follow mode, nframes can't be reliably calculated */
  long long nframes = 0;
  if (!follow) {
    if (stat(name, &stat_buf))
      df_perror(DF_PRN_WARN, "stat");
    else
      nframes = stat_buf.st_size / framesize;
  }

  /* figure out the packing */
  ncol = runfile_rca_param_long("num_cols_reported");
  int nrow = runfile_rca_param_long("num_rows_reported");
  int data_rate = runfile_param_long("cc", "data_rate", -1);
  if (data_rate <= 0) {
    df_printf(DF_PRN_ERR, "Bad cc parameter \"data_rate\"");
    df_exit(1,1);
  }
  int data_mode = runfile_rca_param_long("data_mode");
  if (!mas_data_mode_supported(data_mode)) {
    df_printf(DF_PRN_ERR, "Unsupported data mode: %i\n", data_mode);
    df_exit(1,1);
  }

  double rate = 50e6;
  if (data_mode == DATA_MODE_RAW) { /* the easy case */
    if (follow) {
      df_printf(DF_PRN_ERR,
          "RAW mode (data_mode 12) data can't be read in follow mode");
      df_exit(1,1);
    }
    nrow = 32;
    ncol = 8;
  } else { /* rectangle mode data */
    int cc_count = nrow * ncol;
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
    rate = rate / (num_rows * row_len * data_rate);

    ncol *= num_rc_present;
  }

  /* finally, we can spin up defile */
  df_init(nframes, rate, NULL);

  /* store the runfile data in a new fragment */
  write_rf_header();

  /* make the framedef */
  struct df_fdef_field *field = malloc(sizeof(struct df_fdef_field) * (nrow
      * ncol + NHEADER_FIELDS + 1));
  struct df_fdef_field *f;
  fdef.framesize = (nrow * ncol + HEADER_LEN + 1) * sizeof(uint32_t);
  fdef.framesize = (nrow * ncol + HEADER_LEN + 1) * sizeof(uint32_t);
  fdef.n_fields = nrow * ncol + NHEADER_FIELDS + 1;
  fdef.field = field;
  for (i = 0; i < NHEADER_FIELDS; ++i) {
    f = field + i;
    f->name = (char*)header_field[i];
    f->spf = 1;
    f->type = GD_UINT32;
    f->offset = i * sizeof(uint32_t);
    f->cadence = 0;
  }
  for (i = 0; i < ncol; ++i)
    for (j = 0; j < nrow; ++j) {
      f = field + i * nrow + j + NHEADER_FIELDS;
      f->name = malloc(sizeof("tesdatar##c##"));
      sprintf(f->name, "tesdatar%02ic%02i", i, j);
      f->spf = 1;
      f->type = GD_UINT32;
      f->offset = sizeof(uint32_t) * (i * nrow + j + HEADER_LEN);
      f->cadence = 0;
    }
  f = field + nrow * ncol + NHEADER_FIELDS;
  f->name = "checksum";
  f->spf = 1;
  f->type = GD_UINT32;
  f->offset = sizeof(uint32_t) * (nrow * ncol + HEADER_LEN);
  f->cadence = 0;
  fdind = df_add_framedef(&fdef, 1, 0);

  /* add data_mode derived fields */
  char spec[4096];
  int d;
  for (d = 0; d < 2; ++d) {
    for (i = 0; i < ncol; ++i)
      for (j = 0; j < nrow; ++j) {
        switch (derived[data_mode][d].type) {
          case DERIV_RAW:
            /* use an /ALIAS? */
            sprintf(spec, "%s_r%02ic%02i LINCOM tesdatar%02ic%02i 1 0",
                derived[data_mode][d].name, j, i, j, i);
            df_add_spec(spec, 0);
            break;
          case DERIV_SCALE:
            sprintf(spec, "%s_r%02ic%02i LINCOM tesdatar%02ic%02i %lg 0",
                derived[data_mode][d].name, j, i, j, i,
                derived[data_mode][d].scale);
            df_add_spec(spec, 0);
            break;
          case DERIV_BIT:
            sprintf(spec, "%s_r%02ic%02i %sBIT tesdatar%02ic%02i %i %i",
                derived[data_mode][d].name, j, i,
                derived[data_mode][d].sign ? "S" : "", j, i,
                derived[data_mode][d].bitnum,
                derived[data_mode][d].numbits);
            df_add_spec(spec, 0);
            break;
          case DERIV_BITSCALE:
            sprintf(spec, "INTER_%s_r%02ic%02i %sBIT tesdatar%02ic%02i %i %i",
                derived[data_mode][d].name, j, i,
                derived[data_mode][d].sign ? "S" : "", j, i,
                derived[data_mode][d].bitnum,
                derived[data_mode][d].numbits);
            df_add_spec(spec, 0);
            sprintf(spec, "%s_r%02ic%02i LINCOM INTER_%s_r%02ic%02i %lg 0",
                derived[data_mode][d].name, j, i,
                derived[data_mode][d].name, j, i,
                derived[data_mode][d].scale);
            df_add_spec(spec, 0);
            break;
          default:
            /* skip */
            break;
        }
      }
  }

  /* OK Go */
  if (df_ready("checksum"))
    df_exit(1, 1);

  /* frame loop */
  char *fr = malloc(fdef.framesize);
  int eof;
  for (;;) {
    for (eof = read_datafile(&fh, fr); !eof; eof = read_datafile(NULL, fr))
      df_push_frame(fdind, 1, fr, 1);

    if (!follow)
      break;

    usleep(1000);
    df_check_abort();
  }

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
