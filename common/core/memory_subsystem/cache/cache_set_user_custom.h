// Referenced code from Round Robin CacheSet
#ifndef CACHE_SET_USER_CUSTOM_H
#define CACHE_SET_USER_CUSTOM_H

#include "cache_set.h"

class CacheSetUserCustom : public CacheSet
{
   public:
      CacheSetUserCustom(CacheBase::cache_t cache_type,
            UInt32 associativity, UInt32 blocksize);
      ~CacheSetUserCustom();

      UInt32 getReplacementIndex(CacheCntlr *cntlr);
      void updateReplacementIndex(UInt32 accessed_index);

   private:
      UInt32 m_replacement_index;
};

#endif /* CACHE_SET_USER_CUSTOM_H */
