# loop_profiler
A python profiler for many passings


```python
    import logging
    from loop_profiler import LoopProfiler

    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    p = LoopProfiler(logger=logger)
    for _ in range(1000):
        p.record('A')
        time.sleep(0.01)
        p.record('B')
        time.sleep(0.03)
        p.record('C')
        time.sleep(0.02)
        p.record('D')
```
