#include<stdio.h>
#include<stdlib.h>
#include<string.h>
#include"servo_err.h"
#include"servo.h"

/******************************************************************
 * servo.c contains subroutines called by sq1servo.c and sq2servo.c
 * 
 * Revision History:
 * <date $Date> 
 * $Log: servo.c,v $
 * Revision 1.1  2007/10/03 23:03:15  mce
 * MA contains subroutines used by sq1servo and sq2servo, for now, only genrunfile
 *
 *
 ******************************************************************/

/*******************************************
 * flux_fb_set_arr: Sets flux_fb to distinct values per channel on a particular bc card
 * args           : which_bc specifies 1, 2, 3 for bc1, bc2, bc3
 *                  arr, specifies 32 values for flux_fb
 *       
 *******************************************/
int flux_fb_set_arr(int which_bc, int *arr){
  char cmd[1024];
  char tempbuf[20];
  int j;
  int sysret;
  char errmsg_temp[1024];

  sprintf(cmd, "mce_cmd -q -x wb bc%d flux_fb", which_bc);
  for ( j=0; j<MAXVOLTS; j++ ){
    sprintf(tempbuf, " %d", arr[j]);
    strcat(cmd, tempbuf);
  }
  strcat(cmd, "\n" );
  /* issue the command  */
  if ( (sysret = system(cmd)) != 0){
    sprintf(errmsg_temp,"mce_cmd returned %d when setting flux_fb on bc%d!\n%s", sysret, which_bc, cmd);
    ERRPRINT(errmsg_temp);
    exit(6);
  }
  return 0;
}

/*******************************************
 * flux_fb_set: sets flux_fb to a unique value for all 
 *              channels on a particular bc card.
 * args       : which_bc specifies 1, 2, 3 for bc1, bc2, bc3
 *              i is the flux_fb value
 ******************************************/
int flux_fb_set(int which_bc, int i){
  char cmd[1024];
  char tempbuf[20];
  int j;
  int sysret;
  char errmsg_temp[1024];

  sprintf(cmd, "mce_cmd -q -x wb bc%d flux_fb", which_bc );
  sprintf(tempbuf, " %d", i);
  for ( j=0; j<MAXVOLTS; j++ )
    strcat(cmd, tempbuf);
    strcat(cmd, "\n" );
    /* issue the command  */
    if ( (sysret = system(cmd)) != 0){
      sprintf(errmsg_temp,"mce_cmd returned %d when setting flux_fb on bc%d!\n%s", sysret, which_bc, cmd);
      ERRPRINT(errmsg_temp);
      exit(6);
    }
    return 0;
}
/*******************************************
 * sq1fb_set: sets fb_const to a unique value for all 
 *              channels on a particular rc card.
 * args     : which_rc specifies 1, 2, 3 4, for rc1, rc2, etc
 *            i is the fb_const value
 ******************************************/
int sq1fb_set(int which_rc, int i){
  char cmd[1024];
  char tempbuf[20];
  int j;
  int sysret;
  char errmsg_temp[1024];

  sprintf(cmd, "mce_cmd -q -x wb rc%d fb_const", which_rc );
  sprintf(tempbuf, " %d", i);
  for ( j=0; j<MAXCHANNELS; j++ )
    strcat(cmd, tempbuf);
    strcat(cmd, "\n" );
    /* issue the command  */
    if ( (sysret = system(cmd)) != 0){
      sprintf(errmsg_temp,"mce_cmd returned %d when setting sq1fb on rc%d!\n%s", sysret, which_rc, cmd);
      ERRPRINT(errmsg_temp);
      exit(6);
    }
    return 0;
}

/*******************************************
 * sq1bias_set: sets on_bias to a unique value for all rows
 * args       : i is the fb_const value
 ******************************************/
int sq1bias_set(int i){
  char cmd[1024];
  char tempbuf[20];
  int j;
  int sysret;
  char errmsg_temp[1024];

  sprintf(cmd, "mce_cmd -q -x wb ac on_bias");
  sprintf(tempbuf, " %d", i);
  for ( j=0; j<MAXROWS; j++ )
    strcat(cmd, tempbuf);
    strcat(cmd, "\n" );
    /* issue the command  */
    if ( (sysret = system(cmd)) != 0){
      sprintf(errmsg_temp,"mce_cmd returned %d when setting sq1bias \n%s", sysret, cmd);
      ERRPRINT(errmsg_temp);
      exit(6);
    }
    return 0;
}

/*******************************************
 * gengofile: creates a small script file for a single data acquisition
 * args     :
 * return   :  0 success
 *             1 environment vars not set
 *             2 failed to create workfile
 * ****************************************/
int gengofile(char *datafile, char *workfile, int which_rc){
  FILE *gofile;
  char *ctemp;
  char fullname[128];
  
  if ( (ctemp=getenv("MAS_TEMP")) == NULL)
    return 1;
  
  strcpy(fullname, ctemp);
  strcat(fullname, workfile);
  if ( (gofile = fopen(fullname, "w")) == NULL)
    return 2;
  
  if ( (ctemp=getenv("MAS_DATA")) == NULL)
    return 1;
  strcpy(fullname, ctemp);  
  fprintf(gofile, "acq_path %s\nacq_config %s rc%d\nacq_go 1\n", fullname, datafile, which_rc);
  fclose (gofile);
  return 0;
}    
/*******************************************
 * acq: runs a go script to acquire one frame of data
 * args: script filename
 ******************************************/
int acq(char *filename){
  char cmd[1024];
  char *ctemp;
  char fullname[128];
  int sysret;
  char errmsg_temp[1024];
  
  if ( (ctemp = getenv("MAS_TEMP")) == NULL){
    ERRPRINT("Environment variable MAS_TEMP not set! acq failed!");	  
    return 1;
  }  
  strcpy(fullname, ctemp);
  strcat(fullname, filename);
  sprintf(cmd, "mce_cmd -q -f %s", fullname);
  if ( (sysret=system(cmd)) != 0){
    sprintf(errmsg_temp, "acq script %s failed with %d", filename, sysret);
    return sysret;
  }
  return 0;
} 

/***********************************************************
 * genrunfile - creates a runfile
 ***********************************************************/
int genrunfile (
char *full_datafilename, /* datafilename including the path*/
char *datafile,          /* datafilename */
int  which_servo,        /* 1 for sq1servo, 2 for sq2servo*/
int  which_rc,
int  bias, int bstep, int nbias, int feed, int fstep, int nfeed,
char *servo_init1,       /* a line of servo_init var_name and values to be included in <servo_init>*/     
char *servo_init2        /* a line of servo_init var_name and values to be included in <servo_init>*/     
){
/* Method: spawns mcestatus to create <header> section
 *         generates <par_ramp> section
 *         generates <servo_init> section
 *         spawns frameacq_stamp to create <frameacq> section
*/
char command[512];
char myerrmsg[100];
char runfilename[256];
int sysret;
FILE *runfile;

  sprintf(command, "mcestatus %s.run 1", full_datafilename);
  if ((sysret =system (command)) != 0){
    sprintf(myerrmsg, "generating runfile %s.run failed when inserting mcestatus header",datafile);
    ERRPRINT(myerrmsg);
    return sysret;
  }
  sprintf(runfilename, "%s.run",full_datafilename);
  if ((runfile = fopen (runfilename, "a")) == NULL){
    sprintf(myerrmsg, "generating runfile %s failed when appending loop pars", runfilename);
    return 1;
  }
  /*<servo_init section*/
  if (servo_init1 != NULL){
    fprintf (runfile,"<servo_init>\n  %s\n", servo_init1);
    if (servo_init2 != NULL)
       fprintf (runfile,"  %s\n", servo_init2);
    fprintf (runfile, "</servo_init>\n\n");    
  }
  /*<par_ramp> section*/  
  fprintf (runfile,"<par_ramp>\n  <loop_list> loop1 loop2\n");
  fprintf (runfile,"    <par_list loop1> par1\n      <par_title loop1 par1> sq%dbias\n      <par_step loop1 par1> %d %d %d\n",
                        which_servo, bias, bstep, nbias);
  fprintf (runfile,"    <par_list loop2> par1\n      <par_title loop2 par1> sq%dfb\n      <par_step loop2 par1> %d %d %d\n",
                        which_servo, feed, fstep, nfeed);
  fprintf (runfile, "</par_ramp>\n\n");
  fclose(runfile);
  
  /* frameacq_stamp */
  sprintf(command, "frameacq_stamp %d %s %d >> %s.run", which_rc, datafile, nbias*nfeed, full_datafilename);
  if ( (sysret =system (command)) != 0){
    sprintf(myerrmsg, "generating runfile %s.run failed when inserting frameacq_stamp",datafile);
    ERRPRINT(myerrmsg);
    return sysret;
  }
  return 0;
}

