# Oracle Cloud (OCI) Networking Guide: VCN, Subnets, Gateways and Public IPs

Oct 12, 2026 · @Aniket

## Overview

On your account, the working design is one VCN with one public subnet behind an internet gateway; a NAT gateway is not available because your tenancy limit for it is 0. A private subnet is still possible, but it will have no internet access unless you upgrade or use a workaround.

The fastest path is the VCN wizard: Networking → Virtual cloud networks → Actions → Start VCN Wizard → Create VCN with Internet Connectivity. It builds the VCN, subnets, gateways, route tables and security lists in one go. The manual steps below give you full control and explain what each piece does.

&#91;embedded content: VCN layout · 2 subnets, 1 gateway, NAT unavailable\]

Only the public subnet is reachable from the internet; the dashed NAT gateway cannot be created on your limits.

| Component | What it does | Needed? |
| --- | --- | --- |
| VCN | Your private network (10.0.0.0/16) | Yes |
| Internet gateway (IGW) | Two-way internet access for public IPs | Yes, for a reachable VM |
| Public subnet | Holds VMs that have public IPs | Yes |
| Private subnet | Holds backends and databases with no public IP | Optional |
| NAT gateway | Outbound-only internet for private subnets | Not available on your limits |
| Service gateway | Private path to Oracle services (Object Storage, repos) | Optional |
| Route tables | Decide where non-local traffic goes | Yes |
| Security lists / NSGs | Allow or deny traffic by port and source | Yes |

### Limits seen on this account

| Limit | Value | Meaning |
| --- | --- | --- |
| NAT gateways per VCN | 0 | You cannot create one |
| Internet gateways per VCN | 1 | One is all you need |
| Reserved public IPs | 1 (0 used) | One fixed IP available |
| VCNs | 2 (1 used) | One more VCN available |
| Subnets, route tables, security lists per VCN | 300 each | Not a constraint |

## Step 1: Create the VCN

Go to Networking → Virtual cloud networks → Create VCN, fill the form as below, then click Create VCN.

| Field | What to enter |
| --- | --- |
| Name | Anything descriptive, for example `vcn-main` |
| Create in compartment | `Reikun (root)` works; a dedicated compartment is cleaner later |
| IPv4 CIDR block | `10.0.0.0/16` (65,536 addresses). Avoid ranges that overlap your home, office or other VCNs if you will connect them later |
| IPv6 prefixes | Leave empty unless you specifically need IPv6 |
| Use DNS hostnames in this VCN | Leave checked. This cannot be changed after creation |
| DNS label | Leave blank; it is generated from the name (for example `vcnmain`) |

A VCN is a regional resource; subnets inside it can be regional (recommended) and span all availability domains.

## Step 2: Internet gateway and route rule

A public subnet has no internet access until an internet gateway exists and the subnet's route table sends `0.0.0.0/0` to it.

### Create the internet gateway

Open the VCN → Internet Gateways → Create Internet Gateway.

| Field | What to enter |
| --- | --- |
| Name | `igw` |
| Compartment | Same as the VCN |
| Route Table Association (Advanced) | Leave blank. It is for advanced ingress routing, and once set the gateway must always keep a route table |

### Add the route rule

VCN → Route Tables → Default Route Table for your VCN → Add Route Rules.

| Field | Value |
| --- | --- |
| Target Type | Internet Gateway |
| Destination CIDR Block | `0.0.0.0/0` |
| Target Internet Gateway | `igw` |
| Description (optional) | `Default route to internet` |

Ignore the banner about Private IP and Skip Source/Destination Check; it applies only when the target type is Private IP (the NAT-instance workaround below).

If the target dropdown is empty, wait until the gateway state is Available and check that the compartment field matches the gateway's compartment.

## Step 3: Create the subnets

Open the VCN → Subnets → Create Subnet. The Create Subnet dialog can only select existing route tables, not create them, so create any custom route table first.

| Setting | Public subnet | Private subnet (optional) |
| --- | --- | --- |
| Name | `public-subnet` | `private-subnet` |
| Type | Regional | Regional |
| IPv4 CIDR | `10.0.0.0/24` | `10.0.1.0/24` |
| Route table | Default (has the `igw` rule) | A table with no internet route (see Step 4) |
| Subnet access | Public subnet | Private subnet |
| Security list | Default | Default or a dedicated one |
| DNS hostnames | Leave as default | Leave as default |

To change a subnet's route table later: open the subnet → Edit → Route Table. If a table is missing from the dropdown, it is in a different compartment than the one selected.

## Step 4: NAT gateway and private routing

A NAT gateway lets instances without public IPs start outbound connections (package updates, image pulls, API calls) while the internet cannot start connections to them. On your account you cannot create one, because the limit is 0, so read this section for the concept and the workarounds.

### Why a separate route table

Each subnet uses exactly one route table, and one table cannot send `0.0.0.0/0` to two targets. The public subnet needs `0.0.0.0/0` → internet gateway; a private subnet that needs outbound access needs `0.0.0.0/0` → NAT gateway. Keep the Default Route Table for the public subnet and create a custom table for the private one.

### How it is done when NAT is available

1. VCN → NAT Gateways → Create NAT Gateway: name `nat-gw`, same compartment as the VCN, public IP **Ephemeral** (choose Reserved only if a third party must whitelist a fixed outbound IP). Leave Route Table Association blank.
2. VCN → Route Tables → Create Route Table: name `private-rt`, rule Target Type **NAT Gateway**, Destination `0.0.0.0/0`, Target `nat-gw`.
3. Create or edit the private subnet and select `private-rt`.

The NAT gateway must exist before it can be picked as a route target, and the route table must exist before the subnet can select it.

### The error "NAT gateway limit per VCN reached"

This means the tenancy limit `nat-gateway-count` is 0, which is typical for Always Free accounts. Confirm it under Governance & Administration → Limits, Quotas and Usage → Service: Virtual Cloud Network, with Scope set to your region rather than Tenancy. Your account shows NAT Gateways (per VCN) = 0.

| Option | How | Trade-off |
| --- | --- | --- |
| Single public subnet (recommended here) | Put VMs in the public subnet with a public IP; restrict ports with security rules | Simple; every VM is exposed, so keep rules tight |
| Private subnet with no internet route | Databases reachable only from your web VM inside the VCN | No internet, no updates |
| Service gateway | Private subnet reaches Oracle services (Object Storage, OS repositories) | Oracle services only, not the general internet |
| NAT instance | Small VM in the public subnet with IP forwarding and masquerading; route `private-rt` to its private IP (target type Private IP) | You maintain it; single point of failure. Enable Skip Source/Destination Check on its VNIC |
| Upgrade to Pay As You Go | Billing → Upgrade; limits usually rise afterwards | Needs a card; Always Free resources stay free, and OCI does not charge for NAT gateways themselves |

## Step 5: Security rules

Security lists apply to every VNIC in a subnet; network security groups (NSGs) apply only to the VNICs you add to them. Either works. Rules are stateful by default, so replies to allowed traffic come back automatically; leave Stateless unchecked.

### The default security list

| Rule | Source | Protocol | Port / type | Keep? |
| --- | --- | --- | --- | --- |
| SSH | `0.0.0.0/0` | TCP | 22 | Works, but tighten it (below) |
| Path MTU discovery | `0.0.0.0/0` | ICMP | type 3, code 4 | Yes |
| Destination unreachable | `10.0.0.0/16` | ICMP | type 3 | Yes |
| Egress | all | all | all | Yes, lets instances make outbound connections |

### Tighten and extend

- **SSH:** edit the rule so the source is your own IP as `x.x.x.x/32`. Update it if your home IP changes. Port 22 open to the world gets constant bot attempts.
- **Web server:** add ingress rules with source `0.0.0.0/0`, protocol TCP, destination port `80` and `443`; leave Source Port Range empty.
- **Database in a private subnet:** allow its port (for example 3306 or 5432) only from the public subnet's CIDR `10.0.0.0/24`, never from `0.0.0.0/0`.
- **On the VM:** keep the Linux firewall (ufw or firewalld) as a second layer. Oracle images ship with restrictive iptables rules, so a port open in the security list can still be blocked on the instance.

## Step 6: Public IPs

A public IP is attached to an instance's network interface (VNIC), not to the subnet, the internet gateway or the NAT gateway. The subnet's Public setting only controls whether public IPs are allowed there, and a NAT gateway's IP is used only for outbound traffic from private subnets.

| Type | How | Lifetime |
| --- | --- | --- |
| Ephemeral | At instance creation, tick **Automatically assign public IPv4 address** | Released when the instance is terminated |
| Reserved | Networking → IP Management → Reserved Public IPs → Reserve Public IP Address, then attach it to the VNIC | Yours until you delete it; can move between instances |

### Attach a reserved IP to an instance

1. Reserve the IP (name it, for example `vm-ip`). Your account allows one.
2. Open the instance → Attached VNICs → the primary VNIC → IPv4 Addresses.
3. On the private IP, choose Edit and set Public IP type to **Reserved public IP**, then pick `vm-ip`.

If the instance already has an ephemeral IP, first edit the private IP and choose **No public IP**, save, then edit again and attach the reserved one. Oracle does not swap them in one step.

## Step 7: Launch an instance and connect

Compute → Instances → Create instance.

1. **Image and shape:** pick an image (Ubuntu or Oracle Linux) and a shape. Always Free offers a small AMD shape and Arm (Ampere A1) shapes; Oracle publishes the exact free allowances, so check its current Always Free page. A1 capacity is often short, and "Out of host capacity" errors are common.
2. **Networking:** select your VCN and `public-subnet`, and tick **Automatically assign public IPv4 address**.
3. **SSH keys:** let Oracle generate a key pair and download the private key, or paste your own public key.
4. Create the instance and wait for the state *Running*.
5. Connect, using `ubuntu` for Ubuntu images or `opc` for Oracle Linux:

```bash
chmod 400 ~/Downloads/ssh-key.key
ssh -i ~/Downloads/ssh-key.key ubuntu@<public_ip>
```

Before relying on a free instance, check Oracle's policy on idle Always Free instances, which can be reclaimed if usage stays very low.

## Troubleshooting and checklist

If SSH times out, work down this list in order; the first three cause most failures.

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| SSH times out | No `0.0.0.0/0` → `igw` route on the subnet's route table | Add the rule (Step 2) |
| SSH times out | Instance has no public IP | Attach one (Step 6) |
| SSH times out | Security list does not allow your IP on port 22 | Edit the ingress rule (Step 5) |
| Port open in security list but unreachable | Firewall on the VM blocks it | Open it in ufw, firewalld or iptables |
| Permission denied (publickey) | Wrong user or key | `ubuntu` or `opc`; run `chmod 400` on the key |
| NAT gateway limit per VCN reached | Limit is 0 on this account | Use a public subnet or upgrade (Step 4) |
| Route table missing from subnet dropdown | Different compartment | Match the compartment fields |
| Internet gateway target empty | Gateway still provisioning or in another compartment | Wait for Available; check compartment |

### Build checklist

- [ ] VCN `10.0.0.0/16` created with DNS hostnames on
- [ ] Internet gateway `igw` created, Route Table Association blank
- [ ] Default route table has `0.0.0.0/0` → `igw`
- [ ] `public-subnet` (10.0.0.0/24, Public) created
- [ ] Optional `private-subnet` (10.0.1.0/24, Private) with no internet route
- [ ] SSH rule limited to your IP as `/32`
- [ ] Instance launched in the public subnet with a public IP
- [ ] Optional reserved public IP attached
- [ ] VM firewall and OS updates in place
