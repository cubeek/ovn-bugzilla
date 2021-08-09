# ovn-bugzilla

This repository contains code to monitor trends in Bugzilla for OVN project under OpenStack Red Hat Product.

# Command examples

### Using --speed to get the BZs completion speed (in days)

```
$ python3 bug-trends.py -k BZ_API_KEY -v 16.1 --speed -r z1 --squad OVN
```

This will return two tables, one with the *average* number of days that a bug
spent on going from NEW (date of creation) to that STATE.

The second table is a helper to understand the values, as it shows a **count of
bugs** that went through that stage. The justification for this is that not
every bug needs to go through every stage, so the average might be less 
significant for some states than others.


```
[Output]

Bug Speed (Days)
+--------------+----------+---------+--------+------+----------+-------+----------+-----------------+--------+
| Prio | State | assigned | triaged | on_dev | post | modified | on_qa | verified | release_pending | closed |
+--------------+----------+---------+--------+------+----------+-------+----------+-----------------+--------+
|  unspecified  |    0     |    2    |   0    |   0  |    80    |   13  |     0    |         0       |    1   |
|    urgent    |    13    |    9    |   9    |  22  |   108    |  110  |   124    |       244       |  221   |
|     high     |    11    |   69    |   7    | 127  |   215    |   93  |    21    |       426       |  380   |
|    medium    |    29    |   14    |  12    |  89  |   100    |  150  |   200    |       300       |  204   |
|     low      |    91    |    4    |   0    |   0  |     0    |    0  |     0    |         0       |    0   |
+--------------+----------+---------+--------+------+----------+-------+----------+-----------------+--------+
Bugs with states (Bug Count)
+--------------+----------+---------+--------+------+----------+-------+----------+-----------------+--------+
| Prio | State | assigned | triaged | on_dev | post | modified | on_qa | verified | release_pending | closed |
+--------------+----------+---------+--------+------+----------+-------+----------+-----------------+--------+
|  unspecified  |    0     |    1    |   0    |  0   |    1     |   1   |    0     |        0        |   1    |
|    urgent    |    2     |    5    |   2    |  2   |    1     |   5   |    5     |        4        |  12    |
|     high     |    6     |    7    |   5    |  5   |    2     |   7   |    7     |        7        |   8    |
|    medium    |    2     |    3    |   2    |  1   |    3     |   3   |    4     |        2        |   4    |
|     low      |    3     |    2    |   0    |  0   |    0     |   0   |    0     |        0        |   1    |
+--------------+----------+---------+--------+------+----------+-------+----------+-----------------+--------+
```
