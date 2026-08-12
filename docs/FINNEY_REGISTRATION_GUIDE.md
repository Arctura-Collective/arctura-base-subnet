# Arctura Base Subnet: Finney Registration & AWS Deployment Guide

**Prepared by:** Manus AI (World-Class Bittensor Expert)  
**Parent Project:** [Arctura Network](https://arctura.network) | [arctura.network/base](https://arctura.network/base/)  
**Repository:** [github.com/bittensaur/arctura-base-subnet](https://github.com/bittensaur/arctura-base-subnet)  

---

## 1. Bittensor Finney Registration & Burn Cost Requirements

To launch a new subnet on Bittensor Finney mainnet, operators must navigate dynamic economic parameters governed by supply, demand, and block-based decay curves [3].

### Subnet Slot Creation (`btcli subnet create`)
- **Mechanism:** Registering a brand-new subnet requires locking/burning TAO via the owner coldkey [11] [12]. 
- **Burn Cost Dynamics:** The cost is dynamic and floats based on network demand [15]. When slots are congested, registration costs rise significantly (historically ranging from 200 to over 1,500+ TAO) [6] [4]. The cost halves over a half-life block decay curve if demand subsides [3].
- **Live Check Command:** Always verify the live burn cost within 30 minutes of executing registration:
  ```bash
  btcli subnet burn_cost --subtensor.network finney
  ```
- **Capital Buffer Rule:** Ensure your owner coldkey holds the current burn cost **plus a 20% safety buffer**, alongside sufficient TAO for neuron `recycle_register` fees for your validators and miners [15].

### Neuron Registration (`btcli subnet recycle_register`)
- Once the owner creates the subnet and obtains a unique `netuid`, validators and miners must register their hotkeys to the subnet using the recycle registration command [29] [62]:
  ```bash
  btcli subnet recycle_register --netuid N --wallet.name validator --subtensor.network finney
  btcli subnet recycle_register --netuid N --wallet.name miner --subtensor.network finney
  ```

---

## 2. Automated AWS Deployment & Docker Compose Setup

To eliminate manual configuration errors and ensure 24/7 reliability, the repository now includes a complete Docker Compose setup and automated AWS initialization script.

### A. AWS Instance Provisioning
1. Launch an Ubuntu 24.04 LTS EC2 instance (`c6i.2xlarge` for validators, `c6i.xlarge` for miners).
2. Attach an **Elastic IP (EIP)** to guarantee a permanent static public IP.
3. Configure your AWS Security Group:
   - Inbound TCP `22` (SSH)
   - Inbound TCP `8091` (Miner Axon)
   - Inbound TCP `8092` (Validator Axon)
   - Outbound TCP `30333` (Bittensor P2P)

### B. Automated Deployment Script
SSH into your AWS instance and run the deployment script:
```bash
git clone https://github.com/bittensaur/arctura-base-subnet.git
cd arctura-base-subnet
bash scripts/deploy_aws.sh
```

### C. Docker Compose Configuration (`docker-compose.yml`)
The repository includes a production-ready `docker-compose.yml` file that orchestrates both validator and miner containers with auto-restart policies:

```yaml
version: '3.8'

services:
  validator:
    build: .
    container_name: arctura-validator
    restart: always
    environment:
      - NETWORK=finney
      - NETUID=${NETUID}
      - WALLET_NAME=validator
      - WALLET_HOTKEY=default
      - BASE_RPC_URL=${BASE_RPC_URL}
      - LOGGING_LEVEL=info
    ports:
      - "8092:8092"
    command: >
      python neurons/validator.py
        --wallet.name validator
        --wallet.hotkey default
        --subtensor.network finney
        --netuid ${NETUID}
        --logging.info

  miner:
    build: .
    container_name: arctura-miner
    restart: always
    environment:
      - NETWORK=finney
      - NETUID=${NETUID}
      - WALLET_NAME=miner
      - WALLET_HOTKEY=default
      - BASE_RPC_URL=${BASE_RPC_URL}
      - CDP_API_KEY_NAME=${CDP_API_KEY_NAME}
      - CDP_API_KEY_PRIVATE_KEY=${CDP_API_KEY_PRIVATE_KEY}
      - LOGGING_LEVEL=info
    ports:
      - "8091:8091"
    command: >
      python neurons/miner.py
        --wallet.name miner
        --wallet.hotkey default
        --subtensor.network finney
        --netuid ${NETUID}
        --axon.port 8091
        --logging.info
```

### D. Launching the Subnet Stack
1. Populate your `.env` file with your live `NETUID`, `BASE_RPC_URL`, and wallet credentials.
2. Spin up the containers in detached mode:
   ```bash
   docker compose up -d --build
   ```
3. Monitor live logs:
   ```bash
   docker compose logs -f
   ```

---

## References

- [Bittensor Documentation](https://www.bittensor.com/docs) [11]
- [Taostats Subnet Explorer](https://taostats.io/subnets) [2]
- [Base Documentation](https://docs.base.org) [284]
