#
# Routines for PCI card debugging
#
#  MFH 11-03-25


#Low-level

function pciread {
    # usage: pciread <BANK> <ADDR>
    dsp_cmd -qpx read $1 $2 | cut -d' ' -f5
}
function pciwrite {
    # usage: pciwrite <BANK> <ADDR> <VAL>
    dsp_cmd -qpx write $1 $2 $3
}
function pcidump {
    # usage: pcidump <BANK> <START> <COUNT>
    for i in `seq -f '%9.0f' $2 $(( $2 + $3 - 1 ))`; do printf "%s %#8x 0x%06x\n" $1 $i `pciread $1 $i`; done
}
function pciwash {
    # usage: pciwash <BANK> <START> <COUNT> <VALUE>
    for i in `seq -f '%9.0f' $2 $(( $2 + $3 - 1 ))`; do pciwrite $1 $i $4; done
}


#PCI burst error dump, U01015

function pci_pcierrs {
    echo $@
    date
    date +%s
    pcidump X 0x34 8 
}


#Packet handling error dump, U01015

function pci_packerrs {
    echo $@
    date
    date +%s
    pcidump X 0x26 3
}
