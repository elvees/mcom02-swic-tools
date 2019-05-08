ifndef TARGET_IP
$(error TARGET_IP is not set)
endif

TARGET_USER=root
TARGET_PASSWORD=root
SSH_OPTS=-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null

.PHONY: all
all: stat graph

.PHONY: stat
stat:
	sshpass -p $(TARGET_PASSWORD) ssh $(SSH_OPTS) -p 22 $(TARGET_USER)@$(TARGET_IP) 'swic-throughput.py'
	mkdir -p results
	sshpass -p $(TARGET_PASSWORD) scp $(SSH_OPTS) -P 22 $(TARGET_USER)@$(TARGET_IP):/tmp/data-test-speed.csv ./results
	sshpass -p $(TARGET_PASSWORD) scp $(SSH_OPTS) -P 22 $(TARGET_USER)@$(TARGET_IP):/tmp/data-test-mtu.csv ./results
	sshpass -p $(TARGET_PASSWORD) scp $(SSH_OPTS) -P 22 $(TARGET_USER)@$(TARGET_IP):/tmp/log.csv ./results

.PHONY: graph
graph:
	pipenv run ./swic-graphs.py test_speed
	pipenv run ./swic-graphs.py test_mtu
