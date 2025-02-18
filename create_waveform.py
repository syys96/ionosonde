#!/usr/bin/env python3
# ----------------------------------------------------------------------------
# Copyright (c) 2017 Massachusetts Institute of Technology (MIT)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
"""Create pseudorandom-coded waveform files for sounding.

See the following paper for a description and application of meteor radar using
pseudorandom codes:

Vierinen, J., Chau, J. L., Pfeffer, N., Clahsen, M., and Stober, G.,
Coded continuous wave meteor radar, Atmos. Meas. Tech., 9, 829-839,
doi:10.5194/amt-9-829-2016, 2016.

"""
from argparse import ArgumentParser
import numpy as n
import os
import scipy.signal
import matplotlib.pyplot as plt
import iono_config
import scipy.signal as ss


def lpf(dec=10, om_factor=1.0, filter_len=4):
    """ a better lpf """
    om0=om_factor*2.0*n.pi/dec
    dec2=filter_len*dec
    m=n.array(n.arange(filter_len*dec), dtype=n.float32)
    m=m-n.mean(m)
    # windowed low pass filter
    wfun=n.array(ss.hann(len(m))*n.sin(om0*(m+1e-6))/(n.pi*(m+1e-6)), dtype=n.complex64)
    return(wfun)


# seed is a way of reproducing the random code without
# having to store all actual codes. the seed can then
# act as a sort of station_id.
def create_pseudo_random_code(clen=10000, seed=0, pulse_length=-1, ipp=1000):
    n.random.seed(seed)
    # Each bit has a random phase between \phi_t = U(0,2*pi). The waveform is e^(i \phi_t).
    code = n.array(n.exp(1j*n.random.rand(clen)*2*n.pi), dtype=n.complex64)

    if pulse_length > 0:
        # if a pulse length is specified, notch everything to zero after pulse
        n_pulses=int(clen/ipp)
        for i in range(n_pulses):
            code[(i*ipp + pulse_length): ((i+1)*ipp)] = 0.0

    return(code)


def create_prn_dft_code(clen=10000, seed=0):
    """
    this is a perfect code that is randomized.
    however, it has horrible cross-correlation
    properties and should be avoided with multi-static
    radar networks.
    """
    n.random.seed(seed)
    N=int(n.sqrt(clen))
    # random phases
    rp=n.exp(1j*n.random.rand(N)*2*n.pi)
    code=n.array([], dtype=n.complex64)
    idx=n.arange(N, dtype=n.float32)
    for i in range(N):
        code=n.concatenate((code, rp*n.exp(1j*2.0*n.pi*float(i)*idx/float(N))))
    code=n.array(code, dtype=n.complex64)
    return(code)


# oversample a phase code by a factor of rep
def rep_seq(x, rep=10):
    L = len(x) * rep
    res = n.zeros(L, dtype=x.dtype)
    idx = n.arange(len(x)) * rep
    for i in n.arange(rep):
        res[idx + i] = x
    return(res)


def filter_waveform(waveform,
                    sr=1e6,
                    bandwidth=100e3,
                    max_power_outside_band=0.01,
                    plot=False):
    """
    Filter the waveform in such a way that it meets a 1% out of
    band power requirement. filter the code in such a way that there
    is a delay of 200 microseconds at DC.  Assumes that waveform is periodic.

    The 200 microsecond delay is to ensure that the transmit pulse is
    well above the 0 range gate in a monostatic case, so that we
    can keep an eye on the direct transmitted signal range as
    part of the procedure of making sure that the transmitter and
    receiver are in sync
    """
    # filter window
    w = n.zeros(len(waveform), dtype=n.complex64)

    # first try
    fl = int(sr/bandwidth/2)*2
    power_outside_band=1.0

    fvec=n.fft.fftshift(n.fft.fftfreq(len(waveform), d=1.0/sr))
    # which frequency bins are in the band
    fidx=n.where(n.abs(fvec) < bandwidth/2.0)[0]

    waveform_f=n.fft.fft(waveform)
#    print("Searching for filter length")
    while power_outside_band > max_power_outside_band:

        w[0:fl] = scipy.signal.flattop(fl)
        # filter
        aa = n.fft.ifft(n.fft.fft(w) * waveform_f)
        # scale maximum amplitude to unity
        a = aa / n.max(n.abs(aa))
        a = n.array(a, dtype=n.complex64)
        # remove filter time shift add a fixed shift of 20 samples
        a=n.roll(a, -int(fl/2)+20)
        # power spectrum
        S=n.fft.fftshift(n.abs(n.fft.fft(a))**2.0)
        P_tot=n.sum(S)
        P_in=n.sum(S[fidx])
        power_outside_band = 1.0-P_in/P_tot
        #print("fl %d power outside band %1.3f"%(fl,power_outside_band))
        fl+=2
#    print("Using filter length of %d samples"%(fl-2))

    if plot:
        plt.plot(a.real, a.imag, ".")
        plt.show()

    return(a)

def barker36(clen=10000,
             ipp=1000):
    #Friese 1996
    #Polyphase Barker sequences up to length 36
    P = 180.0
    code = n.zeros(clen,dtype=n.complex64)#)n.array(n.exp(1j*n.random.rand(clen)*2*n.pi), dtype=n.complex64)
    phi = n.array([0,0, 41, 59,  114, 114, 29, 30, 77, 54, 10, 117, 106, 131, 118, 
                   98, 110, 58, 6, 113, 89, 61, 63, 38, 133, 57,
                   128, 54, 160, 50, 133, 15, 62, 123, 30, 93],dtype=n.float32)
    barker36=n.exp(1j*2.0*n.pi*phi/P)
    n_ipp = int(n.floor(clen/ipp))
    print(n_ipp)
    for i in range(n_ipp):
        if i%2 == 0:
            code[(i*ipp):(i*ipp+36)]=barker36
        else:
            code[(i*ipp):(i*ipp+36)]=barker36[::-1]
            
#    plt.plot(code.real)
 #   plt.plot(code.imag)
  #  plt.show()
    return(code)
    

def barker13ipps(clen=10000,
                 ipp=1000):
    barker13=n.array([1, 1, 1, 1, 1, -1, -1, 1, 1, -1, 1, -1, 1], dtype=n.complex64)
    code = n.zeros(clen,dtype=n.complex64)#)n.array(n.exp(1j*n.random.rand(clen)*2*n.pi), dtype=n.complex64)
    n_ipp = int(n.floor(clen/ipp))
    for i in range(n_ipp):
        code[(i*ipp):(i*ipp+13)]=barker13
    return(code)
    

#
# lets use 0.1 s code cycle and coherence assumption
# our transmit bandwidth is 100 kHz, and with a 10e3 baud code,
# that is 0.1 seconds per cycle as a coherence assumption.
# furthermore, we use a 1 MHz bandwidth, so we oversample by a factor of 10.
#
def waveform_to_file(station=0,
                     clen=10000,
                     oversample=10,
                     filter_output=False,
                     sr=1e6,
                     bandwidth=100e3,
                     power_outside_band=0.01,
                     pulse_length=-1,
                     ipp=1000,
                     code_type="prn",
                     write_file=True):

    os.system("mkdir -p waveforms")
    ofname='waveforms/code-l%d-b%d-%06df_%dk.bin' % (clen, oversample, station, int(bandwidth/1e3))

    if code_type=="prn":
        code=create_pseudo_random_code(clen=clen, seed=station, pulse_length=pulse_length, ipp=ipp)
    elif code_type=="barker13":
        code=barker13ipps(clen=clen,ipp=ipp)
    elif code_type=="barker36":
        code=barker36(clen=clen,ipp=ipp)
    else:
        code=create_prn_dft_code(clen=clen, seed=station)
        
    # oversample code
    a = rep_seq(code,
                rep=oversample)

    if filter_output:
        a=filter_waveform(a,
                          sr=sr,
                          bandwidth=bandwidth,
                          max_power_outside_band=power_outside_band)

    if write_file:
        print("Writing file %s" % (ofname))
        a.tofile(ofname)
    return(ofname, code)


def barker_to_file(
    station=0, clen=10000, oversample=10, filter_output=False,
):
    a=n.zeros(clen*oversample, dtype=n.complex64)
    barker13=n.array([1, 1, 1, 1, 1, -1, -1, 1, 1, -1, 1, -1, 1], dtype=n.complex64)
    barker130=rep_seq(barker13, rep=oversample)
    a[0:130]=barker130
    print(len(a))
    w = n.zeros([oversample * clen], dtype=n.complex64)
    fl = (int(2*oversample))
    w[0:fl] = scipy.signal.blackmanharris(fl)
    aa = n.fft.ifft(n.fft.fft(w) * n.fft.fft(a))
    a = aa / n.max(n.abs(aa))
    a = n.array(a, dtype=n.complex64)
    a.tofile('code-barkerf.bin')


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument(
        '-l', '--length', type=int, default=10000,
        help='''Code length (number of bauds). (default: %(default)s)''',
    )

    parser.add_argument(
        '-t', '--code_type', default="prn",
        help='''Code type. Options: prn, perfect. (default: %(default)s)''',
    )

    parser.add_argument(
        '-b', '--oversampling', type=int, default=10,
        help='''Oversampling factor (number of samples per baud).
                (default: %(default)s)''',
    )
    parser.add_argument(
        '-s', '--station', type=int, default=0,
        help='''Station ID (seed). (default: %(default)s)''',
    )
    parser.add_argument(
        '-f', '--filter', action='store_true',
        help='''Filter waveform with Blackman-Harris window.
                (default: %(default)s)''',
    )
    parser.add_argument(
        '-w', '--bandwidth', type=float, default=100.0,
        help='''Code bandwidth in kHz
        (default: %(default)s)''',
    )
    parser.add_argument(
        '-r', '--sample_rate', type=float, default=1000000,
        help='''Sample rate in Hz
        (default: %(default)s)''',
    )
    parser.add_argument(
        '-p', '--pulse_length', type=float, default=-1,
        help='''Pulse length (default 100% duty-cycle)
        (default: %(default)s)''',
    )
    parser.add_argument(
        '-i', '--ipp', type=float, default=1000,
        help='''How many samples is the pulse spacing
        (default: %(default)s)''',
    )
    parser.add_argument(
        '-o', '--out_of_band_power', type=float, default=0.01,
        help='''How much power is allowed to be out of band.
        (default: %(default)s)''',
    )

    op = parser.parse_args()

    waveform_to_file(
        station=op.station, clen=op.length, oversample=op.oversampling,
        filter_output=op.filter, bandwidth=1e3*op.bandwidth, sr=op.sample_rate,
        power_outside_band=op.out_of_band_power, code_type=op.code_type,
        ipp=op.ipp, pulse_length=op.pulse_length
    )
