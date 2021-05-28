#ifndef __ZSIM_HOOKS_H__
#define __ZSIM_HOOKS_H__

#include <stdint.h>
#include <stdio.h>

//#if defined(MSG) || defined(MSGMS) || defined(MEM) // cgiannoula
typedef struct {
    unsigned long int addr;
    uint32_t toCore;
    uint32_t type;  // 1: barier arrive, 2: barrier depart(1-thread)
                    // 3: lock acquire,  4: lock release
} msg_t;
//#endif

//Avoid optimizing compilers moving code around this barrier
#define COMPILER_BARRIER() { __asm__ __volatile__("" ::: "memory");}

//These need to be in sync with the simulator
#define ZSIM_MAGIC_OP_ROI_BEGIN         (1025)
#define ZSIM_MAGIC_OP_ROI_END           (1026)
#define ZSIM_MAGIC_OP_REGISTER_THREAD   (1027)
#define ZSIM_MAGIC_OP_HEARTBEAT         (1028)
#define ZSIM_MAGIC_OP_WORK_BEGIN        (1029) //ubik
#define ZSIM_MAGIC_OP_WORK_END          (1030) //ubik

#define ZSIM_MAGIC_OP_FUNCTION_BEGIN    (1031) // LOIS
#define ZSIM_MAGIC_OP_FUNCTION_END      (1032) // LOIS
#define ZSIM_MAGIC_OP_SET_LOCAL         (1033) // cgiannoula 

#ifdef __x86_64__
#define HOOKS_STR  "HOOKS"
static inline void zsim_magic_op(uint64_t op) {
    COMPILER_BARRIER();
    __asm__ __volatile__("xchg %%rcx, %%rcx;" : : "c"(op));
    COMPILER_BARRIER();
}
#else
#define HOOKS_STR  "NOP-HOOKS"
static inline void zsim_magic_op(uint64_t op) {
    //NOP
}
#endif

static inline void zsim_roi_begin() {
    printf("[" HOOKS_STR "] ROI begin\n");
    zsim_magic_op(ZSIM_MAGIC_OP_ROI_BEGIN);
}

static inline void zsim_roi_end() {
    zsim_magic_op(ZSIM_MAGIC_OP_ROI_END);
    printf("[" HOOKS_STR  "] ROI end\n");
}

// LOIS
static inline void zsim_PIM_function_begin() {
    zsim_magic_op(ZSIM_MAGIC_OP_FUNCTION_BEGIN);
}

// LOIS
static inline void zsim_PIM_function_end() {
    zsim_magic_op(ZSIM_MAGIC_OP_FUNCTION_END);
}

// cgiannoula
static inline void zsim_PIM_send_msg(uint64_t op) {
//#if defined(MSG) || defined(MSGMS) || defined(MEM) // cgiannoula
    zsim_magic_op(op);
//#endif
}

static inline void zsim_PIM_set_local() {
    zsim_magic_op(ZSIM_MAGIC_OP_SET_LOCAL);
}

static inline void zsim_heartbeat() {
    zsim_magic_op(ZSIM_MAGIC_OP_HEARTBEAT);
}

static inline void zsim_work_begin() { zsim_magic_op(ZSIM_MAGIC_OP_WORK_BEGIN); }
static inline void zsim_work_end() { zsim_magic_op(ZSIM_MAGIC_OP_WORK_END); }

#endif /*__ZSIM_HOOKS_H__*/