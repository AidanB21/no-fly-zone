
#!/usr/bin/env python3
"""
IWR1443 Radar Doppler Data Viewer
=================================
Real-time visualization of Doppler data from the TI IWR1443Boost radar board.
Connects via two COM ports (config + data), sends radar configuration,
parses the binary TLV packet stream, and displays:
  - XY scatter plot of detected objects colored by Doppler velocity
  - Range-Doppler heat map (when enabled in config)
  - Live terminal output with per-object numerical data

Usage:
    python radar_doppler_viewer.py --cfg_port COM3 --data_port COM4
    python radar_doppler_viewer.py --cfg_port COM3 --data_port COM4 --config config_doppler.cfg
    python radar_doppler_viewer.py --cfg_port COM3 --data_port COM4 --log data.csv
    python radar_doppler_viewer.py --list-ports

Dependencies: pyserial, numpy, matplotlib  (see requirements.txt)
"""

import argparse
import struct
import sys
import threading
import time
from collections import deque

import numpy as np
import serial
import serial.tools.list_ports
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# ---------------------------------------------------------------------------
# Constants — from TI IWR1443 Demo firmware (mmw_output.h / detected_obj.h)
# ---------------------------------------------------------------------------

# Magic word at the start of every frame packet (little-endian byte order)
# Firmware: magicWord = {0x0102, 0x0304, 0x0506, 0x0708}
MAGIC_WORD = b'\x02\x01\x04\x03\x06\x05\x08\x07'

# Header layout: magicWord[4](8B) version(4B) totalPacketLen(4B) platform(4B)
#   frameNumber(4B) timeCpuCycles(4B) numDetectedObj(4B) numTLVs(4B)  = 36 B
HEADER_FMT = '<4H7I'
HEADER_SIZE = struct.calcsize(HEADER_FMT)  # 36

# TLV type codes
TLV_DETECTED_POINTS        = 1
TLV_RANGE_PROFILE           = 2
TLV_NOISE_PROFILE           = 3
TLV_AZIMUTH_STATIC_HEAT_MAP = 4
TLV_RANGE_DOPPLER_HEAT_MAP  = 5
TLV_STATS                   = 6

# TLV header: type(u32) + length(u32)
TLV_HDR_FMT  = '<II'
TLV_HDR_SIZE = struct.calcsize(TLV_HDR_FMT)  # 8

# Detected-object descriptor: numDetObj(u16) + xyzQFormat(u16)
OBJ_DESCR_FMT  = '<HH'
OBJ_DESCR_SIZE = struct.calcsize(OBJ_DESCR_FMT)  # 4

# Single detected object: rangeIdx(u16) dopplerIdx(i16) peakVal(u16) x(i16) y(i16) z(i16)
OBJ_FMT  = '<HhHhhh'
OBJ_SIZE = struct.calcsize(OBJ_FMT)  # 12

# Stats: 6 × uint32
STATS_FMT  = '<6I'
STATS_SIZE = struct.calcsize(STATS_FMT)  # 24

SPEED_OF_LIGHT = 3.0e8

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _next_pow2(x):
    return 1 << (x - 1).bit_length() if x > 0 else 1


def list_serial_ports():
    """Print a table of available serial ports."""
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("  No serial ports found.")
        return
    print(f"  {'Port':<10} {'Description':<50} {'HWID'}")
    print("  " + "-" * 90)
    for p in sorted(ports, key=lambda x: x.device):
        print(f"  {p.device:<10} {p.description:<50} {p.hwid}")

# ---------------------------------------------------------------------------
# Config file parser
# ---------------------------------------------------------------------------

def parse_config(path):
    """Read a TI mmWave .cfg file.  Returns (params dict, command list)."""
    params = {}
    commands = []

    with open(path, 'r') as f:
        for raw in f:
            line = raw.strip()

            # --- extract values from header comment lines ---
            if not line or line.startswith('%'):
                if ':' in line:
                    try:
                        key, val = line.split(':', 1)
                        v = val.strip().split()[0]
                        if 'Range Resolution' in key and 'Maximum' not in key:
                            params['range_res'] = float(v)
                        elif 'Maximum unambiguous Range' in key:
                            params['max_range'] = float(v)
                        elif 'Maximum Radial Velocity' in key:
                            params['max_velocity'] = float(v)
                        elif 'Radial velocity resolution' in key:
                            params['vel_res'] = float(v)
                    except (ValueError, IndexError):
                        pass
                continue

            commands.append(line)
            tok = line.split()
            cmd = tok[0]

            if cmd == 'profileCfg' and len(tok) >= 12:
                params['start_freq']      = float(tok[2])   # GHz
                params['idle_time']       = float(tok[3])   # us
                params['ramp_end_time']   = float(tok[5])   # us
                params['freq_slope']      = float(tok[8])   # MHz/us
                params['num_adc_samples'] = int(tok[10])
                params['adc_sample_rate'] = float(tok[11])  # ksps

            elif cmd == 'frameCfg' and len(tok) >= 6:
                params['start_chirp']  = int(tok[1])
                params['end_chirp']    = int(tok[2])
                params['num_loops']    = int(tok[3])
                params['frame_period'] = float(tok[5])      # ms

            elif cmd == 'channelCfg' and len(tok) >= 3:
                params['num_rx'] = bin(int(tok[1])).count('1')
                params['num_tx'] = bin(int(tok[2])).count('1')

            elif cmd == 'guiMonitor' and len(tok) >= 7:
                params['gui_detected_objects'] = int(tok[1])
                params['gui_log_mag_range']    = int(tok[2])
                params['gui_noise_profile']    = int(tok[3])
                params['gui_azimuth_heat_map'] = int(tok[4])
                params['gui_doppler_heat_map'] = int(tok[5])
                params['gui_stats']            = int(tok[6])

    # --- derived values ---
    nchirps = (params.get('end_chirp', 2) - params.get('start_chirp', 0) + 1)
    params['num_doppler_bins'] = params.get('num_loops', 32)
    params['num_range_bins']   = _next_pow2(params.get('num_adc_samples', 64))
    params['num_chirps_per_frame'] = nchirps * params.get('num_loops', 32)

    # compute velocity params from chirp config if not in comments
    needed = ('start_freq', 'idle_time', 'ramp_end_time', 'num_tx')
    if 'vel_res' not in params and all(k in params for k in needed):
        wl = SPEED_OF_LIGHT / (params['start_freq'] * 1e9)
        Tc = (params['idle_time'] + params['ramp_end_time']) * 1e-6
        params['vel_res']      = wl / (2 * params['num_doppler_bins'] * params['num_tx'] * Tc)
        params['max_velocity'] = wl / (4 * params['num_tx'] * Tc)

    if 'range_res' not in params:
        needed_r = ('freq_slope', 'num_adc_samples', 'adc_sample_rate')
        if all(k in params for k in needed_r):
            bw = (params['freq_slope'] * 1e12
                  * params['num_adc_samples']
                  / (params['adc_sample_rate'] * 1e3))
            params['range_res'] = SPEED_OF_LIGHT / (2 * bw)

    if 'max_range' not in params:
        params['max_range'] = params.get('range_res', 0.047) * params['num_range_bins']

    return params, commands

# ---------------------------------------------------------------------------
# Send configuration to radar
# ---------------------------------------------------------------------------

def send_config(ser, commands):
    """Push each command over the config UART and wait for acknowledgement."""
    # Wake up the CLI — send a bare newline and drain any boot messages
    ser.write(b'\n')
    time.sleep(0.2)
    if ser.in_waiting:
        ser.read(ser.in_waiting)      # discard boot banner / old prompt

    ok_count = 0
    for cmd in commands:
        print(f"  >> {cmd}")
        # TI CLI expects CR+LF on Windows
        ser.write((cmd + '\r\n').encode('utf-8'))
        time.sleep(0.05)          # give the radar a moment

        resp = b''
        deadline = time.time() + 1.0   # 1 s timeout per command
        while time.time() < deadline:
            if ser.in_waiting:
                resp += ser.read(ser.in_waiting)
                if b'Done' in resp or b'Error' in resp:
                    break
            time.sleep(0.01)

        got_done = False
        for part in resp.decode('utf-8', errors='replace').split('\n'):
            part = part.strip()
            if part and part != cmd and not part.startswith('mmwDemo'):
                print(f"     {part}")
            if 'Done' in part:
                got_done = True

        if got_done:
            ok_count += 1
        elif resp:
            print(f"     (no 'Done' ack — response was: "
                  f"{resp[:80]!r})")
        else:
            print(f"     (no response — port may be wrong)")

    print(f"  [{ok_count}/{len(commands)} commands acknowledged]")

# ---------------------------------------------------------------------------
# Background reader — parses binary TLV frames from the data UART
# ---------------------------------------------------------------------------

class RadarDataReader:
    """Reads the 921600-baud data UART in a background thread.
    Synchronises on the 8-byte magic word, parses the header + TLVs,
    and stores the latest parsed frame for the main thread to consume."""

    def __init__(self, ser, params):
        self.ser = ser
        self.params = params
        self.running = False
        self.frame_count = 0
        self.bytes_received = 0
        self.magic_found = 0
        self._thread = None
        self._lock = threading.Lock()
        self._latest = None

    # -- public API --------------------------------------------------------

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def get_frame(self):
        """Return the most recent parsed frame (or None).  Consumes it."""
        with self._lock:
            f = self._latest
            self._latest = None
            return f

    # -- background loop ---------------------------------------------------

    def _loop(self):
        buf = bytearray()

        while self.running:
            try:
                chunk = self.ser.read(4096)
                if not chunk:
                    continue
                self.bytes_received += len(chunk)
                buf.extend(chunk)
            except serial.SerialException:
                break

            # process every complete packet sitting in buf
            while True:
                idx = buf.find(MAGIC_WORD)
                if idx < 0:
                    # keep tail in case magic word straddles two reads
                    if len(buf) > len(MAGIC_WORD) - 1:
                        buf = buf[-(len(MAGIC_WORD) - 1):]
                    break
                self.magic_found += 1
                if idx > 0:
                    buf = buf[idx:]           # discard bytes before magic

                if len(buf) < HEADER_SIZE:
                    break                     # need more data for header

                hdr = self._parse_header(bytes(buf[:HEADER_SIZE]))
                pkt_len = hdr['totalPacketLen']

                # sanity-check
                if pkt_len < HEADER_SIZE or pkt_len > 65536:
                    buf = buf[len(MAGIC_WORD):]   # skip bad magic, try again
                    continue

                if len(buf) < pkt_len:
                    break                     # packet incomplete

                payload = bytes(buf[HEADER_SIZE:pkt_len])
                buf = buf[pkt_len:]

                frame = self._parse_tlvs(hdr, payload)
                with self._lock:
                    self._latest = frame
                    self.frame_count += 1

    # -- packet parsing ----------------------------------------------------

    @staticmethod
    def _parse_header(data):
        f = struct.unpack(HEADER_FMT, data)
        return {
            'version':        f[4],
            'totalPacketLen': f[5],
            'platform':       f[6],
            'frameNumber':    f[7],
            'timeCpuCycles':  f[8],
            'numDetectedObj': f[9],
            'numTLVs':        f[10],
        }

    def _parse_tlvs(self, hdr, payload):
        frame = {
            'frameNumber':    hdr['frameNumber'],
            'numDetectedObj': hdr['numDetectedObj'],
            'objects':        [],
            'range_profile':  None,
            'doppler_heatmap': None,
            'stats':          None,
        }

        off = 0
        for _ in range(hdr['numTLVs']):
            if off + TLV_HDR_SIZE > len(payload):
                break
            ttype, tlen = struct.unpack(TLV_HDR_FMT,
                                        payload[off:off + TLV_HDR_SIZE])
            off += TLV_HDR_SIZE
            if off + tlen > len(payload):
                break
            body = payload[off:off + tlen]
            off += tlen

            if ttype == TLV_DETECTED_POINTS:
                frame['objects'] = self._parse_detected(body)
            elif ttype == TLV_RANGE_PROFILE:
                frame['range_profile'] = self._unpack_u16(body)
            elif ttype == TLV_RANGE_DOPPLER_HEAT_MAP:
                frame['doppler_heatmap'] = self._parse_heatmap(body)
            elif ttype == TLV_STATS:
                frame['stats'] = self._parse_stats(body)

        return frame

    def _parse_detected(self, data):
        if len(data) < OBJ_DESCR_SIZE:
            return []
        num_obj, xyz_q = struct.unpack(OBJ_DESCR_FMT, data[:OBJ_DESCR_SIZE])
        q_div = float(1 << xyz_q) if xyz_q > 0 else 1.0
        vel_r = self.params.get('vel_res', 0.06)
        rng_r = self.params.get('range_res', 0.047)

        objs = []
        for i in range(num_obj):
            s = OBJ_DESCR_SIZE + i * OBJ_SIZE
            if s + OBJ_SIZE > len(data):
                break
            ri, di, pv, x, y, z = struct.unpack(OBJ_FMT, data[s:s + OBJ_SIZE])
            objs.append({
                'range_idx':   ri,
                'doppler_idx': di,
                'peak_val':    pv,
                'x':           x / q_div,
                'y':           y / q_div,
                'z':           z / q_div,
                'range_m':     ri * rng_r,
                'velocity':    di * vel_r,
            })
        return objs

    @staticmethod
    def _unpack_u16(data):
        n = len(data) // 2
        return np.array(struct.unpack(f'<{n}H', data[:n * 2]), dtype=np.float32)

    def _parse_heatmap(self, data):
        nr = self.params.get('num_range_bins', 64)
        nd = self.params.get('num_doppler_bins', 32)
        need = nr * nd * 2
        if len(data) < need:
            return None
        hm = np.array(struct.unpack(f'<{nr * nd}H', data[:need]),
                       dtype=np.float32).reshape(nr, nd)
        # re-order so negative velocities are on the left
        return np.fft.fftshift(hm, axes=1)

    @staticmethod
    def _parse_stats(data):
        if len(data) < STATS_SIZE:
            return None
        f = struct.unpack(STATS_FMT, data[:STATS_SIZE])
        return {
            'interFrameProcessingTime':   f[0],
            'transmitOutputTime':         f[1],
            'interFrameProcessingMargin': f[2],
            'interChirpProcessingMargin': f[3],
            'activeFrameCPULoad':         f[4],
            'interFrameCPULoad':          f[5],
        }

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description='IWR1443 Radar Doppler Viewer — real-time Doppler visualisation')
    ap.add_argument('--cfg_port',  help='Config UART COM port  (e.g. COM3)')
    ap.add_argument('--data_port', help='Data UART COM port    (e.g. COM4)')
    ap.add_argument('--config',    default='config_doppler.cfg',
                    help='Radar .cfg file (default: config_doppler.cfg)')
    ap.add_argument('--list-ports', action='store_true',
                    help='List available COM ports and exit')
    ap.add_argument('--log', default=None,
                    help='Log detected objects to a CSV file')
    ap.add_argument('--raw-test', action='store_true',
                    help='Read raw bytes from data port for 3 sec and show hex dump (diagnostic)')
    ap.add_argument('--no-config', action='store_true',
                    help='Skip sending config (use if radar is already running, '
                         'e.g. started by TI Visualizer)')
    args = ap.parse_args()

    # ── list ports mode ───────────────────────────────────────
    if args.list_ports:
        print("\nAvailable serial ports:")
        list_serial_ports()
        return

    if not args.cfg_port or not args.data_port:
        ap.error('--cfg_port and --data_port are required '
                 '(use --list-ports to find them)')

    # ── raw diagnostic mode ───────────────────────────────────
    if args.raw_test:
        print(f"\n[RAW TEST] Opening {args.data_port} at 921600 baud ...")
        try:
            s = serial.Serial(args.data_port, 921600, timeout=0.1)
        except serial.SerialException as e:
            print(f"[!] Cannot open: {e}")
            sys.exit(1)

        s.reset_input_buffer()
        print("[RAW TEST] Reading for 3 seconds ...\n")
        raw = bytearray()
        deadline = time.time() + 3.0
        while time.time() < deadline:
            chunk = s.read(4096)
            if chunk:
                raw.extend(chunk)
        s.close()

        print(f"Total bytes received: {len(raw)}")
        if len(raw) == 0:
            print("NO DATA — port is silent.  The radar may not be running,")
            print("or this is actually the config port.")
            return

        # show first 256 bytes as hex
        show = min(len(raw), 256)
        print(f"\nFirst {show} bytes (hex):")
        for i in range(0, show, 16):
            hexpart = ' '.join(f'{b:02x}' for b in raw[i:i+16])
            print(f"  {i:04x}: {hexpart}")

        # search for magic word
        mw = b'\x02\x01\x04\x03\x06\x05\x08\x07'
        count = 0
        pos = 0
        first_pos = -1
        while True:
            idx = raw.find(mw, pos)
            if idx < 0:
                break
            if first_pos < 0:
                first_pos = idx
            count += 1
            pos = idx + len(mw)

        print(f"\nMagic word (02 01 04 03 06 05 08 07) found: {count} times")
        if count > 0:
            print(f"First occurrence at byte offset: {first_pos}")
            # show 48 bytes starting from first magic word
            peek = min(len(raw) - first_pos, 48)
            print(f"First packet header ({peek} bytes):")
            hdr_bytes = raw[first_pos:first_pos+peek]
            hexpart = ' '.join(f'{b:02x}' for b in hdr_bytes)
            print(f"  {hexpart}")
            if peek >= HEADER_SIZE:
                f = struct.unpack(HEADER_FMT, bytes(hdr_bytes[:HEADER_SIZE]))
                print(f"\n  Decoded header:")
                print(f"    version:        0x{f[4]:08x}")
                print(f"    totalPacketLen: {f[5]} bytes")
                print(f"    platform:       0x{f[6]:x}")
                print(f"    frameNumber:    {f[7]}")
                print(f"    numDetectedObj: {f[9]}")
                print(f"    numTLVs:        {f[10]}")
        else:
            print("\nNO magic word found in the data stream!")
            print("This data might not be TLV packets. Could be:")
            print("  - The board is running different firmware")
            print("  - The config was never sent (radar streaming old config)")
            print("  - This is actually the config port echoing text")
            # check if it looks like ASCII
            ascii_count = sum(1 for b in raw[:200] if 32 <= b < 127)
            if ascii_count > len(raw[:200]) * 0.7:
                print(f"\n  Data looks like ASCII text ({ascii_count}/200 "
                      f"printable chars):")
                print(f"  {raw[:200].decode('utf-8', errors='replace')}")
        return

    # ── parse radar config ────────────────────────────────────
    print(f"\n[*] Loading config: {args.config}")
    try:
        params, commands = parse_config(args.config)
    except FileNotFoundError:
        print(f"[!] Config file not found: {args.config}")
        sys.exit(1)

    print(f"    Range resolution:    {params.get('range_res', 0):.4f} m")
    print(f"    Max range:           {params.get('max_range', 0):.2f} m")
    print(f"    Velocity resolution: {params.get('vel_res', 0):.4f} m/s")
    print(f"    Max velocity:        {params.get('max_velocity', 0):.3f} m/s")
    print(f"    Range bins:          {params.get('num_range_bins', '?')}")
    print(f"    Doppler bins:        {params.get('num_doppler_bins', '?')}")
    print(f"    Frame period:        {params.get('frame_period', 0):.1f} ms")

    has_heatmap = params.get('gui_doppler_heat_map', 0) == 1
    print(f"    Doppler heatmap:     {'ON' if has_heatmap else 'OFF'}")

    # ── open serial ports ─────────────────────────────────────
    ser_cfg = None
    if not args.no_config:
        print(f"\n[*] Opening config port: {args.cfg_port}  (115200 baud)")
        try:
            ser_cfg = serial.Serial(args.cfg_port, 115200, timeout=0.5)
        except serial.SerialException as e:
            print(f"[!] Cannot open {args.cfg_port}: {e}")
            sys.exit(1)

    print(f"[*] Opening data port:   {args.data_port}  (921600 baud)")
    try:
        ser_data = serial.Serial(args.data_port, 921600, timeout=0.01)
    except serial.SerialException as e:
        if ser_cfg:
            ser_cfg.close()
        print(f"[!] Cannot open {args.data_port}: {e}")
        sys.exit(1)

    # flush any stale data sitting in the serial buffers
    if ser_cfg:
        ser_cfg.reset_input_buffer()
        ser_cfg.reset_output_buffer()
    ser_data.reset_input_buffer()
    time.sleep(0.05)

    # ── send config ───────────────────────────────────────────
    if args.no_config:
        print("\n[*] --no-config: skipping config send (radar should already be running)")
    else:
        print(f"\n[*] Sending radar configuration ...")
        time.sleep(0.1)
        send_config(ser_cfg, commands)
        print("[*] Configuration complete.")

    # flush data port again — sensorStart may have pushed a partial frame
    time.sleep(0.1)
    ser_data.reset_input_buffer()
    print("[*] Data port flushed — ready for clean frames.\n")

    # ── optional CSV log ──────────────────────────────────────
    log_file = None
    if args.log:
        log_file = open(args.log, 'w')
        log_file.write('frame,time_s,obj,range_m,velocity_m_s,'
                       'peak,x_m,y_m,z_m,range_idx,doppler_idx\n')
        print(f"[*] Logging detections to: {args.log}")

    # ── start background reader ───────────────────────────────
    reader = RadarDataReader(ser_data, params)
    reader.start()
    t_start = time.time()
    warned = False
    print("[*] Waiting for radar data ...  (close the plot window to exit)\n")
    print("=" * 95)

    # ── build matplotlib figure ───────────────────────────────
    fig, ax_sc = plt.subplots(1, 1, figsize=(9, 7),
                              facecolor='#0a1628')  # dark navy outer bg

    try:
        fig.canvas.manager.set_window_title('IWR1443 Doppler Viewer')
    except Exception:
        pass
    fig.suptitle('IWR1443 Radar — Doppler Data Viewer',
                 fontsize=14, fontweight='bold', color='white')

    max_v = params.get('max_velocity', 1.0)
    max_r = params.get('max_range', 3.0)

    # -- scatter plot (detected objects coloured by velocity) --
    ax_sc.set_facecolor('#0f2044')               # dark blue radar background
    ax_sc.set_title('Detected Objects  (top-down XY)', color='white', fontsize=11)
    ax_sc.set_xlabel('X  (m)', color='white')
    ax_sc.set_ylabel('Y  (m)', color='white')
    ax_sc.set_xlim(-max_r, max_r)
    ax_sc.set_ylim(0, max_r)
    ax_sc.set_aspect('equal')
    ax_sc.grid(True, alpha=0.2, color='#4488cc')
    ax_sc.tick_params(colors='white')
    for spine in ax_sc.spines.values():
        spine.set_color('#4488cc')

    # Doppler colour range — tightened for micro-motion detection.
    # Fruit fly movements are tiny, so ±0.15 m/s makes subtle
    # velocity differences show up as strong colour shifts.
    # Anything faster just saturates to full red/blue.
    doppler_scale = min(max_v, 0.15)

    sc = ax_sc.scatter([], [], c=[], cmap='coolwarm', s=35,
                       vmin=-doppler_scale, vmax=doppler_scale,
                       edgecolors='white', linewidth=0.4)
    cbar = fig.colorbar(sc, ax=ax_sc, label='Doppler velocity (m/s)',
                        shrink=0.8)
    cbar.ax.yaxis.set_tick_params(color='white')
    cbar.ax.yaxis.label.set_color('white')
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color='white')

    ax_sc.plot(0, 0, marker='^', color='#00ff88', ms=10, label='Radar',
               linestyle='none')
    ax_sc.legend(loc='upper right', fontsize=8, facecolor='#0a1628',
                 edgecolor='#4488cc', labelcolor='white')

    info_txt = ax_sc.text(0.02, 0.98, '', transform=ax_sc.transAxes,
                          va='top', fontsize=9, color='white',
                          bbox=dict(boxstyle='round', fc='#0a1628',
                                    ec='#4488cc', alpha=0.9))

    plt.tight_layout()

    # ── animation callback ────────────────────────────────────
    fps_q = deque(maxlen=30)

    def _update(_frame_num):
        nonlocal warned

        frame = reader.get_frame()
        if frame is None:
            # warn once if no data after 5 s — include diagnostics
            if (not warned and reader.frame_count == 0
                    and time.time() - t_start > 5):
                brcv = reader.bytes_received
                mfnd = reader.magic_found
                print(f"\n[!] No valid frames after 5 s.")
                print(f"    Bytes received on data port: {brcv}")
                print(f"    Magic words found:           {mfnd}")
                if brcv == 0:
                    print("    >> ZERO bytes — data port is silent.")
                    print("    Likely cause: COM ports are SWAPPED.")
                    print(f"    Try: --cfg_port {args.data_port} "
                          f"--data_port {args.cfg_port}")
                    print("    Also: power-cycle the board and close "
                          "TI Demo Visualizer if open.")
                elif mfnd == 0:
                    print("    >> Bytes flowing but no magic word found.")
                    print("    The data port may be echoing config text.")
                    print(f"    Try swapping: --cfg_port {args.data_port} "
                          f"--data_port {args.cfg_port}")
                else:
                    print("    >> Magic words found but packets failed "
                          "sanity check.")
                    print("    Board may need a power-cycle.")
                warned = True
            return [sc, info_txt]

        now = time.time()
        fps_q.append(now)
        fps = (len(fps_q) / max(fps_q[-1] - fps_q[0], 1e-9)
               if len(fps_q) > 1 else 0)

        objs = frame['objects']
        n = len(objs)

        # ── update scatter plot ───────────────────────────────
        if n > 0:
            xs = np.array([o['x'] for o in objs])
            ys = np.array([o['y'] for o in objs])
            vs = np.array([o['velocity'] for o in objs])
            sc.set_offsets(np.column_stack([xs, ys]))
            sc.set_array(vs)
        else:
            sc.set_offsets(np.empty((0, 2)))
            sc.set_array(np.array([]))

        info_txt.set_text(
            f"Frame {frame['frameNumber']}  |  {n} obj  |  {fps:.1f} FPS")

        # ── terminal output ───────────────────────────────────
        line = f"Frame {frame['frameNumber']:>5d}  |  {n:>3d} objects"
        if frame.get('stats'):
            st = frame['stats']
            line += (f"  |  CPU {st['activeFrameCPULoad']}%"
                     f"/{st['interFrameCPULoad']}%")
        line += f"  |  {fps:.1f} FPS"
        print(line)

        if n > 0:
            print(f"  {'#':>3} {'Range':>8} {'Velocity':>10} "
                  f"{'Peak':>6} {'X':>8} {'Y':>8} {'Z':>8}")
            for i, o in enumerate(objs):
                print(f"  {i:>3} {o['range_m']:>8.3f} "
                      f"{o['velocity']:>+10.4f} {o['peak_val']:>6} "
                      f"{o['x']:>8.3f} {o['y']:>8.3f} {o['z']:>8.3f}")
            vels = [o['velocity'] for o in objs]
            print(f"  Vel: min={min(vels):+.4f}  max={max(vels):+.4f}  "
                  f"mean={np.mean(vels):+.4f}  std={np.std(vels):.4f} m/s")

        print("-" * 95)

        # ── CSV logging ───────────────────────────────────────
        if log_file:
            t = now - t_start
            fn = frame['frameNumber']
            for i, o in enumerate(objs):
                log_file.write(
                    f"{fn},{t:.3f},{i},"
                    f"{o['range_m']:.4f},{o['velocity']:.4f},"
                    f"{o['peak_val']},"
                    f"{o['x']:.4f},{o['y']:.4f},{o['z']:.4f},"
                    f"{o['range_idx']},{o['doppler_idx']}\n")
            log_file.flush()

        return [sc, info_txt]

    # ── run ───────────────────────────────────────────────────
    ani = animation.FuncAnimation(fig, _update, interval=50, blit=False,
                                   cache_frame_data=False)

    try:
        plt.show()
    except KeyboardInterrupt:
        pass
    finally:
        print("\n[*] Shutting down ...")
        reader.stop()
        # stop the radar sensor
        if ser_cfg:
            try:
                ser_cfg.write(b'sensorStop\r\n')
                time.sleep(0.1)
            except Exception:
                pass
            ser_cfg.close()
        ser_data.close()
        if log_file:
            log_file.close()
            print(f"[*] Log saved: {args.log}")
        print("[*] Done.")


if __name__ == '__main__':
    main()
