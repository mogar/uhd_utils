#!/usr/bin/env python
#
# Copyright 2004,2005,2007 Free Software Foundation, Inc.
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

from gnuradio import gr
from gnuradio import audio
from gnuradio.eng_option import eng_option
from optparse import OptionParser
from gnuradio import uhd

from grc_gnuradio import blks2 as grc_blks2
import time

class my_top_block(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self)

        parser = OptionParser(option_class=eng_option)
        parser.add_option("-r", "--sample-rate", type="eng_float", default=1000000,
                          help="set sample rate to RATE [default=%default]")
        parser.add_option("-f", "--freq", type="eng_float", default=650000000,
                          help="set RF frequency [default=%default]")
        parser.add_option("", "--sin_freq", type="eng_float", default=100000,
                          help="set sinusoid frequency [default=%default]")
        parser.add_option("-a", "--amp", type="eng_float", default=.8,
                          help="set sinusoid amplitude, 0<=amp<=1 [default=%default]")
                          
        (options, args) = parser.parse_args ()
        if len(args) != 0:
            parser.print_help()
            raise SystemExit, 1

        sample_rate = int(options.sample_rate)
        ampl = options.amp

        src0 = gr.sig_source_c (sample_rate, gr.GR_SIN_WAVE, options.sin_freq, ampl)
        self.dst =  uhd.usrp_sink(device_addr="", io_type=uhd.io_type.COMPLEX_FLOAT32, num_channels=1)
        self.dst.set_samp_rate(sample_rate) 
        self.dst.set_center_freq(options.freq, 0)
        self.dst.set_gain(self.dst.get_gain_range().stop()/2, 0)

        self.connect (src0, self.dst)

if __name__ == '__main__':
    tb = my_top_block()    
    try:
        tb.start()              # start executing flow graph in another thread...
        while 1:
        	pass
    except KeyboardInterrupt:
        tb.stop()
        tb.wait()
