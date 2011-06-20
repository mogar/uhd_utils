#!/usr/bin/env python
#
# Copyright 2005,2007 Free Software Foundation, Inc.
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

from gnuradio import gr, gru, eng_notation, optfir, window
from gnuradio import audio
#updated 2011 May 27, MR
from gnuradio import uhd
#from gnuradio import usrp
from gnuradio.eng_option import eng_option
from optparse import OptionParser
#from usrpm import usrp_dbid
import sys
import math
import time

#from current dir
from sense_path import *


class my_top_block(gr.top_block):

    def __init__(self, options):
        gr.top_block.__init__(self)
        
        # build graph
        
        #updated 2011 May 27, MR
        self.u = uhd.usrp_source(device_addr="", io_type=uhd.io_type.COMPLEX_FLOAT32, num_channels=1)
        self.u.set_subdev_spec("", 0)
        self.u.set_antenna("TX/RX", 0)
        self.u.set_samp_rate(options.samp_rate)

        #adc_rate = self.u.adc_rate()                # 64 MS/s
        #usrp_decim = options.decim
        #self.u.set_decim_rate(usrp_decim)
        self.usrp_rate = self.u.get_samp_rate() #adc_rate / usrp_decim
        if options.verbose:
            print "sample rate is", self.usrp_rate
        
        self.sense = sense_path(self.usrp_rate, self.set_freq, options)

        self.connect(self.u, self.sense)

        if options.gain is None:
            # if no gain was specified, use the mid-point in dB
            # updated 2011 May 31, MR
            #g = self.subdev.gain_range()
            g = self.u.get_gain_range()
            options.gain = float(g.start()+g.stop())/2

        self.set_gain(options.gain)
        if options.verbose:
            print "gain =", options.gain
            
    def set_freq(self, target_freq):
        """
        Set the center frequency we're interested in.
            
        @param target_freq: frequency in Hz
        @rypte: bool
            
        Tuning is a two step process.  First we ask the front-end to
        tune as close to the desired frequency as it can.  Then we use
        the result of that operation and our target_frequency to
        determine the value for the digital down converter.
        """
        #updated 2011 May 31, MR
        #return self.u.tune(0, self.subdev, target_freq)
        return self.u.set_center_freq(target_freq, 0)
            
    def set_gain(self, gain):
        #updated 2011 May 31, MR
        #self.subdev.set_gain(gain)
        self.u.set_gain(gain)
    
    def add_options(normal, expert):
        normal.add_option("-g", "--gain", type="eng_float", default=None,
                          help="set gain in dB (default is midpoint)")
        normal.add_option("-s", "--samp_rate", type="intx", default=6000000,
                          help="set sample rate to SAMP_RATE [default=%default]")
        normal.add_option("-v", "--verbose", action="store_true", default=False)
    # Make a static method to call before instantiation
    add_options = staticmethod(add_options)


def main_loop(tb, log):
    if log:
        filename = "spectrum_sense_exp_" + time.strftime('%y%m%d_%H%M%S') + ".csv"
        f = open(filename, 'w')
        f.write("detecting on %s BW channels between " %(tb.usrp_rate))
        f.write("%s and " %(tb.sense.min_freq))
        f.write("%s\n" %(tb.sense.max_freq))
        f.close()
    i = 0
    mywindow = window.blackmanharris(tb.sense.fft_size)
    power = 0
    for tap in mywindow:
        power += tap*tap
        
    k = -20*math.log10(tb.sense.fft_size)-10*math.log10(power/tb.sense.fft_size)
    
    while i < 9*tb.sense.num_tests:
        i = i+1
        # Get the next message sent from the C++ code (blocking call).
        # It contains the center frequency and the mag squared of the fft
        m = parse_msg(tb.sense.msgq.delete_head())
        
        #fft_sum_db = 20*math.log10(sum(m.data)/m.vlen)
        temp_list = []
        for item in m.data:
            temp_list.append(10*math.log10(item) + k)
        fft_sum_db = sum(temp_list)/m.vlen
        if log:
            f = open(filename, 'a')
            if fft_sum_db > tb.sense.threshold:
                f.write("1,")
            else:
                f.write("0,")
            #f.write(str(m.center_freq))
            #f.write(", ")
            #f.write(str(fft_sum_db))
            #f.write("\n")
        print m.center_freq, fft_sum_db

        
        if log:
            if m.center_freq >= tb.sense.max_center_freq - tb.sense.freq_step:
                f.write("\n")
            #    break
            f.close()
    
    
if __name__ == '__main__':
    parser = OptionParser(option_class=eng_option)
    expert_grp = parser.add_option_group("Expert")
    parser.add_option("", "--log", action="store_true", default=False)
    sense_path.add_options(parser, expert_grp)
    my_top_block.add_options(parser, expert_grp)

    (options, args) = parser.parse_args()
    
    tb = my_top_block(options)
    try:
        tb.start()              # start executing flow graph in another thread...
        main_loop(tb, options.log)
        tb.stop()
        tb.wait()
        
    except KeyboardInterrupt:
        pass
