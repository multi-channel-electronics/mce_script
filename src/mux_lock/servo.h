#include <stdio.h>

#define MAXLINE 1024
#define MAXVOLTS 32
#define MAXCHANNELS 8
#define MAXROWS 41

#define SAFB_CARD 1
#define SQ2FB_CARD 2
#define SQ2BIAS_CARD 3

int flux_fb_set(int which_bc, int value);
int flux_fb_set_arr(int which_bc, int *arr);
int sq1fb_set(int which_rc, int value);
int sq1bias_set(int value);
int gengofile(char *datafile, char *workfile, int which_rc);
int acq(char *filename);

int genrunfile (
char *full_datafilename, /* datafilename including the path*/
char *datafile,          /* datafilename */
int  which_servo,        /* 1 for sq1servo, 2 for sq2servo*/
int  which_rc,
int  bias, int bstep, int nbias, int feed, int fstep, int nfeed,
char *initline1, char *initline2 /*init lines to be included in <servo_init> section*/
);

