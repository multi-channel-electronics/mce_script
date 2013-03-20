-- -*- mode:rst ; mode:auto-fill -*-

Protocol Description
====================

Overview
--------

Clients connect to a server.  Clients are typically data producers
(sources) or data consumers (sinks).  An example of a source is a data
acquisition program that makes a measurement and reports the data to
the server.  An example of a sink is be a plotting program that reads
data from the server and displays it to a user.

A source provides one or more "streams" of data, which may be
distributed by the server to an arbitrary number of sinks.  When a
source connects to the server, it informs the server of the data
streams that it can provide.  When a sink connects to the server, it
obtains a list of all the data stream available.  The sink
"subscribes" to one or more data streams provided by the server, and
from that point the server is responsible for transmitting data from
the source to the sink.

Information provided by a data source consists of raw data as well as
auxiliarly information describing the meaning of that data.  To adapt
to network or sink capabilities, the raw data may be decimated (so
that only occasional packets are routed to sinks).  Status
information, in contrast, is critical to data interpretation and is
always transmitted to subscribed sinks.  Status information may in
some cases be cached by servers, and provided to newly subscribed
sinks.


Packet format
-------------

All communication between servers and clients takes place with
formatted data packets.  The packet consists of address and payload
blocks.  The payload block consists of unicode JSON data followed by a
binary data block.

In the following table, offsets are given in bytes.  Block sizes are
specified as 4-byte integers, stored little-endian.


Top-level encapsulating packet format
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. table:: Packet format, top-level
========   ====================================================
Offset     Description
========   ====================================================
[0]        Protocol identifier, "dahi", little-endian
[4]	   Size of address packet - N_A
[8]	   Size of payload packet - N_P
[12]       Address packet (size N_A)
[12+N_A]   Payload packet (size N_P)
========   ====================================================


Address block format
~~~~~~~~~~~~~~~~~~~~

The address block consists of 4 null-terminated ascii strings.  Maybe
UTF-8 is what I'm talking about.  Whatever, keep them simple.  The
strings represent:

.. table:: Packet format, top-level
=============  ======================================================
Identifier     Purpose
=============  ======================================================
message_type   message type, see options below
stream_name    name of the stream to which the message belongs
originator     client_name of the message sender
target         client_name of the intended message recipient
=============  ======================================================

Only the message_type and stream_name are mandatorily non-empty.  The
originator should be provided as a courtesy and the target may be
useful in some cases but is not currently implemented.  All strings,
even empty ones, must be null-terminated.  Your block should have
exactly 4 nulls in it in all cases.

.. table:: message_type values
==========    ========================================================
Value         Description
==========    ========================================================
control       Message from a stream subscriber to control the behavior
              of the stream originator.
data          Data packet from stream originator.  Data packet streams
              may be decimated according to subscriber throughput
	      restrictions. 
notify        Status packet from stream originator.  Status packets
              are routed to all subscribers.  The server can cache
	      some data in these packets.  They probably shouldn't 
	      make use of the binary data block.
==========    ========================================================


Payload block format
~~~~~~~~~~~~~~~~~~~~

.. table:: Payload format
========   ====================================================
Offset     Description
========   ====================================================
[0]        Size of JSON block in bytes - N_J
[4]        Size of binary block in bytes - N_P
[8]        JSON block
[12+N_J]   binary block
========   ====================================================

The JSON block must consist of a single valid JSON object
specification, for example:

{
 "id": 7,
 "some_numbers": [1,2,3],
 "an_object": {"name": "treasure", "property": "gold" }
}

There are no restrictions on the binary block format, except that it
should be less than a gazillion bytes long.

