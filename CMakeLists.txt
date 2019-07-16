cmake_minimum_required(VERSION 3.1)

project(SWICxfer C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED TRUE)

add_executable(swic-xfer swic-xfer.c)

install(TARGETS swic-xfer DESTINATION bin)
install(PROGRAMS swic-loopback-test.py DESTINATION bin)
install(PROGRAMS swic-max-speed.sh DESTINATION bin)
