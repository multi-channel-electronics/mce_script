#!/bin/bash
#
# This file defines a few handy bash functions which wrap the MAS
# program dsp_cmd which are useful for debugging the PCI fibre
# card.  Use it like this:
#
# user@ubuntu:~$ . pci_debug_library.bash
# user@ubuntu:~$ pciread x 0
# 0x208
# user@ubuntu:~$ pciwrite y 0 0x1234
#
# user@ubuntu:~$ pcidump Y 0x100000 4
# Y 0x100000 0x004f4b
# Y 0x100001 0x00474f
# Y 0x100002 0x000016
# Y 0x100003 0x000003
#
# See
# http://e-mode.phas.ubc.ca/mcewiki/index.php/PCI_card_hacking
# for further details

# read a word from the PCI card
function pciread {
    dsp_cmd -qpx read $1 $2 | cut -d' ' -f5
}

# write a word to the PCI card
function pciwrite {
    dsp_cmd -qpx write $1 $2 $3
}

# read a block from the PCI card
function pcidump {
    # usage: pcidump <BANK> <START> <COUNT>
    for i in `seq -f '%9.0f' $2 $(( $2 + $3 - 1 ))`; do printf "%s %#8x 0x%06x\n" $1 $i `pciread $1 $i`; done
}

# set a block of PCI DSP RAM to a particular value
function pciwash {
    # usage: pciwash <BANK> <START> <COUNT> <VALUE>
    for i in `seq -f '%9.0f' $2 $(( $2 + $3 - 1 ))`; do pciwrite $1 $i $4; done
}
