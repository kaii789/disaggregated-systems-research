#include "hashed_linked_list.h"

bool
HashedLinkedList::find(UInt64 val)
{
    return map.find(val) != map.end();
}

void
HashedLinkedList::push_back(UInt64 val)
{
    list.push_back(val);
    map.emplace(val, --list.end());
    m_size += 1;
}

void
HashedLinkedList::remove(UInt64 val)
{
    if (m_size > 0) {
        list.erase(map.at(val));
        map.erase(val);
        m_size -= 1;
    }
}

size_t
HashedLinkedList::size()
{
    return (size_t)m_size;
}

UInt64
HashedLinkedList::front()
{
    return list.front();
}

void
HashedLinkedList::pop_front()
{
    if (m_size > 0) {
        map.erase(list.front());
        list.pop_front();
        m_size -= 1;
    }
}

std::list<UInt64>::iterator
HashedLinkedList::begin()
{
    return list.begin();
}

std::list<UInt64>::iterator
HashedLinkedList::end()
{
    return list.end();
}