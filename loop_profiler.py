import copy
from collections import OrderedDict, abc
import logging
from logging import Logger
import inspect
import sys
import threading
import time
from typing import NamedTuple, List, Mapping

import numpy


class TimeInfo(NamedTuple):
    record_times: List[float]
    filename: str
    lineno: int


class LoopProfiler:
    def __init__(self,
                 interval: float=3.,
                 maxlogs=100,
                 logger: Logger=None,
                 loglevel: int=10,
                 show_last2first_record=False):
        self._interval = float(interval)
        if logger is not None:
            self._logger = logger
        else:
            self._logger = logging
        self._loglevel = int(loglevel)
        self._maxlogs = maxlogs

        self._d = OrderedDict()
        self._close = False
        self._lock = threading.Lock()
        self._show_last2first_record = show_last2first_record

    def record(self, name):
        with self._lock:
            if name in self._d and not self._close:
                self._close = True
                t = threading.Thread(target=self._loop)
                t.daemon = True
                t.start()

            _mes = ('For each monitoring cycles, '
                    'same name cannot occured twice, '
                    'and the cycles must have the same order of the names.')
            if self._close and name not in self._d:
                raise RuntimeError(_mes)

            if name not in self._d:
                if hasattr(sys, '_getframe'):
                    frame = inspect.stack()[1]
                    if frame is not None and frame.filename is not None:
                        self._d[name] =\
                            TimeInfo([], frame.filename, frame.lineno)
                    else:
                        self._d[name] = TimeInfo([], None, None)
                    del frame
                else:
                    self._d[name] = TimeInfo([], None, None)

            key_list = list(self._d.keys())
            prev_idx = key_list.index(name) - 1
            if prev_idx != -1:
                if len(self._d[key_list[prev_idx]].record_times) != \
                        len(self._d[name].record_times) + 1:
                    raise RuntimeError(_mes)
            else:
                if len(self._d[key_list[prev_idx]].record_times) != \
                        len(self._d[name].record_times):
                    raise RuntimeError(_mes)

            self._d[name].record_times.append(time.perf_counter())

    def _loop(self):
        while True:
            time.sleep(self._interval)
            self.show()
            with self._lock:
                length = len(list(self._d.values())[-1].record_times)
                if length > self._maxlogs:
                    for info in self._d.values():
                        info.record_times[:] =\
                            info.record_times[length - self._maxlogs - 1:]

    def show(self):
        with self._lock:
            if len(self._d) == 0:
                return

            # Derive delta
            deltas = {}
            prev_rec = None

            for name, info in self._d.items():
                if prev_rec is None:
                    prev_rec = tuple(self._d.values())[-1].record_times
                    prev_name = tuple(self._d.keys())[-1]
                    cur = info.record_times[1:]
                else:
                    cur = info.record_times
                ds = [c - p for c, p in zip(cur, prev_rec)]
                if len(ds) == 0:
                    deltas[name] = (prev_name, None, None, None)
                else:
                    mean = numpy.mean(ds)
                    num = len(ds)
                    ste = numpy.std(ds) / numpy.sqrt(num)
                    deltas[name] = (prev_name, mean, ste, num)
                prev_rec = info.record_times
                prev_name = name

            _length = 26

            key_list = list(self._d.keys())
            max_len = max(len(k1) + len(k2)
                          for k1, k2 in zip(key_list[-1:] + key_list[:-1],
                                            key_list))
            if self._show_last2first_record:
                _sum = numpy.sum(m for _, m, _, _ in deltas.values()
                                 if m is not None)
            else:
                _sum = numpy.sum(m for _, m, _, _ in list(deltas.values())[1:]
                                 if m is not None)
            total_mes = ['***** Profiling *****']
            for idx, (name, info) in enumerate(self._d.items()):
                if not self._show_last2first_record and idx == 0:
                    continue
                prev_name, mean, ste, num = deltas[name]
                if mean is None:
                    time_mes = '-' * _length
                else:
                    time_mes = '{:.5f}s(+-{:.5f}, n={}), {:.1f}%'.format(
                        mean, ste, num, mean / _sum * 100)

                if info.filename is not None:
                    src_info = '{}({}L)'.format(info.filename, info.lineno)
                else:
                    src_info = '-'

                _mes = '{}-{}{} | {} | {}'.format(
                    prev_name, name,
                    ' ' * (max_len - len(name) - len(prev_name)),
                    time_mes, src_info)
                total_mes.append(_mes)
            self._logger.log(self._loglevel, '\n'.join(total_mes))
