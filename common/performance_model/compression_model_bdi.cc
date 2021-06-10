#include "compression_model_bdi.h"

CompressionModelBDI::CompressionModelBDI(String name, UInt32 page_size, UInt32 cache_line_size)
    : m_name(name)
    , m_page_size(page_size)
    , m_cache_line_size(cache_line_size)
{

}

CompressionModelBDI::~CompressionModelBDI()
{}

SubsecondTime
CompressionModelBDI::compress(IntPtr addr, size_t data_size, core_id_t core_id, UInt32 *compressed_page_size)
{
    // Get Data
    char *buffer = (char*)malloc(data_size * sizeof(char));
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    core->getApplicationData(Core::NONE, Core::READ, addr, buffer, data_size, Core::MEM_MODELED_NONE);

    
    // BDI
    char *compressed_buffer = (char*)malloc(data_size * sizeof(char));
    int cacheline_count = data_size / m_cache_line_size;
    int compressed_size[cacheline_count];
    uint32_t total_bytes = 0;
    uint32_t total_cache_lines = 0;
    memset(compressed_buffer, 0, data_size);
    memset(compressed_size, 0, sizeof(int) * cacheline_count);
    for (int i = 0; i < cacheline_count; i++)
    {
        compressed_size[i] = compress_cache_line(buffer + i * m_cache_line_size, compressed_buffer + i * m_cache_line_size);
        total_bytes += compressed_size[i];
        if (compressed_size[i] < m_cache_line_size)
            total_cache_lines++;
        //std::cout << "size " << compressed_size[i] << " total_bytes " << total_bytes << " total_cache_lines " << total_cache_lines << std::endl;
    }
   
    /*
     * Log for compressed data
    // Log
    FILE *fp;
    fp = fopen("compression.log", "a");
    // for (int i = 0; i < (int)data_size; i++) {
    //     fprintf(fp, "%c ", buffer[i]);
    // }
    fprintf(fp, "##########################%s#############################\n", "PAGE START");
    for (int i = 0; i < cacheline_count; i++)
    {
        // Orig
        fprintf(fp, "Uncompressed: ");
        for (int j = 0; j < m_cache_line_size; j++)
        {
            fprintf(fp, "%hhu ", (uint8_t)buffer[i * m_cache_line_size + j]);
        }
        // Compressed
        fprintf(fp, "\nCompressed: ");
        int size = compressed_size[i];
        for (int j = 0; j < size; j++)
        {
            fprintf(fp, "%hhu ", (uint8_t)compressed_buffer[i * m_cache_line_size + j]);
        }
        fprintf(fp, "\n\n");
    }
    fprintf(fp, "##########################%s#############################\n", "PAGE END");

    free(buffer);
    free(compressed_buffer);
    *
    */
   
    // Return compressed pages size in Bytes
    *compressed_page_size = total_bytes;

    // Return compression latency
    ComponentLatency compress_latency(ComponentLatency(core->getDvfsDomain(), total_cache_lines * m_compression_latency));
    return compress_latency.getLatency();

}

SubsecondTime
CompressionModelBDI::decompress(IntPtr addr, UInt32 compressed_cache_lines, core_id_t core_id)
{
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    ComponentLatency decompress_latency(ComponentLatency(core->getDvfsDomain(), compressed_cache_lines * m_decompression_latency));

    return decompress_latency.getLatency();

}


Byte* 
CompressionModelBDI::MakeCompBuf()
{
   Byte* buf = new Byte[m_cache_line_size+1]();
   return buf;
}

long int 
CompressionModelBDI::ReadWord(void *ptr, unsigned int idx, int k) //idx says which word of input ptr to read (i from main code/decode loop)
{
    long int   x;

    /* Read the word as unsigned int or unsigned long int from the stream according to wordsize*/
    switch (k)
    {
        case 8:
        x =((long int *) ptr)[ idx ];
        break;

        case 4:
        x = ((int*)ptr)[ idx ];
        break;    

        case 2:
        x = ((short int*)ptr) [ idx ];
        break;

        case 1:
        x = ((signed char*)ptr) [ idx ];
        break;

        default:
        fprintf(stderr,"Unknown base size\n");
        exit(1);
    }

    return x;
}


void 
CompressionModelBDI::WriteWord( void *ptr, unsigned int idx, long int x ,int Dsize)
{
    
    switch(Dsize)
    {

        case 8:   
       ((long int *) ptr)[ idx ] = (long int)x;
        break;          

        case 4:   
        ((int *) ptr)[ idx ] = (int)x;
        break;

        case 2:
        ((short int*)ptr)[ idx ] = (short int) x;
        break;

        case 1:
        ((signed char*)ptr)[ idx ] = (signed char)x;
        break;

        default:
        fprintf(stderr,"Unknown Delta size\n");
        exit(1);
    }      
}

bool 
CompressionModelBDI::checkDeltalimits(long int Delta,int Dsize)
{
    bool check=1;
    switch(Dsize)
    {          
        case 4:   
        if ((Delta<INT_MIN)||(Delta>INT_MAX)) check=0;
        break;

        case 2:
        if ((Delta<SHRT_MIN)||(Delta>SHRT_MAX)) check=0;
        break;

        case 1:
        if ((Delta<SCHAR_MIN)||(Delta>SCHAR_MAX)) check=0;
        break;

        default:
        fprintf(stderr,"Unknown Delta size\n");
        exit(1);
    }      
    
        return check;

}


boost::tuple<bool,unsigned int> 
CompressionModelBDI::Specialized_compress(void *in, void *out, int k, int Dsize)
{
 
    unsigned int i;
    long int Base,x,Delta;
    bool check=0;
    boost::tuple <bool,unsigned int> result; 

    Base = ReadWord(in,0,k);
    WriteWord(out,0,Base,k);
    for(i=0;i<((m_cache_line_size/k)-1);i++){
       x=ReadWord((void*) (((char*)in)+k*sizeof(unsigned char)),i,k);
       Delta=Base-x;
       check=checkDeltalimits(Delta,Dsize);
       if (check!=1) break;
       else WriteWord((void*) (((char*)out)+k*sizeof(unsigned char)),i,Delta,Dsize);
    }
    
    result = boost::make_tuple(check,((m_cache_line_size/k)-1)*Dsize+k);
    return result; 

}

boost::tuple<bool,unsigned int> 
CompressionModelBDI::zeros(void* in, void* out)
{
    char Base;
    unsigned char i;
    boost::tuple<bool,unsigned int> result; 
    Base=((char*)in)[0];
    for (i=1;i<m_cache_line_size;i++)
        if((Base-((char*)in)[i])!=0)
            break;
    
    if(i==m_cache_line_size){
        result=boost::make_tuple(1,1);
        WriteWord(out,0,Base,sizeof(char));
    }        
    else
        result=boost::make_tuple(0,m_cache_line_size);
        
    return result;
}

boost::tuple<bool,unsigned int> 
CompressionModelBDI::repeated(void* in, void* out)
{
    unsigned char i;
    long int Base;
    boost::tuple<bool,unsigned int> result; 
    Base=((long int*)in)[0];
    for (i=1;i<m_cache_line_size;i++)
        if((Base-((long int*)in)[i])!=0)
            break;
    
    if(i==m_cache_line_size){
        result=boost::make_tuple(1,8);
        WriteWord(out,0,Base,sizeof(long int));
    }        
    else
        result=boost::make_tuple(0,m_cache_line_size);
        
    return result;
}


UInt32 
CompressionModelBDI::compress_cache_line(void* in, void* out)
{
    boost::tuple<bool,unsigned int> Results[8];
    char* pointers[8];
    int i,j,counter;

    for(i=0;i<8;i++)
        pointers[i]=new char[m_cache_line_size]();

    for(i=0;i<8;i++)
        Results[i]=boost::make_tuple(0,m_cache_line_size);

    Results[0]= zeros(in, (void*) pointers[0]);
    Results[1]= repeated(in, (void*) pointers[1]);
    counter=2;

    for(i=8;i>=2;i/=2)
        for(j=1;j<=(i/2);j*=2){
            Results[counter]=Specialized_compress(in, (void*)pointers[counter],i,j);
            counter++;
        }

    unsigned int compressed_size=(unsigned int)m_cache_line_size;
    char chosen=15;

    for (i=0;i<7;i++){
        if(Results[i].get<0>()==1){
            if(Results[i].get<1>()<compressed_size){
                compressed_size=Results[i].get<1>();
                chosen=(char)i;
            }            
        }
    }
    ((char*)out)[0]=chosen;    
    if (chosen==15)
        memcpy((void*)(((char*)out)+sizeof(char)),in,m_cache_line_size);
    else
        memcpy((void*)(((char*)out)+sizeof(char)),pointers[chosen],compressed_size);

    for(i=0;i<8;i++)
        delete [] pointers[i];


    return (UInt32)(compressed_size+1);
}



UInt32 
CompressionModelBDI::decompress_cache_line(void *in, void *out)
{
    char code;
    unsigned int i;
    long int Base,Delta,x;

    code=((char*)in)[0];
    in=(void*)(((char*)in)+1);

    switch (code)
    {
        case 0:
        Base=ReadWord(in,0,sizeof(char));
        memset(out,Base,m_cache_line_size);       
        break;

        case 1:
        Base=ReadWord(in,0,sizeof(long int));
        for (i=0;i<(m_cache_line_size/sizeof(long int));i++)
            ((long int*)out)[i]=Base;
        break;

        case 2:
        Base=ReadWord(in,0,sizeof(long int));
        WriteWord(out,0,Base,sizeof(long int));
        in=(void*)(((char*)in)+sizeof(long int));
        out=(void*)(((char*)out)+sizeof(long int));
        for (i=0;i<(m_cache_line_size/sizeof(long int)-1);i++){
            Delta=ReadWord(in,i,sizeof(char));
            x=Base-Delta;
            WriteWord(out,i,x,sizeof(long int));   
        }
        break;

        case 3:
        Base=ReadWord(in,0,sizeof(long int));
        WriteWord(out,0,Base,sizeof(long int));
        in=(void*)(((char*)in)+sizeof(long int));
        out=(void*)(((char*)out)+sizeof(long int));
        for (i=0;i<(m_cache_line_size/sizeof(long int)-1);i++){
            Delta=ReadWord(in,i,sizeof(short int));
            x=Base-Delta;
            WriteWord(out,i,x,sizeof(long int));   
        }
        break;
        

        case 4:
        Base=ReadWord(in,0,sizeof(long int));
        WriteWord(out,0,Base,sizeof(long int));
        in=(void*)(((char*)in)+sizeof(long int));
        out=(void*)(((char*)out)+sizeof(long int));
        for (i=0;i<(m_cache_line_size/sizeof(long int)-1);i++){
            Delta=ReadWord(in,i,sizeof(int));
            x=Base-Delta;
            WriteWord(out,i,x,sizeof(long int));   
        }
        break;


        case 5:
        Base=ReadWord(in,0,sizeof(int));
        WriteWord(out,0,Base,sizeof(int));
        in=(void*)(((char*)in)+sizeof(int));
        out=(void*)(((char*)out)+sizeof(int));
        for (i=0;i<(m_cache_line_size/sizeof(int)-1);i++){
            Delta=ReadWord(in,i,sizeof(char));
            x=Base-Delta;
            WriteWord(out,i,x,sizeof(int));   
        }
        break;


        case 6:
        Base=ReadWord(in,0,sizeof(int));
        WriteWord(out,0,Base,sizeof(int));
        in=(void*)(((char*)in)+sizeof(int));
        out=(void*)(((char*)out)+sizeof(int));
        for (i=0;i<(m_cache_line_size/sizeof(int)-1);i++){
            Delta=ReadWord(in,i,sizeof(short int));
            x=Base-Delta;
            WriteWord(out,i,x,sizeof(int));   
        }
        break;

    
        case 7:
        Base=ReadWord(in,0,sizeof(short int));
        WriteWord(out,0,Base,sizeof(short int));
        in=(void*)(((char*)in)+sizeof(short int));
        out=(void*)(((char*)out)+sizeof(short int));
        for (i=0;i<(m_cache_line_size/sizeof(short int)-1);i++){
            Delta=ReadWord(in,i,sizeof(char));
            x=Base-Delta;
            WriteWord(out,i,x,sizeof(short int));   
        }
        break;
        

        case 15:
        memcpy(out,in,m_cache_line_size);
        break;


        default:
        fprintf(stderr,"Unknown code\n");
        exit(1);

    }

    return 0;

}
