#include <assert.h>
#include <limits>
#include <iostream>
#include "CAM_lz.h"


CAMLZ::CAMLZ(string name, bool size_limit)
    : m_name(name)
    , m_cur_size(0)
    , m_size_limit(size_limit) 
{
    m_dictionary_table = map<string, UInt32>();
    m_reverse_table = map<UInt32, string>();

    if(m_size_limit == true)
        LRU = new UInt32[m_size+1]{0};
    std::cout << "dict size: " << m_size << "size limit " << size_limit << std::endl;
}

CAMLZ::CAMLZ(string name, UInt32 size, bool size_limit)
    : m_name(name)
    , m_size(size) 
    , m_cur_size(0)
    , m_size_limit(size_limit) 
{
    m_dictionary_table = map<string, UInt32>();
    m_reverse_table = map<UInt32, string>();

    if(m_size_limit == true)
        LRU = new UInt32[m_size+1]{0};

    std::cout << "dict size: " << m_size << "size limit " << size_limit << std::endl;
}

CAMLZ::~CAMLZ() 
{
    m_dictionary_table.clear();
    m_reverse_table.clear();

    if(m_size_limit == true)
        delete[] LRU;
}

void 
CAMLZ::clear() 
{
    m_cur_size = 0;
    m_dictionary_table.clear();

    if(m_size_limit == true) {
        m_reverse_table.clear();
        for (UInt32 i = 0; i <= m_size; i++) 
            LRU[i] = 0;
    }
}

void
CAMLZ::setReplacementIndex(UInt32 start_index)
{
    m_start_replacement_index = start_index + 1;
}

bool
CAMLZ::find(string s)
{
    bool found = false;

    map<string, UInt32>::iterator it;
    it = m_dictionary_table.find(s);

    if(it == m_dictionary_table.end()) { // Not found in the dictionary
        found = false;
    } else {
        found = true;
        if(m_size_limit == true) { // If found and size_limit = true, update the LRU policy (= increase the corresponding counter for that dictionary entry in the LRU table
            LRU[it->second]++;
        }
    }
    return found;
}

void 
CAMLZ::insert(string s) 
{
    if(m_size_limit == false) { // If there is no size limit, just insert it in the dictionary table
        m_cur_size++;
        m_dictionary_table.insert(pair<string,UInt32>(s, m_cur_size));
        //m_reverse_table.insert(pair<UInt32, string>(m_cur_size, s));
    } else { 
        if (m_cur_size < m_size){ // If the dictionary table is not full, add a new entry at the end of it
            m_cur_size++;
            m_dictionary_table.insert(pair<string, UInt32>(s, m_cur_size));
            m_reverse_table.insert(pair<UInt32, string>(m_cur_size, s));
            LRU[m_cur_size]++;
        } else { // If the dictionary table is full, insert the new string by replacing the least recently used entry

            // Find the LRU entry and its index
            UInt32 lru_entry = INT32_MAX;
            UInt32 lru_index = m_start_replacement_index; // Assuming that we always start the dictionary table from 1
            for (UInt32 i = m_start_replacement_index; i <= m_size; i++) {
                if(LRU[i] < lru_entry) {
                    lru_entry = LRU[i];
                    lru_index = i;
                }
            }
    
            // Remove the entry from the dictionary table
            map<UInt32, string>::iterator rit;
            rit = m_reverse_table.find(lru_index);
            assert(lru_index == rit->first);
            if((rit == m_reverse_table.end()) || (rit->first > m_size)) {
                assert("[CAMLZ] Entry not found or wrong dictionary data");
            }
            m_dictionary_table.erase(rit->second);
            m_reverse_table.erase(rit->first);

            // Insert new entry in the dictionary table
            m_dictionary_table.insert(pair<string, UInt32>(s, lru_index));
            m_reverse_table.insert(pair<UInt32, string>(lru_index, s));
        }
    }

}

UInt32
CAMLZ::getSize() 
{
    if(m_size_limit == true) { 
        assert(m_dictionary_table.size() == m_reverse_table.size() && "[CAMLZ] Wrong dictionary size");
        assert(m_dictionary_table.size() <= m_size && "[CAMLZ] Wrong dictionary size");
        return m_size;
    }

    return m_dictionary_table.size();
}
