#!/usr/bin/env python
#
# Copyright 2005, 2006 Free Software Foundation, Inc.
# 
# This file is part of GNU Radio
# 
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 


#
# This script acts as a simulated primary for qpCSMA/CA testing.
#


from gnuradio import gr, blks2
from gnuradio import eng_notation
from gnuradio.eng_option import eng_option
from optparse import OptionParser
from gnuradio import uhd

import time, struct, sys, random

class my_top_block(gr.top_block):
    def __init__(self, options):
        gr.top_block.__init__(self)

        self._tx_freq            = options.tx_freq         # tranmitter's center frequency
        self._rate               = options.rate #*options.num_channels           # USRP sample rate
        self.gain                 = options.gain               # USRP gain
        self.amp                 = options.amp
        self.sin_freq            = options.sin_freq

        if self._tx_freq is None:
            sys.stderr.write("-f FREQ or --freq FREQ or --tx-freq FREQ must be specified\n")
            raise SystemExit

        # Set up USRP sink; also adjusts interp, and bitrate
        self._setup_usrp_sink()

        sample_rate = 2000000
        src0 = gr.sig_source_c (sample_rate, gr.GR_SIN_WAVE, self.sin_freq, self.amp)
        self.connect (src0, self.u)
        
        
        if options.verbose:
            self._print_verbage()
        
    def _setup_usrp_sink(self):
        """
        Creates a USRP sink, determines the settings for best bitrate,
        and attaches to the transmitter's subdevice.
        """
        self.u = uhd.usrp_sink(
            device_addr = "",
            io_type=uhd.io_type.COMPLEX_FLOAT32,
            num_channels=1,
        )

        self.u.set_samp_rate(self._rate)

        # Set center frequency of USRP
        ok = self.set_freq(self._tx_freq)

        # Set the USRP for maximum transmit gain
        # (Note that on the RFX cards this is a nop
        gain = self.u.get_gain_range()
        #set the gain to the midpoint if it's currently out of bounds
        if self.gain > gain.stop() or self.gain < gain.start():
            self.gain = (gain.stop() + gain.start()) / 2
        self.set_gain(self.gain)

    def set_freq(self, target_freq):
        """
        Set the center frequency we're interested in.

        @param target_freq: frequency in Hz
        @rypte: bool

        Tuning is a two step process.  First we ask the front-end to
        tune as close to the desired frequency as it can.  Then we use
        the result of that operation and our target_frequency to
        determine the value for the digital up converter.
        """
        r = self.u.set_center_freq(target_freq)
        
    def set_gain(self, gain):
        """
        Sets the analog gain in the USRP
        """
        self.u.set_gain(gain)

    def add_options(normal, expert):
        """
        Adds usrp-specific options to the Options Parser
        """
        add_freq_option(normal)
        normal.add_option("-v", "--verbose", action="store_true", default=False)
        expert.add_option("", "--tx-freq", type="eng_float", default=None,
                          help="set transmit frequency to FREQ [default=%default]", metavar="FREQ")
        expert.add_option("-r", "--rate", type="eng_float", default=2e6,
                          help="set fpga sample rate to RATE [default=%default]")
        expert.add_option("", "--amp", type="eng_float", default=.8,
                          help="set sinusoid amplitude 0<amp<1 [default=%default]")
        expert.add_option("-r", "--sin-freq", type="eng_float", default=4e3,
                          help="set sinusoid frequency [default=%default]")
    # Make a static method to call before instantiation
    add_options = staticmethod(add_options)

    def _print_verbage(self):
        """
        Prints information about the transmit path
        """
        #print "modulation:      %s"    % (self._modulator_class.__name__)
        print "sample rate      %3d"   % (self._rate)
        print "Tx Frequency:    %s"    % (eng_notation.num_to_str(self._tx_freq))
        print "Tx Gain:         %s"    % (self.gain)
        

def add_freq_option(parser):
    """
    Hackery that has the -f / --freq option set both tx_freq and rx_freq
    """
    def freq_callback(option, opt_str, value, parser):
        parser.values.rx_freq = value
        parser.values.tx_freq = value

    if not parser.has_option('--freq'):
        parser.add_option('-f', '--freq', type="eng_float",
                          action="callback", callback=freq_callback,
                          help="set Tx and/or Rx frequency to FREQ [default=%default]",
                          metavar="FREQ")

# /////////////////////////////////////////////////////////////////////////////
#                                   main
# /////////////////////////////////////////////////////////////////////////////

def main():

    def send_pkt(payload='', eof=False):
        return tb.txpath.send_pkt(payload, eof)

    parser = OptionParser(option_class=eng_option, conflict_handler="resolve")
    expert_grp = parser.add_option_group("Expert")
    parser.add_option("","--gain", type="eng_float", default=13,
                      help="set transmitter gain [default=%default]")
    parser.add_option("","--channel-interval", type="eng_float", default=5,
                      help="set the time between channel changes [default=%default]")
    #parser.add_option("","--num-channels", type="int", default=1,
    #                  help="set number of (contiguous) occupied channels [default=%default]")
    #parser.add_option("", "--start-freq", type="eng_float", default="631M",
    #                      help="set the start of the frequency band to sense over [default=%default]")
    #parser.add_option("", "--end-freq", type="eng_float", default="671M",
    #                      help="set the end of the frequency band to sense over [default=%default]")
    parser.add_option("", "--random", action="store_true", default=False,
                          help="enable random frequency selection")
    parser.add_option("", "--channel_rate", type="eng_float", default=6e6,
                          help="Set bandwidth of an expected channel [default=%default]")
     
                      
    my_top_block.add_options(parser, expert_grp)

    (options, args) = parser.parse_args ()

    total_samp_rate = options.rate #*options.num_channels

    channels = [600000000, 620000000, 625000000, 640000000, 645000000, 650000000]

    # build the graph
    tb = my_top_block(options)
    
    r = gr.enable_realtime_scheduling()
    if r != gr.RT_OK:
        print "Warning: failed to enable realtime scheduling"

    tb.start()                       # start flow graph
    
    # generate and send packets
    nbytes = int(1e6 * options.megabytes)
    n = 0
    pktno = 0
    pkt_size = int(options.size)

    #timing parameters
    last_change = time.clock()
    
    print "\nstarting frequency: ", options.tx_freq, " at time: ", time.strftime("%X")
    
    current_chan = 0
    while n < nbytes:
        if time.clock() - last_change < options.channel_interval:
            pass 
        else:
            
            #change channels
            if options.random:
                current_chan = random.randint(0, len(channels) - 1)
            else:
                current_chan = (current_chan + 1) % len(channels)
            new_freq = channels[current_chan]

            #if options.num_channels == 1:
            #    new_freq = (options.start_freq + 3*options.channel_rate/2) + (random.randint(0,4))*options.channel_rate
            #elif options.num_channels == 3:
            #    new_freq = (options.start_freq + 3*options.channel_rate/2) + (random.randint(1,5))*options.rate
            #else:
            #    pass
                #just do nothing for now
            last_change = time.clock()
            print "\nchanging frequencies to ", new_freq, " at time ", time.strftime("%X")
            tb.set_freq(new_freq)
        
    tb.wait()                       # wait for it to finish

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
