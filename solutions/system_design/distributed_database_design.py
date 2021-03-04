"""
Distributed database design ( key value )
-----------------------------------------
Note : This derived from the youtube video tutorial from Tushar roy.

talking points:
1. characteristics
2. basic operations
3. overall architecture
4. Metadata Manager
5. Replication
6. Data Plane
7. control plane
8. Edge cases
9. scale numbers


1. characteristics:
    durability : If we loose data there will be no business
    Availability
    Performance

    consistency model : This design is Strongly consistent;
    Read after most recent write always gets the most recent write
    no ACID : NOT (all no none); no locking ;

2. basic operations
    create table
    put (table,key,value)
    get(table,key) -> value
    Delete (table,key)
    List (Keys in tabel in sorted order)
    Delete Table (optional)

    sequencer : timestamp in nanosecond + unique per node +unique_node_id
                (8 byte)                  (4 byte)          (4 byte)      = 16 byte = 2^32bit = 4 billion

    table :

    stocks
    ---------------------------
    | Name | Price | sequence |
    ----------------------------
    |      |       |          |
       A      120      seq2
       B      100      seq1
       C      135      seq3

    why we need sequencer ?
    put (D,140)
    put (D,160)
    someone might put same thing at same time. when reconciliation happens sequencer is used.

3. Overall Architecture

    a. Load balancer (LB) : sends request to Request Manager(RM)

    b. Request Manager (RM) : consults with Metadata Manager (MM) and sends req. to speficic replication group.
                        who is owner of specific part of table, as guided by Metadata Manager.

    c. controller / control plane: keep an eye in Replication Group (RG). If they become too hot,
            it starts splitting table into small tables and distributes it to multiple Replication Group.
            deals with,
            - leader management
            - follower falling behind
            - split hot tables


                    <heart beat>
        [leader] ----------------->  Metadata
        [follower1] ------------>     Manager
                [Follower2]---->
        [replication group ]

        heartbeat based leader election ;two problems
            old leader could still be alive but new leader is elected
            replication group unavailable for split seconds ==> consistancy preferred

            followers starts falling behind the leader ( no sync with leader; malfunctioning hardware)

            [controller] takes from pool of available node and swap with falling behind node and update
            metadata manager.

            hot table ==> growing really big in size or I/0 number high. controller monitors the table size.
                    which table is growing in replication group 1.

                    controller figure out what point tosplit the table, eg. 30% . controller decides.

                    create new replication group if already not there. tell them to be prepared to take part
                    of stocks table. update metadata mgr not to make call for

                    [A-C] => repgr2
                    stocks[c-Q]=>repgr1

                    request mgr eventually will know and respond accordingly for get and put requests.
                    but it will take certain interval of time.

                    that time interval Fix => if get request comes during hot data transfer , metadata mgr
                    needs to guide for DUAL REQUEST and get data from both repgroup and return data back to
                    requester, if same data in both pick one with highest sequence number.
                    merge data and send to client.


                    once completely copied the data then ; special marker in range [A-C] can be removed in
                    metadata manager and BAU can happen.



    d. replication group :
        odd count replication group (3,5,7 etc)
        3 node : 1 leader 2 follower
        to apply put make sure you can get confirmation from two nodes ( ie. majority)
        every request goes though the leader (gives system consistency )




    e. metadata manager :
            leader election in replication group
            keep mapping of table part to replication group
            eg. stock [A-C] => replication group 1
                stock [C-L] => replication group 2
                stock [L-q] => replication group 3
                ...
            application like zookeeper, etcd or redis
            (or custom implement paxos , raft algorithms)

            data not always consistent because of network split
            keep all data 'In Memory' of request manager
            backup frequently metadata manager


    f. controller :

    g. leader :

    h. node : two parts. a. append log or data to hard drive
                            put comes -> append to append only log
                          b. b+tree or LSM tree for indexing

        put -> leader -> apply to append only log -> send to follower ->
        -->one follower responds OK--> send back response to user

    Problem : two leader/split leader

    i. Table :
        table 1: big table : part1 and part 2  [repgr1 and   repgr2]
        table 2:    repgr1
        table 3:    repgr1
        table 4:    repgr2

Operations:

stock[A-L] --> RG1
stock[L-Q] --> RG2

RG1 --> a,b,c
RG2 --> d,e,f


put (Stock,G,100)
put (Stock, Y, 100)
get(stock,Y)
list(Stocks)


lb --> RM , generates sequencer--> Metamgr -->RG1-->leader of RG1(a) , put (g,100),
        'a' would apply data to append only log and b+tree , pass it to followers --->  end (g,100) to b,c
        ----> get response from either b or c and respond back to user.


8. Errors and edge cases:

- split brain (two leader) : make new leader talk to majority nodes and get enough votes to remain leader
- No leader : (for a second or two) ; availability problem ; but we are planning for durability;
                be more agressive in seconds ; eg. if no leader in milliseconds then pick new leader.


- Network split at metadata manager (mm)
- outdated table metadata
        => network split within metadata mgr (2 vs 3 in total 5).
        mm2 has info 1 but not mm2.  mm2 can direct RM to wrong replicationgroup, in that case
        replicationgroup will talk back to RM you are consulting with wrong mm or outdated table.
        then RM can correct itself to connect to majority /leader of mm.

- node goes down before updating B+tree or LSM tree ==> replay from the append only log; data is flushed to HD
- bad request manager ==> Incorrect metaddata info, it is ok. replication group will reject request, and notify back
- bad replication group node ==> majority holds is fine, one fails is good
- multiple node failure ==> availability problem, have 5 node replication group instead of 3.

9. Scale numbers : (How much data our database can handle)

    replication group capacity = 5 TB per node

    1000 replication group = 5 pb

    limit on key/value = 1MB
    overhead = 30 bytes

    I/O => 2000 req per sec per replication group.

    metadata overhead per replication group = 30 bytes
    metadata overhead per table = 30 bytes
    RAM on request manager = 16 GB , 4gb metadata

    Architecture
    -------------------
    load balancer

    [Request Manager] [Request Manager] [R..M..]


    [Replication group 1]  [Replication group 2]


"""
