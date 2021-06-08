#include "compression_model_bdi.h"

CompressionModelBDI::CompressionModelBDI(String name, UInt32 page_size, UInt32 cache_line_size)
    : m_name(name)
    , m_page_size(page_size)
    , m_cache_line_size(cache_line_size)
{

}

CompressionModelBDI::~CompressionModelBDI()
{}

UInt32
CompressionModel::compress(IntPtr addr, size_t data_size, core_id_t core_id)
{
    // Get Data
    char *buffer = (char*)malloc(data_size * sizeof(char));
    Core *core = Sim()->getCoreManager()->getCoreFromID(core_id);
    core->getApplicationData(Core::NONE, Core::READ, addr, buffer, data_size, Core::MEM_MODELED_NONE);

    // Log
    FILE *fp;
    fp = fopen("compression.log", "a");
    for (int i = 0; i < (int)data_size; i++) {
        fprintf(fp, "%c ", buffer[i]);
    }
    fprintf(fp, "\n\n");

    free(buffer);

    return data_size; // FIXME return compressed_size in page granularity to be used to simulate bandwidth delay
}

UInt32
CompressionModel::decompress(IntPtr addr, size_t data_size, core_id_t core_id)
{
    return 0;
}
