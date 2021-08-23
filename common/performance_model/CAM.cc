#include "CAM.h"

CAM::CAM(UInt32 size):m_size(size)
{
    dictionary_table = new UInt64[size]();
    LRU = new UInt8[size]();
}

CAM::~CAM()
{
    delete [] dictionary_table;
    delete [] LRU;
}

void
CAM:: clear() 
{
    UInt32 i;
    for(i=0; i<m_size; i++) {
        dictionary_table[i] = (UInt64) 0; 
        LRU[i] = 0x00;
    }
}

UInt64
CAM::read_value(UInt8 indx)
{
    return dictionary_table[indx];
}

void 
CAM::write_value(UInt8 indx, UInt64 word)
{
    dictionary_table[indx] = word;
}

UInt8 
CAM::replace_value(UInt64 word)
{
    UInt8 indx=0, older=0xff, i=0;
    for(i=0; i<m_size; i++)
    {
        if(LRU[i] < older)
        {
            indx = i;
            older = LRU[i];
        }
    }

    dictionary_table[indx] = word;
    LRU[indx] = 0x00;

    return indx;
}

void 
CAM::update_LRU(UInt8 indx)
{
    UInt8 i, mask=0x80;

    for(i=0; i<m_size; i++)
    {
        LRU[i] >>= 1;
        if(i == indx) 
            LRU[i] |= mask;
    }
}

dictionary_info
CAM::search_value(UInt64 word)
{
    UInt8 i=0;
    dictionary_info res;
    res.found = false;
    res.indx = 0;

    for (i=0; i<m_size; i++) {
        if(dictionary_table[i] == word)
        {
            res.found = true;
            res.indx = i;
        }
    }

    if(!res.found)
        res.indx = replace_value(word);

    update_LRU(res.indx);

    return res;
}

dictionary_info
CAM::find_min_diff(UInt64 word, UInt8 threshold)
{
    UInt8 indx, i=0;
    SInt8 diff=threshold;
    bool found=0;

    for (i=0; i<m_size; i++) {
        if(abs((SInt64)(dictionary_table[i] - word)) < (abs(diff)))
        {
            found = 1;
            diff = (SInt8)(dictionary_table[i]-word);
            indx = i;
        }
    }

    if (found) 
        write_value(indx, word);

    if(!found)
        indx = replace_value(word);

    update_LRU(indx);
    dictionary_info res;
    res.found = found;
    res.indx = indx;
    res.diff = diff;
    return res;
}
