#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#include "servo_err.h"
#include "servo.h"

/***********************************************************
 *    sq2servo       : locks sq2 by calculating new sa_fb value and sweeping sq2_fb
 *    Author         : Mandana@ubc/Dennis@atc     4May2005
 *    History        :
 *       31May2005   : target and rc number are parameters now
 *       2May2005    : changed readline to fgets, changed fprintf to outfile, removed mcexml_split
 *       4May2005    : parametrize which RC card is going to take data
 *                   : swapped bc1, bc3
 *       18May2005   : re-ordered bc1, bc2, bc3
 *
 *  Revision history:
 *  <date $Date: 2007/10/22 23:38:35 $>    - <initials $Author: mce $>
 *  $Log: sq2servo.c,v $
 *  Revision 1.21  2007/10/22 23:38:35  mce
 *    * EB: MH fixed a bug
 *    * MA added <> to .bias header line
 *    * MA renamed .fb to .bias and creates a merger-friendly format of .bias file
 *
 ***********************************************************/
/************************************************************
 *          M A I N
 ************************************************************/
int main ( int argc, char **argv )
{
   char datafile[256];     /* datafile being written by DAS */
   char full_datafilename[256]; /*full path for datafile*/
   char workfile[20];      /* temporary batch file */
   char safb_initfile[256];      /* filename for safb.init*/
   char *datadir;
   char errmsg_temp[256];
   int sysret;
 
   int i;
   int j;
   FILE *fd;                /* pointer to output file*/
   FILE *df;                /* pointer to datafile*/
   FILE *tempf;             /* pointer to safb.init file*/
   int fstatus;             /* error checking in file operation*/ 
   double gain;             /* servo gain (=P=I) for the 0th calculation of the servo*/
   char *endptr;
   char line[MAXLINE]; 
   char init_line[MAXLINE];    /* record a line of init values and pass it to genrunfile*/
   int rowline[MAXCHANNELS]; /* error signal input */
   int ncol;
   int nbias;
   int nfeed;
   char outfile[256];       /* output data file */
   int snum;                /* loop counter */
   int ssafb[MAXVOLTS];     /* series array feedback voltages */
   int sq2bias;             /* SQ2 bias voltage */
   int sq2bstep;            /* SQ2 bias voltage step */
   int sq2feed;             /* SQ2 feedback voltage */
   int sq2fstep;            /* SQ2 feedback voltage step */
   double z;                /* servo feedback offset */ 
   int  which_rc;
   int  skip_sq2bias = 0;
   char tempbuf[30];
   int  error = 0;
   time_t start, finish;
   
   time(&start);
   
/* check command-line arguments */
   if ( argc != 11 && argc != 12)
   {  
      printf ( "Rev. 1.23\n");
      printf ( "usage: sq2servo outfile sq2bias sq2bstep nbias\n" );
      printf ( "sq2feed sq2fstep nfeed N target gain skip_sq2bias\n" );
      printf ( "   outfile = name of file for output data\n" );
      printf ( "   sq2bias = starting SQ2 bias\n" );
      printf ( "   sq2bstep = step for SQ2 bias\n" );
      printf ( "   nbias = number of bias steps\n" );
      printf ( "   sq2feed = starting SQ2 feedback\n" );
      printf ( "   sq2fstep = step for SQ2 feedback\n" );
      printf ( "   nfeed = number of feedback steps\n" );
      printf ( "   N = readout-card number (1 to 4)\n" );
      printf ( "   target = lock target \n");
      printf ( "   gain = servo gain (double) \n");
      printf ( "   skip_sq2bias (optional) = if specified as 1, then no sq2_bias is applied.\n");
      ERRPRINT("wrong number of arguments");
      return 1;
   }
   // Load MCE config information ("xml")
   mceconfig_t *conf;
   if (mceconfig_load(CONFIG_FILE, &conf) != 0) {
     sprintf(errmsg_temp, "Load MCE configuration file %s", CONFIG_FILE);
     ERRPRINT(errmsg_temp);
     return ERR_MCE_LCFG;
   }

   // Connect to an mce_cmd device.
   int handle = mce_open(CMD_DEVICE);
   if (handle < 0) {
     sprintf(errmsg_temp, "Failed to open %s.\n", CMD_DEVICE);
     ERRPRINT(errmsg_temp);
     return ERR_MCE_OPEN;
   }

   // Share the config information with the mce_cmd device
   mce_set_config(handle, conf);
   
   // Lookup "bc1 flux_fb"
   mce_param_t m_safb;
   if ((error=mce_load_param(handle, &m_safb, SAFB_CARD, "flux_fb")) != 0) {
     sprintf(errmsg_temp, "lookup of %s flux_fb failed with %d", SAFB_CARD, error); 
     ERRPRINT(errmsg_temp);
     return ERR_MCE_PARA;
   }     
   // Lookup "bc1 flux_fb"
   mce_param_t m_sq2fb;
   if ((error=mce_load_param(handle, &m_sq2fb, SQ2FB_CARD, "flux_fb")) != 0) {
     sprintf(errmsg_temp, "lookup of %s flux_fb failed with %d", SQ2FB_CARD, error); 
     ERRPRINT(errmsg_temp);
     return ERR_MCE_PARA;
   }     
   // Lookup "bc3 flux_fb"
   mce_param_t m_sq2bias;
   if ((error=mce_load_param(handle, &m_sq2bias, SQ2BIAS_CARD, "flux_fb")) != 0) {
     sprintf(errmsg_temp, "lookup of %s flux_fb failed with %d", SQ2BIAS_CARD, error); 
     ERRPRINT(errmsg_temp);
     return ERR_MCE_PARA;
   }     

   if ( (datadir=getenv("MAS_DATA")) == NULL){
      ERRPRINT("Enviro var. $MAS_DATA not set, quit");
      return ERR_DATA_DIR;
   }
   strcpy (datafile, argv[1]);
   sprintf (full_datafilename, "%s%s",datadir, datafile);

/* Open output file to append modified data set */
   sprintf(outfile, "%s%s.bias", datadir, argv[1]);
   fd = fopen ( outfile, "a" );

/* Get starting SA feedback values  from a file called safb.init*/
   strcpy (safb_initfile, datadir);
   strcat (safb_initfile, "safb.init");
   if ((tempf = fopen (safb_initfile, "r")) == NULL){
      ERRPRINT("failed to open safb.init to read initial settings for safb");
      return ERR_SAFB_INI;
   }
   
   /* prepare a line of init values for runfile*/   
   sprintf(init_line, "<safb.init> ");
   for ( j=0; j<MAXVOLTS; j++ ){
     if ( fgets (line, MAXLINE, tempf) == NULL){
       ERRPRINT("reading safb.init quitting...."); 
       return ERR_INI_READ;
     }
     ssafb[j] = atoi (line );
     sprintf(tempbuf, "%d ", ssafb[j]);
     strcat(init_line, tempbuf);
   }
   fclose(tempf);

/* Get range of values for second stage SQUIDs */
   sq2bias = atoi ( argv[2] );
   sq2bstep = atoi ( argv[3] );
   nbias = atoi ( argv[4] );
   sq2feed = atoi ( argv[5] );
   sq2fstep = atoi ( argv[6] );
   nfeed = atoi ( argv[7] );
   which_rc = atoi ( argv[8]);
   z = atoi (argv[9]);
   gain = strtod(argv[10], &endptr);

   if (argc == 12){
      skip_sq2bias = atoi(argv[11]);
      if (nbias <1) nbias = 1;
      printf ("No SQ2 bias is applied!\n");
   }
   else
      skip_sq2bias = 0;
  
   /** generate a runfile **/
   sysret=genrunfile (full_datafilename, datafile, 2, which_rc, 
                      sq2bias, sq2bstep, nbias, sq2feed, sq2fstep, nfeed, 
                      init_line, NULL);
   if (sysret != 0){
     sprintf(errmsg_temp, "genrunfile %s.run failed with %d", full_datafilename, sysret);
     ERRPRINT(errmsg_temp);
     return ERR_RUN_FILE; 
   }

   /* generate the header line for the bias file*/
   for ( snum=(which_rc-1)*8; snum<which_rc*8; snum++ )
     fprintf ( fd, "  <error%02d> ", snum);  
         
   for ( snum=(which_rc-1)*8; snum<which_rc*8; snum++ )
     fprintf ( fd, "  <ssafb%02d> ", snum);  
   fprintf ( fd, "\n");
  
   /* create the temp script to acquire one frame*/ 
   strcpy (workfile, "sq2servo.temp");
   if ( (sysret=gengofile(datafile, workfile,  which_rc)) != 0){
     sprintf(errmsg_temp, "gengofile failed %d", sysret);
     ERRPRINT(errmsg_temp);
     return ERR_TMP_FILE;
   }  
   
   /* write the initial ssafb values, do not apply any bias, 
      Execute a go command to take one frame of data to start the algorithm */
   
   if ((error = mce_write_block(handle, &m_safb, MAXVOLTS, (u32 *)ssafb)) != 0) /*array*/
     error_action("mce_write_block safb", error);

   for ( snum=(which_rc-1)*8; snum<which_rc*8; snum++ ){
     if ((error = mce_write_element(handle, &m_sq2fb, snum, sq2feed)) != 0)
       error_action("mce_write_element sq2fb", error);
   }
   if ( (sysret = acq(workfile)) != 0)
     return sysret;
   
   for ( j=0; j<nbias; j++ ){
      sq2bias += sq2bstep;
      if (skip_sq2bias == 0){
        for ( snum=(which_rc-1)*8; snum<which_rc*8; snum++ )
          if ((error = mce_write_element(handle, &m_sq2bias, snum, sq2bias)) != 0)
            error_action("mce_write_element sq2bias", error);
      }

      for ( i=0; i<nfeed; i++ ){
         /* we calculate and read sa_fb twice for every sq2feed iteration*/
         sq2feed += sq2fstep;

         /* Get the data read from the previous setting*/
         if( (df = fopen(full_datafilename, "r")) == NULL){
            sprintf(errmsg_temp, "openning data file: %s", full_datafilename);
            ERRPRINT(errmsg_temp);
            exit(7);
         }
         /* read the last row, skip the checksum (8+1)*4 */
         if ((fstatus = fseek(df, -36, SEEK_END)) != 0){
            sprintf(errmsg_temp,"fseek on %s returned %d", full_datafilename, fstatus);
            ERRPRINT(errmsg_temp);
            exit(8);
         }
         if (fread (rowline, sizeof(int), MAXCHANNELS, df) == 0){
           sprintf (errmsg_temp,"fread on %s failed", full_datafilename);
           ERRPRINT(errmsg_temp);
           exit (8);
         }
         fclose (df);
         /* done with reading the file*/

         /* now extract each column's reading*/
         for (ncol=0; ncol<MAXCHANNELS; ncol++)
           fprintf ( fd, "%11d ", rowline[ncol] );

         for ( snum=(which_rc-1)*8; snum<which_rc*8; snum++ ){
           ssafb[snum] += gain * (rowline[snum%8]-z );
           fprintf ( fd, "%11d ", ssafb[snum] );
         }
         fprintf ( fd, "\n" );
         fflush (fd);
         /* change voltages and trigguer more data acquisition */
         if ((error = mce_write_block(handle, &m_safb, MAXVOLTS, (u32 *)ssafb)) != 0) /*array*/
           for ( snum=(which_rc-1)*8; snum<which_rc*8; snum++ )
             error = mce_write_element(handle, &m_sq2fb, snum, sq2feed);
         
	 /* if this is the last iteration, skip_go */
         if ( (j != nbias-1) || (i != nfeed-1)){ 
           if ( (sysret = acq(workfile)) != 0)		   
             return sysret;
	 }  
      }
   }

   /* reset biases back to 0*/
   for ( snum=(which_rc-1)*8; snum<which_rc*8; snum++ ){
     ssafb[snum] = 0;
     if ((error = mce_write_element(handle, &m_sq2fb, snum, 0)) != 0)
       error_action("mce_write_element sq2fb", error);
   }
   if ((error = mce_write_block(handle, &m_safb, MAXVOLTS, (u32 *)ssafb)) != 0) /*array*/
     error_action("mce_write_block safb failed", error);

   if (skip_sq2bias == 0)
     for ( snum=(which_rc-1)*8; snum<which_rc*8; snum++ )
       if ((error = mce_write_element(handle, &m_sq2bias, snum, sq2bias)) != 0)
         error_action("mce_write_element sq2bias", error);
   else
     printf("This script did not apply SQ2 bias, you may need to turn biases off manually!\n");
   
   time(&finish);
   //elapsed = ((double) (end - start))/CLOCKS_PER_SEC;
   printf ("sq2servo: elapsed time is %fs \n", difftime(finish,start));	   
   return SUCCESS;
}
