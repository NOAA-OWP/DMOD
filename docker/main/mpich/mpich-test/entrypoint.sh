#!/bin/sh
set -e

echo "--- Running MPI Hello World Example ---"

printf "it should find mpicc, mpicxx, and mpif90... "
mpicc --version > /dev/null
mpicxx --version > /dev/null
mpif90 --version > /dev/null
echo ok

printf "it should find mpiexec... "
mpiexec --version > /dev/null
echo ok

printf "it should compile mpi_hello_world.c or mpi_hello_world.f90..."
mpicc -o mpi_hello_world mpi_hello_world.c > /dev/null
#mpif90 -o mpi_hello_world mpi_hello_world.f90 > /dev/null
echo ok

printf "it should run mpi_hello_world program successfully... "
echo
#mpirun -n 4 ./mpi_hello_world > /dev/null
mpirun -n 4 ./mpi_hello_world
echo ok
