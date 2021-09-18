#ifndef __HASHED_LINKED_LIST__
#define __HASHED_LINKED_LIST__

#include "fixed_types.h"
#include <unordered_map>
#include <list>

class HashedLinkedList
{
    private:
        size_t m_size;
        std::unordered_map<UInt64, std::list<UInt64>::iterator> map;
        std::list<UInt64> list;

    public:
        bool find(UInt64 val);
        void push_back(UInt64 val);
        void remove(UInt64 val);
        size_t size();
        UInt64 front();
        void pop_front();
        std::list<UInt64>::iterator begin();
        std::list<UInt64>::iterator end();
};
#endif /* __HASHED_LINKED_LIST__ */