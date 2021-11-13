#!/usr/bin/env python

import sys, os, getopt, sniper_lib


def generate_simout(jobid = None, resultsdir = None, partial = None, output = sys.stdout, silent = False):

  try:
    res = sniper_lib.get_results(jobid = jobid, resultsdir = resultsdir, partial = partial)
  except (KeyError, ValueError), e:
    if not silent:
      print 'Failed to generated sim.out:', e
    return

  results = res['results']
  config = res['config']
  ncores = int(config['general/total_cores'])

  format_int = lambda v: str(long(v))
  format_pct = lambda v: '%.1f%%' % (100. * v)
  def format_float(digits):
    return lambda v: ('%%.%uf' % digits) % v
  def format_ns(digits):
    return lambda v: ('%%.%uf' % digits) % (v/1e6)

  if 'barrier.global_time_begin' in results:
    time0_begin = results['barrier.global_time_begin']
    time0_end = results['barrier.global_time_end']

  if 'barrier.global_time' in results:
    time0 = results['barrier.global_time'][0]
  else:
    time0 = time0_begin - time0_end

  if sum(results['performance_model.instruction_count']) == 0:
    # core.instructions is less exact, but in cache-only mode it's all there is
    results['performance_model.instruction_count'] = results['core.instructions']

  results['performance_model.elapsed_time_fixed'] = [
    time0
    for c in range(ncores)
  ]
  results['performance_model.cycle_count_fixed'] = [
    results['performance_model.elapsed_time_fixed'][c] * results['fs_to_cycles_cores'][c]
    for c in range(ncores)
  ]
  results['performance_model.ipc'] = [
    i / (c or 1)
    for i, c in zip(results['performance_model.instruction_count'], results['performance_model.cycle_count_fixed'])
  ]
  results['performance_model.nonidle_elapsed_time'] = [
    results['performance_model.elapsed_time'][c] - results['performance_model.idle_elapsed_time'][c]
    for c in range(ncores)
  ]
  results['performance_model.idle_elapsed_time'] = [
    time0 - results['performance_model.nonidle_elapsed_time'][c]
    for c in range(ncores)
  ]
  results['performance_model.idle_elapsed_percent'] = [
    results['performance_model.idle_elapsed_time'][c] / float(time0)
    for c in range(ncores)
  ]

  template = [
    ('  Instructions', 'performance_model.instruction_count', str),
    ('  Cycles',       'performance_model.cycle_count_fixed', format_int),
    ('  IPC',          'performance_model.ipc', format_float(4)),
    ('  Time (ns)',    'performance_model.elapsed_time_fixed', format_ns(0)),
    ('  Idle time (ns)', 'performance_model.idle_elapsed_time', format_ns(0)),
    ('  Idle time (%)',  'performance_model.idle_elapsed_percent', format_pct),
  ]

  if 'branch_predictor.num-incorrect' in results:
    results['branch_predictor.missrate'] = [ 100 * float(results['branch_predictor.num-incorrect'][core])
      / ((results['branch_predictor.num-correct'][core] + results['branch_predictor.num-incorrect'][core]) or 1) for core in range(ncores) ]
    results['branch_predictor.mpki'] = [ 1000 * float(results['branch_predictor.num-incorrect'][core])
      / (results['performance_model.instruction_count'][core] or 1) for core in range(ncores) ]
    template += [
      ('Branch predictor stats', '', ''),
      ('  num correct',  'branch_predictor.num-correct', str),
      ('  num incorrect','branch_predictor.num-incorrect', str),
      ('  misprediction rate', 'branch_predictor.missrate', lambda v: '%.2f%%' % v),
      ('  mpki', 'branch_predictor.mpki', lambda v: '%.2f' % v),
    ]

  template += [
    ('TLB Summary', '', ''),
  ]

  for tlb in ('itlb', 'dtlb', 'stlb'):
    if '%s.access'%tlb in results:
      results['%s.missrate'%tlb] = map(lambda (a,b): 100*a/float(b or 1), zip(results['%s.miss'%tlb], results['%s.access'%tlb]))
      results['%s.mpki'%tlb] = map(lambda (a,b): 1000*a/float(b or 1), zip(results['%s.miss'%tlb], results['performance_model.instruction_count']))
      template.extend([
        ('  %s' % {'itlb': 'I-TLB', 'dtlb': 'D-TLB', 'stlb': 'L2 TLB'}[tlb], '', ''),
        ('    num accesses', '%s.access'%tlb, str),
        ('    num misses', '%s.miss'%tlb, str),
        ('    miss rate', '%s.missrate'%tlb, lambda v: '%.2f%%' % v),
        ('    mpki', '%s.mpki'%tlb, lambda v: '%.2f' % v),
      ])

  template += [
    ('Cache Summary', '', ''),
  ]
  allcaches = [ 'L1-I', 'L1-D' ] + [ 'L%u'%l for l in range(2, 5) ]
  existcaches = [ c for c in allcaches if '%s.loads'%c in results ]
  for c in existcaches:
    results['%s.accesses'%c] = map(sum, zip(results['%s.loads'%c], results['%s.stores'%c]))
    results['%s.misses'%c] = map(sum, zip(results['%s.load-misses'%c], results.get('%s.store-misses-I'%c, results['%s.store-misses'%c])))
    results['%s.missrate'%c] = map(lambda (a,b): 100*a/float(b) if b else float('inf'), zip(results['%s.misses'%c], results['%s.accesses'%c]))
    results['%s.mpki'%c] = map(lambda (a,b): 1000*a/float(b) if b else float('inf'), zip(results['%s.misses'%c], results['performance_model.instruction_count']))
    template.extend([
      ('  Cache %s'%c, '', ''),
      ('    num cache accesses', '%s.accesses'%c, str),
      ('    num cache misses', '%s.misses'%c, str),
      ('    miss rate', '%s.missrate'%c, lambda v: '%.2f%%' % v),
      ('    mpki', '%s.mpki'%c, lambda v: '%.2f' % v),
    ])

  allcaches = [ 'nuca-cache', 'dram-cache' ]
  existcaches = [ c for c in allcaches if '%s.reads'%c in results ]
  for c in existcaches:
    results['%s.accesses'%c] = map(sum, zip(results['%s.reads'%c], results['%s.writes'%c]))
    results['%s.misses'%c] = map(sum, zip(results['%s.read-misses'%c], results['%s.write-misses'%c]))
    results['%s.missrate'%c] = map(lambda (a,b): 100*a/float(b) if b else float('inf'), zip(results['%s.misses'%c], results['%s.accesses'%c]))
    icount = sum(results['performance_model.instruction_count'])
    icount /= len([ v for v in results['%s.accesses'%c] if v ]) # Assume instructions are evenly divided over all cache slices
    results['%s.mpki'%c] = map(lambda a: 1000*a/float(icount) if icount else float('inf'), results['%s.misses'%c])
    template.extend([
      ('  %s cache'% c.split('-')[0].upper(), '', ''),
      ('    num cache accesses', '%s.accesses'%c, str),
      ('    num cache misses', '%s.misses'%c, str),
      ('    miss rate', '%s.missrate'%c, lambda v: '%.2f%%' % v),
      ('    mpki', '%s.mpki'%c, lambda v: '%.2f' % v),
    ])

  results['dram.accesses'] = map(sum, zip(results['dram.reads'], results['dram.writes']))
  if 'dram.remote-reads' in results:
    results['dram.local-reads'] = map(lambda (a,b): a-b, zip(results['dram.reads'], results['dram.remote-reads']))
  if 'dram.remote-writes' in results:
    results['dram.local-writes'] = map(lambda (a,b): a-b, zip(results['dram.writes'], results['dram.remote-writes']))
  if 'dram.remote-reads' and 'dram.remote-writes' in results:
    results['dram.remote-accesses'] = map(sum, zip(results['dram.remote-reads'], results['dram.remote-writes']))
    results['dram.local-accesses'] = map(lambda (a,b): a-b, zip(results['dram.accesses'], results['dram.remote-accesses']))

  if 'dram.total-remote-access-latency' in results:  # stat from dram_perf_model_disagg.cc
    results['dram.total-access-latency'] = map(sum, zip(results['dram.total-remote-access-latency'], results['dram.total-local-access-latency']))
    results['dram.localavglatency'] = map(lambda (a,b): a/b if b else float('inf'), zip(results['dram.total-local-access-latency'], results['dram.local-accesses']))
    results['dram.localavghardwarelatency'] = map(lambda (a,b): a/b if b else 0.0, zip(results['dram.total-local-dram-hardware-latency'], results['dram.total-local-dram-hardware-latency-count']))
    results['dram.localavghardwarelatency_processing_time'] = map(lambda (a,b): a/b if b else 0.0, zip(results['dram.total-local-dram-hardware-latency-processing-time'], results['dram.total-local-dram-hardware-latency-count']))
    results['dram.localavghardwarelatency_queue_delay'] = map(lambda (a,b): a/b if b else 0.0, zip(results['dram.total-local-dram-hardware-latency-queue-delay'], results['dram.total-local-dram-hardware-latency-count']))

    results['dram.remoteavglatency'] = map(lambda (a,b): a/b if b else float('inf'), zip(results['dram.total-remote-access-latency'], results['dram.remote-accesses']))
    results['dram.remoteavghardwarelatency_pages'] = map(lambda (a,b): a/b if b else 0.0, zip(results['dram.total-remote-dram-hardware-latency-pages'], results['dram.total-remote-dram-hardware-latency-pages-count']))  # Prefetched pages not currently accounted for in sniper stats
    results['dram.remoteavghardwarelatency_pages_processing_time'] = map(lambda (a,b): a/b if b else 0.0, zip(results['dram.total-remote-dram-hardware-latency-pages-processing-time'], results['dram.total-remote-dram-hardware-latency-pages-count']))  # Prefetched pages not currently accounted for in sniper stats
    results['dram.remoteavghardwarelatency_pages_queue_delay'] = map(lambda (a,b): a/b if b else 0.0, zip(results['dram.total-remote-dram-hardware-latency-pages-queue-delay'], results['dram.total-remote-dram-hardware-latency-pages-count']))  # Prefetched pages not currently accounted for in sniper stats
    
    results['dram.localavghardwarewritelatency_pages'] = map(lambda (a,b): a/b if b else 0.0, zip(results['dram.total-local-dram-hardware-write-latency-pages'], results['dram.total-remote-dram-hardware-latency-pages-count']))  # Prefetched pages not currently accounted for in sniper stats
    
    results['dram.remoteavghardwarelatency_cachelines'] = map(lambda (a,b): (a)/b if b else 0.0, zip(results['dram.total-remote-dram-hardware-latency-cachelines'], results['dram.total-remote-dram-hardware-latency-cachelines-count']))
    results['dram.remoteavghardwarelatency_cachelines_processing_time'] = map(lambda (a,b): (a)/b if b else 0.0, zip(results['dram.total-remote-dram-hardware-latency-cachelines-processing-time'], results['dram.total-remote-dram-hardware-latency-cachelines-count']))
    results['dram.remoteavghardwarelatency_cachelines_queue_delay'] = map(lambda (a,b): (a)/b if b else 0.0, zip(results['dram.total-remote-dram-hardware-latency-cachelines-queue-delay'], results['dram.total-remote-dram-hardware-latency-cachelines-count']))
    
    results['dram.remote_datamovement_avglatency'] = map(lambda (a,b): a/b if b else 0.0, zip(results['dram.total-remote-datamovement-latency'], results['dram.remote-accesses']))
    results['dram.avg_remotetolocal_cacheline_network_processing_time'] = map(lambda (a,b): a/b if b else 0.0, zip(results['dram.total-network-cacheline-processing-time'], results['dram.total-remote-to-local-cacheline-move-count']))
    results['dram.avg_remotetolocal_cacheline_network_queue_delay'] = map(lambda (a,b): a/b if b else 0.0, zip(results['dram.total-network-cacheline-queue-delay'], results['dram.total-remote-to-local-cacheline-move-count']))
    results['dram.avg_remotetolocal_page_network_processing_time'] = map(lambda (a,b): a/b if b else 0.0, zip(results['dram.total-network-page-processing-time'], results['dram.total-remote-to-local-page-move-count']))
    results['dram.avg_remotetolocal_page_network_queue_delay'] = map(lambda (a,b): a/b if b else 0.0, zip(results['dram.total-network-page-queue-delay'], results['dram.total-remote-to-local-page-move-count']))
  if 'dram.page-movement-num-global-time-much-larger' in results and sum(results['dram.page-movement-num-global-time-much-larger']) > 0:
    results['dram.pagemovement_avg_globaltime_much_larger'] = map(lambda (a,b): a/b if b else float('inf'), zip(results['dram.page-movement-global-time-much-larger-total-time'], results['dram.page-movement-num-global-time-much-larger']))
  results['dram.avglatency'] = map(lambda (a,b): a/b if b else float('inf'), zip(results['dram.total-access-latency'], results['dram.accesses']))

  if 'dram-datamovement-queue.num-cacheline-requests' in results and sum(results['dram-datamovement-queue.num-requests']) > 0:
    # New combined partition queues implementation
    results['dram.page_queue_avgdelay'] = map(lambda (a,b): a/b if b else float('inf'), zip(results['dram-datamovement-queue.total-page-queue-delay'], results['dram-datamovement-queue.num-page-requests']))
    if sum(results['dram-datamovement-queue.num-cacheline-requests']) > 0:
      results['dram.cacheline_queue_avgdelay'] = map(lambda (a,b): a/b if b else float('inf'), zip(results['dram-datamovement-queue.total-cacheline-queue-delay'], results['dram-datamovement-queue.num-cacheline-requests']))
    results['dram.both_queues_total_avgdelay'] = map(lambda (a,b,c): (a+b)/c if c else float('inf'), zip(results['dram-datamovement-queue.total-page-queue-delay'], results['dram-datamovement-queue.total-cacheline-queue-delay'], results['dram-datamovement-queue.num-requests']))
    
    if 'dram-datamovement-queue.max-effective-bandwidth-ps' in results and sum(results['dram-datamovement-queue.max-effective-bandwidth-ps']) > 0:
      results['dram.both_queues_total_max_effective_bandwidth'] = map(lambda (a,b): 1000*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue.max-effective-bandwidth-bytes'], results['dram-datamovement-queue.max-effective-bandwidth-ps']))
    if 'dram-datamovement-queue.page-max-effective-bandwidth-ps' in results and sum(results['dram-datamovement-queue.page-max-effective-bandwidth-ps']) > 0:
      results['dram.page_queue_max_effective_bandwidth'] = map(lambda (a,b): 1000*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue.page-max-effective-bandwidth-bytes'], results['dram-datamovement-queue.page-max-effective-bandwidth-ps']))
    if 'dram-datamovement-queue.cacheline-max-effective-bandwidth-ps' in results and sum(results['dram-datamovement-queue.cacheline-max-effective-bandwidth-ps']) > 0:
      results['dram.cacheline_queue_max_effective_bandwidth'] = map(lambda (a,b): 1000*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue.cacheline-max-effective-bandwidth-bytes'], results['dram-datamovement-queue.cacheline-max-effective-bandwidth-ps']))
  
    if 'dram-datamovement-queue.total-page-utilization-injected-time' in results:
      results['dram.page_queue_avg_injected_time'] = map(lambda (a,b): a/b if b else float('inf'), zip(results['dram-datamovement-queue.total-page-utilization-injected-time'], results['dram-datamovement-queue.num-page-requests']))
    if 'dram-datamovement-queue.total-cacheline-utilization-injected-time' in results and sum(results['dram-datamovement-queue.num-cacheline-requests']) > 0:
      results['dram.cacheline_queue_avg_injected_time'] = map(lambda (a,b): a/b if b else float('inf'), zip(results['dram-datamovement-queue.total-cacheline-utilization-injected-time'], results['dram-datamovement-queue.num-cacheline-requests']))
    
    if 'dram-datamovement-queue.num-cacheline-requests-capped-by-window-size' in results and sum(results['dram-datamovement-queue.num-requests']) > 0:
      results['dram.remotequeuemodel_datamovement_percent_capped_by_window_size'] = map(lambda (a,b): 100*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue.num-page-requests-capped-by-window-size'], results['dram-datamovement-queue.num-page-requests']))
      results['dram.remotequeuemodel_datamovement_percent_queue_full'] = map(lambda (a,b): 100*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue.num-page-requests-queue-full'], results['dram-datamovement-queue.num-page-requests']))
      results['dram.remotequeuemodel_datamovement2_percent_capped_by_window_size'] = map(lambda (a,b): 100*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue.num-cacheline-requests-capped-by-window-size'], results['dram-datamovement-queue.num-cacheline-requests']))
      results['dram.remotequeuemodel_datamovement2_percent_queue_full'] = map(lambda (a,b): 100*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue.num-cacheline-requests-queue-full'], results['dram-datamovement-queue.num-cacheline-requests']))

    elif 'dram-datamovement-queue.num-requests-capped-by-window-size' in results and sum(results['dram-datamovement-queue.num-requests']) > 0:
      results['dram.remotequeuemodel_datamovement_percent_capped_by_window_size'] = map(lambda (a,b): 100*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue.num-requests-capped-by-window-size'], results['dram-datamovement-queue.num-requests']))
      results['dram.remotequeuemodel_datamovement_percent_queue_full'] = map(lambda (a,b): 100*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue.num-requests-queue-full'], results['dram-datamovement-queue.num-requests']))
      results['dram.remotequeuemodel_datamovement_percent_capped_by_custom_cap'] = map(lambda (a,b): 100*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue.num-requests-capped-by-custom-cap'], results['dram-datamovement-queue.num-requests']))

    if 'dram-datamovement-queue.total-cacheline-queue-utilization-during-page-requests-numerator' in results:
      results['dram.avg_cacheline_queue_utilization_during_page_requests'] = map(lambda (a,b,c): float(a)/b /c if b and c else float('inf'), zip(results['dram-datamovement-queue.total-cacheline-queue-utilization-during-page-requests-numerator'], results['dram-datamovement-queue.total-cacheline-queue-utilization-during-page-requests-denominator'], results['dram-datamovement-queue.num-page-requests']))
    if 'dram-datamovement-queue.total-page-queue-utilization-during-cacheline-requests-numerator' in results:
      results['dram.avg_page_queue_utilization_during_cacheline_requests'] = map(lambda (a,b,c): float(a)/b /c if b and c else float('inf'), zip(results['dram-datamovement-queue.total-page-queue-utilization-during-cacheline-requests-numerator'], results['dram-datamovement-queue.total-page-queue-utilization-during-cacheline-requests-denominator'], results['dram-datamovement-queue.num-cacheline-requests']))

    if 'dram-datamovement-queue.total-cacheline-queue-utilization-during-page-no-effect-numerator' in results:
      results['dram.avg_cacheline_queue_utilization_during_page_no_effect'] = map(lambda (a,b,c): float(a)/b /c if b and c else float('inf'), zip(results['dram-datamovement-queue.total-cacheline-queue-utilization-during-page-no-effect-numerator'], results['dram-datamovement-queue.total-cacheline-queue-utilization-during-page-no-effect-denominator'], results['dram-datamovement-queue.num-no-effect-page-requests']))
    if 'dram-datamovement-queue.total-page-queue-utilization-during-cacheline-no-effect-numerator' in results:
      results['dram.avg_page_queue_utilization_during_cacheline_no_effect'] = map(lambda (a,b,c): float(a)/b /c if b and c else float('inf'), zip(results['dram-datamovement-queue.total-page-queue-utilization-during-cacheline-no-effect-numerator'], results['dram-datamovement-queue.total-page-queue-utilization-during-cacheline-no-effect-denominator'], results['dram-datamovement-queue.num-no-effect-cacheline-requests']))

    if 'dram-datamovement-queue.num-requests-cacheline-inserted-ahead-of-inflight-pages' in results:
      results['dram.cacheline_request_percent_inserted_ahead_of_inflight_pages'] = map(lambda (a,b): 100*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue.num-requests-cacheline-inserted-ahead-of-inflight-pages'], results['dram-datamovement-queue.num-cacheline-requests']))
    if 'dram-datamovement-queue.num-no-effect-requests-cacheline-inserted-ahead-of-inflight-pages' in results:
      results['dram.cacheline_no_effect_percent_inserted_ahead_of_inflight_pages'] = map(lambda (a,b): 100*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue.num-no-effect-requests-cacheline-inserted-ahead-of-inflight-pages'], results['dram-datamovement-queue.num-no-effect-cacheline-requests']))

  else:
    if 'dram-datamovement-queue.num-requests' in results and sum(results['dram-datamovement-queue.num-requests']) > 0:
      results['dram.page_queue_avgdelay'] = map(lambda (a,b): a/b if b else float('inf'), zip(results['dram-datamovement-queue.total-queue-delay'], results['dram-datamovement-queue.num-requests']))
    if 'dram-datamovement-queue-2.num-requests' in results and sum(results['dram-datamovement-queue-2.num-requests']) > 0:
      results['dram.cacheline_queue_avgdelay'] = map(lambda (a,b): a/b if b else float('inf'), zip(results['dram-datamovement-queue-2.total-queue-delay'], results['dram-datamovement-queue-2.num-requests']))
    
    if 'dram-datamovement-queue.max-effective-bandwidth-ps' in results and sum(results['dram-datamovement-queue.max-effective-bandwidth-ps']) > 0:
      results['dram.page_queue_max_effective_bandwidth'] = map(lambda (a,b): 1000*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue.max-effective-bandwidth-bytes'], results['dram-datamovement-queue.max-effective-bandwidth-ps']))
    if 'dram-datamovement-queue-2.max-effective-bandwidth-ps' in results and sum(results['dram-datamovement-queue-2.max-effective-bandwidth-ps']) > 0:
      results['dram.cacheline_queue_max_effective_bandwidth'] = map(lambda (a,b): 1000*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue-2.max-effective-bandwidth-bytes'], results['dram-datamovement-queue-2.max-effective-bandwidth-ps']))

    if 'dram-datamovement-queue.num-requests-capped-by-window-size' in results and sum(results['dram-datamovement-queue.num-requests']) > 0:
      results['dram.remotequeuemodel_datamovement_percent_capped_by_window_size'] = map(lambda (a,b): 100*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue.num-requests-capped-by-window-size'], results['dram-datamovement-queue.num-requests']))
      results['dram.remotequeuemodel_datamovement_percent_queue_full'] = map(lambda (a,b): 100*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue.num-requests-queue-full'], results['dram-datamovement-queue.num-requests']))
      results['dram.remotequeuemodel_datamovement_percent_capped_by_custom_cap'] = map(lambda (a,b): 100*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue.num-requests-capped-by-custom-cap'], results['dram-datamovement-queue.num-requests']))
    if 'dram-datamovement-queue-2.num-requests-capped-by-window-size' in results and sum(results['dram-datamovement-queue-2.num-requests']) > 0:
      results['dram.remotequeuemodel_datamovement2_percent_capped_by_window_size'] = map(lambda (a,b): 100*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue-2.num-requests-capped-by-window-size'], results['dram-datamovement-queue-2.num-requests']))
      results['dram.remotequeuemodel_datamovement2_percent_queue_full'] = map(lambda (a,b): 100*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue-2.num-requests-queue-full'], results['dram-datamovement-queue-2.num-requests']))
      results['dram.remotequeuemodel_datamovement2_percent_capped_by_custom_cap'] = map(lambda (a,b): 100*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue-2.num-requests-capped-by-custom-cap'], results['dram-datamovement-queue-2.num-requests']))

  if 'dram.local-dram-sum-dirty-write-buffer-size' in results:
    results['dram.local-avg-dirty-write-buffer-size'] = map(lambda (a,b): a/b if b else float('inf'), zip(results['dram.local-dram-sum-dirty-write-buffer-size'], results['dram.accesses']))
  if 'dram.sum-simultaneous-inflight-cachelines-total' in results:
    results['dram.avg_simultaneous_inflight_cachelines_reads'] = map(lambda (a,b): a/b if b else float('inf'), zip(results['dram.sum-simultaneous-inflight-cachelines-reads'], results['dram.accesses']))
    results['dram.avg_simultaneous_inflight_cachelines_writes'] = map(lambda (a,b): a/b if b else float('inf'), zip(results['dram.sum-simultaneous-inflight-cachelines-writes'], results['dram.accesses']))
    results['dram.avg_simultaneous_inflight_cachelines_total'] = map(lambda (a,b): a/b if b else float('inf'), zip(results['dram.sum-simultaneous-inflight-cachelines-total'], results['dram.accesses']))


  # Compression
  bytes_saved = results['compression.bytes-saved'][0] if 'compression.bytes-saved' in results else 0
  cacheline_bytes_saved = results['compression.cacheline-bytes-saved'][0] if 'compression.cacheline-bytes-saved' in results else 0
  if bytes_saved != 0:
    data_moves = results['dram.page-moves'][0]
    total_compression_latency = results['compression.total-compression-latency'][0]
    total_decompression_latency = results['compression.total-decompression-latency'][0]

    gran_size = 64 if config['perf_model/dram/remote_use_cacheline_granularity'] == "true" else int(config['perf_model/dram/page_size'])
    results['compression.avg-compression-ratio'] = [float((data_moves * gran_size)) / float(((data_moves * gran_size) - bytes_saved))] + [0]*(ncores - 1)
    results['compression.avg-compression-latency'] = [total_compression_latency / data_moves] + [0]*(ncores - 1)
    results['compression.avg-decompression-latency'] = [total_decompression_latency / data_moves] + [0]*(ncores - 1)

    if cacheline_bytes_saved != 0:
      data_moves = results['dram.remote-reads'][0] + results['dram.remote-writes'][0]
      total_cacheline_compression_latency = results['compression.total-cacheline-compression-latency'][0]
      total_cacheline_decompression_latency = results['compression.total-cacheline-decompression-latency'][0]

      gran_size = 64
      results['compression.avg-cacheline-compression-ratio'] = [float((data_moves * gran_size)) / float(((data_moves * gran_size) - cacheline_bytes_saved))] + [0]*(ncores - 1)
      results['compression.avg-cacheline-compression-latency'] = [total_cacheline_compression_latency / data_moves] + [0]*(ncores - 1)
      results['compression.avg-cacheline-decompression-latency'] = [total_cacheline_decompression_latency / data_moves] + [0]*(ncores - 1)

    if 'compression.adaptive-low-compression-count' in results:
      low_bytes_saved = results['compression.adaptive-low-bytes-saved'][0]
      low_total_compression_latency = results['compression.adaptive-low-total-compression-latency'][0]
      low_total_decompression_latency = results['compression.adaptive-low-total-decompression-latency'][0]
      low_data_moves = results['compression.adaptive-low-compression-count'][0]

      results['compression.adaptive-low-avg-compression-ratio'] = [float((low_data_moves * gran_size)) / float(((low_data_moves * gran_size) - low_bytes_saved))] + [0]*(ncores - 1) if low_data_moves != 0 else [0] + [0]*(ncores - 1)
      results['compression.adaptive-low-avg-compression-latency'] = [low_total_compression_latency / low_data_moves] + [0]*(ncores - 1) if low_data_moves > 0 else [0] + [0]*(ncores - 1)
      results['compression.adaptive-low-avg-decompression-latency'] = [low_total_decompression_latency / low_data_moves] + [0]*(ncores - 1) if low_data_moves > 0 else [0] + [0]*(ncores - 1)

      high_bytes_saved = results['compression.adaptive-high-bytes-saved'][0]
      high_total_compression_latency = results['compression.adaptive-high-total-compression-latency'][0]
      high_total_decompression_latency = results['compression.adaptive-high-total-decompression-latency'][0]
      high_data_moves = results['compression.adaptive-high-compression-count'][0]

      results['compression.adaptive-high-avg-compression-ratio'] = [float((high_data_moves * gran_size)) / float(((high_data_moves * gran_size) - high_bytes_saved))] + [0]*(ncores - 1) if high_data_moves != 0 else [0] + [0]*(ncores - 1)
      results['compression.adaptive-high-avg-compression-latency'] = [high_total_compression_latency / high_data_moves] + [0]*(ncores - 1) if high_data_moves > 0 else [0] + [0]*(ncores - 1)
      results['compression.adaptive-high-avg-decompression-latency'] = [high_total_decompression_latency / high_data_moves] + [0]*(ncores - 1) if high_data_moves > 0 else [0] + [0]*(ncores - 1)

      results['compression.adaptive-low-compression-percentage'] = [(float(low_data_moves) / float(low_data_moves + high_data_moves)) * 100] + [0]*(ncores - 1)
      results['compression.adaptive-high-compression-percentage'] = [(float(high_data_moves) / float(low_data_moves + high_data_moves)) * 100] + [0]*(ncores - 1)

    # print("bytes_saved", bytes_saved)
    # print("data moves", data_moves)
    # print("avg compression ratio", results['compression.avg-compression-ratio'])
    # print("avg compression latency", results['compression.avg-compression-latency'])
    # print("avg decompression latency", results['compression.avg-decompression-latency'])

    # print("total compression latency", (results['compression.total-compression-latency'][0] / 10**6))
    # print("avg compression latency", (results['compression.total-compression-latency'][0] / 10**6) / data_moves)

  template += [
    ('DRAM summary', '', ''),
    ('  num dram accesses', 'dram.accesses', str),
    ('    num dram reads', 'dram.reads', str),
    ('      num local reads', 'dram.local-reads', str),
    ('        num local reads remote origin', 'dram.local-reads-remote-origin', str),  
    ('      num remote reads', 'dram.remote-reads', str),
    ('    num dram writes', 'dram.writes', str),
    ('      num local writes', 'dram.local-writes', str),
    ('        num local writes remote origin', 'dram.local-writes-remote-origin', str),  
    ('      num remote writes', 'dram.remote-writes', str),
    # ('    num dram reads', 'dram.readwrite-reads', str),
    # ('    num dram writes', 'dram.readwrite-writes', str),
    ('    local avg inflight dirty write buffer size', 'dram.local-avg-dirty-write-buffer-size', str),
    ('    local max inflight dirty write buffer size', 'dram.local-dram-max-dirty-write-buffer-size', str),
    ('    avg simultaneous inflight cachelines - total', 'dram.avg_simultaneous_inflight_cachelines_total', str),
    ('    max simultaneous inflight cachelines - total', 'dram.max-simultaneous-inflight-cachelines-total', str),
    ('    avg simultaneous inflight cachelines - reads', 'dram.avg_simultaneous_inflight_cachelines_reads', str),
    ('    max simultaneous inflight cachelines - reads', 'dram.max-simultaneous-inflight-cachelines-reads', str),
    ('    avg simultaneous inflight cachelines - writes', 'dram.avg_simultaneous_inflight_cachelines_writes', str),
    ('    max simultaneous inflight cachelines - writes', 'dram.max-simultaneous-inflight-cachelines-writes', str),
    ('  average dram access latency (ns)', 'dram.avglatency', format_ns(2)),
    ('    local dram avg access latency (ns)', 'dram.localavglatency', format_ns(2)),
    ('      local dram avg hardware latency (ns)', 'dram.localavghardwarelatency', format_ns(2)),
    ('        local dram avg HW processing time (ns)', 'dram.localavghardwarelatency_processing_time', format_ns(2)),
    ('        local dram avg HW queue delay (ns)', 'dram.localavghardwarelatency_queue_delay', format_ns(2)),
    ('    local dram avg hardware write latency: pages (ns)', 'dram.localavghardwarewritelatency_pages', format_ns(2)),
    ('    remote dram avg access latency (ns)', 'dram.remoteavglatency', format_ns(2)),
    ('      remote dram avg hardware latency: cachelines (ns)', 'dram.remoteavghardwarelatency_cachelines', format_ns(2)),
    ('        remote dram avg HW processing time: cachelines (ns)', 'dram.remoteavghardwarelatency_cachelines_processing_time', format_ns(2)),
    ('        remote dram avg HW queue delay: cachelines (ns)', 'dram.remoteavghardwarelatency_cachelines_queue_delay', format_ns(2)),
    ('      remote dram avg hardware latency: pages (ns)', 'dram.remoteavghardwarelatency_pages', format_ns(2)),
    ('        remote dram avg HW processing time: pages (ns)', 'dram.remoteavghardwarelatency_pages_processing_time', format_ns(2)),
    ('        remote dram avg HW queue delay: pages (ns)', 'dram.remoteavghardwarelatency_pages_queue_delay', format_ns(2)),
    ('      avg remote-to-local datamovement latency (ns)', 'dram.remote_datamovement_avglatency', format_ns(2)),
    ('        avg remote-to-local network processing time: cachelines (ns)', 'dram.avg_remotetolocal_cacheline_network_processing_time', format_ns(2)),
    ('        avg remote-to-local network queue delay: cachelines (ns)', 'dram.avg_remotetolocal_cacheline_network_queue_delay', format_ns(2)),
    ('        avg remote-to-local network processing time: pages (ns)', 'dram.avg_remotetolocal_page_network_processing_time', format_ns(2)),
    ('        avg remote-to-local network queue delay: pages (ns)', 'dram.avg_remotetolocal_page_network_queue_delay', format_ns(2)),
    ('      remote avg pagemove global time much larger (ns)', 'dram.pagemovement_avg_globaltime_much_larger', format_ns(2)),
    ('      remote pagemove global time much larger count', 'dram.page-movement-num-global-time-much-larger', str),
    ('      remote both queues total avg access latency (ns)', 'dram.both_queues_total_avgdelay', format_ns(2)),
    ('        remote datamovement queue model avg access latency (ns)', 'dram.page_queue_avgdelay', format_ns(2)),
    ('        remote datamovement2 queue model avg access latency (ns)', 'dram.cacheline_queue_avgdelay', format_ns(2)),
    ('  num page moves', 'dram.page-moves', str),
    ('  num page prefetches', 'dram.page-prefetches', str),
    ('  page prefetch not done due to full queue', 'dram.queue-full-page-prefetch-not-done', str),
    ('  page prefetch not done since page local already', 'dram.page-local-already-page-prefetch-not-done', str),
    ('  page prefetch not done since page uninitialized/not seen yet', 'dram.page-not-initialized-page-prefetch-not-done', str),
    ('  num inflight hits', 'dram.inflight-hits', str),
    ('  num writeback pages', 'dram.writeback-pages', str),
    ('  num local evictions', 'dram.local-evictions', str),
    ('  num pages disturbed by extra traffic', 'dram.extra-traffic', str),
    ('  num redundant moves total', 'dram.redundant-moves', str),
    ('    num redundant moves type1', 'dram.redundant-moves-type1', str),
    ('      num type1 cacheline slower than page', 'dram.pq-cacheline-slower-than-page', str),
    ('    num redundant moves type2', 'dram.redundant-moves-type2', str),
    ('      num type2 cancelled due to already inflight', 'dram.already-inflight-redundant-moves-type2-cancelled', str),
    ('      num type2 cancelled due to full queue', 'dram.queue-full-redundant-moves-type2-cancelled', str),
    ('      num type2 cacheline slower than page arrival', 'dram.cacheline-slower-than-inflight-page-arrival', str),
    ('  max simultaneous # inflight pages, both directions (bufferspace)', 'dram.max-total-bufferspace', str),
    ('  max simultaneous # inflight remote->local pages (bufferspace)', 'dram.max-inflight-bufferspace', str),
    ('  max simultaneous # inflight extra remote->local pages', 'dram.max-inflight-extra-bufferspace', str),
    ('  max simultaneous # inflight local->remote evicted pages (bufferspace)', 'dram.max-inflightevicted-bufferspace', str),
    ('  remote page move cancelled due to full bufferspace', 'dram.bufferspace-full-move-page-cancelled', str),
    ('    remote page move full bufferspace yet moved with penalty', 'dram.bufferspace-full-page-still-moved', str),
    ('  remote page move cancelled due to full queue', 'dram.queue-full-move-page-cancelled', str),
    ('    remote page move full queue yet moved with penalty', 'dram.queue-full-page-still-moved', str),
    ('  remote page move cancelled due to rmode5', 'dram.rmode5-move-page-cancelled', str),
    ('  remote page moved due to exceeding threshold in rmode5', 'dram.rmode5-page-moved-due-to-threshold', str),
  ('    remote cacheline move full queue, moved with penalty', 'dram.queue-full-cacheline-still-moved', str),
  ]


  if 'dram.total-read-queueing-delay' in results:
    results['dram.avgqueueread'] = map(lambda (a,b): a/(b or 1), zip(results['dram.total-read-queueing-delay'], results['dram.reads']))
    results['dram.avgqueuewrite'] = map(lambda (a,b): a/(b or 1), zip(results['dram.total-write-queueing-delay'], results['dram.writes']))
    template.append(('  average dram read queueing delay', 'dram.avgqueueread', format_ns(2)))
    template.append(('  average dram write queueing delay', 'dram.avgqueuewrite', format_ns(2)))
  else:
    results['dram.avgqueue'] = map(lambda (a,b): a/(b or 1), zip(results.get('dram.total-queueing-delay', [0]*ncores), results['dram.accesses']))
    template.append(('  average dram queueing delay', 'dram.avgqueue', format_ns(2)))
  if 'dram-queue.total-time-used' in results:
    results['dram.bandwidth'] = map(lambda a: 100*a/time0 if time0 else float('inf'), results['dram-queue.total-time-used'])
    template.append(('  average dram bandwidth utilization', 'dram.bandwidth', lambda v: '%.2f%%' % v))

  if "dram.bw-utilization-decile-0" in results:
    total_count = results["dram.accesses"][0]
    end_decile = 9
    if "dram.bw-utilization-decile-10" in results:
      end_decile = 10
    for i in range(end_decile + 1):  # the last number is end_decile
      decile_count = results["dram.bw-utilization-decile-{}".format(i)][0]
      percentage = ((float)(decile_count) / (float)(total_count)) * 100
      results["dram.bw-utilization-decile-percentage-{}".format(i)] = [percentage] + [0]*(ncores - 1)
      template.append(('  bw utilization % decile {}'.format(i), "dram.bw-utilization-decile-percentage-{}".format(i), str))

  results['dram.avg-bw-utilization'] =  map(lambda (a,b): (a/100000)/b if b else float('inf'), zip(results['dram.total-bw-utilization-sum'], results['dram.accesses']))
  template.append(('avg bw utilization', 'dram.avg-bw-utilization', str))

  # Compression
  if bytes_saved != 0:
    template.append(('Compression', '', ''))
    template += [
      ('  bytes saved', 'compression.bytes-saved', str),
      ('  avg compression ratio', 'compression.avg-compression-ratio', str),
      ('  avg compression latency(ns)', 'compression.avg-compression-latency', format_ns(2)),
      ('  avg decompression latency(ns)', 'compression.avg-decompression-latency', format_ns(2)),
      # ('  overflowed_pages', 'compression.num_overflowed_pages', str),
    ]

    if 'compression.num_overflowed_pages' in results:
      template += [('  overflowed_pages', 'compression.num_overflowed_pages', str),]

  if cacheline_bytes_saved != 0:
    template += [
      ('  cacheline bytes saved', 'compression.cacheline-bytes-saved', str),
      ('  avg cacheline compression ratio', 'compression.avg-cacheline-compression-ratio', str),
      ('  avg cacheline compression latency(ns)', 'compression.avg-cacheline-compression-latency', format_ns(2)),
      ('  avg cacheline decompression latency(ns)', 'compression.avg-cacheline-decompression-latency', format_ns(2)),
    ]

  max_dict_size = results['compression.max_dictionary_size'][0] if 'compression.max_dictionary_size' in results else 0
  if max_dict_size != 0:
    template += [
            ('  avg_dictionary_size', 'compression.avg_dictionary_size', str),
            ('  max_dictionary_size', 'compression.max_dictionary_size', str),
            ('  avg_max_dictionary_entry', 'compression.avg_max_dictionary_entry', str),
            ('  avg_avg_dictionary_entry', 'compression.avg_avg_dictionary_entry', str),
            ('  max_dictionary_entry', 'compression.max_dictionary_entry', str),
            # ('  overflowed_pages', 'compression.num_overflowed_pages', str),
        ]

  # BDI and LZBDI Stats
  bdi_total_compressed = results['compression.bdi_total_compressed'][0] if 'compression.bdi_total_compressed' in results else 0
  if bdi_total_compressed != 0:
    template += [
      ('  bdi_successful_compression', 'compression.bdi_total_compressed', str)]
    for i in range(0, 16): 
      bdi_option = float(results['compression.bdi_usage_option-{}'.format(i)][0]) / float(bdi_total_compressed) * 100
      bdi_option_format = "{:.2f}".format(bdi_option)
      results['compression.bdi_usage_option-{}'.format(i)] = [bdi_option_format] + [0]*(ncores - 1)
      template.append(('  bdi_usage(%)_option-{}'.format(i), 'compression.bdi_usage_option-{}'.format(i), str))
    for i in range(0, 16): 
      template.append(('  bdi_bytes_saved_option-{}'.format(i), 'compression.bdi_bytes_saved_option-{}'.format(i), str))

  # Hybrid FPCBDI Stats
  fpcbdi_total_compressed = results['compression.fpcbdi_total_compressed'][0] if 'compression.fpcbdi_total_compressed' in results else 0
  if fpcbdi_total_compressed != 0:
    template += [
      ('  fpcbdi_successful_compression', 'compression.fpcbdi_total_compressed', str)]
    for i in range(0, 24): 
      fpcbdi_option = float(results['compression.fpcbdi_usage_option-{}'.format(i)][0]) / float(fpcbdi_total_compressed) * 100
      fpcbdi_option_format = "{:.2f}".format(fpcbdi_option)
      results['compression.fpcbdi_usage_option-{}'.format(i)] = [fpcbdi_option_format] + [0]*(ncores - 1)
      template.append(('  fpcbdi_usage(%)_option-{}'.format(i), 'compression.fpcbdi_usage_option-{}'.format(i), str))
    for i in range(0, 24): 
      template.append(('  fpcbdi_bytes_saved_option-{}'.format(i), 'compression.fpcbdi_bytes_saved_option-{}'.format(i), str))


  # FPC Stats
  fpc_total_compressed = results['compression.fpc_total_compressed'][0] if 'compression.fpc_total_compressed' in results else 0
  if fpc_total_compressed != 0:
    template += [
      ('  fpc_successful_compression', 'compression.fpc_total_compressed', str)]
    for i in range(7): 
      fpc_pattern = float(results['compression.fpc_usage_pattern-{}'.format(i)][0]) / float(fpc_total_compressed) * 100
      fpc_pattern_format = "{:.2f}".format(fpc_pattern)
      results['compression.fpc_usage_pattern-{}'.format(i)] = [fpc_pattern_format] + [0]*(ncores - 1)
      template.append(('  fpc_usage(%)_pattern-{}'.format(i), 'compression.fpc_usage_pattern-{}'.format(i), str))
    for i in range(7): 
      template.append(('  fpc_bytes_saved_pattern-{}'.format(i), 'compression.fpc_bytes_saved_pattern-{}'.format(i), str))

  # LZ Stats
  lz_compression = results['compression.avg_dictionary_size'][0] if 'compression.avg_dictionary_size' in results else 0
  if lz_compression != 0:
    template.append(('  Dictionary table stats (count within dictionary_size, entire ROI)', '', ''))
    for i in range(10, 101, 10):  # 10, 20, ..., 100
        template.append(('    {}% percentile - dictionary_size'.format(i), 'compression.lz-dictsize-count-p{}'.format(i), str))
        template.append(('    {}% percentile - total_bytes_saved'.format(i), 'compression.lz-bytes_saved-count-p{}'.format(i), str))
        template.append(('    {}% percentile - accesses'.format(i), 'compression.lz-accesses-count-p{}'.format(i), str))
        template.append(('    {}% percentile - max_entry_bytes'.format(i), 'compression.lz-max_entry_bytes-count-p{}'.format(i), str))

  # Adaptive Stats
  if 'compression.adaptive-low-compression-count' in results:
    template += [
      ('  adaptive low compression %', 'compression.adaptive-low-compression-percentage', str),
      ('  adaptive low compression count', 'compression.adaptive-low-compression-count', str),
      ('  adaptive low bytes saved', 'compression.adaptive-low-bytes-saved', str),
      ('  adaptive low avg compression ratio', 'compression.adaptive-low-avg-compression-ratio', str),
      ('  adaptive low avg compression latency(ns)', 'compression.adaptive-low-avg-compression-latency', format_ns(2)),
      ('  adaptive low avg decompression latency(ns)', 'compression.adaptive-low-avg-decompression-latency', format_ns(2)),

      ('  adaptive high compression %', 'compression.adaptive-high-compression-percentage', str),
      ('  adaptive high compression count', 'compression.adaptive-high-compression-count', str),
      ('  adaptive high bytes saved', 'compression.adaptive-high-bytes-saved', str),
      ('  adaptive high avg compression ratio', 'compression.adaptive-high-avg-compression-ratio', str),
      ('  adaptive high avg compression latency(ns)', 'compression.adaptive-high-avg-compression-latency', format_ns(2)),
      ('  adaptive high avg decompression latency(ns)', 'compression.adaptive-high-avg-decompression-latency', format_ns(2)),
    ]

  if "compression.adaptive-bw-utilization-decile-0" in results:
    total_count = results['dram.page-moves'][0]
    for i in range(10):
      decile_count = results["compression.adaptive-bw-utilization-decile-{}".format(i)][0]
      percentage = ((float)(decile_count) / (float)(total_count)) * 100 if total_count != 0 else 0
      results["compression.adaptive-bw-utilization-decile-percentage-{}".format(i)] = [percentage] + [0]*(ncores - 1)
      template.append(('  adaptive bw utilization % decile {}'.format(i), "compression.adaptive-bw-utilization-decile-percentage-{}".format(i), str))

  if 'dram-single-queue.num-requests' in results and sum(results['dram-single-queue.num-requests']) > 0:
    results['dram.single_local_queue_avgdelay'] = map(lambda (a,b): a/b if b else float('inf'), zip(results['dram-single-queue.total-queue-delay'], results['dram-single-queue.num-requests']))
  if 'dram-single-remote-queue.num-requests' in results and sum(results['dram-single-remote-queue.num-requests']) > 0:
    results['dram.single_remote_queue_avgdelay'] = map(lambda (a,b): a/b if b else float('inf'), zip(results['dram-single-remote-queue.total-queue-delay'], results['dram-single-remote-queue.num-requests']))

  # if 'dram.redundant-moves-temp1-time-savings' in results:
  template.extend([
      ('Experiment stats', '', ''),
      ('  DRAM access cost single local queue avg delay (ns)', 'dram.single_local_queue_avgdelay', format_ns(2)),
      ('  DRAM access cost remote queue avg delay (ns)', 'dram.single_remote_queue_avgdelay', format_ns(2)),
      ('  PQ=1 type1 time savings (ns)', 'dram.redundant-moves-type1-time-savings', format_ns(2)),
      ('  PQ=1 type2 time savings (ns)', 'dram.redundant-moves-type2-time-savings', format_ns(2)),
      # ('  PQ=1 page queue avg injected time (ns)', 'dram.page_queue_avg_injected_time', format_ns(2)),
      # ('  PQ=1 cacheline queue avg injected time (ns)', 'dram.cacheline_queue_avg_injected_time', format_ns(2)),
      # ('  PQ=1 max imbalanced page requests', 'dram-datamovement-queue.max-imbalanced-page-requests', str),
      # ('  PQ=1 max imbalanced cacheline requests', 'dram-datamovement-queue.max-imbalanced-cacheline-requests', str),
      # ('  PQ=1 page imbalanced decreased from window size', 'dram-datamovement-queue.page-imbalance-decreased-due-to-window-size', str),
      # ('  PQ=1 cacheline imbalanced decreased from window size', 'dram-datamovement-queue.cacheline-imbalance-decreased-due-to-window-size', str),
      ('  PQ idea page queue overflowed', 'dram-datamovement-queue.num-requests-page-queue-overflowed-to-cacheline-queue', str),
      ('  PQ idea cacheline queue overflowed', 'dram-datamovement-queue.num-requests-cacheline-queue-overflowed-to-page-queue', str),
      ('  PQ idea avg cacheline % util during page requests', 'dram-datamovement-queue.avg_cacheline_queue_utilization_during_page_requests', str),
      ('  PQ idea avg page % util during cacheline requests', 'dram-datamovement-queue.avg_page_queue_utilization_during_cacheline_requests', str),
      ('  PQ idea avg cacheline % util during page no-effect requests', 'dram-datamovement-queue.avg_cacheline_queue_utilization_during_page_no_effect', str),
      ('  PQ idea avg page % util during cacheline no-effect requests', 'dram-datamovement-queue.avg_page_queue_utilization_during_cacheline_no_effect', str),
      ('  PQ idea % cacheline inserted ahead of inflight pages', 'dram.cacheline_request_percent_inserted_ahead_of_inflight_pages', format_float(2)),
      ('  PQ idea % cacheline no effect ahead of inflight pages', 'dram.cacheline_no_effect_percent_inserted_ahead_of_inflight_pages', format_float(2)),
      ('  PQ idea inflight page delayed', 'dram.inflight-page-delayed', str),
      ('  PQ idea inflight page total delayed time (ns)', 'dram.inflight-page-total-delay-time', format_ns(2)),
      ('  PQ idea cacheline requests saved time (ns)', 'dram-datamovement-queue.total-cacheline-queue-delay-saved', format_ns(2)),
      ('  Dynamic cl ratio: min runtime cl queue fraction', 'dram.min-runtime-cl-queue-fraction', lambda v: ('%%.%uf' % 4) % (v/10000.0)),
      ('  Dynamic cl ratio: max runtime cl queue fraction', 'dram.max-runtime-cl-queue-fraction', lambda v: ('%%.%uf' % 4) % (v/10000.0)),
      ('  Dynamic cl ratio: num cl queue fraction increased', 'dram.num-cl-queue-fraction-increased', str),
      ('  Dynamic cl ratio: num cl queue fraction decreased', 'dram.num-cl-queue-fraction-decreased', str),
      ('  num unique pages accessed', 'dram.unique-pages-accessed', str),
      ('  remote datamovement max effective bandwidth (GB/s)', 'dram.both_queues_total_max_effective_bandwidth', format_float(4)),
      ('    page queue max effective bandwidth (GB/s)', 'dram.page_queue_max_effective_bandwidth', format_float(4)),
      ('    cacheline queue max effective bandwidth (GB/s)', 'dram.cacheline_queue_max_effective_bandwidth', format_float(4)),
      ('  remote datamovement % capped by window size', 'dram.remotequeuemodel_datamovement_percent_capped_by_window_size', format_float(2)),
      ('  remote datamovement % queue utilization full', 'dram.remotequeuemodel_datamovement_percent_queue_full', format_float(2)),
      ('  remote datamovement % queue capped by custom cap', 'dram.remotequeuemodel_datamovement_percent_capped_by_custom_cap', format_float(2)),
      ('  remote datamovement2 % capped by window size', 'dram.remotequeuemodel_datamovement2_percent_capped_by_window_size', format_float(2)),
      ('  remote datamovement2 % queue utilization full', 'dram.remotequeuemodel_datamovement2_percent_queue_full', format_float(2)),
      ('  remote datamovement2 % queue capped by custom cap', 'dram.remotequeuemodel_datamovement2_percent_capped_by_custom_cap', format_float(2)),
      ('  ideal page throttling: num swaps inflight', 'dram.ideal-page-throttling-num-swaps-inflight', str),
      ('  ideal page throttling: num swaps non-inflight', 'dram.ideal-page-throttling-num-swaps-non-inflight', str),
      ('  ideal page throttling: num swaps unavailable', 'dram.ideal-page-throttling-num-swap-unavailable', str),
  ])

  # if '' in results:
  template.append(('Page locality stats (count within phys_page, entire ROI)', '', ''))
  for i in range(10, 101, 10):  # 10, 20, ..., 100
    template.append(('  {}% percentile'.format(i), 'dram.page-access-count-p{}'.format(i), str))

  if 'ddr.page-hits' in results:
    template.extend([
        ('DDR', '', ''),
        ('  DDR page hits', 'ddr.page-hits' , str),
        ('  DDR page misses', 'ddr.page-misses' , str),
        ('  DDR page empty', 'ddr.page-empty' , str),
        ('  DDR page closing', 'ddr.page-closing' , str),
      ])

  if 'L1-D.loads-where-dram-local' in results:
    results['L1-D.loads-where-dram'] = map(sum, zip(results['L1-D.loads-where-dram-local'], results['L1-D.loads-where-dram-remote']))
    results['L1-D.stores-where-dram'] = map(sum, zip(results['L1-D.stores-where-dram-local'], results['L1-D.stores-where-dram-remote']))
    template.extend([
        ('Coherency Traffic', '', ''),
        ('  num loads from dram', 'L1-D.loads-where-dram' , str),
        #('  num stores from dram', 'L1-D.stores-where-dram' , str),
        ('  num loads from dram cache', 'L1-D.loads-where-dram-cache' , str),
        #('  num stores from dram cache', 'L1-D.stores-where-dram-cache' , str),
        ('  num loads from remote cache', 'L1-D.loads-where-cache-remote' , str),
        #('  num stores from remote cache', 'L1-D.stores-where-cache-remote' , str),
      ])

  lines = []
  lines.append([''] + [ 'Core %u' % i for i in range(ncores) ])

  for title, name, func in template:
    line = [ title ]
    if name and name in results:
      for core in range(ncores):
        line.append(' '+func(results[name][core]))
    else:
      line += [''] * ncores
    lines.append(line)


  widths = [ max(10, max([ len(l[i]) for l in lines ])) for i in range(len(lines[0])) ]
  for j, line in enumerate(lines):
    output.write(' | '.join([ ('%%%s%us' % ((j==0 or i==0) and '-' or '', widths[i])) % line[i] for i in range(len(line)) ]) + '\n')



if __name__ == '__main__':
  def usage():
    print 'Usage:', sys.argv[0], '[-h (help)] [--partial <section-start>:<section-end> (default: roi-begin:roi-end)] [-d <resultsdir (default: .)>]'

  jobid = 0
  resultsdir = '.'
  partial = None

  try:
    opts, args = getopt.getopt(sys.argv[1:], "hj:d:", [ 'partial=' ])
  except getopt.GetoptError, e:
    print e
    usage()
    sys.exit()
  for o, a in opts:
    if o == '-h':
      usage()
      sys.exit()
    if o == '-d':
      resultsdir = a
    if o == '-j':
      jobid = long(a)
    if o == '--partial':
      if ':' not in a:
        sys.stderr.write('--partial=<from>:<to>\n')
        usage()
      partial = a.split(':')

  if args:
    usage()
    sys.exit(-1)

  generate_simout(jobid = jobid, resultsdir = resultsdir, partial = partial)
