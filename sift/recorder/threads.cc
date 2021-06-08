#include "threads.h"
#include "sift_assert.h"
#include "recorder_control.h"

#include <iostream>
#include <unistd.h>
#include <syscall.h>
#include <linux/futex.h>

// Get Application Data
#include "zfstream.h"
#include "pin.H"
#include <fstream>

// Enable the below to print out sizeof(thread_data_t) at compile time
#if 0
// http://stackoverflow.com/questions/7931358/printing-sizeoft-at-compile-time
template<int N>
struct _{ operator char() { return N+ 256; } }; //always overflow
void print_size() { char(_<sizeof(thread_data_t)>()); }
#endif

static_assert((sizeof(thread_data_t) % LINE_SIZE_BYTES) == 0, "Error: Thread data should be a multiple of the line size to prevent false sharing");

thread_data_t *thread_data;

bool handleAccessMemoryDataServer(Sift::MemoryLockType lock_signal, uint64_t d_addr, uint8_t* data_buffer, uint32_t data_size)
{
   // Lock memory globally if requested
   // This operation does not occur very frequently, so this should not impact performance
   if (lock_signal == Sift::MemLock)
   {
      PIN_GetLock(&access_memory_lock, 0);
   }

      PIN_SafeCopy(data_buffer, reinterpret_cast<void*>(d_addr), data_size);


   if (lock_signal == Sift::MemUnlock)
   {
      PIN_ReleaseLock(&access_memory_lock);
   }

   return true;
}

unsigned int thread_num = 0;
unsigned int get_tid() {
   return __sync_fetch_and_add(&thread_num, 1); // Atomic addition is needed since multiple PIN threads access this variable
}

// Get Application Data
VOID thread_data_server(VOID *arg){
   // int* thread_id = static_cast<int*>(arg);
   // int thread_id_temp = *thread_id;
   unsigned int thread_id_temp = get_tid();
   printf("[SIFT] Hello from spawned data server for Thread %d\n",thread_id_temp);
   std::cerr << "[SIFT] Hello from spawned data server for Thread" << std::endl;

   char request_filename[1024];
   sprintf(request_filename,"data_request_pipe.app%" PRIu32 ".th%" PRIu32, app_id, thread_id_temp);
   vistream *data_server_request = new vifstream(request_filename, std::ios::in);

   char response_filename[1024];
   sprintf(response_filename,"data_response_pipe.app%" PRIu32 ".th%" PRIu32, app_id, thread_id_temp);
   vostream *data_server_response = new vofstream(response_filename, std::ios::out | std::ios::binary | std::ios::trunc);

   while (true)
   {
      uint64_t addr;
      uint32_t data_size;
      Sift::MemoryLockType lock_signal;

      data_server_request->read(reinterpret_cast<char*>(&addr), sizeof(addr));
      data_server_request->read(reinterpret_cast<char*>(&data_size), sizeof(data_size));
      data_server_request->read(reinterpret_cast<char*>(&lock_signal), sizeof(lock_signal));

      char *read_data = new char[data_size];
      bzero(read_data, data_size);
      handleAccessMemoryDataServer(lock_signal, addr,(uint8_t*) read_data, data_size);

      data_server_response->write(reinterpret_cast<char*>(&addr), sizeof(addr));
      data_server_response->write(read_data, data_size);
      data_server_response->flush();
   }
}

// The thread that watched this new thread start is responsible for setting up the connection with the simulator
static VOID threadStart(THREADID threadid, CONTEXT *ctxt, INT32 flags, VOID *v)
{
   sift_assert(threadid < max_num_threads);
   sift_assert(thread_data[threadid].bbv == NULL);

   // The first thread (master) doesn't need to join with anyone else
   PIN_GetLock(&new_threadid_lock, threadid);
   if (tidptrs.size() > 0)
   {
      thread_data[threadid].tid_ptr = tidptrs.front();
      tidptrs.pop_front();
   }
   PIN_ReleaseLock(&new_threadid_lock);

   thread_data[threadid].thread_num = num_threads++;
   thread_data[threadid].bbv = new Bbv();

   if (threadid > 0 && (any_thread_in_detail || KnobEmulateSyscalls.Value()))
   {
      openFile(threadid);

      // We should send a EmuTypeSetThreadInfo, but not now as we hold the Pin VM lock:
      // Sending EmuTypeSetThreadInfo requires the response channel to be opened,
      // which is done by TraceThread but not any time soon if we aren't scheduled on a core.
      thread_data[threadid].should_send_threadinfo = true;

      // Get Application Data
      PIN_THREAD_UID threadUid;
      void * threadArg = (void *) (&threadid);
      PIN_SpawnInternalThread(thread_data_server, threadArg, 0, &threadUid);
   }

   thread_data[threadid].running = true;
}

static VOID threadFinishHelper(VOID *arg)
{
   uint64_t threadid = reinterpret_cast<uint64_t>(arg);
   if (thread_data[threadid].tid_ptr)
   {
      // Set this pointer to 0 to indicate that this thread is complete
      intptr_t tid = (intptr_t)thread_data[threadid].tid_ptr;
      *(int*)tid = 0;
      // Send the FUTEX_WAKE to the simulator to wake up a potential pthread_join() caller
      syscall_args_t args = {0};
      args[0] = (intptr_t)tid;
      args[1] = FUTEX_WAKE;
      args[2] = 1;
      thread_data[threadid].output->Syscall(SYS_futex, (char*)args, sizeof(args));
   }

   if (thread_data[threadid].output)
   {
      closeFile(threadid);
   }

   delete thread_data[threadid].bbv;

   thread_data[threadid].bbv = NULL;
}

static VOID threadFinish(THREADID threadid, const CONTEXT *ctxt, INT32 flags, VOID *v)
{
#if DEBUG_OUTPUT
   std::cerr << "[SIFT_RECORDER:" << app_id << ":" << thread_data[threadid].thread_num << "] Finish Thread" << std::endl;
#endif

   if (thread_data[threadid].thread_num == 0 && thread_data[threadid].output && KnobEmulateSyscalls.Value())
   {
      // Send SYS_exit_group to the simulator to end the application
      syscall_args_t args = {0};
      args[0] = flags;
      thread_data[threadid].output->Syscall(SYS_exit_group, (char*)args, sizeof(args));
   }

   thread_data[threadid].running = false;

   // To prevent deadlocks during simulation, start a new thread to handle this thread's
   // cleanup.  This is needed because this function could be called in the context of
   // another thread, creating a deadlock scenario.
   PIN_SpawnInternalThread(threadFinishHelper, (VOID*)(unsigned long)threadid, 0, NULL);
}

void initThreads()
{
   PIN_AddThreadStartFunction(threadStart, 0);
   PIN_AddThreadFiniFunction(threadFinish, 0);
}
