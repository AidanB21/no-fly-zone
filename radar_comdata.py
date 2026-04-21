#!/usr/bin/env python3
"""
radar_comdata.py  —  TI IWR1443 Radar Data Pipeline
=====================================================
Mirrors what comdata.py does for the VOC sensors, but for the mmWave radar.

Connects to the two IWR1443 COM ports, sends the radar configuration,
then continuously reads the binary TLV data stream and appends one row
per radar frame to  data/sensor_data/radar_log.csv  so that gui.py can
display live radar data alongside the gas-sensor readings.

CSV columns written
-------------------
  Timestamp     – human-readable datetime string
  presence      – 1 if any objects were detected this frame, else 0
  distance_m    – mean range of detected objects in metres  (0 if none)
  micro_doppler – mean Doppler velocity of detected objects  (0 if none)
  num_objects   – raw count of detected objects
  peak_velocity – fastest (abs) Doppler velocity seen this frame

Usage
-----
  python radar_comdata.py --cfg_port COM3 --data_port COM5
  python radar_comdata.py --cfg_port COM3 --data_port COM5 --config config_doppler.cfg
  python radar_comdata.py --list-ports          # see available ports

Tip
---
  The IWR1443Boost enumerates as TWO virtual COM ports on Windows.
  The LOWER-numbered port is the Application/Config UART (115 200 baud).
  The HIGHER-numbered port is the Data UART (921 600 baud).
  Example: if you see COM3 and COM4 for the radar, use
           --cfg_port COM3 --data_port COM4
  (COM4 is also your VOC sensor — use the actual ports shown by --list-ports)
"""

import argparse
import os
import csv
import struct
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import serial
import serial.tools.list_ports

# ---------------------------------------------------------------------------
# Constants — TI IWR1443 firmware (mmw_output.h / detected_obj.h)
# ---------------------------------------------------------------------------

MAGIC_WORD   = b'\x02\x01\x04\x03\x06\x05\x08\x07'
HEADER_FMT   = '<4H7I'
HEADER_SIZE  = struct.calcsize(HEADER_FMT)   # 36 bytes

TLV_DETECTED_POINTS       = 1
TLV_RANGE_PROFILE         = 2
TLV_RANGE_DOPPLER_HEAT_MAP = 5
TLV_STATS                 = 6

TLV_HDR_FMT  = '<II'
TLV_HDR_SIZE = struct.calcsize(TLV_HDR_FMT)  # 8 bytes

OBJ_DESCR_FMT  = '<HH'
OBJ_DESCR_SIZE = struct.calcsize(OBJ_DESCR_FMT)  # 4 bytes

OBJ_FMT  = '<HhHhhh'
OBJ_SIZE = struct.calcsize(OBJ_FMT)  # 12 bytes

SPEED_OF_LIGHT = 3.0e8

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _next_pow2(x):
    return 1 << (x - 1).bit_length() if x > 0 else 1


def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("  No serial ports found.")
        return
    print(f"  {'Port':<10} {'Description':<50} {'HWID'}")
    print("  " + "-" * 90)
    for p in sorted(ports, key=lambda x: x.device):
        print(f"  {p.device:<10} {p.description:<50} {p.hwid}")

# ---------------------------------------------------------------------------
# Config parser  (reads the TI .cfg file)
# ---------------------------------------------------------------------------

def parse_config(path):
    """Return (params dict, list of CLI command strings) from a .cfg file."""
    params   = {}
    commands = []

    with open(path, 'r') as f:
        for raw in f:
            line = raw.strip()
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
                params['start_freq']      = float(tok[2])
                params['idle_time']       = float(tok[3])
                params['ramp_end_time']   = float(tok[5])
                params['freq_slope']      = float(tok[8])
                params['num_adc_samples'] = int(tok[10])
                params['adc_sample_rate'] = float(tok[11])

            elif cmd == 'frameCfg' and len(tok) >= 6:
                params['start_chirp']  = int(tok[1])
                params['end_chirp']    = int(tok[2])
                params['num_loops']    = int(tok[3])
                params['frame_period'] = float(tok[5])

            elif cmd == 'channelCfg' and len(tok) >= 3:
                params['num_rx'] = bin(int(tok[1])).count('1')
                params['num_tx'] = bin(int(tok[2])).count('1')

    # derived
    nchirps = (params.get('end_chirp', 2) - params.get('start_chirp', 0) + 1)
    params['num_doppler_bins']       = params.get('num_loops', 32)
    params['num_range_bins']         = _next_pow2(params.get('num_adc_samples', 64))
    params['num_chirps_per_frame']   = nchirps * params.get('num_loops', 32)

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
# Send config over the CLI UART
# ---------------------------------------------------------------------------

def send_config(ser, commands):
    ser.write(b'\n')
    time.sleep(0.2)
    if ser.in_waiting:
        ser.read(ser.in_waiting)

    ok_count = 0
    for cmd in commands:
        print(f"  >> {cmd}")
        ser.write((cmd + '\r\n').encode('utf-8'))
        time.sleep(0.05)

        resp     = b''
        deadline = time.time() + 1.0
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
        elif not resp:
            print(f"     (no response — port may be wrong)")

    print(f"  [{ok_count}/{len(commands)} commands acknowledged]")

# ---------------------------------------------------------------------------
# Background reader — parses binary TLV frames off the data UART
# ---------------------------------------------------------------------------

class RadarDataReader:
    def __init__(self, ser, params):
        self.ser            = ser
        self.params         = params
        self.running        = False
        self.frame_count    = 0
        self.bytes_received = 0
        self.magic_found    = 0
        self._thread        = None
        self._lock          = threading.Lock()
        self._latest        = None

    def start(self):
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def get_frame(self):
        """Return and consume the latest parsed frame (or None)."""
        with self._lock:
            f = self._latest
            self._latest = None
            return f

    # ------------------------------------------------------------------ loop

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

            while True:
                idx = buf.find(MAGIC_WORD)
                if idx < 0:
                    if len(buf) > len(MAGIC_WORD) - 1:
                        buf = buf[-(len(MAGIC_WORD) - 1):]
                    break

                self.magic_found += 1
                if idx > 0:
                    buf = buf[idx:]

                if len(buf) < HEADER_SIZE:
                    break

                hdr     = self._parse_header(bytes(buf[:HEADER_SIZE]))
                pkt_len = hdr['totalPacketLen']

                if pkt_len < HEADER_SIZE or pkt_len > 65536:
                    buf = buf[len(MAGIC_WORD):]
                    continue

                if len(buf) < pkt_len:
                    break

                payload = bytes(buf[HEADER_SIZE:pkt_len])
                buf     = buf[pkt_len:]

                frame = self._parse_tlvs(hdr, payload)
                with self._lock:
                    self._latest = frame
                    self.frame_count += 1

    # ---------------------------------------------------------------- parsing

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
        }

        off = 0
        for _ in range(hdr['numTLVs']):
            if off + TLV_HDR_SIZE > len(payload):
                break
            ttype, tlen = struct.unpack(TLV_HDR_FMT, payload[off:off + TLV_HDR_SIZE])
            off += TLV_HDR_SIZE
            if off + tlen > len(payload):
                break
            body = payload[off:off + tlen]
            off += tlen

            if ttype == TLV_DETECTED_POINTS:
                frame['objects'] = self._parse_detected(body)

        return frame

    def _parse_detected(self, data):
        if len(data) < OBJ_DESCR_SIZE:
            return []
        num_obj, xyz_q = struct.unpack(OBJ_DESCR_FMT, data[:OBJ_DESCR_SIZE])
        q_div  = float(1 << xyz_q) if xyz_q > 0 else 1.0
        vel_r  = self.params.get('vel_res',   0.06)
        rng_r  = self.params.get('range_res', 0.047)

        objs = []
        for i in range(num_obj):
            s = OBJ_DESCR_SIZE + i * OBJ_SIZE
            if s + OBJ_SIZE > len(data):
                break
            ri, di, pv, x, y, z = struct.unpack(OBJ_FMT, data[s:s + OBJ_SIZE])
            objs.append({
                'range_m':  ri * rng_r,
                'velocity': di * vel_r,
                'peak_val': pv,
                'x': x / q_div,
                'y': y / q_div,
                'z': z / q_div,
            })
        return objs

# ---------------------------------------------------------------------------
# Summarise a frame into the four CSV columns gui.py expects
# ---------------------------------------------------------------------------

def frame_to_row(frame):
    """
    Returns a dict with the columns written to radar_log.csv.

    presence      – 1 if ≥1 object detected, else 0
    distance_m    – mean range of all detected objects  (0 if none)
    micro_doppler – mean Doppler velocity of all objects (0 if none)
    num_objects   – raw object count
    peak_velocity – highest |velocity| seen this frame  (0 if none)
    """
    objs = frame.get('objects', [])
    n    = len(objs)

    if n == 0:
        return {
            'presence':      0,
            'distance_m':    0.0,
            'micro_doppler': 0.0,
            'num_objects':   0,
            'peak_velocity': 0.0,
        }

    ranges    = [o['range_m']  for o in objs]
    velocities = [o['velocity'] for o in objs]

    return {
        'presence':      1,
        'distance_m':    round(sum(ranges)     / n, 4),
        'micro_doppler': round(sum(velocities) / n, 4),
        'num_objects':   n,
        'peak_velocity': round(max(abs(v) for v in velocities), 4),
    }

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description='IWR1443 radar → CSV pipeline (feeds gui.py)')
    ap.add_argument('--cfg_port',   help='Config UART COM port  (e.g. COM3)')
    ap.add_argument('--data_port',  help='Data  UART COM port  (e.g. COM5)')
    ap.add_argument('--config',     default='config_doppler.cfg',
                    help='Radar .cfg file  (default: config_doppler.cfg)')
    ap.add_argument('--no-config',  action='store_true',
                    help='Skip sending config — use if radar is already running')
    ap.add_argument('--list-ports', action='store_true',
                    help='List available COM ports and exit')
    args = ap.parse_args()

    # ── list ports ────────────────────────────────────────────────────────
    if args.list_ports:
        print("\nAvailable serial ports:")
        list_serial_ports()
        return

    if not args.cfg_port or not args.data_port:
        ap.error('--cfg_port and --data_port are required '
                 '(use --list-ports to discover them)')

    # ── load radar config ─────────────────────────────────────────────────
    print(f"\n[*] Loading radar config: {args.config}")
    try:
        params, commands = parse_config(args.config)
    except FileNotFoundError:
        print(f"[!] Config file not found: {args.config}")
        sys.exit(1)

    print(f"    Range res:    {params.get('range_res', '?')} m")
    print(f"    Max range:    {params.get('max_range', '?')} m")
    print(f"    Velocity res: {params.get('vel_res', '?')} m/s")
    print(f"    Frame period: {params.get('frame_period', '?')} ms")

    # ── CSV output ────────────────────────────────────────────────────────
    BASE_DIR = Path(__file__).resolve().parent
    out_dir  = BASE_DIR / "data" / "sensor_data"
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "radar_log.csv"

    CSV_COLUMNS = ['Timestamp', 'presence', 'distance_m',
                   'micro_doppler', 'num_objects', 'peak_velocity']

    log_file   = open(csv_path, 'w', newline='')
    log_writer = csv.DictWriter(log_file, fieldnames=CSV_COLUMNS)
    log_writer.writeheader()
    log_file.flush()
    print(f"[*] Logging to: {csv_path}")

    # ── open serial ports ─────────────────────────────────────────────────
    ser_cfg = None
    if not args.no_config:
        print(f"\n[*] Opening config port: {args.cfg_port}  (115200 baud)")
        try:
            ser_cfg = serial.Serial(args.cfg_port, 115200, timeout=0.5)
        except serial.SerialException as e:
            print(f"[!] Cannot open {args.cfg_port}: {e}")
            log_file.close()
            sys.exit(1)

    print(f"[*] Opening data port:   {args.data_port}  (921600 baud)")
    try:
        ser_data = serial.Serial(args.data_port, 921600, timeout=0.01)
    except serial.SerialException as e:
        if ser_cfg:
            ser_cfg.close()
        print(f"[!] Cannot open {args.data_port}: {e}")
        log_file.close()
        sys.exit(1)

    if ser_cfg:
        ser_cfg.reset_input_buffer()
        ser_cfg.reset_output_buffer()
    ser_data.reset_input_buffer()
    time.sleep(0.05)

    # ── send config ───────────────────────────────────────────────────────
    if args.no_config:
        print("\n[*] --no-config: skipping config send.")
    else:
        print(f"\n[*] Sending radar configuration ...")
        send_config(ser_cfg, commands)
        print("[*] Configuration complete.")

    time.sleep(0.1)
    ser_data.reset_input_buffer()
    print("[*] Data port flushed — ready for frames.\n")

    # ── start background reader ───────────────────────────────────────────
    reader  = RadarDataReader(ser_data, params)
    reader.start()
    t_start = time.time()
    warned  = False

    print("Monitoring radar...  Press Ctrl+C to stop.\n")
    print(f"  {'Frame':>7}  {'Objs':>5}  {'Presence':>10}  "
          f"{'Distance(m)':>12}  {'µ-Doppler':>10}  {'PeakVel':>9}")
    print("  " + "-" * 65)

    try:
        while True:
            frame = reader.get_frame()

            if frame is None:
                # warn once if nothing arrives after 5 s
                if (not warned
                        and reader.frame_count == 0
                        and time.time() - t_start > 5):
                    brcv = reader.bytes_received
                    mfnd = reader.magic_found
                    print(f"\n[!] No valid frames after 5 s.")
                    print(f"    Bytes received on data port: {brcv}")
                    print(f"    Magic words found:           {mfnd}")
                    if brcv == 0:
                        print("    >> ZERO bytes — the ports may be swapped.")
                        print(f"    Try: --cfg_port {args.data_port} "
                              f"--data_port {args.cfg_port}")
                    elif mfnd == 0:
                        print("    >> Data flowing but no magic word — "
                              "try swapping ports.")
                    warned = True
                time.sleep(0.01)
                continue

            row  = frame_to_row(frame)
            now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            row['Timestamp'] = now

            log_writer.writerow(row)
            log_file.flush()

            # terminal feedback
            if row['presence'] and abs(row['micro_doppler']) > 0.005:
                status_str = "MOTION"
            elif row['presence']:
                status_str = "STATIC"
            else:
                status_str = "clear"

            print(f"  {frame['frameNumber']:>7}  "
                  f"{row['num_objects']:>5}  "
                  f"{status_str:>10}  "
                  f"{row['distance_m']:>12.4f}  "
                  f"{row['micro_doppler']:>+10.4f}  "
                  f"{row['peak_velocity']:>9.4f}")

    except KeyboardInterrupt:
        pass
    finally:
        print("\n[*] Shutting down ...")
        reader.stop()
        if ser_cfg:
            try:
                ser_cfg.write(b'sensorStop\r\n')
                time.sleep(0.1)
            except Exception:
                pass
            ser_cfg.close()
        ser_data.close()
        log_file.close()
        print(f"[*] Log saved: {csv_path}")
        print("[*] Done.")


if __name__ == '__main__':
    main()
