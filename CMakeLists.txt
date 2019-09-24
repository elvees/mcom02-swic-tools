cmake_minimum_required(VERSION 3.1)

project(SWICxfer C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED TRUE)

add_executable(swic-xfer swic-xfer.c)
add_executable(swic swic.c)

install(TARGETS swic-xfer
                swic
        DESTINATION bin)
install(PROGRAMS swic-loopback-test.py DESTINATION bin)
install(PROGRAMS swic-max-speed.sh DESTINATION bin)
install(FILES spacewire-video-receive.service
              spacewire-video-transmit.service
        DESTINATION lib/systemd/system)
