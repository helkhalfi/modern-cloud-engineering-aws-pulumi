import pulumi
from pulumi_aws import ec2

group = ec2.SecurityGroup('web-secgrp', ingress=[
    { "protocol": "tcp", "from_port": 80, "to_port": 80, "cidr_blocks": ["0.0.0.0/0"] },
    # uncomment to have the test to pass.
    #{ "protocol": "tcp", "from_port": 443, "to_port": 443, "cidr_blocks": ["0.0.0.0/0"] },

])
