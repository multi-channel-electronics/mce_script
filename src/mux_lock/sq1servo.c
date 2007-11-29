#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include "servo_err.h"
#include "servo.h"

/***********************************************************
 *    sq1servo       : locks sq1 by calculating new sq2_fb value and sweeping sq2_bias
 *    Author         : Mandana@ubc/Dennis@atc     5May2005
 *    Original Source: ssaservo
 *    History        : updated the directory path for datafile and configfile to be extracted from the new DAS global variables $DATADIR and $USRCONFIGDIR
 *    31May2005      : lock target and readout-card number are parameters now
 *    18May2005      : re-ordered bc1, bc2, bc3
 *
 * Revision history:
 * <date $Date: 2007/10/22 23:38:35 $>    - <initials $Author: mce $>
 * $Log: sq1servo.c,v $
 * Revision 1.27  2007/10/22 23:38:35  mce
 *   * EB: MH fixed a bug
 *   * MA added <> to .bias header line
 *   * MA renamed .fb to .bias and creates a merger-friendly format of .bias file
 *
 ***********************************************************/

/************************************************************
 *          M A I N
 ************************************************************/
int main ( int argc, char **argv )
{
   char command[256];      /* command sent to shell */
   char datafile[256];     /* datafile being written by DAS */
   char full_datafilename[256]; /*full path for datafile*/
   char workfile[20];      /* temporary batch file */
   char sq2fb_initfile[256];      /* filename for sq2fb.init*/
   char row_initfile[256];
   char errmsg_temp[256];

   int i;
   int j;
   FILE *fd;                /* pointer to output file*/
   FILE *df;                /* pointer to datafile*/
   FILE *tempf;             /* pointer to sq2fb.init file*/
   double gain;             /* servo gain (=P=I) */
   char *endptr;
   char line[MAXLINE];
   char *datadir;
   char init_line1[MAXLINE];    /* record a line of init values and pass it to genrunfile*/
   char init_line2[MAXLINE];    /* record a line of init values and pass it to genrunfile*/
   int rowline[MAXVOLTS];
   int nbias;
   int nfeed;
   char outfile[256];       /* output data file */
   int snum;                /* loop counter */
   int sq2fb[MAXVOLTS];     /* sq2 feedback voltages */
   int sq1bias;             /* SQ2 bias voltage */
   int sq1bstep;            /* SQ2 bias voltage step */
   int sq1feed;             /* SQ2 feedback voltage */
   int sq1fstep;            /* SQ2 feedback voltage step */
   char *fstatus;
   double z;                /* servo feedback offset */
   int  which_rc;
   int nrow[MAXVOLTS];
   int total_row;
   int sysret;
   int col;
   int skip_sq1bias = 0;
   char tempbuf[30];

/* check command-line arguments */

   if ( argc != 12 && argc != 13)
   {  
      printf ( "Rev. 1.27\n");
      printf ( "usage:- sq1servo outfile sq1bias sq1bstep nbias " );
      printf ( "sq1fb sq1fstep nfb N target total_row gain skip_sq1bias\n" );
      printf ( "   outfile = filename for output data\n" );
      printf ( "   sq1bias = starting SQ1 bias\n" );
      printf ( "   sq1bstep = step size for SQ1 bias\n" );
      printf ( "   nbias = number of bias steps\n" );
      printf ( "   sq1fb = starting SQ1 feedback\n" );
      printf ( "   sq1fstep = step size for SQ1 feedback\n" );
      printf ( "   nfb = number of feedback steps\n" );
      printf ( "   N = readout-card number (1 to 4)\n");
      printf ( "   target = lock target \n");
      printf ( "   total_row = total number of rows in the system \n");
      printf ( "   gain = gain of the servo (double)\n");
      printf ( "   skip_sq1bias (optional) = if specified as 1, no SQ1 bias is applied\n");
      printf ( "*NOTE*: Make sure sq2fb.init (32 single-entry lines) and row.init (32 single-entry lines between 0 to 40) are present in the data directory\n"); 
      ERRPRINT("no argument specified");
      return 1;
   }

   if ( (datadir=getenv("MAS_DATA")) == NULL){
     ERRPRINT("Enviro var. $MAS_DATA not set, quit");
     return 2;
   }
   
   strcpy ( datafile, argv[1]);
   sprintf(full_datafilename, "%s%s",datadir, datafile);
/* Open output file to append modified data set */
   sprintf(outfile, "%s%s.bias", datadir, argv[1]);

   fd = fopen ( outfile, "a" );

/* Get starting SQ2 feedback values  from a file called sq2fb.init*/
   strcpy (sq2fb_initfile, datadir);
   strcat (sq2fb_initfile, "sq2fb.init");
   if ((tempf = fopen (sq2fb_initfile, "r")) == NULL){
      sprintf (errmsg_temp,"failed to open sq2fb.init (%s) to read initial settings for sq2fb", sq2fb_initfile);
      ERRPRINT(errmsg_temp);
      exit(4);
   }
   /*prepare a line of init values for runfile*/
   sprintf(init_line1, "<sq2fb.init> ");
   for ( j=0; j<MAXVOLTS; j++ ){
     if ((fstatus = fgets (line, MAXLINE, tempf)) == NULL){
       ERRPRINT ("reading sq2fb.init quitting....");
       exit(5);
     }
     sq2fb[j] = atoi (line );
     sprintf(tempbuf, "%d ", sq2fb[j]);
     strcat(init_line1, tempbuf);
   }
   fclose(tempf);

/* Get row number for each column to servo on*/
   strcpy (row_initfile, datadir);
   strcat (row_initfile, "row.init");
   if ((tempf = fopen (row_initfile, "r")) == NULL){
      sprintf (errmsg_temp, "failed to open row.init (%s) to read row numbers to servo on", row_initfile);
      ERRPRINT(errmsg_temp);
      exit(6);
   }
   /*prepare a line of init values for runfile*/
   sprintf(init_line2, "<row.init> ");
   for ( j=0; j<MAXVOLTS; j++ )
   {
     if ((fstatus = fgets (line, MAXLINE, tempf)) == NULL){
       ERRPRINT("reading row.init quitting....");
       exit (7);
     }
     nrow[j] = atoi (line );
     sprintf(tempbuf, "%d ", nrow[j]);
     strcat(init_line2, tempbuf);
     if (nrow[j]<0 || nrow[j]>40){
       sprintf (errmsg_temp, "a row number has to be between 0 and 40, not %d!", nrow[j]); 
       ERRPRINT(errmsg_temp);
       exit(8);
     } 
   }
   fclose(tempf);

/* Get range of values for second stage SQUIDs */
   sq1bias = atoi ( argv[2] );
   sq1bstep = atoi ( argv[3] );
   nbias = atoi ( argv[4] );
   sq1feed = atoi ( argv[5] );
   sq1fstep = atoi ( argv[6] );
   nfeed = atoi ( argv[7] );
   which_rc = atoi (argv[8]);
   z = atoi (argv[9]);
   total_row = atoi(argv[10]);
   gain = strtod (argv[11], &endptr);
   if (argc == 13){
      skip_sq1bias = atoi(argv[12]);
      if (nbias <1 ) nbias = 1;
      printf("No SQ1 bias is applied!\n");
   }
   else 
     skip_sq1bias = 0;

   /** generate a runfile **/
   sysret=genrunfile (full_datafilename, datafile, 1, which_rc, 
                      sq1bias, sq1bstep, nbias, sq1feed, sq1fstep, nfeed, 
                      init_line1, init_line2);
   if (sysret != 0){
     sprintf(errmsg_temp, "genrunfile %s.run failed with %d", datafile, sysret);
     ERRPRINT(errmsg_temp);
     exit(17);
   }

   /* generate the header line for the bias file*/
   for ( snum=(which_rc-1)*8; snum<which_rc*8; snum++ )
      fprintf ( fd, "  <error%02d> ", snum);
         
   for ( snum=(which_rc-1)*8; snum<which_rc*8; snum++ )
      fprintf ( fd, "  <sq2fb%02d> ", snum); 
   fprintf ( fd, "\n");

   /* create the temp script to acquire one frame*/
   strcpy (workfile, "sq1servo.temp");
   if ( (sysret=gengofile(datafile, workfile,  which_rc)) != 0){
     sprintf(errmsg_temp, "gengofile failed %d", sysret);
     ERRPRINT(errmsg_temp);
     return 6;
   }
   
   /* apply the sq2fb starting values (as specified in sq2fb.init) and sq1bias starting value
      and trigger one-frame data acqusition*/
   flux_fb_set_arr(SQ2FB_CARD, sq2fb);
   sq1fb_set(which_rc, sq1feed);
   
   if (skip_sq1bias == 0)
     sq1bias_set(sq1bias);
   
   if ((sysret = acq(workfile)) != 0)
     return sysret;
  
   /* start the servo*/
   for ( j=0; j<nbias; j++ ){
      sq1bias += sq1bstep;
      if (skip_sq1bias == 0)
        sq1bias_set(sq1bias);      
      for ( i=0; i<nfeed; i++ ){
         /* we calculate and read sa_fb twice for every sq1feed iteration*/
         sq1feed += sq1fstep;

         /* Get the data read from the previous setting*/
         if( (df = fopen(full_datafilename, "r")) == NULL){
            sprintf(errmsg_temp,"openning temp file %s\n", full_datafilename);
            ERRPRINT(errmsg_temp);
            exit(10);
         }
         
         for (col=0; col<MAXCHANNELS; col++){
            if (fseek(df, col*4 -(4+ (total_row - nrow[col+((which_rc-1)*8)])*MAXCHANNELS*4), SEEK_END)!= 0){
               sprintf (errmsg_temp, "fseek %s, quitting....", full_datafilename);
               ERRPRINT(errmsg_temp);
               exit(11);
            }
            if (fread(&rowline[col],sizeof(int), 1, df) == 0){
              sprintf (errmsg_temp, "fread %s failed", full_datafilename);
              ERRPRINT(errmsg_temp);
              exit(12);
            }
            fprintf(fd, "%11d ", rowline[col]);
	 }
	 fclose (df); 
         
         /* get the right columns*/
         for ( snum=(which_rc-1)*8; snum<which_rc*8; snum++ ){
            sq2fb[snum] += gain * ( rowline[snum%8]-z );
            fprintf ( fd, "%11d ", sq2fb[snum] );
         }
         fprintf ( fd, "\n" );
         fflush (fd);
         /* Change voltages and trigger more data acquisition */
	 flux_fb_set_arr(SQ2FB_CARD, sq2fb);
	 sq1fb_set(which_rc, sq1feed);
	 
         /* if this is the last iteration, skip_go */
          if ((j!=nbias-1) || (i!=nfeed-1))
            if ( (sysret = acq(workfile)) != 0)
	      return sysret;
      }
   }
   /* reset values back to 0*/
   flux_fb_set (SQ2FB_CARD, 0);
   sq1fb_set(which_rc, -8192);
   if (skip_sq1bias == 0)
     sq1bias_set(0);
   else
      printf("This script did not apply SQ1 bias, you may need to turn biases off manually!\n"); 
   return 0;
}
