The scripts and codes here provide a simple example for running a MPI app in Docker

To build the mpi image in linux environment, type:
docker build -t 127.0.0.1:5000/my_mpi ./mpich

To run the test, type:
docker run --rm -it --name mpi_test 127.0.0.1:5000/my_mpi
or
docker run --rm -it -v /var/run/docker.sock:/var/run/docker.sock --name mpi_test 127.0.0.1:5000/my_mpi
