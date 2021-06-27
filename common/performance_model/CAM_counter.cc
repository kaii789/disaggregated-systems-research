#include "CAM_counter.h"

CAM_counter::CAM_counter(unsigned int size):_size(size)
{
    FV_table=new unsigned long int[size]();
    counter= new unsigned char[size]();
    hit_table= new bool[size]();
}

CAM_counter::~CAM_counter()
{
    delete [] FV_table;
    delete [] counter;
    delete [] hit_table;
}

unsigned long int CAM_counter::Read(unsigned char indx)
{
    return FV_table[indx];
}

void CAM_counter::Write(unsigned char indx,unsigned long int x)
{
    FV_table[indx]=x;
}



void CAM_counter::Update1(std::pair <bool,unsigned char>* result, unsigned long int x)
{
    
    if(!result->first)
        miss_buffer.push_back(x);
    else{    
        hit_table[result->second]=1;
        if(counter[result->second]<256)
           counter[result->second]+=2;
     }

}


void CAM_counter::Update2()
{  
    int i;
    for (i=0;i<_size;i++){
        if (hit_table[i]==0)
            counter[i]-=1;        
    }
    
    memset(hit_table,0x00,_size*sizeof(bool));

    for (i=0;i<_size;i++){
        if(counter[i]==0){
            if (!miss_buffer.empty()){
                FV_table[i]=miss_buffer.front(); 
                miss_buffer.pop_front();
            }
            else
                break;        
        }
    }
    
    miss_buffer.clear();
    
}



std::pair<bool,unsigned char> CAM_counter::Search(unsigned long int x)
{
    unsigned char i=0;
    std::pair<bool,unsigned char> result(0,0);
    for (i=0;i<_size;i++)
        if(FV_table[i]==x)
        {
            result.first=1;
            result.second=i;
        }

    return result;
}


