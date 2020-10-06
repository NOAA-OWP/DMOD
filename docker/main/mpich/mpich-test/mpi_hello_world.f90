program main

  use mpi

  integer ( kind = 4 ) error
  integer ( kind = 4 ) id
  integer ( kind = 4 ) p
  real ( kind = 8 ) wtime
!
!  Initialize MPI.
!
  call MPI_Init ( error )
!
!  Get the number of processes.
!
  call MPI_Comm_size ( MPI_COMM_WORLD, p, error )
!
!  Get the individual process ID.
!
  call MPI_Comm_rank ( MPI_COMM_WORLD, id, error )
!
!  Print a message.
!
  if ( id == 0 ) then

    wtime = MPI_Wtime ( )

!    call timestamp ( )
    write ( *, '(a)' ) ''
    write ( *, '(a,i1,2x,a)' ) 'P', id, 'HELLO_MPI - Master process:'
    write ( *, '(a,i1,2x,a)' ) 'P', id, '  FORTRAN90/MPI version'
    write ( *, '(a,i1,2x,a)' ) 'P', id, '  An MPI test program.'
    write ( *, '(a,i1,2x,a,i8)' ) 'P', id, '  The number of MPI processes is ', p

  end if
!
!  Every MPI process will print this message.
!
  write ( *, '(a,i1,2x,a)' ) 'P', id, '"Hello, world!"'

  if ( id == 0 ) then

    write ( *, '(a)' ) ''
    write ( *, '(a,i1,2x,a)' ) 'P', id, 'HELLO_MPI - Master process:'
    write ( *, '(a,i1,2x,a)' ) 'P', id, '  Normal end of execution: "Goodbye, world!".'

    wtime = MPI_Wtime ( ) - wtime
    write ( *, '(a)' ) ''
    write ( *, '(a,i1,2x,a,g14.6,a)' ) &
      'P', id, '  Elapsed wall clock time = ', wtime, ' seconds.'

  end if
!
!  Shut down MPI.
!
  call MPI_Finalize ( error )
!
!  Terminate.
!
  if ( id == 0 ) then
    write ( *, '(a)' ) ''
    write ( *, '(a,i1,2x,a)' ) 'P', id, 'HELLO_MPI - Master process:'
    write ( *, '(a,i1,2x,a)' ) 'P', id, '  Normal end of execution.'
    write ( *, '(a)' ) ''
!    call timestamp ( )
  end if

  stop
end
