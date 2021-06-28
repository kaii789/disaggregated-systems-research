#include "CAM.h"

CAM::CAM(unsigned int size):_size(size)
{
    FV_table=new unsigned long int[size]();
    LRU=new unsigned char[size]();
}

CAM::~CAM()
{
    delete [] FV_table;
    delete [] LRU;
}

unsigned long int CAM::Read(unsigned char indx)
{
    return FV_table[indx];
}

void CAM::Write(unsigned char indx,unsigned long int x)
{
    FV_table[indx]=x;
}

unsigned char CAM::Replace(unsigned long int x)
{
    unsigned char indx=0,older=0xff,i=0;
    for(i=0;i<_size;i++)
    {
        if(LRU[i]<older)
        {
            indx=i;
            older=LRU[i];
        }

    }

    FV_table[indx]=x;
    LRU[indx]=0x00;

    return indx;
}

void CAM::Update_Lru(unsigned char indx)
{
    unsigned char i,mask=0x80;

    for(i=0;i<_size;i++)
    {
        LRU[i]>>=1;
        if(i==indx) LRU[i]|=mask;
    }

}

std::pair<bool,unsigned char> CAM::Search(unsigned long int x)
{
    unsigned char i=0;
    std::pair<bool,unsigned char> result(0,0);
    for (i=0;i<_size;i++)
        if(FV_table[i]==x)
        {
            result.first=1;
            result.second=i;
        }
    if(!result.first)
        result.second=Replace(x);

    Update_Lru(result.second);

    return result;
}


boost::tuple<bool,unsigned char, char>CAM::Find_min_diff(unsigned long int x, unsigned char threshold)
{
    unsigned char indx,i=0;
    char diff=threshold;
    bool hit=0;

    for (i=0;i<_size;i++)
        if(abs((long int)(FV_table[i]-x))<(abs(diff)))
        {
            hit=1;
            diff=(char)(FV_table[i]-x);
            indx=i;
        }
    if(hit) Write(indx,x);
    if(!hit)
        indx=Replace(x);

    Update_Lru(indx);
    boost::tuple<bool,unsigned char,char> result = boost::make_tuple(hit,indx,diff);
    return result;
}
