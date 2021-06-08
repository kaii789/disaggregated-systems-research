#include "compression_model.h"

void
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
}