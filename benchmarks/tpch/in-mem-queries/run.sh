for ((i=1;i<=22;i++)); do
  ../qgen -v -c -s 1 ${i} > ${i}.sql
done