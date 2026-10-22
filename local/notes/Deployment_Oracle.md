# Oracle Cloud VM — Always Free Instance Setup & Shutdown

> **Internal documentation only** — do not reference outside the files in
> `local/notes/` and commit messages.

## Creating an Always Free compute instance

OCI's Always Free tier includes the following resources in the **home region** for the life of the account:

**Compute:**
- **AMD `VM.Standard.E2.1.Micro`** (1/8th OCPU with burst capability, 1 GB RAM) — up to 2 instances
- **ARM `VM.Standard.A1.Flex`** (2 OCPUs total, 12 GB RAM total) — flexible allocation across 1–2 instances
  - Monthly free allowance: 1,500 OCPU hours + 9,000 GB hours = equivalent to 2 OCPUs and 12 GB for Always Free tenancies
  - Can allocate all resources to a single instance (e.g., 2 OCPUs, 12 GB) or split (e.g., two 1 OCPU, 6 GB instances)

**Storage:**
- **200 GB total block storage** — includes boot volumes and custom data volumes
- Minimum boot volume size is 47 GB regardless of shape (limits how many instances you can run)

**Networking:**
- **1 NAT Gateway** (free)
- **10 Mbps Load Balancer** (free)
- Public IP addresses (one per instance on `E2.1.Micro`; VNICs scale with OCPUs on `A1.Flex`)
- VCN, subnets, internet gateway, route tables, security lists — free infrastructure

**Other:**
- **5 Certificate Authorities** and **150 certificates**
- Compartment quotas for resource control

**⚠️ IMPORTANT: Choose your home region carefully at sign-up**

The home region you select when creating your tenancy is **permanent** and determines which Always Free shapes are available to you:

- **AMD `E2.1.Micro`** (1 OCPU, 1 GB) is **not Always Free in all regions** — e.g., Madrid 3 does not offer it as Always Free. If your home region lacks AMD Always Free, you cannot create AMD instances without billing.
- **ARM `A1.Flex`** (2 OCPUs, 12 GB total) is more widely available as Always Free, but availability still varies by region.

Before committing to a home region at sign-up, verify in the console (or documentation) that your preferred shapes are Always Free there. **You cannot change your home region later**, even if you delete the account and re-sign up.

**Limit:** one Always Free tenancy per email/account.

### Architecture compatibility

| Image architecture | Compatible shapes | Always Free availability |
|---|---|---|
| **ARM (`aarch64`)** | `VM.Standard.A1.Flex` (ARM) | Yes in most regions — 2 OCPUs, 12 GB total (flexible allocation) |
| **AMD/x86** | `VM.Standard.E2.1.Micro` (AMD) | **Region-dependent** — not Always Free in some regions (e.g., Madrid 3) |

**Do not mix architectures:** an AMD image cannot run on an ARM shape, and vice versa. The console will show "not compatible with the selected image" if you pair them incorrectly.

**If AMD `E2.1.Micro` is not Always Free in your home region**, your only Always Free option is ARM `A1.Flex`. Use the ARM image (`Ubuntu aarch64`) and select `A1.Flex` with 1 OCPU, 6 GB RAM.

### Region capacity

Some regions (e.g., Madrid 3, certain Availability Domains) have limited Always Free capacity. If instance creation repeatedly fails with capacity errors, options are:

1. **Try a different Availability Domain** within the same region (if the region has multiple ADs)
   - ARM `A1.Flex`: available in any AD except South Korea North (Chuncheon)
   - AMD `E2.1.Micro`: available in only one AD per region
2. **Wait and retry** — capacity may free up
3. **Switch to a region with better capacity** — but this is constrained by your tenancy:
   - **Home region** — assigned at sign-up, **permanent**. Your Always Free AMD compute (2 `E2.1.Micro` instances) is tied to this region.
   - **ARM A1.Flex** — may be available in multiple regions, but this varies by tenancy. You can create a VCN + instance in another region if ARM shapes are available there.
   - If your home region is Madrid and only AMD `E2.1.Micro` is Always Free for you, switching regions for AMD shapes is not possible without billing.

**Note:** VCNs are region-specific. If you create a VCN in a region other than your home region, the Always Free limits apply separately (subject to regional availability). If your home region has capacity issues and shapes aren't available elsewhere, you may need to:
- Wait for capacity to free up
- Accept that Always Free may not be available in your preferred region
- Consider paid compute in the alternative region (not recommended for always-free usage)

### Step-by-step creation

**Pre-creation setup**

**1. Check your tenancy home region**
- Sign in to OCI console
- Top-right → your profile → **Tenancy Details**
- Note the **Home Region** — compute and storage resources are region-specific

**2. Create a VCN (if one doesn't exist)**
- Networking → **Virtual Cloud Networks** → **Start VCN Wizard**
- Choose **"Create VCN with Internet Connectivity"** (or use the default VCN if already created)
- Accept defaults (name it e.g., `reikun-vcn` or keep `Default-VCN`)
- This creates:
  - VCN with CIDR `10.0.0.0/16`
  - Public subnet (`10.0.0.0/24`)
  - Internet gateway
  - Route table with `0.0.0.0/0` → Internet Gateway
  - Security list allowing ingress on port 22 (SSH)

**Instance creation wizard (Compute → Instances → Create Instance)**

#### Step 1. Basic Information
- **Compute Instance Name:**
  - Name your instance (e.g., `reikun-vm`).
  - Select your **Compartment** (root compartment or dedicated project compartment).
  - Verify **Placement / Availability Domain** (try alternative ADs if capacity errors occur).
- **Image selection:**
  - Choose OS image marked **Always Free Eligible** (architecture dictates compatible shapes).
  - **ARM:** `Canonical Ubuntu 24.04 / 26.04 Minimal aarch64` (recommended for flexible compute/memory).
  - **AMD/x86:** `Canonical Ubuntu 24.04 / 26.04 Minimal` (non-ARM; verify Always Free availability in your region).
  - Avoid Oracle Linux unless you specifically prefer `opc` / yum over `ubuntu` / apt.
- **Shape selection:**
  - **ARM (`aarch64`):** Select `VM.Standard.A1.Flex` → configure OCPUs and memory (e.g., 1 OCPU, 6 GB RAM or up to 2 OCPUs, 12 GB RAM for a single instance within Always Free allowance).
  - **AMD (`x86`):** Select `VM.Standard.E2.1.Micro` (fixed 1/8th OCPU burstable, 1 GB RAM — only if Always Free in your region).

**Advanced options (if visible):**

**Capacity type:**
- **On-demand capacity** — choose this for Always Free. Default, appropriate for free shapes. Your instance won't be reclaimed unless it's idle (see idle reclamation policy).
- **Preemptible capacity** — not needed for Always Free. Designed for cost savings on paid workloads; since your shape is already free, you gain nothing and introduce premature termination risk.
- **Capacity reservation** — not applicable to Always Free. Paid feature to guarantee capacity for future use.
- **Dedicated host** — not applicable to Always Free. Paid feature for compliance/licensing isolation.

**Note:** For Always Free shapes, capacity type doesn't affect cost — the shapes are free regardless. Stick with on-demand to avoid unnecessary complexity.

**Instance metadata service (IMDS):**
- Provides metadata about the instance (hostname, network, region, etc.) for bootstrapping
- **Require an authorization header** — enables IMDSv2 (requires authorization header; IMDSv1 is denied). More secure against lateral movement attacks. No cost difference.
- If enabled by default, keep it enabled. If disabled, you can leave it disabled for simplicity — only applications that use IMDS are affected.

**Initialization script (cloud-init):**
- Optional startup script that runs when the instance boots or restarts
- Can install software, apply updates, configure services
- Upload a file or paste a cloud-init script
- Useful for automation (e.g., installing Docker, cloning repos on first boot)
- Leave empty for manual setup

**Tagging:**
- Optional tags to organize resources (e.g., `Environment: dev`, `Project: reikun`)
- Not required for Always Free; helpful if you have many resources

**Availability configuration (live migration):**
- Controls how infrastructure maintenance is handled
- **Let OCI choose the best migration option** — recommended. OCI selects live migration or reboot migration as appropriate.
- **Use live migration if possible** — instance is live migrated without disruption; some shapes don't support it.
- **Send maintenance notification** — you get notified and can proactively reboot before the due date.
- **Restore instance lifecycle state after maintenance** — when enabled (default), a running instance automatically restarts after maintenance; when disabled, it stays stopped. Keep enabled for Always Free to ensure the instance stays available.

**Oracle Cloud Agent:**
- Lightweight process that manages plugins (performance metrics, OS updates, instance management)
- Enabled by default; plugins collect metrics and handle management tasks
- Can be disabled to save a tiny amount of memory (~50–100 MB), but it's negligible for 1–2 GB instances
- Recommendation: leave enabled for Always Free unless you're extremely memory-constrained

**Default plugins (selected by default):**
- **OS Management Service Agent** — handles OS updates and patching. Useful for keeping the instance patched; can be disabled if you manage updates manually.
- **Custom Logs Monitoring** — sends custom log data to OCI Monitoring. Not needed for basic workloads; can be disabled to save minimal overhead.
- **Compute instance run command** — allows running commands on the instance via OCI console. Useful for remote management; disable if you don't need this.
- **Compute instance monitoring** — collects performance metrics (CPU, memory, disk). Recommended to keep for visibility into instance health.
- **Cloud Guard workload protection** — monitors for security misconfigurations. Recommended to keep for security posture; can be disabled if not needed.

**Plugin recommendations for Always Free:**
- Keep: Compute instance monitoring (health visibility; stays within free tier limits), Cloud Guard workload protection (security; Basic tier is free)
- Optional: OS Management Service Agent (if you want automated patching; may have costs depending on usage)
- Disable: Custom Logs Monitoring (Logging service has free tier limits, but safer to disable if not needed), Compute instance run command (free, but disable if not used)

**Note on costs:** The Oracle Cloud Agent itself is free, but the services that plugins send data to have free tier limits (Monitoring: 1M data points/month, Logging: 10 GB/month, Cloud Guard Basic: free). For a single Always Free instance, you'll typically stay within limits, but disable plugins you don't use to avoid accidental overages.

#### Step 2. Security
- **Shielded instances:** Hardens firmware security using:
  - **Secure Boot:** Ensures only signed, trusted firmware and OS boot.
  - **Measured Boot:** Cryptographically measures boot components for integrity verification.
  - **Trusted Platform Module (TPM):** Hardware-based cryptographic key storage.
  - *Note:* On some shapes, these must be enabled together. Only the instance name can be changed after a shielded instance is launched.
- **Confidential computing:** Alternative to shielded instances; protects data in use via hardware-based memory encryption.
- **Security attributes (ZPR):** Up to 3 security attributes for Zero Trust Packet Routing fine-grained access control.
- **Recommendation for Always Free instances:** Leave these disabled/default for development and standard workloads to avoid unnecessary complexity.

#### Step 3. Networking
A Virtual Network Interface Card (VNIC) connects your instance to the VCN and endpoints. A public IPv4 address is required to make the instance accessible from the internet.

- **Primary VNIC & Network:**
  - **VNIC name:** Optional custom name (defaults to instance name).
  - **Primary network:** Choose **Select existing virtual cloud network** (or create new / specify OCID). Select your VCN compartment (e.g., `root`) and VCN (e.g., `reikun-vcn` or `Default-VCN`).
  - **Subnet:** Choose **Select existing subnet** (or create new public subnet). Select your public subnet (e.g., `reikun-vcn-subnet`). *Required.*
- **Private IPv4 address assignment:**
  - **Automatically assign private IPv4 address** (default; Oracle assigns the next unused address in the chosen subnet).
  - (Options for manual IP entry or existing private IPv4 OCID are also available).
- **Public IPv4 address assignment:**
  - Select **Automatically assign public IPv4 address** (required for internet/SSH access; requires a public subnet).
- **IPv6 address assignment:**
  - Optional. Requires a subnet configured and enabled for IPv6 prefixes.
- **Add SSH keys:**
  - **Upload public key file (.pub):** Upload your existing public key (e.g., `~/.ssh/id_rsa.pub`).
  - **Paste public key:** Paste an existing OpenSSH public key string.
  - **Generate a key pair for me:** OCI generates a key pair. You **must click "Download private key"** immediately (it will not be shown again).
  - **No SSH keys:** Do not use unless using cloud-init / custom credentials, or you will be locked out.

#### Step 4. Storage
- **Boot volume size:**
  - Default boot volume size is 46.6–50 GB.
  - Always Free tier includes **200 GB total block storage** across all boot and custom data volumes.
  - Set boot volume size accordingly (e.g., 50 GB to allow space for multiple instances or custom volumes, or up to 200 GB if running a single instance).
- **Volume performance:** Leave at default Balanced (10 VPUs/GB) for Always Free tier. Higher performance tiers are paid.
- **Use in-transit encryption:** Enabled by default. Encrypts data in transit between the instance, boot volume, and block volumes. No cost; keep enabled for security.
- **Encrypt this volume with a key that you manage:**
  - Default: Oracle manages the encryption keys (Oracle-managed keys). Recommended for Always Free. 
  - Optional: Choose a key from a vault you manage (customer-managed keys). Only needed if you have specific compliance or key lifecycle control requirements. This involves setting up OCI Vault and KMS, which adds complexity. Leave at default (Oracle-managed) for Always Free.
- **Encryption:** Use Oracle-managed key (default) or customer-managed Vault key if required.
- **Transit encryption:** Optional in-transit encryption for block volume attachments.

#### Step 5. Review & Launch
- **Review:**
  - Verify Shape shows Always Free eligibility (`A1.Flex` or `E2.1.Micro`).
  - Verify VCN, public subnet, public IP assignment, and SSH key configuration.
  - Verify total storage allocation fits within the 200 GB limit.
- **⚠️ Cost estimator inaccuracy:**
  - Oracle's "View estimated cost" shows pay-as-you-go pricing (e.g., €1.85–€2/month) even for Always Free eligible resources.
  - **This is a known UI quirk** — the estimator doesn't account for Always Free tier limits.
  - If your configuration is within Always Free limits (2 OCPUs, 12 GB, ≤200 GB storage), **you will NOT be charged**.
  - To verify your actual limits: Governance → Limits, Quotas and Usage → filter by Compute/Storage.
- **Common configuration issues:**
  - **No public IP assigned by default** → Change "Public IPv4 address" to "Yes" in Networking section (required for SSH; no extra cost).
  - **Boot volume size** → Keep at 50 GB (minimum viable; stays within 200 GB free tier).
- **Create:** Click **Create** to launch the instance.
- **Access the instance:**
  - Instance transitions from "Provisioning" to "Running" within 2–5 minutes.
  - Note the assigned **Public IP** address in the instance details.
  - Connect via SSH:
    ```bash
    ssh ubuntu@<public-ip>
    ```
    (or `ssh -i /path/to/private-key ubuntu@<public-ip>` if using a downloaded key pair).
- **Post-creation limits verification:**
  - Confirm shape in **Compute → Instances**.
  - Set a budget alert under **Billing → Cost Management → Budgets** (e.g., €5 threshold) to catch accidental billable overages.

### Gotchas

- **Ubuntu image has no `rsync`** by default (OCI minimal image) — install with `sudo apt update && sudo apt install rsync` if needed for ingestion workflows
- **Reserved public IPs** bill monthly — the instance gets an ephemeral IP by default (free), but if you explicitly create a reserved IP, delete it when terminating
- **Block storage** is the main hidden cost — 200 GB total is free, but boot volumes count toward this. If you create custom data volumes, keep the total under 200 GB
- **NAT Gateway** — only 1 is free per tenancy; if you create more, they bill hourly
- **Load Balancer** — only 10 Mbps is free; higher tiers bill hourly

### Choosing AMD vs ARM

- **AMD (`E2.1.Micro`)**: simpler if Always Free in your region, but 1 OCPU/1 GB is tight for embeddings/heavy Docker stacks. **Check Always Free availability** before choosing this path.
- **ARM (`A1.Flex`)**: better performance, can allocate up to 2 OCPUs/12 GB total across instances. Good for CPU-intensive work (embeddings, inference), requires ARM-compatible images (Ubuntu ARM works fine). Generally more widely available as Always Free.

### Always Free-eligible images

Only images marked "Always Free Eligible" in the Console can be used with Always Free compute without licensing fees:

**For AMD `E2.1.Micro`:**
- Oracle Linux Cloud Developer 8
- Oracle Linux
- Ubuntu
- CentOS

**For ARM `A1.Flex`:**
- Oracle Linux Cloud Developer (requires at least 8 GB memory)
- Oracle Linux
- Ubuntu

To use an image not marked Always Free-eligible, you must have a paid account or Free Trial with available credits.

### Idle instance reclamation

Oracle may reclaim idle Always Free compute instances. An instance is considered idle during a 7-day period if:
- CPU utilization (95th percentile) < 20%
- Network utilization < 20%
- Memory utilization < 20% (applies to `A1.Flex` shapes only)

To avoid reclamation, ensure the instance does some work (e.g., periodic background tasks, low-intensity monitoring).

### Availability domain restrictions

- **ARM `A1.Flex`**: Can be created in any availability domain within the home region, except South Korea North (Chuncheon)
- **AMD `E2.1.Micro`**: Can only be created in one availability domain (specific to the region)

If you get an "out of host capacity" error, try a different availability domain or wait and retry.

For Reikun's ingestion or eval workloads, ARM with 2–4 OCPUs is more practical than the single AMD micro.

## Shutdown and Cleanup

The Oracle Cloud (OCI) VM stack was superseded by the managed production stack:
- **Old:** Oracle VM → Docker + Caddy (self-hosted, name.com DNS)
- **New:** Cloud Run API + Cloudflare Workers static (reikun.app + workers.dev mirror)

The VM was retained as a frozen rollback backup after the cutover. This document
covers the complete shutdown to eliminate all recurring charges.

## What bills

| Resource | Bills when | Action to stop charges |
|---|---|---|
| **Compute instance** | Running or Stopped | Terminate (not just Stop) |
| **Boot volume** | Exists (instance stopped/terminated) | Delete (choose "Delete associated boot volume" during termination, or delete separately after) |
| **Reserved public IP** | Exists (attached to nothing) | Delete (ephemeral IPs auto-release with instance) |
| **Block volumes** (custom data) | Exists | Delete if unneeded |
| **NAT Gateway** | Exists | Delete (hourly charge) |
| **Load Balancer** | Exists | Delete (hourly charge even idle) |

## What does NOT bill (leave alone)

- **VCN, subnets, route tables, security lists, internet gateways** — Always Free infrastructure
- **Private DNS Zones / Private Views** — system-managed (`*.oraclevcn.com`, `*.in-addr.arpa`) are protected and free
- **Budgets** — free alert configurations
- **Private IP addresses** — free, tied to subnets

## Shutdown checklist (dependency order)

**1. Terminate the instance**
- Compute → Instances → select → **Terminate**
- Choose "Delete associated boot volume" if you're done with the data
- If you chose "Preserve boot volume" → Block Storage → Boot Volumes → delete separately later

**2. Delete reserved public IPs**
- Networking → Virtual Cloud Networks → each VCN → **Public IPs** tab
- Delete anything marked **"Reserved"** (ephemeral IPs are already gone)
- These continue billing even when the instance is gone

**3. Delete custom block volumes (if any)**
- Block Storage → **Block Volumes** → delete any data volumes you don't need

**4. Delete subnets (if deleting custom VCNs)**
- Networking → Virtual Cloud Networks → your VCN → **Subnets**
- Delete subnets first (they reference route tables/security lists)

**5. Delete route tables (if deleting custom VCNs)**
- Networking → Virtual Cloud Networks → your VCN → **Route Tables**
- **Key step** — remove the internet gateway rule first:
  - Edit the route table → find the `0.0.0.0/0` rule with target "Internet Gateway"
  - Delete that rule → Save
- Then delete the route table itself

**6. Delete internet gateways (if deleting custom VCNs)**
- Networking → Virtual Cloud Networks → your VCN → **Internet Gateways**
- Delete after removing the route table reference (see above)
- Blocked by circular dependency if the route table still points to it

**7. Delete custom VCNs (optional)**
- Networking → Virtual Cloud Networks → select the VCN → **Delete**
- Only delete custom VCNs you created for this stack
- Leave the default Always Free VCN (`Default-VCN`) alone — it's free and reusable

**8. NAT Gateways / Load Balancers (if any)**
- Networking → Virtual Cloud Networks → **NAT Gateways** → delete if unused
- Networking → **Load Balancers** → delete if unused

## Common blockers

### "Operation not allowed on protected resource"
- Appears on system-managed Private DNS Zones (`*.oraclevcn.com`, `*.in-addr.arpa`)
- These are OCI-auto-created and tied to the VCN lifecycle
- **Don't delete them** — they're free and protected for a reason
- If you accidentally added a lock: DNS → Private Zones → select → Locks tab → remove lock

### "Before you delete a VCN, you must delete all resources"
- OCI scans for dependent resources; the scan can take >20 minutes
- Check the "Associated resources" list — delete each manually in dependency order
- **Or** use "Force delete" after the scan if you're certain (auto-deletes dependencies)

### "The Route Table references the Internet Gateway — must remove reference"
- Circular dependency: route table has a rule pointing to IGW, IGW can't delete
- **Fix:** Edit the route table → delete the `0.0.0.0/0` rule with IGW target → Save
- Then delete the IGW, then the route table, then the VCN

### Cost Analysis shows "Compute" charges after termination
- Billing takes hours to a day to reflect termination
- If the instance is terminated and Block Storage is empty, this is the final pro-rated charge
- Check the actual € amount (not the "estimated savings" from recommendations)
- If it shows €0 for the current month, you're clean

## Verification

After cleanup:
1. Billing → **Cost Analysis** → group by "Service" → should show €0 for current month
2. Compute → **Instances** → should be empty or only show "Terminated"
3. Block Storage → **Boot Volumes** → should be empty
4. Networking → Virtual Cloud Networks → Public IPs → no "Reserved" entries
5. Set a €1 budget alert as a safety net (optional)

## Reikun-specific cleanup

The Reikun stack used:
- One VM (europe-southwest-1 or similar)
- Docker + Caddy on the VM
- Custom VCN named `reikun-public-subnet` (or similar)
- Reserved public IP for name.com A record
- No NAT Gateway or Load Balancer

Deletion path:
1. Terminate instance with "Delete associated boot volume"
2. Delete reserved public IP from the VCN
3. Edit route table → remove IGW rule
4. Delete internet gateway
5. Delete route table
6. Delete subnets
7. Delete custom VCN (`reikun-public-subnet`)
8. Leave default VCN and system DNS zones alone
