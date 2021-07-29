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
    results['dram.remoteavglatency'] = map(lambda (a,b): a/b if b else float('inf'), zip(results['dram.total-remote-access-latency'], results['dram.remote-accesses']))
  results['dram.avglatency'] = map(lambda (a,b): a/b if b else float('inf'), zip(results['dram.total-access-latency'], results['dram.accesses']))

  if 'dram-datamovement-queue.num-requests' in results and sum(results['dram-datamovement-queue.num-requests']) > 0:
    results['dram.remotequeuemodel_datamovement_avgdelay'] = map(lambda (a,b): a/b if b else float('inf'), zip(results['dram-datamovement-queue.total-queue-delay'], results['dram-datamovement-queue.num-requests']))
  if 'dram-datamovement-queue-2.num-requests' in results and sum(results['dram-datamovement-queue-2.num-requests']) > 0:
    results['dram.remotequeuemodel_datamovement2_avgdelay'] = map(lambda (a,b): a/b if b else float('inf'), zip(results['dram-datamovement-queue-2.total-queue-delay'], results['dram-datamovement-queue-2.num-requests']))

  # Compression
  bytes_saved = results['compression.bytes-saved'][0] if 'compression.bytes-saved' in results else 0
  cacheline_bytes_saved = results['compression.cacheline-bytes-saved'][0] if 'compression.cacheline-bytes-saved' in results else 0
  if bytes_saved != 0:
    data_moves = results['dram.page-moves'][0]
    total_compression_latency = results['compression.total-compression-latency'][0]
    total_decompression_latency = results['compression.total-decompression-latency'][0]

    gran_size = 64 if config['perf_model/dram/remote_use_cacheline_granularity'] == "true" else 4096
    results['compression.avg-compression-ratio'] = [float((data_moves * gran_size)) / float(((data_moves * gran_size) - bytes_saved))]
    results['compression.avg-compression-latency'] = [total_compression_latency / data_moves]
    results['compression.avg-decompression-latency'] = [total_decompression_latency / data_moves]

    if cacheline_bytes_saved != 0:
      data_moves = results['dram.remote-reads'][0] + results['dram.remote-writes'][0]
      total_cacheline_compression_latency = results['compression.total-cacheline-compression-latency'][0]
      total_cacheline_decompression_latency = results['compression.total-cacheline-decompression-latency'][0]

      gran_size = 64
      results['compression.avg-cacheline-compression-ratio'] = [float((data_moves * gran_size)) / float(((data_moves * gran_size) - cacheline_bytes_saved))]
      results['compression.avg-cacheline-compression-latency'] = [total_cacheline_compression_latency / data_moves]
      results['compression.avg-cacheline-decompression-latency'] = [total_cacheline_decompression_latency / data_moves]

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
    ('  average dram access latency (ns)', 'dram.avglatency', format_ns(2)),
    ('    local dram avg access latency (ns)', 'dram.localavglatency', format_ns(2)),
    ('    remote dram avg access latency (ns)', 'dram.remoteavglatency', format_ns(2)),
    ('      remote datamovement queue model avg access latency (ns)', 'dram.remotequeuemodel_datamovement_avgdelay', format_ns(2)),
    ('      remote datamovement2 queue model avg access latency (ns)', 'dram.remotequeuemodel_datamovement2_avgdelay', format_ns(2)),
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
    ('      num type1 cache slower than page', 'dram.pq-cacheline-slower-than-page', str),
    ('    num redundant moves type2', 'dram.redundant-moves-type2', str),
    ('  max simultaneous # inflight pages (bufferspace)', 'dram.max-bufferspace', str),
    ('  remote page move cancelled due to full bufferspace', 'dram.bufferspace-full-move-page-cancelled', str),
    ('  remote page move cancelled due to full queue', 'dram.queue-full-move-page-cancelled', str),
    ('  remote page move cancelled due to rmode5', 'dram.rmode5-move-page-cancelled', str),
    ('  remote page moved due to exceeding threshold in rmode5', 'dram.rmode5-page-moved-due-to-threshold', str),
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

  if 'dram-datamovement-queue.max-effective-bandwidth-ps' in results and sum(results['dram-datamovement-queue.max-effective-bandwidth-ps']) > 0:
    results['dram.remotequeuemodel_datamovement_max_effective_bandwidth'] = map(lambda (a,b): 1000*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue.max-effective-bandwidth-bytes'], results['dram-datamovement-queue.max-effective-bandwidth-ps']))
  if 'dram-datamovement-queue-2.max-effective-bandwidth-ps' in results and sum(results['dram-datamovement-queue-2.max-effective-bandwidth-ps']) > 0:
    results['dram.remotequeuemodel_datamovement2_max_effective_bandwidth'] = map(lambda (a,b): 1000*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue-2.max-effective-bandwidth-bytes'], results['dram-datamovement-queue-2.max-effective-bandwidth-ps']))

  if 'dram-datamovement-queue.num-requests-capped-by-window-size' in results and sum(results['dram-datamovement-queue.num-requests']) > 0:
    results['dram.remotequeuemodel_datamovement_percent_capped_by_window_size'] = map(lambda (a,b): 100*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue.num-requests-capped-by-window-size'], results['dram-datamovement-queue.num-requests']))
    results['dram.remotequeuemodel_datamovement_percent_queue_full'] = map(lambda (a,b): 100*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue.num-requests-queue-full'], results['dram-datamovement-queue.num-requests']))
    results['dram.remotequeuemodel_datamovement_percent_capped_by_custom_cap'] = map(lambda (a,b): 100*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue.num-requests-capped-by-custom-cap'], results['dram-datamovement-queue.num-requests']))
  if 'dram-datamovement-queue-2.num-requests-capped-by-window-size' in results and sum(results['dram-datamovement-queue-2.num-requests']) > 0:
    results['dram.remotequeuemodel_datamovement2_percent_capped_by_window_size'] = map(lambda (a,b): 100*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue-2.num-requests-capped-by-window-size'], results['dram-datamovement-queue-2.num-requests']))
    results['dram.remotequeuemodel_datamovement2_percent_queue_full'] = map(lambda (a,b): 100*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue-2.num-requests-queue-full'], results['dram-datamovement-queue-2.num-requests']))
    results['dram.remotequeuemodel_datamovement2_percent_capped_by_custom_cap'] = map(lambda (a,b): 100*float(a)/b if b else float('inf'), zip(results['dram-datamovement-queue-2.num-requests-capped-by-custom-cap'], results['dram-datamovement-queue-2.num-requests']))

  # Compression
  if bytes_saved != 0:
    template.append(('Compression', '', ''))
    template += [
      ('  bytes saved', 'compression.bytes-saved', str),
      ('  avg compression ratio', 'compression.avg-compression-ratio', str),
      ('  avg compression latency(ns)', 'compression.avg-compression-latency', format_ns(2)),
      ('  avg decompression latency(ns)', 'compression.avg-decompression-latency', format_ns(2)),
    ]
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
        ]

  bdi_total_compressed = results['compression.bdi_total_compressed'][0] if 'compression.bdi_total_compressed' in results else 0
  if bdi_total_compressed != 0:
    template += [
      ('  bdi_successful_compression', 'compression.bdi_total_compressed', str)]
    for i in range(0, 13): 
      bdi_option = float(results['compression.bdi_usage_option-{}'.format(i)][0]) / float(bdi_total_compressed) * 100
      bdi_option_format = "{:.2f}".format(bdi_option)
      results['compression.bdi_usage_option-{}'.format(i)] = [bdi_option_format]
      template.append(('  bdi_usage(%)_option-{}'.format(i), 'compression.bdi_usage_option-{}'.format(i), str))
    for i in range(0, 13): 
      template.append(('  bdi_bytes_saved_option-{}'.format(i), 'compression.bdi_bytes_saved_option-{}'.format(i), str))

  lz_compression = results['compression.avg_dictionary_size'][0] if 'compression.avg_dictionary_size' in results else 0
  if lz_compression != 0:
    template.append(('  Dictionary table stats (count within dictionary_size, entire ROI)', '', ''))
    for i in range(10, 101, 10):  # 10, 20, ..., 100
        template.append(('    {}% percentile - dictionary_size'.format(i), 'compression.lz-dictsize-count-p{}'.format(i), str))
        template.append(('    {}% percentile - total_bytes_saved'.format(i), 'compression.lz-bytes_saved-count-p{}'.format(i), str))
        template.append(('    {}% percentile - accesses'.format(i), 'compression.lz-accesses-count-p{}'.format(i), str))
        template.append(('    {}% percentile - max_entry_bytes'.format(i), 'compression.lz-max_entry_bytes-count-p{}'.format(i), str))



  # if 'dram.redundant-moves-temp1-time-savings' in results:
  template.extend([
      ('Experiment stats', '', ''),
      ('  PQ=1 type1 time savings (ns)', 'dram.redundant-moves-type1-time-savings', format_ns(2)),
      ('  PQ=1 type2 time savings (ns)', 'dram.redundant-moves-type2-time-savings', format_ns(2)),
      ('  num unique pages accessed', 'dram.unique-pages-accessed', str),
      ('  remote datamovement max effective bandwidth (GB/s)', 'dram.remotequeuemodel_datamovement_max_effective_bandwidth', format_float(4)),
      ('  remote datamovement2 max effective bandwidth (GB/s)', 'dram.remotequeuemodel_datamovement2_max_effective_bandwidth', format_float(4)),
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
