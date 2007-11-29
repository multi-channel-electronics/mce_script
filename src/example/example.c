#include <stdio.h>
#include <stdlib.h>

/* These are the MCE include files; they should all be in /usr/include */

#include <mcecmd.h>
#include <mceconfig.h>
#include <mcedata.h>


/* Default device, config files */

#define CMD_DEVICE "/dev/mce_cmd0"
#define CONFIG_FILE "/etc/mce.cfg"


int main()
{
	// Load MCE config information ("xml")
	mceconfig_t *conf;
	if (mceconfig_load(CONFIG_FILE, &conf) != 0) {
		fprintf(stderr, "Failed to load MCE configuration file %s.\n",
			CONFIG_FILE);
		return 1;
	}

	int handle = mce_open(CMD_DEVICE);
	if (handle < 0) {
		fprintf(stderr, "Failed to open %s.\n", CMD_DEVICE);;
		return 1;
	}


	// Lookup "rc1 fw_rev"
	card_t rc1;
	param_t fw_rev;
	if (mceconfig_lookup(conf, "rc1", "fw_rev", &rc1, &fw_rev)) {
		fprintf(stderr, "Lookup failed.\n");
		return 1;
	}

	// Read.
	u32 data;
	if (mce_read_block(handle, rc1.id, fw_rev.id,
			   1 /* number of words to read, per card */,
			   &data /* buffer for the words */,
			   1 /* number of cards that are returning data */)) {
		fprintf(stderr, "MCE command failed!\n");
		return 1;
	}

	printf("Read value %u\n", data);	

	mceconfig_destroy(conf);

	mce_close(handle);

	return 0;
}
