#include "fixed_types.h"


typedef struct {
    bool found; 
    UInt8  indx;
    SInt8  diff;
} dictionary_info;

class CAM {

    public:
        CAM(UInt32);
        ~CAM();

        UInt64 read_value(UInt8);
        void write_value(UInt8, UInt64);
        UInt8 replace_value(UInt64);
        void update_LRU(UInt8);
        dictionary_info search_value(UInt64);
        dictionary_info find_min_diff(UInt64, UInt8);

    private:
        UInt32 m_size;
        UInt64* dictionary_table;
        UInt8* LRU;

};
