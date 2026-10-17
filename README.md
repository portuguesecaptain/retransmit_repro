# TCP Retransmit Repro

## Or ways to ensure that one will always check MTU settings going forward

This very basic reproduction of an issue is somewhat based on a real-life production incident that happened to a customer during my time at Cockroach Labs. The incident started with getting a page on a 200+ node CRDB production cluster for a very large investment company. This cluster was THE database for the day-to-day stock trading, and the overall issue was that p99.9 latency was approaching ~150 ms. After some initial inspection to make sure hardware resource exhaustion wasn't occurring, digging into further metrics exported by the database to Prometheus showed a TCP retransmit rate of around 3-4% per node, on about 1/3 of the total nodes. These nodes are nodes that were on-prem, versus the rest of the cluster consisting of EC2 instances running in AWS.

On the Zoom, a screen share was setup and we ssh'ed into a single node that was in that 1/3 group, to start with. We went ahead and proceeded to run a `netstat` that quickly showed a fairly high number of TCP retransmits, which confirmed the issue. The customer insisted that despite running on prem, the machines were about as apples to apples as possible, so we continued to proceed to run a `tcpdump` in order to capture live packet data. The packet capture further confirmed an active rate of TCP retransmits, and some analysis showed very large TCP segments. While not definitive, comparing these retransmitted packets to those that went through on the first go, the length of the segment was generally below 1500 per frame, when compared to the retransmitted ones, which were almost always 8k.

With that in mind, I had them run a simple test with a `ping -M do -s` and then a `ping -M do -s`, to try to simulate different packet lengths, and monitor the behavior, while also enforcing MTU settings on the interfaces. We saw that the pings using 1400 packet size completed as expected, quickly. The 8192 pings did have varying bits of latency, and some even were dropped. With this bit of evidence, we checked MTUs on the interfaces confirmed that the MTU configs on the networking interfaces were different. This is the day I learned that day that AWS is setup for jumbo frames out of the box, and that their on-prem server were setup with the more traditional 1440 size MTU. We advised them of the discrepancy and they proceeded to modify everything from their side to reflect AWS configs.

In this reproduction, given the lack of hardware resources on my tiny Macbook, a more simplified version of this issue is created. Two containers are running as server and client. The client is running a Python script that creates and sends three files of 245 MiB each to the server, pausing two seconds between files. This is a light simulation of the consistent snapshot traffic that occurs in a CockroachDB cluster of that size and activity, as data is streamed from node to node, Raft memberhsoip changes and workloads are rebalanced for optimal hardware utilization across the cluster, which was automagickally done by the database. 

The server is listening, and writes the file to its own volume, as the receiving node would write the snapshot data to its Raftlog. There's significantly more complexity in the database, but the general principles and concepts are close enough for the purposes of this exercise. The server and client are also started with tcpdump installed, in order to be able to collect the packet captures, and a sample output is contained within the images of the containers in their `/test` directories respectively. The MTU was modified via the Dockerfile with a command on the client(sender), and both containers are started with a Docker compose file. The network was also created simply to ensure that no default values were going to be included, although the `CMD` hard coding should supercede that anyway.

Analysis was done on my Macbook using SSH commands (through `docker exec` shell access) as well as WireShark for packet capture analysis. To demonstrate the same troubleshooting steps, starting with the netstats to show the retransmits, leveraging another [container](https://github.com/nicolaka/netshoot) for further networking troubleshooting tools:

```
34241415b31f  ~  nstat -az TcpOutSegs TcpRetransSegs
#kernel
TcpOutSegs                      13724835           0.0
TcpRetransSegs                  9239               0.0
```

The tcpdump was copied over to my Macbook and analyzed in Wireshark, to show the lengths of the segments for each frame, as well as the retransmit times. I used the filter `tcp.analysis.retransmission` to show only frames that Wireshark believes were retransmitted. Given that everything is local, retransmits on this infra are significantly faster than anything using different datacenters and regions, where network hops become much more visible in Wireshark, and much costlier in production.

```
76949	0.761573	192.168.97.3	192.168.97.2	TCP	64770	[TCP Spurious Retransmission] 50912 → 55001 [PSH, ACK] Seq=182755713 Ack=1 Win=123 Len=64704 TSval=1099289068 TSecr=1721675732
```

The ping test utilizes the same pings as mentioned above in the real world scenario:

# Receiver:
```
  e8f98c60a2db  ~  ping -M do -s 8192 192.168.97.2

PING 192.168.97.2 (192.168.97.2) 8192(8220) bytes of data.
8192 bytes from e8f98c60a2db (192.168.97.2): icmp_seq=1 ttl=64 time=0.094 ms
8192 bytes from e8f98c60a2db (192.168.97.2): icmp_seq=2 ttl=64 time=0.173 ms
8192 bytes from e8f98c60a2db (192.168.97.2): icmp_seq=3 ttl=64 time=0.114 ms
8192 bytes from e8f98c60a2db (192.168.97.2): icmp_seq=4 ttl=64 time=0.109 ms
^C
--- 192.168.97.2 ping statistics ---
--- wiz-server-1 ping statistics ---
4 packets transmitted, 4 received, 0% packet loss, time 2027ms
```

# Sender:
```
 34241415b31f  ~  ping -M do -s 8192 192.168.97.3
PING 192.168.97.3 (192.168.97.3) 8192(8220) bytes of data.
ping: sendmsg: Message too large
ping: sendmsg: Message too large
ping: sendmsg: Message too large
ping: sendmsg: Message too large
ping: sendmsg: Message too large
ping: sendmsg: Message too large
^C
--- 192.168.97.3 ping statistics ---
6 packets transmitted, 0 received, 100% packet loss, time 24167ms
```

Finally, we can confirm the MTU settings on each container with the `ip link` command:

# Receiver:

```
e8f98c60a2db  ~  ip link
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN mode DEFAULT group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
2: eth0@if185: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1400 qdisc noqueue state UP mode DEFAULT group default
    link/ether ea:6e:2c:55:fa:bb brd ff:ff:ff:ff:ff:ff link-netnsid 0
```

# Sender:

```
 34241415b31f  ~  ip link
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN mode DEFAULT group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
2: eth0@if186: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 9001 qdisc noqueue state UP mode DEFAULT group default
    link/ether 46:d6:72:f1:42:25 brd ff:ff:ff:ff:ff:ff link-netnsid 0
```

The quickest fix to get optimal traffic for this repro is to run `docker exec wiz-client-1 ip link set eth0 mtu 1400` in order to have both containers set with a uniform MTU. For a long term, more permanent solution, the Dockerfile would need to be modified to prrevent the override from occurring. From an architectural standpoint, utilizing a script like one thats available in this [blogpost](https://oneuptime.com/blog/post/2026-03-20-test-mtu-ping-df-flag/view), to find the optimal MTU across the entire route of the connections for the use case, would be my recommendation.
