#!/usr/bin/env python3

from argparse import ArgumentParser, FileType
from collections import defaultdict
from configparser import ConfigParser
from json import JSONDecoder
from logging import Formatter, StreamHandler, getLogger, DEBUG, ERROR, WARNING
from logging.handlers import TimedRotatingFileHandler
from os.path import (isdir, isfile, basename, dirname, join as joinpath,
                     splitext)
from os import makedirs
from select import poll, POLLIN
from subprocess import Popen, PIPE, call
from sys import modules, stderr
from time import sleep, time as now
from traceback import format_exc

# pylint: disable-msg=invalid-name
# pylint: disable-msg=broad-except


class RtlLogger:

    log = getLogger("rtl")
    log.addHandler(StreamHandler(stderr))
    log.setLevel(level=WARNING)

    @classmethod
    def set_formatter(cls, formatter):
        handlers = list(cls.log.handlers)
        for handler in handlers:
            handler.setFormatter(formatter)

    @classmethod
    def get_level(cls):
        return cls.log.getEffectiveLevel()

    @classmethod
    def set_level(cls, level):
        cls.log.setLevel(level=level)


class RrdStorage:

    RRD = 'rrdtool'

    def __init__(self, rrd_filename, sensors, offsets=None):
        self.log = getLogger('rtl.rrd')
        self._rrd = rrd_filename
        # one data feed every 60 seconds, that is every minute
        self._step = 60
        self._heartbeat = self._step*4
        if not isfile(self._rrd):
            rrd_dir = dirname(self._rrd)
            if rrd_dir and rrd_dir != '.' and not isdir(rrd_dir):
                makedirs(rrd_dir)
            self.log.warning('Creating RRD file %s', basename(self._rrd))
            ds = []
            hb = self._heartbeat
            for sensor in sensors:
                kind = sensor.split('_', 1)[0]
                if kind == 'temp':
                    ds.append('DS:%s:GAUGE:%d:-20:50' % (sensor, hb))
                elif kind == 'humi':
                    ds.append('DS:%s:GAUGE:%d:0:100' % (sensor, hb))
                elif kind == 'rain':
                    ds.append('DS:%s:DERIVE:%d:0:100' % (sensor, hb))
                elif kind == 'batt':
                    ds.append('DS:%s:GAUGE:%d:0:1' % (sensor, hb))
                else:
                    raise ValueError('Unsupported sensor: %s' % sensor)
            args = [self.RRD, 'create', self._rrd,
                    '--start', '-%d' % self._step,
                    '--step', '%d' % self._step]
            args.extend(ds)
            args.extend(('RRA:AVERAGE:0.50:1:1h',     # each min, 1 hour
                         'RRA:AVERAGE:0.50:5:1y',     # 5 min, 1 year
                         'RRA:AVERAGE:0.50:60:10y',   # 1 hour, 10 year
                         'RRA:MIN:0.50:1440:10y',     # 1 day, 10 year
                         'RRA:MAX:0.50:1440:10y',     # 1 day, 10 year
                         'RRA:LAST:0.50:1:10'))       # each min, 10 min
            self.log.debug("Args: %s", ' '.join(args))
            rc = call(args)
            if rc:
                exit(rc)
            # rrd.create(rrd_filename,
            #           *args)
        self._sensors = {sensor: pos for pos, sensor in enumerate(sensors)}
        self._cache = ['U'] * len(self._sensors)
        self._last = now()
        self._offsets = offsets or defaultdict(dict)

    def push(self, sensor, msg):
        temperature = msg.get('temperature_C', None)
        if temperature is not None:
            pos = self._sensors.get('temp_%s' % sensor, None)
            if pos is not None:
                temperature += self._offsets[sensor].get('temperature', 0.0)
                self._cache[pos] = '%.1f' % temperature
                self.log.info('%s temperature: %.1f', sensor, temperature)
        humidity = msg.get('humidity', None)
        if humidity is not None:
            pos = self._sensors.get('humi_%s' % sensor, None)
            if pos is not None:
                self._cache[pos] = '%d' % humidity
                self.log.info('%s humidity: %.1f', sensor, humidity)
        rain = msg.get('rain', None)
        if rain is not None:
            pos = self._sensors.get('rain_%s' % sensor, None)
            if pos is not None:
                self._cache[pos] = '%d' % rain
                self.log.info('%s rain: %.1f', sensor, rain)
        battery = msg.get('battery', None)
        if battery is not None:
            low = battery.upper() != 'OK'
            pos = self._sensors.get('batt_%s' % sensor, None)
            if pos is not None:
                self._cache[pos] = '%d' % int(low)
                if low:
                    self.log.warning('%s battery low', sensor)
        ts = now()
        if ts > self._last + self._step:
            update = 'N:%s' % ':'.join(self._cache)
            self.log.debug("Update: %s", update)
            args = (self.RRD, 'update', self._rrd, update)
            call(args)
            self._cache = ['U'] * len(self._sensors)
            self._last = ts
        else:
            self.log.debug('%d seconds before next update',
                           ((self._last + self._step)-ts))
        # result = rrd.updatev(self._rrd, update)
        # self.log.debug('RRD changes:')
        # for line in pformat(result).split('\n'):
        #    self.log.debug('  %s', line)


class Rtl433Receiver:

    def __init__(self):
        self.log = getLogger('rtl.rx')
        self._devices = {}
        self._rrd = None
        self._resume = False
        self._protocols = set()

    def configure(self, inifp):
        parser = ConfigParser()
        parser.read_file(inifp)
        rrd = None
        sensors = []
        offsets = defaultdict(dict)
        self._protocols.clear()
        for section in parser.sections():
            self.log.info('Section: %s', section)
            if section == 'rrd':
                try:
                    rrd = parser.get(section, 'file')
                except Exception as ex:
                    raise RuntimeError('Missing RRD file: %s' % ex)
                continue
            try:
                devid = parser.get(section, 'id')
                protocol = int(parser.get(section, 'protocol'))
            except Exception as ex:
                raise RuntimeError('Missing device configuration: %s' % ex)
            self._devices[devid] = section
            for sensor in 'temperature humidity rain battery'.split():
                if parser.has_option(section, sensor):
                    sensors.append('_'.join((sensor[:4], section)))
                offset_name = '%s_offset' % sensor
                if parser.has_option(section, offset_name):
                    try:
                        offset = float(parser.get(section, offset_name))
                        offsets[section][sensor] = offset
                    except ValueError:
                        raise ValueError('%s:%s invalid offset value' %
                                         (section, sensor))
            self._protocols.add(protocol)
        if rrd:
            sensors.sort()
            self.log.info('Sensors: %s', ', '.join(sensors))
            self._rrd = RrdStorage(rrd, sensors, offsets)

    def run(self):
        args = '/usr/local/bin/rtl_433 -F json'.split()
        for protocol in sorted(self._protocols):
            args.append('-R')
            args.append('%d' % protocol)
        self._resume = True
        while self._resume:
            self.log.info("Start rtl_433")
            with Popen(args, stdout=PIPE, stderr=PIPE,
                       universal_newlines=True) as rtl:
                if not self._receive(rtl):
                    continue

    def _receive(self, rtl):
        poller = poll()
        poller.register(rtl.stdout.fileno(), POLLIN)
        poller.register(rtl.stderr.fileno(), POLLIN)
        try:
            decoder = JSONDecoder()
            while self._resume:
                ready = poller.poll(0.2)
                if not ready:
                    continue
                err = ''
                for fd, event in ready:
                    if fd == rtl.stderr.fileno():
                        err = rtl.stderr.readline().strip()
                        if err:
                            self.log.warning(err)
                        break
                if err:
                    continue
                js = rtl.stdout.readline()
                if not js:
                    self.log.error('No data, restart')
                    sleep(0.5)
                    ready = poller.poll(0.2)
                    if ready:
                        for fd, event in ready:
                            if fd == rtl.stderr.fileno():
                                err = rtl.stderr.read()
                                for line in err.split('\n'):
                                    line = line.strip()
                                    if line:
                                        self.log.warning(line)
                                    if line.startswith('Unable to open'):
                                        self.log.fatal('No RTL-SDR device')
                                        self._resume = False
                    return None
                try:
                    data = decoder.decode(js)
                except ValueError as ex:
                    self.log.error('Error: %s', ex)
                    self.log.info('JSON: %s', js)
                    continue
                self.log.debug('JS: %s', data)
                dev_id = data.get('id', 0)
                dev_rid = data.get('rid', 0)
                dev_ch = data.get('channel', 0)
                device = (dev_id, dev_rid, dev_ch)
                dev_str = ':'.join(['%d' % it for it in device])
                if dev_str not in self._devices:
                    self.log.warning('Device %s ignored', dev_str)
                    continue
                self.log.debug('Pushing message to %s', dev_str)
                sensor = self._devices[dev_str]
                if self._rrd:
                    self._rrd.push(sensor, data)
        except KeyboardInterrupt:
            self._resume = False


def configure_logging(verbosity, debug, logfile=None, loggers=None):
    """Create a default configuration for logging, as the same logging idiom
       is used with many scripts.

       Note: the order of loggers does matter, as any logger which does not
       have at least a handler is assigned all the handlers of the first logger
       that does have one or more.

       :param verbosity: a verbosity level, usually args.verbose
       :param debug: a boolean value, usually args.debug
       :param logfile: a log file for the output stream, defaults to stderr
       :param loggers: an iterable of loggers to reconfigure

       :return: the loglevel, in logging enumerated value
    """
    loglevel = max(DEBUG, ERROR - (10 * (verbosity or 0)))
    loglevel = min(ERROR, loglevel)
    if debug:
        formatter = Formatter(
            '%(asctime)s.%(msecs)03d %(levelname)-8s %(name)-20s %(message)s',
            '%H:%M:%S')
    else:
        formatter = Formatter('%(message)s')
    default_handlers = []
    for logger in loggers or []:
        # replicate the handlers of the first loggger to all other handlers
        # which have not been assigned one or more handlers yet
        if not default_handlers and logger.log.handlers:
            default_handlers = logger.log.handlers
        elif not logger.log.handlers and default_handlers:
            for handler in default_handlers:
                logger.log.addHandler(handler)
        if logfile:
            # create a copy of handlers, as we need to modify it
            handlers = list(logger.log.handlers)
            for handler in handlers:
                if isinstance(handler, StreamHandler):
                    # remove all StreamHandlers
                    logger.log.removeHandler(handler)
            logger.log.addHandler(TimedRotatingFileHandler(logfile, when='D',
                                                           backupCount=14))
            # those ones are far too verbose
        logger.set_formatter(formatter)
        logger.set_level(loglevel)
    return loglevel


def main():
    """Main routine"""

    debug = True
    try:
        default_ini = '.'.join((splitext(basename(__file__))[0], 'ini'))
        argparser = ArgumentParser(description=modules[__name__].__doc__)
        argparser.add_argument('-i', '--ini',
                               default=default_ini,
                               type=FileType('rt'),
                               help='configuration file')
        argparser.add_argument('-l', '--log',
                               help='logfile (defaults to stderr)')
        argparser.add_argument('-v', '--verbose', action='count', default=0,
                               help='increase verbosity')
        argparser.add_argument('-d', '--debug', action='store_true',
                               help='enable debug mode')
        args = argparser.parse_args()
        debug = args.debug

        configure_logging(args.verbose, debug, args.log,
                          (RtlLogger,))

        rtl = Rtl433Receiver()
        rtl.configure(args.ini)
        rtl.run()

    except Exception as e:
        print('\nError: %s' % e, file=stderr)
        if debug:
            print(format_exc(chain=False), file=stderr)
        exit(1)
    except KeyboardInterrupt:
        exit(2)


if __name__ == '__main__':
    main()
