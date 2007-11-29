/***********************************************************
 *    servo_err.h: for error handling
 * Revision history:
 * <date $Date: 2007/09/20 21:35:35 $>
 * $Log: servo_err.h,v $
 * Revision 1.1  2007/09/20 21:35:35  mce
 * MA initital release
 *
 ***********************************************************/
#include <stdio.h>

/* error handling defines */
#define ERROR_MSG_PREAMBLE "ERROR:"
#define ERR_OUTPUT stderr
#define ERRPRINT(s) fprintf(ERR_OUTPUT, "%s %s\n",ERROR_MSG_PREAMBLE,s);

