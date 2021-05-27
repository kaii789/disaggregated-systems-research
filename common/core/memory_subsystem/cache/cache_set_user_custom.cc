// Referenced code from Round Robin CacheSet
#include "cache_set_user_custom.h"

CacheSetUserCustom::CacheSetUserCustom(
      CacheBase::cache_t cache_type,
      UInt32 associativity, UInt32 blocksize) :
   CacheSet(cache_type, associativity, blocksize)
{
   // m_replacement_index = m_associativity - 1;
   m_replacement_index = 0;
   LOG_PRINT("CacheSetUserCustom, m_replacement_index init = %d", m_replacement_index);
}

CacheSetUserCustom::~CacheSetUserCustom()
{}

UInt32
CacheSetUserCustom::getReplacementIndex(CacheCntlr *cntlr)
{
   UInt32 curr_replacement_index = m_replacement_index;
   // m_replacement_index = (m_replacement_index == 0) ? (m_associativity-1) : (m_replacement_index-1);
   m_replacement_index = (m_replacement_index == m_associativity-1) ? 0 : (m_replacement_index+1);
   LOG_PRINT("CacheSetUserCustom, m_replacement_index = %d", m_replacement_index);

   if (!isValidReplacement(m_replacement_index)) {
      LOG_PRINT("CacheSetUserCustom, invalid replacement encountered");
      return getReplacementIndex(cntlr);
   }
   else {
      return curr_replacement_index;
   }
}

void
CacheSetUserCustom::updateReplacementIndex(UInt32 accessed_index)
{
   return;
}
