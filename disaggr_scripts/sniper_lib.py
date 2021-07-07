import os
import sniper_config
import sniper_stats

ic_invalid = True

def get_results(jobid = None, resultsdir = None, config = None, stats = None, partial = None, force = False, metrics = None):
  if jobid:
    if ic_invalid:
      raise RuntimeError('Cannot fetch results from server, make sure BENCHMARKS_ROOT points to a valid copy of benchmarks+iqlib')
  elif resultsdir:
    results = parse_results_from_dir(resultsdir, partial = partial, metrics = metrics)
    config = get_config(resultsdir = resultsdir)
  elif stats:
    config = config or stats.config
    results = stats.parse_stats(partial or ('roi-begin', 'roi-end'), int(config['general/total_cores']), metrics = metrics)
  else:
    raise ValueError('Need either jobid or resultsdir')

  return {
    'config': config,
    'results': stats_process(config, results),
  }

def parse_results_from_dir(resultsdir, partial = None, metrics = None):
  results = []

  ## sim.cfg
  simcfg = os.path.join(resultsdir, 'sim.cfg')
  if not os.path.exists(simcfg):
    raise Exception("No valid configuration found")
  simcfg = sniper_config.parse_config(open(simcfg).read())
  ncores = int(simcfg['general/total_cores'])

  results += [ ('ncores', -1, ncores) ]
  results += [ ('corefreq', idx, 1e9 * float(sniper_config.get_config(simcfg, 'perf_model/core/frequency', idx))) for idx in range(ncores) ]

  ## sim.info or graphite.out
  siminfo = os.path.join(resultsdir, 'sim.info')
  graphiteout = os.path.join(resultsdir, 'graphite.out')
  if os.path.exists(siminfo):
    s = open(siminfo).read()
    x = s.encode('utf-8')
    x = x.replace(b'L',b'')
    siminfo = eval(x.decode('utf-8'))
  elif os.path.exists(graphiteout):
    siminfo = eval(open(graphiteout).read())
  else:
    siminfo = None
  if siminfo:
    # If we're called from inside run-graphite, sim.info may not yet exist
    results.append(('walltime', -1, siminfo['t_elapsed']))
    results.append(('vmem', -1, siminfo['vmem']))

  ## sim.stats
  if partial:
    k1, k2 = partial[:2]
  else:
    k1, k2 = 'roi-begin', 'roi-end'

  stats = sniper_stats.SniperStats(resultsdir)
  results += stats.parse_stats((k1, k2), ncores, metrics = metrics)

  if not partial:
    walltime = [ v for k, _, v in results if k == 'time.walltime' ]
    instrs = [ v for k, _, v in results if k == 'core.instructions' ]
    if walltime and instrs:
      walltime = walltime[0] / 1e6 # microseconds -> seconds
      instrs = sum(instrs)
      results.append(('roi.walltime', -1, walltime))
      results.append(('roi.instrs', -1, instrs))
      results.append(('roi.ipstotal', -1, instrs / walltime))
      results.append(('roi.ipscore', -1, instrs / (walltime * ncores)))

  ## power.py
  power = {}
  powerfile = os.path.join(resultsdir, 'power.py')
  if os.path.exists(powerfile):
    exec(open(powerfile).read())
    for key, value in list(power.items()):
      results.append(('power.%s' % key, -1, value))

  return results

def get_config(jobid = None, resultsdir = None, force_deleted = True):
  if jobid:
    if ic_invalid:
      raise RuntimeError('Cannot fetch results from server, make sure BENCHMARKS_ROOT points to a valid copy of benchmarks+iqlib')
  elif resultsdir:
    cfgfile = os.path.join(resultsdir, 'sim.cfg')
    if not os.path.exists(cfgfile):
      raise ValueError('Cannot find config file at %s' % resultsdir)
    simcfg = open(cfgfile).read()
  config = sniper_config.parse_config(simcfg)
  return config

def stats_process(config, results):
  ncores = int(config['general/total_cores'])
  stats = {}
  for key, core, value in results:
     if core == -1:
       stats[key] = value
     else:
       if key not in stats:
         stats[key] = [0]*ncores
       if core < len(stats[key]):
         stats[key][core] = value
       else:
         nskipped = core - len(stats[key])
         stats[key] += [0]*nskipped + [value]
  # Figure out when the interval of time, represented by partial, actually begins/ends
  # Since cores can account for time in chunks, per-core time can be
  # both before (``wakeup at future time X'') or after (``sleep until woken up'')
  # the current time.
  if 'barrier.global_time_begin' in stats:
    # Most accurate: ask the barrier
    time0_begin = stats['barrier.global_time_begin'][0]
    time0_end = stats['barrier.global_time_end'][0]
    stats.update({'global.time_begin': time0_begin, 'global.time_end': time0_end, 'global.time': time0_end - time0_begin})
  elif 'performance_model.elapsed_time_begin' in stats:
    # Guess based on core that has the latest time (future wakeup is less common than sleep on futex)
    time0_begin = max(stats['performance_model.elapsed_time_begin'])
    time0_end = max(stats['performance_model.elapsed_time_end'])
    stats.update({'global.time_begin': time0_begin, 'global.time_end': time0_end, 'global.time': time0_end - time0_begin})
  # add computed stats
  try:
    l1access = sum(stats['L1-D.load-misses']) + sum(stats['L1-D.store-misses'])
    l1time = sum(stats['L1-D.total-latency'])
    stats['l1misslat'] = l1time / float(l1access or 1)
  except KeyError:
    pass
  stats['pthread_locks_contended'] = float(sum(stats.get('pthread.pthread_mutex_lock_contended', [0]))) / (sum(stats.get('pthread.pthread_mutex_lock_count', [0])) or 1)
  # femtosecond to cycles conversion
  freq = [ 1e9 * float(sniper_config.get_config(config, 'perf_model/core/frequency', idx)) for idx in range(ncores) ]
  stats['fs_to_cycles_cores'] = [f / 1e15 for f in freq]
  # Backwards compatible version returning fs_to_cycles for core 0, for heterogeneous configurations fs_to_cycles_cores needs to be used
  stats['fs_to_cycles'] = stats['fs_to_cycles_cores'][0]
  # Fixed versions of [idle|nonidle] elapsed time
  if 'performance_model.elapsed_time' in stats and 'performance_model.idle_elapsed_time' in stats:
    stats['performance_model.nonidle_elapsed_time'] = [
      stats['performance_model.elapsed_time'][c] - stats['performance_model.idle_elapsed_time'][c]
      for c in range(ncores)
    ]
    stats['performance_model.idle_elapsed_time'] = [
      time0_end - time0_begin - stats['performance_model.nonidle_elapsed_time'][c]
      for c in range(ncores)
    ]
    stats['performance_model.elapsed_time'] = [ time0_end - time0_begin for c in range(ncores) ]
  # DVFS-enabled runs: emulate cycle_count asuming constant (initial) frequency
  if 'performance_model.elapsed_time' in stats and 'performance_model.cycle_count' not in stats:
    stats['performance_model.cycle_count'] = [ stats['fs_to_cycles_cores'][idx] * stats['performance_model.elapsed_time'][idx] for idx in range(ncores) ]
  if 'thread.nonidle_elapsed_time' in stats and 'thread.nonidle_cycle_count' not in stats:
    stats['thread.nonidle_cycle_count'] = [ int(stats['fs_to_cycles'] * t) for t in stats['thread.nonidle_elapsed_time'] ]
  # IPC
  if 'performance_model.cycle_count' in stats:
    stats['ipc'] = [
      i / (c or 1)
      for i, c in zip(stats['performance_model.instruction_count'], stats['performance_model.cycle_count'])
    ]

  return stats