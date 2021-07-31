#ifndef __CAM_LZ_H__
#define __CAM_LZ_H__

#include <string>
#include <map>
#include <utility>  
#include "fixed_types.h"


using namespace std;

class CAMLZ 
{
public:
    CAMLZ(string name, bool);
    CAMLZ(string name, UInt32, bool);
    ~CAMLZ();

    void clear();
    void setReplacementIndex(UInt32);
    bool find(string);
    void insert(string);
    UInt32 getSize();

private:
    string m_name;
    UInt32 m_size = 1024;
    bool m_size_limit = true;
    UInt32 m_cur_size = 0;
    UInt32 m_start_replacement_index = 1;
 
    map<string, UInt32> m_dictionary_table; 
    map<UInt32, string> m_reverse_table; // This is used to speedup the simulation time when m_size_limit == true. An alternative would be to iterate over m_dictionary_table and find the key (=string) to be deleted by comparing the value m_cur_size (= UInt32)
    UInt32* LRU;

};
#endif /* __CAM_LZ_H__ */
