# Contract Negotiation and Data Transfer between Omega-X and Data Cellar

This repository contains configuration files and scripts to deploy two demo EDC connectors:

* A Sovity v11.0 connector (based on EDC v0.7) that represents the Omega-X data space
* An EDC v0.6 connector that represents Data Cellar

## User Guide

To deploy both connectors, generate the required certificates, and start all companion services, run:

```
task deploy
```

Once the containers are up and running, access the Omega-X provider connector's Web UI at `http://localhost:11000`. Click on _Create Data Offer_ to create a new offer. The offer will automatically be linked to an _always true_ policy, which is what we want for this demo. Make sure to set the asset ID to `my-asset`.

Next, run the following script to consume the created asset from Data Cellar's connector using the _Provider Push_ data transfer type:

```
task run-script
```